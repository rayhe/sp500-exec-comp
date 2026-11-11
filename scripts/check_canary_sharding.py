#!/usr/bin/env python3
"""Guard: drift-canary sharded mode partitions and merges honestly.

Failure mode (416th review): the full canary suite grew to 226 guards /
~15.3 min of guard time, at the scheduled-exec ceiling, so a full run
dies mid-suite and writes no state at all. drift_canary.py gained
--shard INDEX COUNT: a shard runs its round-robin slice and merges the
fresh verdicts into the shared state. Two honest-merge invariants must
hold, or a half-re-baselined suite would claim full freshness and the
watchdog's watchdog would go blind:

  S1 partition covers every discovered guard exactly once, for every
     supported shard count (no guard in two shards, none missing).
  S2 merge advances last_run_utc ONLY when every discovered guard is
     recorded with a run_utc inside STALE_HOURS; otherwise it keeps the
     previous value. A missing guard, a stale recorded verdict, or a
     dropped guard must all keep the merge incomplete.
  S3 shard mode refuses (exit 2) with no prior state file, and refuses
     an out-of-range shard spec, without running any guard.
  S4 run_guard records a parseable per-guard run_utc (the merge's
     freshness input) on a real guard invocation.

All checks are static / subprocess-light (no headless Chromium): S3/S4
invoke drift_canary.py / a fast guard as subprocesses and assert on
their exit codes and outputs only.

Usage:
  scripts/check_canary_sharding.py              # same checks
  scripts/check_canary_sharding.py --static-only # same checks

Exit: 0 = all checks pass; 1 = a check FAILED (blocks the commit);
      2 = infra problem (missing drift_canary module).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-11-10 18:30 - created (416th review). Pins the --shard merge
    contract added the same run: partition coverage, last_run_utc
    advance-only-on-complete, shard-without-state refusal.
"""
import datetime
import json
import os
import subprocess
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


def _fake_result(status="pass", hours_ago=0):
    return {"exit": 0, "status": status, "seconds": 0.1,
            "run_utc": _iso(hours_ago), "tail": []}


def main(argv):
    # S1: partition covers all discovered guards exactly once.
    discovered = [n for n, _, _ in dc.discover_guards()]
    s1_ok = True
    s1_detail = ""
    for count in (2, 3, 4, 5, 6):
        shards = [dc.partition_guards(
            dc.discover_guards(), i, count) for i in range(1, count + 1)]
        seen = [n for shard in shards for n, _, _ in shard]
        if sorted(seen) != sorted(discovered) or len(seen) != len(set(seen)):
            s1_ok = False
            s1_detail = "count=%d: coverage broken (%d seen, %d discovered)" % (
                count, len(seen), len(discovered))
            break
        sizes = [len(s) for s in shards]
        if max(sizes) - min(sizes) > 1:
            s1_ok = False
            s1_detail = "count=%d: unbalanced shards %s" % (count, sizes)
            break
    if s1_ok:
        s1_detail = "%d guards, counts 2-6 partition exactly once, sizes differ by <=1" % len(discovered)
    check("canary-shard-partition", s1_ok, s1_detail)

    # S2: merge advances last_run_utc only on complete fresh coverage.
    names = ["check_a", "check_b", "check_c", "check_d"]
    prev = {
        "last_run_utc": _iso(41),
        "commit": "oldcommit",
        "guards": {
            "check_a": _fake_result(hours_ago=1),
            "check_b": _fake_result(hours_ago=1),
            "check_c": _fake_result(hours_ago=50),
            "check_d": _fake_result(hours_ago=50),
        },
        "overall": "pass",
    }
    # S2a: fresh results for the two stale guards -> complete, and
    # last_run_utc becomes the OLDEST fresh run (the 1h-old pair), not now.
    fresh = {"check_c": _fake_result(hours_ago=0),
             "check_d": _fake_result(hours_ago=0)}
    merged = dc.merge_shard_results(prev, fresh, names, "newcommit")
    expect_oldest = prev["guards"]["check_a"]["run_utc"]
    s2a_ok = (merged["coverage"]["complete"] is True
              and merged["coverage"]["fresh"] == 4
              and merged["last_run_utc"] == expect_oldest
              and merged["overall"] == "pass")
    check("canary-merge-advances-when-complete", s2a_ok,
          "complete=%s fresh=%d last_run_utc=%s (want oldest fresh %s)"
          % (merged["coverage"]["complete"], merged["coverage"]["fresh"],
             merged["last_run_utc"], expect_oldest))

    # S2b: one guard missing from both prev and fresh -> incomplete,
    # last_run_utc keeps the previous value.
    merged_b = dc.merge_shard_results(prev, fresh, names + ["check_e"],
                                      "newcommit")
    s2b_ok = (merged_b["coverage"]["complete"] is False
              and merged_b["last_run_utc"] == prev["last_run_utc"]
              and merged_b["coverage"]["recorded"] == 4)
    check("canary-merge-holds-on-missing-guard", s2b_ok,
          "complete=%s last_run_utc kept=%s recorded=%d"
          % (merged_b["coverage"]["complete"],
             merged_b["last_run_utc"] == prev["last_run_utc"],
             merged_b["coverage"]["recorded"]))

    # S2c: a stale recorded verdict with no fresh result -> incomplete,
    # last_run_utc keeps the previous value.
    merged_c = dc.merge_shard_results(prev, {}, names, "newcommit")
    s2c_ok = (merged_c["coverage"]["complete"] is False
              and merged_c["coverage"]["fresh"] == 2
              and merged_c["last_run_utc"] == prev["last_run_utc"])
    check("canary-merge-holds-on-stale-verdict", s2c_ok,
          "complete=%s fresh=%d last_run_utc kept=%s"
          % (merged_c["coverage"]["complete"],
             merged_c["coverage"]["fresh"],
             merged_c["last_run_utc"] == prev["last_run_utc"]))

    # S2d: a guard dropped from discovery is dropped from the merged state.
    merged_d = dc.merge_shard_results(prev, fresh, ["check_a", "check_b"],
                                      "newcommit")
    s2d_ok = (set(merged_d["guards"]) == {"check_a", "check_b"}
              and merged_d["coverage"]["recorded"] == 2)
    check("canary-merge-drops-undiscovered", s2d_ok,
          "merged guards=%s" % sorted(merged_d["guards"]))

    # S3: shard mode refuses without a prior state, and refuses an
    # out-of-range shard spec, without running any guard (fast: both
    # fail before the guard loop).
    canary = os.path.join(HERE, "drift_canary.py")
    missing_state = os.path.join(HERE, "__no_such_state__.json")
    proc = subprocess.run(
        [sys.executable, canary, "--shard", "1", "4",
         "--state", missing_state],
        cwd=os.path.join(HERE, ".."),
        capture_output=True, text=True, timeout=60)
    s3a_ok = (proc.returncode == 2
              and "prior canary state" in proc.stdout
              and "running check_" not in proc.stdout)
    check("canary-shard-refuses-without-state", s3a_ok,
          "rc=%d out=%r" % (proc.returncode, proc.stdout.strip()[:120]))
    proc = subprocess.run(
        [sys.executable, canary, "--shard", "5", "4",
         "--state", dc.DEFAULT_STATE],
        cwd=os.path.join(HERE, ".."),
        capture_output=True, text=True, timeout=60)
    s3b_ok = proc.returncode == 2 and "out of range" in proc.stdout
    check("canary-shard-refuses-bad-spec", s3b_ok,
          "rc=%d out=%r" % (proc.returncode, proc.stdout.strip()[:120]))

    # S4: run_guard records a parseable per-guard run_utc on a real
    # invocation (check_canary_freshness is fast and side-effect-free).
    res = dc.run_guard("check_canary_freshness",
                       "check_canary_freshness.py", 60)
    parsed = dc._parse_run_utc(res.get("run_utc"))
    s4_ok = parsed is not None and res.get("seconds", 999) < 5
    check("canary-run-guard-records-run-utc", s4_ok,
          "run_utc=%s seconds=%s" % (res.get("run_utc"), res.get("seconds")))

    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
