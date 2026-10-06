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

A full canary run also reads the previous state first: if the last full
run was more than STALE_HOURS ago, it prints a STALE warning (the run
itself is the remediation, so the exit code is unaffected). The
--check-stale mode is the cheap scheduled variant: exit 0 = fresh,
1 = stale, 2 = no state file (never ran).

Exit: 0 = all guards green; 1 = at least one guard FAILED;
      2 = infra problem before any guard verdict (mirrors the pre-commit
      guard contract: a guard's own exit-2 is reported as INFRA, not FAIL).

Naming: intentionally NOT scripts/check_*.py so the pre-commit hook's
auto-discovery skips it (it is a runner, not a static guard).

History: added 2026-10-06 11:30 PT run per the queued candidate from the
2026-10-06 10:25 PT iteration ("consider a periodic full guard re-run as a
drift canary"). Staleness check added 2026-10-06 14:00 PT run (queued
candidate #5 from the 11:40 PT iteration).
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

# (name, script filename, timeout seconds)
GUARDS = [
    ("metadata-gate", "check_metadata_consistency.py", 120),
    ("methodology-buttons", "check_methodology_buttons.py", 300),
    ("scrollspy-nav", "check_scrollspy_nav.py", 300),
    ("minimap-toggle", "check_minimap_toggle.py", 300),
    ("scroll-hint", "check_scroll_hint.py", 300),
]


def run_guard(name, script, timeout):
    path = os.path.join(HERE, script)
    if not os.path.isfile(path):
        return {"exit": 2, "status": "infra", "seconds": 0.0,
                "note": "guard script missing"}
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
                "tail": tail}
    except subprocess.TimeoutExpired:
        return {"exit": 2, "status": "infra",
                "seconds": round(time.time() - t0, 1),
                "note": "timed out after %ds" % timeout}
    except OSError as e:
        return {"exit": 2, "status": "infra", "seconds": 0.0,
                "note": "spawn failed: %s" % e}


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
    for i, a in enumerate(argv):
        if a == "--no-state":
            write_state = False
        elif a == "--check-stale":
            check_stale_only = True
        elif a == "--state" and i + 1 < len(argv):
            state_path = argv[i + 1]

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

    results = {}
    for name, script, timeout in GUARDS:
        print("canary: running %s ..." % name, flush=True)
        results[name] = run_guard(name, script, timeout)
        r = results[name]
        print("canary: %-18s %-5s exit=%s %ss" % (
            name, r["status"].upper(), r["exit"], r["seconds"]))

    statuses = {r["status"] for r in results.values()}
    overall = ("pass" if statuses == {"pass"}
               else "fail" if "fail" in statuses else "infra")

    state = {
        "last_run_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "guards": results,
        "overall": overall,
    }
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
        ", ".join("%s=%s" % (k, v["status"]) for k, v in results.items())))
    return {"pass": 0, "fail": 1, "infra": 2}[overall]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
