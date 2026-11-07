#!/usr/bin/env python3
"""Guard: Reset All must null the expanded-detail ticker (and its diff key)
so a reload after reset cannot re-expand the old detail panel.

Background (371st review, 2026-11-07): closes the 370th run's candidate
(5). resetAllFilters ended with a no-op block that only inspected
_expandedDetailTicker ("Keep panel open? ...") and never nulled it,
while the renderTable call above it destroys the detail row via its
tbody wipe. The state/DOM mismatch had two live effects: pushState()
re-serialized detail=<ticker> into the hash after the reset (the panel
was gone but the URL still claimed it open), and a reload after a reset
re-expanded the panel for the old ticker via the hash restore at
applyHashState. The fix nulls _expandedDetailTicker -- and _activeDiffKey,
whose diff= param serializeState only emits together with detail= --
with the other state nulls at the top of resetAllFilters, before the
pushState() call near the end; the dead trailing block is deleted. This
is the same pair the hashchange-clear path already nulls together.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: resetAllFilters does not null _expandedDetailTicker.
  C2 HARD FAIL: resetAllFilters does not null _activeDiffKey (the diff
     viewer lives inside the detail panel, so its key dies with it).
  C3 HARD FAIL: either null comes AFTER the pushState() call inside
     resetAllFilters -- pushState serializes detail= from the variable,
     so a late null leaves the stale ticker in the hash.
  C4 HARD FAIL: the dead "Keep panel open?" no-op block still remains
     in js/app.js -- it inspected the variable without nulling it.
  C5 HARD FAIL: serializeState no longer gates the detail= param on
     _expandedDetailTicker -- the null is what drops the param, so a
     re-gated serializer would silently break the fix.

Usage:
  scripts/check_reset_detail_ticker.py
  scripts/check_reset_detail_ticker.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner


def extract_function_body(src, start_marker):
    """Return the brace-matched body starting at start_marker, or None."""
    idx = src.find(start_marker)
    if idx < 0:
        return None
    brace = src.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:i + 1]
    return None


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1/C2/C3: Reset All nulls both, before pushState -------------
    reset_fn = extract_function_body(app, "window.resetAllFilters = function")
    if reset_fn is None:
        failures.append("C1 resetAllFilters function not found in js/app.js")
    else:
        ticker_null = re.search(r"_expandedDetailTicker\s*=\s*null\b", reset_fn)
        if ticker_null is None:
            failures.append("C1 resetAllFilters does not null "
                            "_expandedDetailTicker -- pushState keeps "
                            "re-serializing detail=<ticker> after Reset All "
                            "and a reload re-expands the old panel")
        diff_null = re.search(r"_activeDiffKey\s*=\s*null\b", reset_fn)
        if diff_null is None:
            failures.append("C2 resetAllFilters does not null _activeDiffKey "
                            "-- the repair-diff viewer lives inside the "
                            "detail panel, so its key must die with it")
        push_idx = reset_fn.find("pushState()")
        if push_idx < 0:
            failures.append("C3 resetAllFilters has no pushState() call -- "
                            "cannot verify the null-before-push ordering")
        else:
            if ticker_null is not None and ticker_null.start() > push_idx:
                failures.append("C3 _expandedDetailTicker is nulled AFTER "
                                "pushState() in resetAllFilters -- the stale "
                                "ticker is already in the hash by then")
            if diff_null is not None and diff_null.start() > push_idx:
                failures.append("C3 _activeDiffKey is nulled AFTER pushState() "
                                "in resetAllFilters -- the stale diff key is "
                                "already serialized by then")

    # --- C4: the dead no-op block stays deleted ------------------------
    # The search is over js/app.js only, so the marker phrase quoted
    # here as a string literal cannot false-positive on this guard's
    # own source (same convention as the 370th quartile guard's C4).
    if "Keep panel open?" in app:
        failures.append("C4 js/app.js still carries the dead \"Keep panel "
                        "open?\" block -- it inspected _expandedDetailTicker "
                        "without nulling it; the block was deleted in the "
                        "371st review")

    # --- C5: serializeState still gates detail= on the ticker ---------
    ser_fn = extract_function_body(app, "function serializeState()")
    if ser_fn is None:
        failures.append("C5 serializeState function not found in js/app.js")
    elif "if (_expandedDetailTicker)" not in ser_fn:
        failures.append("C5 serializeState no longer gates detail= on "
                        "_expandedDetailTicker -- the reset null is what "
                        "drops the param, so a re-gated serializer would "
                        "silently break the fix")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: reset-detail-ticker: resetAllFilters nulls "
          "_expandedDetailTicker and _activeDiffKey before pushState; "
          "the dead no-op block is gone; serializeState still gates "
          "detail= on the ticker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
