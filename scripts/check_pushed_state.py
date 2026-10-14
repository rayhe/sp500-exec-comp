#!/usr/bin/env python3
"""Regression guard: the previous commit must be fully pushed (89th).

Failure-mode class: silent-push-failure / commit-without-push.

A run commits, then pushes master:master + master:main so GitHub Pages
rebuilds. If the push FAILS - egress proxy reset, PAT auth rejection, a
`git push ... | tail` masking the exit code (the pipefail hazard in the
run's AGENTS.md notes), or a partial push updating one ref but not the
other - the commit still lands in the iteration log as "pushed ... deploy
healthy" only if the run author eyeballs the push output correctly. Every
SUBSEQUENT commit then goes green on all 88 existing guards while the live
site lags further behind: check_remote_branch_sync.py only asserts
origin/main == origin/master (remote-vs-remote), never local-vs-remote,
and check_live_deploy_currency.py pins the deploy to the LOCAL tree's
fingerprint, so it would eventually report staleness on the shipped
commit - but nothing blocks the widening gap at its source. The only
tripwire on the push itself is the run author's eyeball on the push
output, the same hand-convention pattern the 82nd guard closed for
log-prose numbers, the 86th for staged secrets, the 87th for git
identity, and the 88th for the add-A sweep.

This guard closes it fail-closed at commit time: the pre-commit hook runs
BEFORE the new commit exists, so HEAD is the previous commit. If HEAD is
not the tip of BOTH origin/master and origin/main, the commit is blocked
loudly - HARD FAIL naming the lagging ref(s), their hashes, and HEAD -
forcing the operator to finish the failed push before stacking more
commits on top of a gap nobody can see from the live site.

Checks (all static - one `git ls-remote origin` call, ~1s):
  S1 origin reachable and both refs resolvable (ls-remote failure ->
     exit 2 INFRA advisory, not a commit blocker, mirroring
     check_remote_branch_sync.py; a network outage must not wedge commits)
  S2 origin/master == HEAD
  S3 origin/main == HEAD
     (either mismatch -> HARD FAIL naming the ref, its hash, and HEAD,
     plus the remediation: push the lagging ref(s) before committing)

Usage:
  scripts/check_pushed_state.py
  scripts/check_pushed_state.py --static-only
  scripts/check_pushed_state.py --repo PATH   # fixture repos (negative tests)

Exit: 0 = previous commit fully pushed; 1 = push gap (loud);
      2 = git/origin unreachable (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-14 06:00 - created (06:00 PT iteration). Closes the
    silent-push-failure / commit-without-push class: the push step after
    every commit had only the run author's eyeball on the push output as
    tripwire (a `| tail`-masked failure, a proxy-reset, or a partial
    master-but-not-main push); every guard green on subsequent commits
    while the live Pages site fell behind. No existing guard asserted
    local-vs-remote (the 84th asserts remote/main == remote/master;
    the deploy-currency guard reports staleness on the shipped tree).
"""
import subprocess
import sys

LS_REMOTE_TIMEOUT = 60

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _git(repo, *args, timeout=30):
    """Return (rc, stdout_str, stderr_str) of a git invocation.

    rc None means git itself could not be invoked or timed out (infra),
    distinct from a git-level failure (nonzero rc with stderr).
    """
    try:
        p = subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, timeout=timeout, text=True)
    except (OSError, subprocess.TimeoutExpired) as e:
        return (None, "", "git invocation failed: %s" % e)
    return (p.returncode, p.stdout or "", (p.stderr or "").strip())


def main(argv):
    repo = "."
    args = list(argv)
    if "--repo" in args:
        i = args.index("--repo")
        if i + 1 < len(args):
            repo = args[i + 1]

    # HEAD first: it is the previous commit at pre-commit time (the new
    # commit does not exist yet), i.e. exactly the commit the last run
    # should have pushed.
    rc, head, err = _git(repo, "rev-parse", "HEAD")
    if rc is None or rc != 0:
        print("INFRA: pushed-state: cannot resolve HEAD (%s) - no push "
              "verdict possible (advisory only)" % (err or rc))
        return 2
    head = head.strip()

    # S1: origin must be reachable and carry both refs. A failed
    # ls-remote is INFRA per the pre-commit contract (mirrors
    # check_remote_branch_sync.py), never a commit blocker.
    rc, out, err = _git(repo, "ls-remote", "origin",
                        "refs/heads/master", "refs/heads/main",
                        timeout=LS_REMOTE_TIMEOUT)
    if rc is None:
        print("INFRA: pushed-state: git ls-remote could not run (%s) - "
              "advisory only" % err)
        return 2
    if rc != 0:
        print("INFRA: pushed-state: git ls-remote origin failed (rc %d%s) "
              "- advisory only" % (rc, (": " + err) if err else ""))
        return 2
    refs = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            refs[parts[1]] = parts[0]
    missing = [r for r in ("refs/heads/master", "refs/heads/main")
               if r not in refs]
    if missing:
        print("INFRA: pushed-state: origin lacks %s - cannot verify push "
              "completeness (advisory only)" % ", ".join(missing))
        return 2
    check("S1 origin refs resolvable", True,
          "master=%s main=%s" % (refs["refs/heads/master"][:7],
                                 refs["refs/heads/main"][:7]))

    # S2/S3: both remote tips must be exactly HEAD. A mismatch means the
    # last run's push never completed (or completed only partially) -
    # loud HARD FAIL, because stacking this commit widens the live-site
    # gap that no other guard would block.
    lag = []
    for ref in ("refs/heads/master", "refs/heads/main"):
        tip = refs[ref]
        short = ref.split("/")[-1]
        if tip != head:
            lag.append((short, tip))
    for short, tip in lag:
        print("FAIL: pushed-state: origin/%s is %s but local HEAD is %s - "
              "the previous commit was never fully pushed; push the "
              "lagging ref(s) (git push origin master:master master:main) "
              "BEFORE committing, or the live Pages site falls behind with "
              "every guard green" % (short, tip, head))
    if lag:
        return 1
    check("S2 origin/master == HEAD", True, head[:7])
    check("S3 origin/main == HEAD", True, head[:7])
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
