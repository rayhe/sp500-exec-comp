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

Exit: 0 = all guards green; 1 = at least one guard FAILED;
      2 = infra problem before any guard verdict (mirrors the pre-commit
      guard contract: a guard's own exit-2 is reported as INFRA, not FAIL).

Naming: intentionally NOT scripts/check_*.py so the pre-commit hook's
auto-discovery skips it (it is a runner, not a static guard).

History: added 2026-10-06 11:30 PT run per the queued candidate from the
2026-10-06 10:25 PT iteration ("consider a periodic full guard re-run as a
drift canary").
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


def main(argv):
    write_state = True
    state_path = DEFAULT_STATE
    for i, a in enumerate(argv):
        if a == "--no-state":
            write_state = False
        elif a == "--state" and i + 1 < len(argv):
            state_path = argv[i + 1]

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
