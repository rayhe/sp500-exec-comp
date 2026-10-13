#!/usr/bin/env python3
"""Regression guard: origin/main and origin/master must carry the same commit.

Every iteration run pushes local master to BOTH remote branches
(`git push origin master:master master:main`) by convention, so the live
GitHub Pages site and the mirror branch never diverge. A partial push -
one ref updated, the other rejected or forgotten - leaves origin/main !=
origin/master with nothing at commit time noticing: the run's post-push
ls-remote eyeball check is the only tripwire, and a skipped or misread
check lets the desync ride until the site serves a stale tree or the two
branches diverge far enough that the next push no longer fast-forwards.

Until now nothing asserted the sync, so the class could recur silently -
the last remaining hand-synced pair named in the iteration log
(2026-10-12/13 runs: "master/main branch sync (no guard; runs push both
by convention)").

This guard asserts the invariant itself, fail-closed at commit time: if a
previous run left the branches desynced, the NEXT commit is blocked until
the operator re-syncs them. The guard checks the state the last push left
behind (origin/main vs origin/master); it does not compare against local
master, which is legitimately ahead at commit time.

Checks (all static - one git ls-remote, ~1s):
  S1 git ls-remote origin refs/heads/main refs/heads/master succeeds
     (missing git binary, timeout, or network failure -> exit 2 INFRA
     advisory, not a commit blocker, per the pre-commit contract; a
     broken laptop must not wedge every commit)
  S2 both refs resolve on origin
     (a missing ref is a real desync, not infra -> HARD FAIL)
  S3 the two SHAs are identical
     (mismatch = HARD FAIL: loud message naming both SHAs and the
     re-sync push; verify which branch is authoritative before pushing)

Usage:
  scripts/check_remote_branch_sync.py              # same checks
  scripts/check_remote_branch_sync.py --static-only # same checks

Exit: 0 = in sync; 1 = desynced or a ref missing (loud);
      2 = ls-remote itself failed (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 06:00 - created (06:00 PT iteration). Closes the
    remote-branch desync class; the last hand-synced pair without a guard.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LS_REMOTE_TIMEOUT = 25  # seconds; keeps the pre-commit fast path <2s typical

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _ls_remote():
    """Return (ok, {ref: sha}) or (False, reason). Never raises."""
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "origin",
             "refs/heads/main", "refs/heads/master"],
            cwd=REPO, capture_output=True, text=True,
            timeout=LS_REMOTE_TIMEOUT,
        )
    except FileNotFoundError:
        return False, "git binary not found"
    except subprocess.TimeoutExpired:
        return False, "git ls-remote timed out after %ds" % LS_REMOTE_TIMEOUT
    except OSError as e:
        return False, "could not spawn git: %s" % e
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return False, "git ls-remote failed (rc %d)%s" % (
            proc.returncode, (": " + err[-1]) if err else "")
    refs = {}
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) == 2:
            refs[parts[1]] = parts[0]
    return True, refs


def static_checks():
    ok, refs_or_reason = _ls_remote()
    if not ok:
        print("INFRA: " + refs_or_reason + " - not blocking the commit")
        return 2
    refs = refs_or_reason
    check("S1 git ls-remote origin reached both branch refs", True)
    main_sha = refs.get("refs/heads/main")
    master_sha = refs.get("refs/heads/master")
    both = main_sha is not None and master_sha is not None
    check("S2 both refs/heads/main and refs/heads/master resolve on origin",
          both,
          ("missing: " + ", ".join(
              r for r, s in (("refs/heads/main", main_sha),
                             ("refs/heads/master", master_sha)) if not s)
           + " - a vanished branch is a desync, investigate before pushing")
          if not both else "")
    if not both:
        return 1
    same = main_sha == master_sha
    check("S3 origin/main == origin/master (%s)" % main_sha[:12],
          same,
          ("DESYNC: origin/main=%s origin/master=%s - re-sync the stale "
           "branch (e.g. git push origin master:main if local master is the "
           "source of record; verify which side is authoritative first)"
           % (main_sha, master_sha)) if not same else "")
    return 1 if not same else 0


def main():
    static_only = "--static-only" in sys.argv
    rc = static_checks()
    if rc == 2:
        return 2
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else (rc if rc else 0)


if __name__ == "__main__":
    sys.exit(main())
