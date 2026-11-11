#!/usr/bin/env python3
"""Drift canary: periodic full (render) re-run of every regression guard.

The pre-commit hook runs each guard's static half only (fast). The render
halves (headless Chromium) validate live behavior and otherwise only run
during iteration runs, ad hoc. This canary runs every guard in FULL mode
sequentially, prints a one-line verdict per guard, and records the result
in the goal workspace so future scheduled runs know when the last full
canary ran and what it saw.

Usage:
    python3 scripts/drift_canary.py              # run all guards, record state
    python3 scripts/drift_canary.py --no-state   # run, do not write state
    python3 scripts/drift_canary.py --state PATH # override state file path
    python3 scripts/drift_canary.py --check-stale # read-only staleness check
    python3 scripts/drift_canary.py --shard 1 4  # run shard 1 of 4, merge
                                                 # into the shared state
                                                 # (chunked re-baseline)

A full canary run also reads the previous state first: if the last full
run was more than STALE_HOURS ago, it prints a STALE warning (the run
itself is the remediation, so the exit code is unaffected). The
--check-stale mode is the cheap scheduled variant: exit 0 = fresh,
1 = stale, 2 = no state file (never ran).

Sharded mode (--shard INDEX COUNT): the full suite (226 guards, ~15 min
of guard time) no longer fits inside a single scheduled exec (~15 min
ceiling), so a full run dies mid-suite and writes no state at all. A
shard runs only its round-robin slice (guards[i::COUNT]) and merges the
fresh verdicts into the shared state file, preserving the other shards'
recorded verdicts. last_run_utc only advances once EVERY discovered
guard carries a fresh (<= STALE_HOURS) run_utc, so the freshness guard
keeps its honest fail-closed meaning: a half-re-baselined suite never
claims to be fresh. Run the shards in any order across scheduled runs;
when the last missing shard lands, the merge completes and last_run_utc
becomes the oldest shard's run time. Shard mode refuses (exit 2) with
no prior state file: the first-ever baseline must be a full run.

Exit: 0 = all guards green; 1 = at least one guard FAILED;
      2 = infra problem before any guard verdict (mirrors the pre-commit
      guard contract: a guard's own exit-2 is reported as INFRA, not FAIL).

Naming: intentionally NOT scripts/check_*.py so the pre-commit hook's
auto-discovery skips it (it is a runner, not a static guard).

History: added 2026-10-06 11:30 PT run per the queued candidate from the
2026-10-06 10:25 PT iteration ("consider a periodic full guard re-run as a
drift canary"). Staleness check added 2026-10-06 14:00 PT run (queued
candidate #5 from the 11:40 PT iteration). Guard list auto-discovered
2026-10-08 03:30 PT run: the hardcoded 5-guard list had silently fallen
behind the 21-guard suite (every FY-label, coverage-desc, and vocab-bridge
guard added since Oct 6 never got a scheduled full render re-run), so the
canary now discovers scripts/check_*.py itself, same naming contract as
the pre-commit hook.
  2026-11-10 18:30 - sharded mode (416th review): the full suite hit
    226 guards / ~15.3 min of guard time, at the exec ceiling, so the
    399th run's full canary died mid-suite and the Nov 9 baseline (205
    guards, commit 9e33fec) went 41h stale with 21 newer guards never
    full-run. --shard INDEX COUNT + merge keeps the freshness contract
    honest (last_run_utc advances only on full coverage).
"""
import datetime
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/"
    "hidden_files/drift_canary_state.json"
)

# If the last full canary run is older than this, the drift window has
# lapsed: a cheap --check-stale poll (or the warning line on a full run)
# tells a scheduled run it is time for a fresh full pass.
STALE_HOURS = 48

# Auto-discovery contract (mirrors the pre-commit hook's): every
# scripts/check_*.py guard runs in FULL (no-flag) mode. The pre-commit hook
# only runs the --static-only halves, so the render halves (headless
# Chromium) otherwise run ad hoc during iteration runs only -- this canary
# is the one scheduled full re-run, and a hardcoded list silently falls
# behind as new guards are added (the 2026-10-08 finding: 16 of 21 guards
# were never re-run by the canary). Adding a new guard needs no canary edit.
#
# Per-guard timeout overrides in seconds; everything else gets the default.
# check_metadata_consistency.py has no --static-only split (its no-flag
# invocation IS the full data-truthfulness check), so it is included like
# any other guard.
DEFAULT_GUARD_TIMEOUT = 300
GUARD_TIMEOUT_OVERRIDES = {
    # "check_<thing>.py": 600,
}


def discover_guards():
    scripts = sorted(
        f for f in os.listdir(HERE)
        if f.startswith("check_") and f.endswith(".py")
        and os.path.isfile(os.path.join(HERE, f))
    )
    return [
        (os.path.splitext(s)[0], s,
         GUARD_TIMEOUT_OVERRIDES.get(s, DEFAULT_GUARD_TIMEOUT))
        for s in scripts
    ]


def partition_guards(guards, index, count):
    """Round-robin shard of the discovered guard list (1-based index).

    Guards are already in sorted order from discover_guards(); slice
    [index-1::count] is stable under appends (a newly added guard shifts
    only the shards after its sort position) and evenly sized. Raises
    ValueError on an out-of-range shard spec.
    """
    if count < 2 or index < 1 or index > count:
        raise ValueError("shard %d of %d out of range (need 1 <= index "
                         "<= count, count >= 2)" % (index, count))
    return guards[index - 1::count]


def _parse_run_utc(value):
    """Parse a recorded per-guard run_utc to an aware datetime, or None."""
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.datetime.fromisoformat(
            value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    return ts


def merge_shard_results(prev_state, fresh_results, discovered_names,
                        commit):
    """Merge one shard's fresh verdicts into the shared canary state.

    Pure function (no I/O) so the sharding guard can test it directly.
    Fresh verdicts replace their guards' recorded entries; guards outside
    the shard keep their recorded entries; entries for guards no longer
    discovered are dropped. last_run_utc advances ONLY when every
    discovered guard is recorded with a run_utc inside STALE_HOURS --
    until then it keeps the previous value, so a half-re-baselined suite
    never claims full freshness. coverage reports the merge honestly.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    prev_guards = ((prev_state or {}).get("guards") or {})
    guards = {}
    for name in discovered_names:
        if name in fresh_results:
            guards[name] = fresh_results[name]
        elif name in prev_guards:
            guards[name] = prev_guards[name]
    fresh_count = 0
    oldest = None
    for r in guards.values():
        ts = _parse_run_utc(r.get("run_utc"))
        if ts is not None and (now - ts).total_seconds() <= STALE_HOURS * 3600:
            fresh_count += 1
            if oldest is None or ts < oldest:
                oldest = ts
    complete = (set(discovered_names) == set(guards)
                and fresh_count == len(discovered_names))
    if complete:
        last_run_utc = oldest.isoformat(timespec="seconds")
    else:
        last_run_utc = (prev_state or {}).get("last_run_utc")
    statuses = {r["status"] for r in guards.values()}
    overall = ("pass" if statuses == {"pass"}
               else "fail" if "fail" in statuses else "infra")
    return {
        "last_run_utc": last_run_utc,
        "commit": commit,
        "guards": guards,
        "overall": overall,
        "coverage": {"recorded": len(guards),
                     "discovered": len(discovered_names),
                     "fresh": fresh_count,
                     "complete": complete},
        "sharded": True,
    }


def run_guard(name, script, timeout):
    path = os.path.join(HERE, script)
    # Per-guard run timestamp: the shard merge uses it to decide whether
    # the recorded verdict is still fresh (<= STALE_HOURS). Recorded even
    # on timeout/spawn failure so a failed run is visibly old, not
    # silently timeless.
    run_utc = datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds")
    if not os.path.isfile(path):
        return {"exit": 2, "status": "infra", "seconds": 0.0,
                "run_utc": run_utc, "note": "guard script missing"}
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, path],
            cwd=os.path.join(HERE, ".."),
            capture_output=True, text=True, timeout=timeout,
        )
        secs = time.time() - t0
        rc = proc.returncode
        status = "pass" if rc == 0 else ("infra" if rc == 2 else "fail")
        tail = (proc.stdout or "").strip().splitlines()[-3:]
        return {"exit": rc, "status": status, "seconds": round(secs, 1),
                "run_utc": run_utc, "tail": tail}
    except subprocess.TimeoutExpired:
        return {"exit": 2, "status": "infra",
                "seconds": round(time.time() - t0, 1),
                "run_utc": run_utc,
                "note": "timed out after %ds" % timeout}
    except OSError as e:
        return {"exit": 2, "status": "infra", "seconds": 0.0,
                "run_utc": run_utc, "note": "spawn failed: %s" % e}


def stale_hours(state_path):
    """Hours since the last full canary run recorded in state, or None."""
    try:
        with open(state_path) as f:
            ts = json.load(f).get("last_run_utc")
    except (OSError, ValueError):
        return None
    if not ts:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - dt).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return None


def main(argv):
    write_state = True
    check_stale_only = False
    state_path = DEFAULT_STATE
    shard = None
    for i, a in enumerate(argv):
        if a == "--no-state":
            write_state = False
        elif a == "--check-stale":
            check_stale_only = True
        elif a == "--state" and i + 1 < len(argv):
            state_path = argv[i + 1]
        elif a == "--shard" and i + 2 < len(argv):
            try:
                shard = (int(argv[i + 1]), int(argv[i + 2]))
            except ValueError:
                print("canary: INFRA - --shard needs integer INDEX COUNT")
                return 2

    if check_stale_only:
        # Read-only staleness poll: cheap enough for a scheduled drift check.
        hrs = stale_hours(state_path)
        if hrs is None:
            print("canary: INFRA - no canary state at %s" % state_path)
            return 2
        if hrs > STALE_HOURS:
            print("canary: STALE - last full run %.1fh ago (threshold %dh)"
                  % (hrs, STALE_HOURS))
            return 1
        print("canary: FRESH - last full run %.1fh ago (threshold %dh)"
              % (hrs, STALE_HOURS))
        return 0

    prev_hrs = stale_hours(state_path)
    if prev_hrs is not None and prev_hrs > STALE_HOURS:
        # Warning only: this full run IS the remediation.
        print("canary: STALE - last full run was %.1fh ago (threshold %dh); "
              "drift window exceeded, re-running now" % (prev_hrs, STALE_HOURS))

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=os.path.join(HERE, ".."),
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or "unknown"
    except Exception:
        commit = "unknown"

    all_guards = discover_guards()
    prev_state = None
    if shard is not None:
        # Shard mode merges into the existing state: without a prior
        # baseline there is nothing honest to merge into, so refuse
        # (exit 2) instead of writing a partial state that claims
        # coverage it does not have.
        try:
            with open(state_path) as f:
                prev_state = json.load(f)
        except (OSError, ValueError) as e:
            print("canary: INFRA - shard mode needs a prior canary state "
                  "at %s (%s); run a full canary first" % (state_path, e))
            return 2
        if not isinstance(prev_state.get("guards"), dict) \
                or not prev_state["guards"]:
            print("canary: INFRA - prior canary state at %s carries no "
                  "guard verdicts; run a full canary first" % state_path)
            return 2
        try:
            guards = partition_guards(all_guards, shard[0], shard[1])
        except ValueError as e:
            print("canary: INFRA - %s" % e)
            return 2
        prev_commit = prev_state.get("commit")
        if prev_commit and prev_commit != commit:
            print("canary: WARN - merging shard verdicts recorded at HEAD "
                  "%s with prior state at %s; re-baseline completes when "
                  "every shard has run against the current HEAD"
                  % (commit[:7], prev_commit[:7]))
        print("canary: shard %d of %d (%d of %d guards)"
              % (shard[0], shard[1], len(guards), len(all_guards)))
    else:
        guards = all_guards

    results = {}
    for name, script, timeout in guards:
        print("canary: running %s ..." % name, flush=True)
        results[name] = run_guard(name, script, timeout)
        r = results[name]
        print("canary: %-18s %-5s exit=%s %ss" % (
            name, r["status"].upper(), r["exit"], r["seconds"]))

    if shard is not None:
        state = merge_shard_results(
            prev_state, results,
            [n for n, _, _ in all_guards], commit)
        cov = state["coverage"]
        print("canary: shard %d of %d merged - recorded %d/%d guards, "
              "%d fresh, complete=%s"
              % (shard[0], shard[1], cov["recorded"], cov["discovered"],
                 cov["fresh"], cov["complete"]))
        if not cov["complete"]:
            print("canary: last_run_utc stays %s until every discovered "
                  "guard is fresh" % state["last_run_utc"])
    else:
        statuses = {r["status"] for r in results.values()}
        overall = ("pass" if statuses == {"pass"}
                   else "fail" if "fail" in statuses else "infra")
        state = {
            "last_run_utc": datetime.datetime.now(
                datetime.timezone.utc).isoformat(timespec="seconds"),
            "commit": commit,
            "guards": results,
            "overall": overall,
            "coverage": {"recorded": len(results),
                         "discovered": len(all_guards),
                         "fresh": len(results),
                         "complete": True},
            "sharded": False,
        }

    overall = state["overall"]
    if write_state:
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)
            print("canary: state written to %s" % state_path)
        except OSError as e:
            print("canary: INFRA - could not write state: %s" % e)
            overall = "infra"

    print("canary: overall %s (%s)" % (
        overall.upper(),
        ", ".join("%s=%s" % (k, v["status"]) for k, v in
                  state["guards"].items())))
    return {"pass": 0, "fail": 1, "infra": 2}[overall]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
