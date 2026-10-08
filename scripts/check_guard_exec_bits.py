#!/usr/bin/env python3
"""Regression guard: every scripts/check_*.py must carry the exec bit.

The pre-commit hook direct-execs each --static-only guard as "$g
--static-only". A guard committed without the exec bit fails with
"Permission denied" (rc 126/127), which the hook's rc checks do not treat
as failure - the guard is silently skipped on every commit (observed
2026-10-08 on check_sector_median_fy_key.py, repaired by chore commit
03090dd; observed again the same day on check_composition_fy_detail.py,
repaired by this run). The drift canary is unaffected - it invokes guards
via sys.executable - but the pre-commit gate loses that guard's
static coverage between drift-canary full passes.

This guard asserts the exec bit itself, so the class cannot recur
silently: any future commit that adds a non-executable check_*.py trips
this guard in the same commit's pre-commit run.

Checks:
  A. Static (fast, runs in the pre-commit hook; also the whole guard -
     nothing here needs a browser):
     S1 every scripts/check_*.py file has at least one exec bit set
        (os.access(X_OK) on the checked-out file).

Usage:
  scripts/check_guard_exec_bits.py              # same checks
  scripts/check_guard_exec_bits.py --static-only # same checks

Exit: 0 = all guards executable; 1 = at least one guard is not;
      2 = scripts/ directory missing (infra).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-08 15:30 - created (15:30 PT iteration). Closes the silent-skip
    class behind commits 03090dd (sector-median guard) and the
    check_composition_fy_detail.py chmod repair made in the same run.
"""
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    if not os.path.isdir(SCRIPTS):
        print("INFRA: scripts/ directory missing")
        return 2
    paths = sorted(glob.glob(os.path.join(SCRIPTS, "check_*.py")))
    missing = [os.path.basename(p) for p in paths
               if not os.access(p, os.X_OK)]
    # NOTE: this guard checks itself too - it must stay executable for
    # the pre-commit direct-exec path to reach it.
    check("S1 all %d scripts/check_*.py files are executable" % len(paths),
          not missing,
          ("missing exec bit: " + ", ".join(missing)) if missing else "")
    return 0


def main():
    static_only = "--static-only" in sys.argv
    rc = static_checks()
    if rc == 2:
        return 2
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
