#!/usr/bin/env python3
"""Regression guard: the shared render-half helpers are the one
implementation every adopted guard uses.

Background (429th review, 2026-11-11): scripts/render_guard_common.py
generalizes two per-guard copies -- the render-half retry-once wrapper
(427th review, check_badge_part_spans.py) and get_d3_bytes() (identical
in 83 guards) -- and fixes the d3-shim-unavailable exit mapping
(render_checks() returned False -> exit 1 drift, although every
adopter's docstring promises exit 2 infra). Adopters this run:
check_badge_part_spans.py, check_quartile_hash_roundtrip.py,
check_sector_chip_scope.py. The other 80 guards keep their local
copies until a later iteration adopts them, one guard per run.

430th review (2026-11-11): check_network_residual_keyboard.py
adopted (slowest render guard, ~98.3s). Its pre-fix defect was worse
than the 429th class: main() ignored render_checks()'s return value,
so a missing d3 shim exited 0 with "ALL 6 CHECKS PASSED" while the
render half never ran. 79 local get_d3_bytes copies remain.

431st review (2026-11-11): check_minimap_toggle.py adopted (slowest
remaining render guard, ~69.9s). Same silent-pass variant as the
430th: pre-fix main() ignored render_checks()'s return value and
exited 0 with "7/7 checks passed" on a missing d3 shim, proved
in-process before the fix. 78 local get_d3_bytes copies remain.

432nd review (2026-11-12): check_compare_bridge_keyboard.py adopted
(slowest remaining render guard, ~54.2s). Same silent-pass variant:
pre-fix main() ignored render_checks()'s return value and exited 0
with "ALL 6 CHECKS PASSED" on a missing d3 shim, proved in-process
before the fix (~/workspace/pre432_proof.py: exit 0, 0 R-checks). The
pre-adoption grep across the remaining guards found the silent-pass
signature in 77 of the 78 unadopted guards; the lone exception is
check_crosstab_keyboard.py, whose main() already maps a False render
return to exit 2. 77 local get_d3_bytes copies remain.

434th review (2026-11-12): check_remaining_chip_sweeps.py adopted
(slowest remaining render guard, ~49.1s in the 2026-11-12 shard
runs). Its pre-fix defect was the 429th-review class, not the
silent-pass variant: main() checked render_checks()'s return value,
but a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the guard's docstring
promises exit 2 (infra) -- proved in-process before the fix
(/tmp/pre434_proof.py: rc=1, "11/11 checks passed" printed, 0
R-checks recorded). 76 local get_d3_bytes copies remain.

435th review (2026-11-12): check_scrollspy_nav.py adopted (slowest
remaining render guard, ~43.9s max in the 2026-11-12 shard runs).
Same silent-pass variant as the 430th-432nd: pre-fix main() ignored
render_checks()'s return value and exited 0 with "OK: scroll-spy
nav guard (static)" on a missing d3 shim, proved in-process before
the fix (~/workspace/pre435_proof.py: rc=0, "checks: 7 pass, 0
fail", 0 R-checks recorded). Count correction: 77 unadopted guards
carried a local get_d3_bytes before this run, not the 76 the 434th
note stated (the 432nd note's own "77 of the 78 unadopted guards"
already put the unadopted count at 78; the 434th adoption took it
to 77). 76 local get_d3_bytes copies remain after this adoption.

Checks (all pure Python, no browser; <2s):
  S1  the shared module defines INFRA, get_d3_bytes and
      run_render_with_retry; each adopted guard imports all three
      from render_guard_common, defines no local get_d3_bytes (and
      the badge guard no local _render_with_retry), calls
      run_render_with_retry(render_checks, results, check) in main,
      and maps INFRA to exit 2.
  S2  harness for run_render_with_retry: raise-once-then-True returns
      True after 2 calls with no FAIL recorded; raise-twice returns
      False with exactly one synthetic FAIL recorded; raise-after-an-
      R-check returns False after 1 call with no synthetic FAIL;
      an INFRA return passes through after 1 call; a None return
      passes through after 1 call.
  S3  get_d3_bytes(): the real cache returns >= 100KB; a missing
      cache + a failing curl returns None (curl stubbed in-process,
      no network).
  S4  each adopted guard maps INFRA to exit 2 with no FAIL verdict
      line: the guard module is imported in-process, its
      render_checks is stubbed to return INFRA, main() returns 2.

Usage:
  scripts/check_render_guard_common.py
  scripts/check_render_guard_common.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (shared module or
an adopted guard unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import contextlib
import importlib.util
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_guard_common as rgc  # noqa: E402

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
SCRIPTS = os.path.join(REPO, "scripts")
COMMON = os.path.join(SCRIPTS, "render_guard_common.py")

ADOPTERS = [
    "check_badge_part_spans.py",
    "check_quartile_hash_roundtrip.py",
    "check_sector_chip_scope.py",
    "check_network_residual_keyboard.py",
    "check_minimap_toggle.py",
    "check_compare_bridge_keyboard.py",
    "check_remaining_chip_sweeps.py",
    "check_scrollspy_nav.py",
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def s1_adoption_static():
    try:
        src = open(COMMON, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read render_guard_common.py: %s" % exc)
        return None
    ok = "INFRA = object()" in src
    check("S1a shared module defines the INFRA sentinel", ok,
          "" if ok else "INFRA sentinel missing from render_guard_common.py")
    ok = "def get_d3_bytes(" in src
    check("S1b shared module defines get_d3_bytes", ok,
          "" if ok else "get_d3_bytes missing from render_guard_common.py")
    ok = "def run_render_with_retry(" in src
    check("S1c shared module defines run_render_with_retry", ok,
          "" if ok else "run_render_with_retry missing from render_guard_common.py")
    for name in ADOPTERS:
        path = os.path.join(SCRIPTS, name)
        try:
            gsrc = open(path, encoding="utf-8").read()
        except OSError as exc:
            print("INFRA: cannot read %s: %s" % (name, exc))
            return None
        short = name[:-3]
        ok = ("from render_guard_common import INFRA, get_d3_bytes, "
              "run_render_with_retry" in gsrc)
        check("S1d %s imports INFRA/get_d3_bytes/run_render_with_retry"
              % short, ok,
              "" if ok else "%s does not import the shared helpers" % name)
        ok = "def get_d3_bytes(" not in gsrc
        check("S1e %s defines no local get_d3_bytes" % short, ok,
              "" if ok else "%s still carries a local get_d3_bytes" % name)
        ok = "run_render_with_retry(render_checks, results, check)" in gsrc
        check("S1f %s calls run_render_with_retry in main" % short, ok,
              "" if ok else "%s main() does not use the shared retry" % name)
        ok = "if ok is INFRA:" in gsrc
        check("S1g %s maps INFRA to exit 2 in main" % short, ok,
              "" if ok else "%s main() has no INFRA branch" % name)
        ok = "return INFRA" in gsrc
        check("S1h %s returns INFRA when the d3 shim is unavailable" % short, ok,
              "" if ok else "%s render_checks() never returns INFRA" % name)
        if name == "check_badge_part_spans.py":
            ok = "def _render_with_retry(" not in gsrc
            check("S1i badge guard defines no local _render_with_retry", ok,
                  "" if ok else "badge guard still carries a local _render_with_retry")
    return all(r[1] for r in results if r[0].startswith("S1"))


def s2_retry_harness():
    calls = {"n": 0}
    recorded = []

    def record_fail(name, ok, detail=""):
        recorded.append((name, bool(ok), detail))

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("stall")
        return True

    out = rgc.run_render_with_retry(flaky, [], record_fail)
    check("S2a raise-once-then-True returns True after 2 calls, no FAIL",
          out is True and calls["n"] == 2 and recorded == [],
          "out=%r calls=%d recorded=%r" % (out, calls["n"], recorded))

    recorded.clear()
    calls["n"] = 0

    def always_raise():
        calls["n"] += 1
        raise RuntimeError("boom")

    out = rgc.run_render_with_retry(always_raise, [], record_fail)
    synth = [r for r in recorded
             if r[0] == "R1 render half raised on both attempts" and not r[1]]
    check("S2b raise-twice returns False with exactly one synthetic FAIL",
          out is False and len(synth) == 1 and len(recorded) == 1,
          "out=%r recorded=%r" % (out, recorded))

    recorded.clear()
    calls["n"] = 0
    prior = [("R1 something", False, "pre-recorded")]

    def late_raise():
        calls["n"] += 1
        raise RuntimeError("boom")

    out = rgc.run_render_with_retry(late_raise, prior, record_fail)
    check("S2c raise-after-an-R-check returns False after 1 call, no retry",
          out is False and calls["n"] == 1 and prior == [("R1 something", False, "pre-recorded")]
          and recorded == [],
          "out=%r calls=%d prior=%r recorded=%r" % (out, calls["n"], prior, recorded))

    calls["n"] = 0

    def returns_infra():
        calls["n"] += 1
        return rgc.INFRA

    out = rgc.run_render_with_retry(returns_infra, [], record_fail)
    check("S2d INFRA return passes through after 1 call (no retry)",
          out is rgc.INFRA and calls["n"] == 1,
          "out=%r calls=%d" % (out, calls["n"]))
    calls["n"] = 0

    def returns_none():
        calls["n"] += 1
        return None

    out = rgc.run_render_with_retry(returns_none, [], record_fail)
    check("S2e None return (playwright missing) passes through after 1 call",
          out is None and calls["n"] == 1,
          "out=%r calls=%d" % (out, calls["n"]))
    return all(r[1] for r in results if r[0].startswith("S2"))


def s3_d3_bytes():
    try:
        data = rgc.get_d3_bytes()
    except Exception as exc:  # noqa: BLE001 - cache read failure is a guard input
        check("S3a cached d3 shim returns >= 100KB", False, "%s: %s" % (type(exc).__name__, exc))
        data = None
    else:
        check("S3a cached d3 shim returns >= 100KB",
              isinstance(data, (bytes, bytearray)) and len(data) >= 100000,
              "got %r" % (len(data) if isinstance(data, (bytes, bytearray)) else data,))
    from unittest import mock

    class _Stub:
        returncode = 1

    with mock.patch.object(rgc.subprocess, "run", return_value=_Stub()):
        got = rgc.get_d3_bytes(cache="/nonexistent/sp500-d3-shim.js")
    check("S3b missing cache + failing curl returns None (no network)",
          got is None, "got %r" % (got,))
    return all(r[1] for r in results if r[0].startswith("S3"))


def s4_infra_exit_mapping():
    for name in ADOPTERS:
        short = name[:-3]
        path = os.path.join(SCRIPTS, name)
        spec = importlib.util.spec_from_file_location("sp500_" + short, path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:  # noqa: BLE001 - import failure is a guard input
            check("S4 %s imports for the INFRA harness" % short, False,
                  "%s: %s" % (type(exc).__name__, exc))
            continue
        if not hasattr(mod, "INFRA"):
            check("S4 %s imports INFRA (adoption missing)" % short, False,
                  "%s has no INFRA name" % name)
            continue
        mod.render_checks = lambda: mod.INFRA
        old_argv = sys.argv
        sys.argv = [name]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = mod.main()
        finally:
            sys.argv = old_argv
        out = buf.getvalue()
        check("S4 %s maps a d3-shim INFRA to exit 2, no FAIL verdict" % short,
              rc == 2 and "FAIL:" not in out,
              "rc=%s output tail=%r" % (rc, out.strip().splitlines()[-3:]))
    return all(r[1] for r in results if r[0].startswith("S4"))


def main():
    # Pure-Python guard: identical checks in both modes. The literal
    # "--static-only" in sys.argv below is the hook-discovery opt-in
    # (421st review: the docstring mention alone does not opt in).
    _static_only = "--static-only" in sys.argv
    s1 = s1_adoption_static()
    if s1 is None:
        return 2
    s2 = s2_retry_harness()
    s3 = s3_d3_bytes()
    s4 = s4_infra_exit_mapping()
    failed = [r for r in results if not r[1]]
    print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
