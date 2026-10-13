#!/usr/bin/env python3
"""Regression guard: guard verdict/exit-code consistency (fail-open class).

The pre-commit runner (scripts/pre-commit-guards.sh) blocks a commit on
EXIT CODE alone (rc 1/126/127 block; rc 2 warns; rc 0 passes) and never
inspects a guard's printed output. A guard whose verdict-folding has a bug
- an early return before the results fold, a shadowed results list, a
hardcoded sys.exit(0), an exception swallowed around main() - can print
"FAIL: ..." lines yet exit 0. The runner would pass the commit, and that
guard's entire static coverage would be advisory-only with no tripwire:
the fail-open exit class. Until this guard, nothing asserted that a
printed FAIL verdict always blocks.

Two-layer close (mirrors the check_hook_discovery_sync design):
  S1 (static-only, fast, runs at every commit): the canonical hook source
     scripts/pre-commit-guards.sh contains the FAIL-OPEN-ENFORCEMENT block:
     after capturing each guard's output the runner fails the commit
     loudly when a FAIL verdict line appears with rc != 1. If a hook edit
     drops the enforcement, S1 hard-fails naming the restore-or-update
     remediation (same "shape changed -> loud FAIL, update by hand"
     contract as check_hook_discovery_sync S1).
  S2 (default/full mode only; skipped under --static-only): dynamic sweep
     over every scripts/check_*.py (self excluded): run `<guard>
     --static-only`, capture rc + output, and assert verdict-lines ==>
     rc == 1. A guard printing a FAIL verdict with rc 0 is the fail-open
     bug and hard-fails naming the guard. rc == 1 with no FAIL verdict
     line is a diagnosability gap (commit blocks with no explanation) and
     prints as WARN advisory, not a blocker - the always-run gate's
     "METADATA CONSISTENCY CHECK FAILED:" banner style is grandfathered
     by the verdict pattern below.

The verdict pattern matches both the check() helper convention
("FAIL: <name>") and the gate's banner ("... CHECK FAILED:"), and matched
zero lines across all 80 guards on the green tree at guard creation
(2026-10-13), so it cannot false-positive on passing output.

Checks (S1 static; S2 render-mode sweep):
  S1 canonical hook carries the fail-open enforcement (marker comment +
     verdict grep pattern + loud fail-open message).
  S2 every discovered guard obeys verdict ==> rc==1 on the true tree.

Usage:
  scripts/check_guard_exit_consistency.py              # S1 + S2 sweep
  scripts/check_guard_exit_consistency.py --static-only # S1 only

Exit: 0 = enforcement present and sweep consistent; 1 = enforcement
      missing or a fail-open guard found; 2 = canonical hook or check
      dir missing (infra).

Test hook: set SP500_CHECK_DIR to a fixture dir of check_*.py files to
exercise S2 without touching the real suite (used by the negative tests).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 14:00 - created (14:00 PT iteration). Closes the
    fail-open-exit class: the runner blocked on exit code alone, so a
    guard printing FAIL verdicts with rc 0 would false-green every
    commit. Runner now captures each guard's output and loud-blocks on
    verdict/exit desync; this guard pins the enforcement in the hook
    source (S1) and proves the invariant dynamically (S2).
"""
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.environ.get("SP500_CHECK_DIR", os.path.join(REPO, "scripts"))
CANONICAL_HOOK = os.path.join(REPO, "scripts", "pre-commit-guards.sh")
SELF = os.path.basename(__file__)

# Matches the check() "FAIL: <name>" convention and the gate's
# "METADATA CONSISTENCY CHECK FAILED:" banner; zero hits on the green tree.
VERDICT_RE = re.compile(r"(^|\s)FAIL(ED)?:")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def verdict_lines(output):
    return [l for l in output.splitlines() if VERDICT_RE.search(l)]


def s1_hook_carries_enforcement():
    if not os.path.isfile(CANONICAL_HOOK):
        print("INFRA: canonical hook missing: " + CANONICAL_HOOK)
        return None
    src = open(CANONICAL_HOOK, encoding="utf-8").read()
    has_marker = "# FAIL-OPEN-ENFORCEMENT" in src
    check("S1a hook carries the FAIL-OPEN-ENFORCEMENT marker", has_marker,
          "" if has_marker else "hook edit dropped the enforcement block - restore it or update this guard by hand")
    has_pattern = "(^|[[:space:]])FAIL(ED)?:" in src
    check("S1b hook carries the verdict grep pattern", has_pattern,
          "" if has_pattern else "verdict pattern missing from the hook - restore or update by hand")
    has_message = "printed a FAIL verdict but exited" in src
    check("S1c hook carries the loud fail-open message", has_message,
          "" if has_message else "loud fail-open message missing from the hook - restore or update by hand")
    return all(r[1] for r in results if r[0].startswith("S1"))


def s2_dynamic_sweep():
    guards = sorted(glob.glob(os.path.join(SCRIPTS, "check_*.py")))
    guards = [g for g in guards if os.path.basename(g) != SELF]
    if not guards:
        print("INFRA: no check_*.py found under " + SCRIPTS)
        return None
    check("S2a sweep discovered guards", True, "%d guards (self excluded)" % len(guards))
    fail_open = []
    no_verdict = []
    for g in guards:
        try:
            r = subprocess.run([sys.executable, g, "--static-only"],
                               capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            fail_open.append((os.path.basename(g), "TIMEOUT (>120s) with unknown verdict"))
            continue
        out = (r.stdout or "") + (r.stderr or "")
        vl = verdict_lines(out)
        if vl and r.returncode != 1:
            fail_open.append((os.path.basename(g), "rc=%d with %d FAIL verdict line(s): %s"
                              % (r.returncode, len(vl), vl[0][:100])))
        elif not vl and r.returncode == 1:
            no_verdict.append(os.path.basename(g))
    check("S2b no guard prints FAIL verdict with rc != 1 (fail-open)",
          not fail_open,
          "" if not fail_open else "; ".join("%s [%s]" % t for t in fail_open[:5]))
    if no_verdict:
        print("WARN: S2c diagnosability advisory - rc 1 with no FAIL verdict line: "
              + ", ".join(no_verdict))
    else:
        print("PASS: S2c no rc-1-without-verdict cases")
    return not fail_open


def main():
    static_only = "--static-only" in sys.argv
    s1 = s1_hook_carries_enforcement()
    if s1 is None:
        return 2
    if static_only:
        print("SKIP: S2 dynamic sweep is full-mode-only (exercised by the drift canary)")
        return 0 if s1 else 1
    s2 = s2_dynamic_sweep()
    if s2 is None:
        return 2
    return 0 if (s1 and s2) else 1


if __name__ == "__main__":
    sys.exit(main())
