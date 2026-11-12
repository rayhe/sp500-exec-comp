#!/usr/bin/env python3
"""Shared render-half helpers for the scripts/check_*.py guards.

Background (429th review, 2026-11-11): two latent defects, both carried
from the 427th review, lived in the render guards as duplicated code:

  1. Uncaught-render-exception exposure. The 427th review gave
     check_badge_part_spans.py a retry-once wrapper (_render_with_retry)
     after a canary shard-2 run recorded it FAIL on a 30s
     wait_for_selector timeout under load -- the render half raised
     before any R-check printed, so an uncaught exception read as
     drift (exit 1) even though the static checks passed and the guard
     passes standalone in ~8s. Every sibling render guard still calls
     render_checks() raw in main(), so the same stall class can fake
     drift in any of them. The wrapper is generalized here as
     run_render_with_retry() and adopted first by the guard that
     already had it (badge_part_spans, behavior-preserving) and by
     the two slowest render guards (quartile hash roundtrip ~87.5s,
     sector chip scope ~68.8s -- a stall that far into a run is the
     most expensive to lose). Further per-guard adoption is one guard
     per iteration; the helper's contract is pinned by
     check_render_guard_common.py.
  2. d3-shim-unavailable exit-code mismatch. All three guards'
     docstrings promise exit 2 (infra) for a d3 shim that cannot be
     obtained, but get_d3_bytes() returning None made render_checks()
     return False, which main() folded into exit 1 (drift). The canary
     reports a guard exit 2 as INFRA, not FAIL, so the old mapping
     turned an environment problem (no cached shim, no network) into
     a false drift signal. render_checks() now returns the INFRA
     sentinel below and main() maps it to exit 2; the print stays
     "INFRA: ..." with no FAIL verdict line, so
     check_guard_exit_consistency S2 (FAIL verdict ==> rc == 1) is
     unaffected -- the infra path prints no verdict at all.

get_d3_bytes() is the byte-identical copy that lived in 83 guards
(cache-first, curl fallback to cdn.jsdelivr.net/npm/d3@7); it is
moved here verbatim so future fixes land once instead of 83 times.
Only the three guards named above adopt it this run; the other 80
keep their local copies until a later iteration adopts them.

Contract for adopters:
  - import with the sys.path insert used by check_metadata_consistency
    (scripts/ is sys.path[0] when run as a script, but the insert keeps
    the import working when a guard is imported in-process by a test):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry
  - render_checks(): `d3 = get_d3_bytes()`; on None, print the INFRA
    line and `return INFRA` (never False -- False is drift).
  - main(): `ok = run_render_with_retry(render_checks, results, check)`;
    `if ok is INFRA: return 2` before the None (skip) / False (fail)
    handling. INFRA is a module-level singleton: compare with `is`.

This module is NOT a guard (not named check_*.py), so the pre-commit
hook does not run it directly; it is covered by
scripts/check_render_guard_common.py (static + harness, no browser).

Usage (inside a guard):
  from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry
"""
import os
import subprocess
import tempfile

D3_CACHE = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/methbtn-20261005/d3.min.js")

# Sentinel a guard's render_checks() returns when the render half cannot
# run for an infra reason (d3 shim unavailable). Callers map it to exit 2,
# never to a FAIL verdict: the canary reports guard exit 2 as INFRA.
INFRA = object()


def get_d3_bytes(cache=None):
    """Return d3.min.js bytes: the goal hidden_files cache first, else a
    curl fetch from jsdelivr. Returns None when neither yields >= 100KB.
    Byte-identical logic to the copy that lived in 83 guards; `cache`
    exists only so the harness can force the failure path without
    touching the real cache."""
    if cache is None:
        cache = D3_CACHE
    if os.path.exists(cache):
        return open(cache, "rb").read()
    tmp = tempfile.NamedTemporaryFile(suffix=".js", delete=False).name
    r = subprocess.run(
        ["curl", "-sL", "--http1.1", "-A", "Kit/1.0 (factoryfactorykit@gmail.com)",
         "https://cdn.jsdelivr.net/npm/d3@7", "-o", tmp],
        timeout=60)
    if r.returncode != 0 or os.path.getsize(tmp) < 100000:
        return None
    return open(tmp, "rb").read()


def run_render_with_retry(render_fn, results, record_fail):
    """Run render_fn(), retrying once on an exception that strikes before
    any R-check is recorded (427th review: a load stall can time out the
    table-row wait, which used to surface as an uncaught exception ->
    exit 1 with stdout ending at the last static check, i.e. fake drift).
    Returns render_fn()'s value unchanged (True/False/None/INFRA), except:
    a second exception, or one after an R-check was recorded, records a
    FAIL via record_fail and returns False, so a genuinely broken page
    still fails loudly instead of passing as infra. An INFRA return
    passes through without retry (deterministic: retrying a missing d3
    shim cannot help). `results` is the guard's own results list;
    `record_fail` is its check() helper."""
    for attempt in (1, 2):
        try:
            return render_fn()
        except Exception as exc:  # noqa: BLE001 - render infra is heterogeneous
            rendered = [r for r in results if r[0].startswith("R")]
            print("INFRA: render half attempt %d raised %s: %s"
                  % (attempt, type(exc).__name__, exc))
            if rendered or attempt == 2:
                if not rendered:
                    record_fail("R1 render half raised on both attempts", False,
                                "%s: %s" % (type(exc).__name__, exc))
                return False
    return False
