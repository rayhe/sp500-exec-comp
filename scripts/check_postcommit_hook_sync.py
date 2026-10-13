#!/usr/bin/env python3
"""Regression guard: the installed .git/hooks/post-commit must be an exact,
executable copy of scripts/post-commit-iteration-log.sh.

The post-commit hook is the repo's commit-logging backbone: it appends an
[AUTO-STUB] entry to the canonical iteration log for EVERY commit
(installed 2026-09-12 to kill the recurring commit-without-log-entry
pattern). check_hook_copy_sync (2026-10-08) closed the drift class for the
PRE-commit side, but until this guard nothing asserted the POST-commit
side. An edit to the canonical script without a re-copy, a deleted
installed hook, or a lost exec bit would silently kill the stub mechanism:
the exact commit-without-log-entry pattern the hook was installed to kill
would recur with no tripwire - the post-commit-hook-sync class.

This guard asserts the sync itself, so the class cannot recur silently.

Checks (all static - two small file reads, <0.1s):
  S1 the installed hook .git/hooks/post-commit exists
     (missing = fresh checkout without the install step -> exit 2 infra
     advisory, not a commit blocker; a broken checkout must not wedge
     every commit)
  S2 the installed hook is byte-identical (sha256) to
     scripts/post-commit-iteration-log.sh
     (mismatch = HARD FAIL: loud message naming the re-copy fix)
  S3 the installed hook has the exec bit (git execs hooks; a non-executable
     installed copy never fires, and the stub mechanism dies silently at
     the git layer, not inside the runner - loud FAIL naming chmod +x)

Usage:
  scripts/check_postcommit_hook_sync.py              # same checks
  scripts/check_postcommit_hook_sync.py --static-only # same checks

Exit: 0 = in sync; 1 = drifted or non-executable installed copy (loud);
      2 = installed hook missing (infra advisory); 2 = repo layout missing.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 07:30 - created (07:30 PT iteration). Closes the
    post-commit-hook-sync class; the pre-commit twin was closed 2026-10-08
    by check_hook_copy_sync, which asserts only the pre-commit side.
"""
import hashlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = os.path.join(REPO, "scripts", "post-commit-iteration-log.sh")
INSTALLED = os.path.join(REPO, ".git", "hooks", "post-commit")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    static_only = "--static-only" in sys.argv

    # S0: repo layout sanity (infra, not a commit blocker)
    if not (os.path.isfile(CANONICAL)):
        print("INFRA: canonical script missing: " + CANONICAL)
        return 2

    # S1: installed hook exists
    if not os.path.isfile(INSTALLED):
        print("INFRA: installed post-commit hook missing: " + INSTALLED)
        print("INFRA: fresh checkout without the install step? "
              "Run: cp scripts/post-commit-iteration-log.sh .git/hooks/post-commit "
              "&& chmod +x .git/hooks/post-commit")
        return 2
    check("S1 installed .git/hooks/post-commit exists", True)

    # S2: byte-identical to the canonical script
    canon_sha = sha256(CANONICAL)
    inst_sha = sha256(INSTALLED)
    in_sync = canon_sha == inst_sha
    check(
        "S2 installed post-commit hook byte-identical to canonical script",
        in_sync,
        "sha256 match" if in_sync else
        "DRIFT: canonical %s... != installed %s... - re-copy: "
        "cp scripts/post-commit-iteration-log.sh .git/hooks/post-commit" % (canon_sha[:12], inst_sha[:12]),
    )

    # S3: installed hook executable
    executable = os.access(INSTALLED, os.X_OK)
    check(
        "S3 installed post-commit hook is executable",
        executable,
        "exec bit present" if executable else
        "git never fires a non-executable hook: chmod +x .git/hooks/post-commit",
    )

    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print("HARD FAIL: " + "; ".join(failed))
        return 1
    print("OK: post-commit hook in sync (installed == canonical, executable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
