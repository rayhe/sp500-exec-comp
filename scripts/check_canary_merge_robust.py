#!/usr/bin/env python3
"""Guard: drift-canary shard merge survives malformed recorded entries.

Failure mode (417th review): merge_shard_results built the merged
overall with ``{r["status"] for r in guards.values()}`` and read
``r.get("run_utc")`` on every recorded entry. A recorded entry missing
"status" (hand-edited state, older canary version) crashed the merge
with KeyError 'status'; a non-dict entry crashed with AttributeError.
Either crash kills a shard run with an uncaught traceback and writes
no state at all, so one bad entry wedges the whole re-baseline.

The fix coerces malformed entries to an "infra" verdict with no
run_utc: they can never claim freshness, the merge stays incomplete,
last_run_utc does not advance, and the normalized form is written back
so the next merge cannot crash on the same entry again.

  R1 entry missing "status" merges without crashing; overall is
     "infra", the merge is incomplete, last_run_utc is kept.
  R2 non-dict recorded entry merges without crashing, same fail-closed
     outcome as R1.
  R3 entry missing "run_utc" (status "pass") merges, is treated stale,
     merge incomplete, last_run_utc kept.
  R4 well-formed all-fresh merge still completes and advances
     last_run_utc (no behavior change for good entries).
  R5 a recorded "fail" status still yields overall "fail" (the
     normalization does not swallow real verdicts).
  R6 the merged state carries the normalized "infra" entry back, so a
     second merge over the same state does not crash either.

All checks are pure-function (no subprocess, no Chromium).

Usage:
  scripts/check_canary_merge_robust.py              # same checks
  scripts/check_canary_merge_robust.py --static-only # same checks

Exit: 0 = all checks pass; 1 = a check FAILED (blocks the commit);
      2 = infra problem (missing drift_canary module).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-11-10 21:00 - created (417th review). Pins the merge-robustness
    fix in drift_canary.py: malformed recorded entries coerce to
    "infra" instead of crashing the shard merge.
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import drift_canary as dc
except ImportError as e:  # pragma: no cover - import failure is infra
    print("INFRA: cannot import drift_canary (%s)" % e)
    sys.exit(2)

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _iso(hours_ago):
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=hours_ago)).isoformat(timespec="seconds")


def _good(hours_ago=0):
    return {"exit": 0, "status": "pass", "seconds": 0.1,
            "run_utc": _iso(hours_ago), "tail": []}


def _prev(guards, last_run_hours_ago=41):
    return {"last_run_utc": _iso(last_run_hours_ago),
            "commit": "oldcommit", "guards": guards, "overall": "pass"}


def main(argv):
    names = ["check_a", "check_b"]

    # R1: entry missing "status" merges, fail-closed.
    prev = _prev({"check_a": _good(0),
                  "check_b": {"exit": 0, "seconds": 0.1,
                              "run_utc": _iso(0)}})
    try:
        merged = dc.merge_shard_results(prev, {}, names, "newcommit")
        r1_ok = (merged["overall"] == "infra"
                 and merged["coverage"]["complete"] is False
                 and merged["last_run_utc"] == prev["last_run_utc"])
        r1_detail = ("overall=%s complete=%s last_run_utc kept=%s"
                     % (merged["overall"], merged["coverage"]["complete"],
                        merged["last_run_utc"] == prev["last_run_utc"]))
    except Exception as e:  # noqa: BLE001 - the crash IS the failure
        r1_ok, r1_detail = False, "crashed: %s: %s" % (type(e).__name__, e)
    check("canary-merge-survives-missing-status", r1_ok, r1_detail)

    # R2: non-dict recorded entry merges, fail-closed.
    prev = _prev({"check_a": _good(0), "check_b": "not-a-dict"})
    try:
        merged = dc.merge_shard_results(prev, {}, names, "newcommit")
        r2_ok = (merged["overall"] == "infra"
                 and merged["coverage"]["complete"] is False
                 and merged["last_run_utc"] == prev["last_run_utc"])
        r2_detail = ("overall=%s complete=%s last_run_utc kept=%s"
                     % (merged["overall"], merged["coverage"]["complete"],
                        merged["last_run_utc"] == prev["last_run_utc"]))
    except Exception as e:  # noqa: BLE001
        r2_ok, r2_detail = False, "crashed: %s: %s" % (type(e).__name__, e)
    check("canary-merge-survives-non-dict-entry", r2_ok, r2_detail)

    # R3: entry missing "run_utc" (status pass) is treated stale.
    prev = _prev({"check_a": _good(0),
                  "check_b": {"exit": 0, "status": "pass", "seconds": 0.1}})
    try:
        merged = dc.merge_shard_results(prev, {}, names, "newcommit")
        r3_ok = (merged["coverage"]["complete"] is False
                 and merged["coverage"]["fresh"] == 1
                 and merged["last_run_utc"] == prev["last_run_utc"])
        r3_detail = ("complete=%s fresh=%d last_run_utc kept=%s"
                     % (merged["coverage"]["complete"],
                        merged["coverage"]["fresh"],
                        merged["last_run_utc"] == prev["last_run_utc"]))
    except Exception as e:  # noqa: BLE001
        r3_ok, r3_detail = False, "crashed: %s: %s" % (type(e).__name__, e)
    check("canary-merge-treats-missing-run-utc-stale", r3_ok, r3_detail)

    # R4: well-formed all-fresh merge still completes and advances.
    prev = _prev({"check_a": _good(1), "check_b": _good(50)})
    fresh = {"check_b": _good(0)}
    merged = dc.merge_shard_results(prev, fresh, names, "newcommit")
    r4_ok = (merged["coverage"]["complete"] is True
             and merged["overall"] == "pass"
             and merged["last_run_utc"] == prev["guards"]["check_a"]["run_utc"])
    check("canary-merge-well-formed-still-completes", r4_ok,
          "complete=%s overall=%s last_run_utc=%s"
          % (merged["coverage"]["complete"], merged["overall"],
             merged["last_run_utc"]))

    # R5: a recorded "fail" verdict still yields overall "fail".
    prev = _prev({"check_a": _good(0),
                  "check_b": {"exit": 1, "status": "fail", "seconds": 0.1,
                              "run_utc": _iso(0)}})
    merged = dc.merge_shard_results(prev, {}, names, "newcommit")
    r5_ok = (merged["overall"] == "fail"
             and merged["coverage"]["complete"] is True)
    check("canary-merge-keeps-fail-verdict", r5_ok,
          "overall=%s complete=%s" % (merged["overall"],
                                       merged["coverage"]["complete"]))

    # R6: the normalized "infra" entry is written back, so a second
    # merge over the merged state does not crash either.
    prev = _prev({"check_a": _good(0),
                  "check_b": {"exit": 0, "seconds": 0.1,
                              "run_utc": _iso(0)}})
    try:
        first = dc.merge_shard_results(prev, {}, names, "newcommit")
        second = dc.merge_shard_results(first, {}, names, "newcommit2")
        r6_ok = (first["guards"]["check_b"]["status"] == "infra"
                 and second["guards"]["check_b"]["status"] == "infra"
                 and second["overall"] == "infra")
        r6_detail = ("first status=%s second status=%s second overall=%s"
                     % (first["guards"]["check_b"]["status"],
                        second["guards"]["check_b"]["status"],
                        second["overall"]))
    except Exception as e:  # noqa: BLE001
        r6_ok, r6_detail = False, "crashed: %s: %s" % (type(e).__name__, e)
    check("canary-merge-normalizes-back", r6_ok, r6_detail)

    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
