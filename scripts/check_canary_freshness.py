#!/usr/bin/env python3
"""Regression guard: the drift canary itself must not go stale (83rd).

The full guard suite has two halves: the pre-commit hook runs every guard's
STATIC half (fast), and scripts/drift_canary.py periodically runs every
guard in FULL mode (headless-Chromium render halves) as a drift tripwire.
The canary even ships a --check-stale mode documented as "cheap enough for
a scheduled drift check" - but nothing ever invokes it. The only thing
keeping the full render re-run on cadence is the iteration log's
hand-written "next-run candidates" line (same hand-convention pattern the
82nd guard closed for log-prose numbers).

Failure mode: if the scheduled full canary stops running (cron hiccup, a
run skipped, the operator forgets), commits keep landing with the static
halves green while the render halves go un-run for days. A render-only
regression then ships with every guard nominally passing - the watchdog's
watchdog is missing, and nothing notices.

This guard asserts the canary cadence itself, fail-closed at commit time:
if the last recorded full canary run is older than STALE_HOURS (mirroring
drift_canary.py's own 48h threshold), the NEXT commit is blocked until a
fresh full canary runs. The guard reads the state file the canary writes;
it needs no network and takes <1s.

Checks (all static - one local JSON read):
  S1 state file exists, parses as JSON, and carries a last_run_utc
     (missing file, unreadable JSON, or unparsable timestamp -> exit 2
     INFRA advisory, not a commit blocker, per the pre-commit contract;
     a deleted state file must not wedge every commit - that failure is
     loud enough on its own at the next iteration run)
  S2 age of last_run_utc against STALE_HOURS
     (fresh -> PASS; stale -> HARD FAIL naming the hours-since and the
     remediation command; a fresh state whose recorded guard verdicts
     are not all green is the canary's own report, not this guard's -
     this guard pins cadence only)

Usage:
  scripts/check_canary_freshness.py              # same checks
  scripts/check_canary_freshness.py --static-only # same checks
  scripts/check_canary_freshness.py --state PATH  # override state path
                                                  # (used by negative tests)

Exit: 0 = last full canary fresh; 1 = stale (loud);
      2 = state unreadable (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 18:00 - created (18:00 PT iteration). Closes the
    watchdog-staleness class: drift_canary.py's --check-stale mode was
    documented "cheap enough for a scheduled drift check" yet invoked by
    nothing, and the full-render re-run cadence lived only in the
    iteration log's hand-written next-run candidates list. Negative tests
    (all in /tmp, real tree untouched): stale fixture (50h) -> rc=1
    naming hours + remediation; fresh fixture (2h) -> rc=0; missing
    state -> rc=2 infra; corrupt JSON -> rc=2 infra; unparsable
    timestamp -> rc=2 infra.
"""
import datetime
import json
import os
import sys

CANARY_STATE = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/"
    "hidden_files/drift_canary_state.json"
)
STALE_HOURS = 48  # mirrors drift_canary.py STALE_HOURS

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _state_path(argv):
    if "--state" in argv:
        i = argv.index("--state")
        if i + 1 < len(argv):
            return argv[i + 1]
    return CANARY_STATE


def _parse_ts(value):
    """Parse an ISO-8601 timestamp to an aware datetime, or None."""
    if not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        ts = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    return ts


def main(argv):
    path = _state_path(argv)

    # S1: state readable and carries a parseable last_run_utc (INFRA on any
    # read/parse failure - fail-open so a missing state cannot wedge commits)
    try:
        with open(path) as f:
            state = json.load(f)
    except FileNotFoundError:
        print("INFRA: canary state file not found: %s - no freshness verdict "
              "possible (advisory only)" % path)
        return 2
    except (OSError, ValueError) as e:
        print("INFRA: canary state unreadable (%s) - no freshness verdict "
              "possible (advisory only)" % e)
        return 2

    ts = _parse_ts(state.get("last_run_utc"))
    if ts is None:
        print("INFRA: canary state has no parseable last_run_utc - no freshness "
              "verdict possible (advisory only)")
        return 2

    # S2: freshness against the shared 48h cadence (fail-closed)
    now = datetime.datetime.now(datetime.timezone.utc)
    age_hours = (now - ts).total_seconds() / 3600.0
    fresh = age_hours <= STALE_HOURS
    detail = "last full canary %.1fh ago (threshold %dh)" % (age_hours, STALE_HOURS)
    check("canary-freshness", fresh,
          detail if fresh else
          detail + " - run: python3 scripts/drift_canary.py (18:00 PT slot)")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
