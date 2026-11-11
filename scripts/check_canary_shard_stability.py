#!/usr/bin/env python3
"""Guard: drift-canary shard assignment is stable under roster changes.

Failure mode (418th review): partition_guards used positional
round-robin (guards[index-1::count]) over the sorted guard list, so
adding one guard reshuffled every shard after its sort position. The
417th run added check_canary_merge_robust.py mid-baseline and shard 2
then re-ran most of shard 1's guards: the re-baseline stalled at
60/228 fresh instead of ~114. partition_guards now assigns by
sha256(name) mod count, so a guard's shard depends only on its own
name.

  ST1 inserting a guard (mid-list, head, tail) leaves every existing
      guard's shard unchanged, for every supported shard count, and
      the new guard lands in exactly one shard.
  ST2 removing a guard leaves every remaining guard's shard unchanged.
  ST3 the live roster is stable: adding a hypothetical guard to the
      real 228-guard discovery moves no real guard (the exact
      regression from the 417th run).

All checks are pure-function (no subprocess, no Chromium).

Usage:
  scripts/check_canary_shard_stability.py              # same checks
  scripts/check_canary_shard_stability.py --static-only # same checks

Exit: 0 = all checks pass; 1 = a check FAILED (blocks the commit);
      2 = infra problem (missing drift_canary module).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-11-10 21:15 - created (418th review). Pins the stable-hash
    sharding fix: roster changes never move another guard's shard.
"""
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


def _shard_map(guards, count):
    """name -> shard index for one roster at one shard count."""
    mapping = {}
    for i in range(1, count + 1):
        for n, _, _ in dc.partition_guards(guards, i, count):
            mapping[n] = i
    return mapping


def _fake_guards(names):
    return [(n, n + ".py", 300) for n in sorted(names)]


def main(argv):
    base_names = ["check_%s" % c for c in
                  "alpha beta gamma delta epsilon zeta eta theta".split()]
    base = _fake_guards(base_names)

    # ST1: insertion at head, middle, and tail moves no existing guard.
    st1_ok = True
    st1_detail = ""
    for new in ("check_aaa_first", "check_delta2_mid", "check_zzz_last"):
        grown = _fake_guards(base_names + [new])
        for count in (2, 3, 4, 5, 6):
            before = _shard_map(base, count)
            after = _shard_map(grown, count)
            moved = [n for n in base_names if before[n] != after[n]]
            if moved or len(after) != len(base_names) + 1 \
                    or set(after) - set(base_names) != {new}:
                st1_ok = False
                st1_detail = ("insert %s count=%d moved %s"
                              % (new, count, moved[:3]))
                break
        if not st1_ok:
            break
    if st1_ok:
        st1_detail = "head/mid/tail inserts move no guard, counts 2-6"
    check("canary-shard-stable-under-insert", st1_ok, st1_detail)

    # ST2: removal moves no remaining guard.
    st2_ok = True
    st2_detail = ""
    shrunk = _fake_guards([n for n in base_names if n != "check_delta"])
    for count in (2, 3, 4, 5, 6):
        before = _shard_map(base, count)
        after = _shard_map(shrunk, count)
        moved = [n for n in after if before[n] != after[n]]
        if moved or set(after) != set(base_names) - {"check_delta"}:
            st2_ok = False
            st2_detail = "count=%d moved %s" % (count, moved[:3])
            break
    if st2_ok:
        st2_detail = "removal moves no guard, counts 2-6"
    check("canary-shard-stable-under-remove", st2_ok, st2_detail)

    # ST3: the live roster is stable (the 417th-run regression, replayed
    # on the real discovery: adding a mid-list guard must not move any
    # of the 228 real guards).
    live = dc.discover_guards()
    live_names = [n for n, _, _ in live]
    grown = _fake_guards(live_names + ["check_canary_mid_roster_probe"])
    st3_ok = True
    st3_detail = ""
    for count in (2, 3, 4, 5, 6):
        before = _shard_map(live, count)
        after = _shard_map(grown, count)
        moved = [n for n in live_names if before[n] != after[n]]
        if moved:
            st3_ok = False
            st3_detail = "count=%d moved %d guards, e.g. %s" % (
                count, len(moved), moved[:3])
            break
    if st3_ok:
        st3_detail = "%d live guards unmoved by a mid-list insert, counts 2-6" % len(live_names)
    check("canary-shard-live-roster-stable", st3_ok, st3_detail)

    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
