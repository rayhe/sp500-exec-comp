#!/usr/bin/env python3
"""Regression guard: every scripts/check_*.py must be discoverable by the
pre-commit hook's grep-based auto-discovery.

The pre-commit runner does not execute every scripts/check_*.py - it only
executes the ones its source-grep selects (the three grep patterns in
scripts/pre-commit-guards.sh's discovery `if`). A guard committed with a
--static-only handler spelled differently from those patterns (extra
whitespace between tokens, the flag held in a variable, argparse with a
short flag before --static-only, getopt, etc.) is executable, passes
check_guard_exec_bits, and is silently NEVER run at commit time - the
pre-commit gate loses that guard's static coverage between drift-canary
full passes, exactly the silent-skip shape the 2026-10-08 exec-bit class
had. Until now nothing asserted discovery-visibility.

This guard asserts the discovery itself, so the class cannot recur
silently: any commit that adds or edits a check_*.py in a way the hook's
grep does not select trips this guard in that commit's pre-commit run.

Design notes (avoiding the 2026-10-13 self-satisfaction catch):
  - S1 extracts the discovery patterns from the canonical hook SOURCE
    (scripts/pre-commit-guards.sh), never from this guard's own source,
    so the assertion cannot self-satisfy.
  - The always-run gate (check_metadata_consistency.py, executed directly
    by the hook and skipped by the discovery loop) is exempted by NAME
    extracted from the hook's own case-exclusion line, not hardcoded.
  - Discovery equality with the INSTALLED hook relies on
    check_hook_copy_sync.py pinning the installed copy byte-identical to
    the canonical script (green as of 2026-10-13).

Checks (all static - one directory scan plus small file reads):
  S1 the canonical hook yields exactly the expected discovery patterns:
     two fixed-string grep literals and one add_argument grep regex.
     (Any other count = the hook's discovery contract shape changed and
     this guard's replication must be updated by hand - loud FAIL, not a
     silent false-green.)
  S2 every scripts/check_*.py except the always-run gate matches at
     least one of the extracted discovery patterns.
     (FAIL names each undiscovered file and the exact remediation.)
  S3 the hook's always-run gate file exists under scripts/ and is
     executable (the case-exclusion must name a real, runnable guard).

Usage:
  scripts/check_hook_discovery_sync.py              # same checks
  scripts/check_hook_discovery_sync.py --static-only # same checks

Exit: 0 = all guards discoverable (or properly gated); 1 = at least one
      guard is invisible to the hook's discovery; 2 = canonical hook
      script missing (infra).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 03:30 - created (03:30 PT iteration). Closes the
    discovery-silent-skip class: a guard whose --static-only handling is
    spelled differently from the hook's three grep patterns is skipped by
    every pre-commit run with no warning, while remaining executable
    and exec-bit-green.
"""
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
CANONICAL_HOOK = os.path.join(SCRIPTS, "pre-commit-guards.sh")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _extract_discovery(hook_src):
    """Pull the discovery patterns out of the canonical hook source.

    Returns (literals, regexes, gate_name). literals are fixed-string
    greps, regexes are -E greps, gate_name is the always-run guard
    exempted by the case statement.
    """
    literals = []
    # grep -q -- '<literal>' "$g"   (single-quoted arg, literal has no ')
    literals += re.findall(r"grep -q -- '([^'\n]+)' \"\$g\"", hook_src)
    # grep -q -- "<literal>" "$g"   (double-quoted arg, literal has no ")
    literals += re.findall(r'grep -q -- "([^"\n]+)" "\$g"', hook_src)
    regexes = re.findall(r'grep -qE "([^"\n]+)" "\$g"', hook_src)
    gate_m = re.search(r"\*/(check_[a-z0-9_]+\.py)\)\s*continue", hook_src)
    gate_name = gate_m.group(1) if gate_m else None
    return literals, regexes, gate_name


def _is_discovered(guard_src, literals, regexes):
    for lit in literals:
        if lit in guard_src:
            return True
    for rx in regexes:
        if re.search(rx, guard_src):
            return True
    return False


def static_checks():
    if not os.path.isfile(CANONICAL_HOOK):
        print("INFRA: canonical scripts/pre-commit-guards.sh missing")
        return 2
    with open(CANONICAL_HOOK, "r", encoding="utf-8") as fh:
        hook_src = fh.read()
    literals, regexes, gate_name = _extract_discovery(hook_src)

    ok_shape = len(literals) == 2 and len(regexes) == 1
    check("S1 canonical hook yields exactly 2 discovery literals + 1 regex",
          ok_shape,
          "extracted %d literals + %d regexes - hook discovery shape "
          "changed, update this guard's _extract_discovery"
          % (len(literals), len(regexes)) if not ok_shape else "")
    if not ok_shape:
        return 1

    check("S2b hook's case-exclusion names a gate file",
          gate_name is not None,
          "could not extract the always-run gate from the case statement"
          if gate_name is None else "")
    if gate_name is None:
        return 1

    paths = sorted(glob.glob(os.path.join(SCRIPTS, "check_*.py")))
    gate_path = os.path.join(SCRIPTS, gate_name)
    missing = []
    for p in paths:
        base = os.path.basename(p)
        if base == gate_name:
            continue  # always-run gate: executed directly by the hook
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        if not _is_discovered(src, literals, regexes):
            missing.append(base)
    check("S2 all %d looped scripts/check_*.py are hook-discoverable "
          "(gate %s exempt)" % (len(paths) - 1, gate_name),
          not missing,
          "undiscovered (would never run at commit): " + ", ".join(missing)
          + " - spell --static-only handling exactly as "
          + '"--static-only" in sys.argv or add_argument("--static-only", ...)'
          if missing else "")

    gate_ok = os.path.isfile(gate_path) and os.access(gate_path, os.X_OK)
    check("S3 always-run gate %s exists and is executable" % gate_name,
          gate_ok,
          "hook skips the discovery loop for a missing/non-executable "
          "gate - the always-run coverage is gone" if not gate_ok else "")
    return 0


def main():
    static_only = "--static-only" in sys.argv
    rc = static_checks()
    if rc == 2:
        return 2
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else (rc if rc else 0)


if __name__ == "__main__":
    sys.exit(main())
