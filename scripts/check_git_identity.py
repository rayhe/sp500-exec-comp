#!/usr/bin/env python3
"""Regression guard: commit author identity is Ray He (identity-drift class).

Standing rule (USER.md / MEMORY.md): git commits are authored as
'Ray He <rayche@gmail.com>', never 'Hatch' or any automation identity.
Every iteration run stages, commits, and pushes to a PUBLIC repo, and the
only tripwire on the author identity was the run author's eyeball
("Git identity verified pre-commit: Ray He <rayche@gmail.com>" in the
iteration log) - a hand-convention, the same hand-convention pattern the
82nd guard closed for log-prose numbers and the 86th closed for staged
secrets. A commit landing under a wrong-but-valid identity (e.g. a
misconfigured global gitconfig, a tool that rewrote user.name) would
publish with every other guard green and violate the standing rule
silently.

This guard reads the EFFECTIVE git identity (system + global + local
config, exactly what `git commit` would use absent -c overrides, which
this repo's runs never pass) and HARD FAILs the commit unless it is
exactly the standing identity. The fix is deliberate, not silent: change
the identity, then change this guard.

Checks (all static - two `git config` reads, no network):
  S1 effective `git config user.name` == "Ray He"
     (mismatch or unset -> HARD FAIL naming the value found and the
     remediation `git config user.name "Ray He"`)
  S2 effective `git config user.email` == "rayche@gmail.com"
     (mismatch or unset -> HARD FAIL naming the value found and the
     remediation `git config user.email "rayche@gmail.com"`)
  `git config` failing (not a repo, git missing) -> exit 2 INFRA
  advisory, not a commit blocker, per the pre-commit contract.

Usage:
  scripts/check_git_identity.py              # same checks
  scripts/check_git_identity.py --static-only # same checks
  scripts/check_git_identity.py --repo PATH  # check identity effective
                                             # in another repo (negative tests)

Exit: 0 = identity matches the standing rule; 1 = drift (loud);
      2 = git config itself failed (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-14 02:00 - created (02:00 PT iteration). Closes the
    identity-drift class: the commit-author eyeball ("Git identity
    verified pre-commit") had no fail-closed verifier, so a
    wrong-but-valid gitconfig identity would publish to the public
    repo with every guard green.
"""
import subprocess
import sys

EXPECTED_NAME = "Ray He"
EXPECTED_EMAIL = "rayche@gmail.com"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _effective_config(key, repo):
    """Return (rc, value) of `git -C repo config <key>`; value stripped."""
    try:
        p = subprocess.run(
            ["git", "-C", repo, "config", key],
            capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as e:
        return (None, "git invocation failed: %s" % e)
    if p.returncode != 0:
        # Unset key: git config exits 1 with empty stdout. Any other
        # failure (not a repo) also lands here with stderr explaining.
        err = (p.stderr or "").strip()
        return (p.returncode, "" if p.returncode == 1 and not err
                else "git config failed: %s" % err)
    return (0, (p.stdout or "").strip())


def main(argv):
    repo = "."
    args = list(argv)
    if "--repo" in args:
        i = args.index("--repo")
        if i + 1 < len(args):
            repo = args[i + 1]

    # S1/S2: effective identity must match the standing rule exactly.
    # A `git config` invocation failure (None rc) is INFRA, not a verdict:
    # the pre-commit contract says a broken git must not wedge commits.
    failures = []
    for key, expected, label in (("user.name", EXPECTED_NAME, "name"),
                                 ("user.email", EXPECTED_EMAIL, "email")):
        rc, value = _effective_config(key, repo)
        if rc is None:
            print("INFRA: %s - no identity verdict possible (advisory only)"
                  % value)
            return 2
        if rc != 0 and value.startswith("git config failed"):
            print("INFRA: %s - no identity verdict possible (advisory only)"
                  % value)
            return 2
        ok = (value == expected)
        detail = ("matches standing identity" if ok else
                  "found %r, expected %r - run: git config %s %r"
                  % (value if value else "<unset>", expected, key, expected))
        check("S1/S2 identity %s" % label, ok, detail)
        if not ok:
            failures.append(label)

    if failures:
        print("FAIL: git-identity: author identity drift on (%s) - fix the "
              "gitconfig, then re-run" % ", ".join(failures))
        return 1
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
