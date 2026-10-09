#!/usr/bin/env python3
"""Regression guard: the installed .git/hooks/pre-commit must be an exact
copy of scripts/pre-commit-guards.sh.

The pre-commit hook is a COPY, not a symlink (see the install instructions
in scripts/pre-commit-guards.sh). Every edit to the canonical script that is
not followed by a re-copy leaves the installed hook stale: guards gain static
coverage the hook never runs, or the hook's own hardening (rc 126/127 hard
fail, added 2026-10-08) never takes effect. Until now nothing checked the
copy-sync, so drift could sit for days and only surface as a silent behavior
gap - the last unguarded infra surface (queued candidate #8, 2026-10-08
15:30/19:37 runs).

This guard asserts the sync itself, so the class cannot recur silently:
any commit that touches the canonical script without re-copying it (or that
edits the installed copy directly) trips this guard in that commit's
pre-commit run.

Checks (all static - two small file reads, <0.1s):
  S1 the installed hook .git/hooks/pre-commit exists
     (missing = fresh checkout without the install step -> exit 2 infra
     advisory, not a commit blocker; a broken checkout must not wedge
     every commit)
  S2 the installed hook is byte-identical (sha256) to
     scripts/pre-commit-guards.sh
     (mismatch = HARD FAIL: loud message naming the re-copy fix)
  S3 the installed hook has the exec bit (git execs hooks; a non-executable
     installed copy fails at the git-hook layer, not inside the runner -
     loud FAIL naming the chmod +x fix)

Usage:
  scripts/check_hook_copy_sync.py              # same checks
  scripts/check_hook_copy_sync.py --static-only # same checks

Exit: 0 = in sync; 1 = drifted or non-executable installed copy (loud);
      2 = installed hook missing (infra advisory); 2 = repo layout missing.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-08 22:00 - created (22:00 PT iteration). Closes the hook/copy
    drift class; last unguarded infra surface from the 2026-10-08 runs.
"""
import hashlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = os.path.join(REPO, "scripts", "pre-commit-guards.sh")
INSTALLED = os.path.join(REPO, ".git", "hooks", "pre-commit")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def static_checks():
    if not os.path.isfile(CANONICAL):
        print("INFRA: canonical scripts/pre-commit-guards.sh missing")
        return 2
    if not os.path.isfile(INSTALLED):
        print("INFRA: .git/hooks/pre-commit not installed "
              "(run: cp scripts/pre-commit-guards.sh .git/hooks/pre-commit "
              "&& chmod +x .git/hooks/pre-commit)")
        return 2
    check("S1 installed hook exists", True)
    same = _sha256(INSTALLED) == _sha256(CANONICAL)
    check("S2 installed hook byte-identical to scripts/pre-commit-guards.sh",
          same,
          "copy drifted - re-copy: cp scripts/pre-commit-guards.sh "
          ".git/hooks/pre-commit && chmod +x .git/hooks/pre-commit" if not same else "")
    if not same:
        return 1
    x = os.access(INSTALLED, os.X_OK)
    check("S3 installed hook is executable", x,
          ".git/hooks/pre-commit lacks the exec bit - chmod +x it" if not x else "")
    return 1 if not x else 0


def main():
    static_only = "--static-only" in sys.argv
    rc = static_checks()
    if rc == 2:
        return 2
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else (rc if rc else 0)


if __name__ == "__main__":
    sys.exit(main())
