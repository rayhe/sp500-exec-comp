#!/usr/bin/env python3
"""Guard: Reset All must clear the quartile filter's zone highlight, and
the two dead sibling clear calls must stay deleted.

Background (370th review, 2026-11-07): resetAllFilters carried three
guarded clear calls -- peer-dist, quartile, position -- of which only
the community sibling (clearCommunityHighlight, 356th review) was ever
defined. The 356th review filed all three as self-correcting, but its
stated mechanism (the detail panel is wiped by renderTable's tbody
wipe) is wrong for quartile: the quartile zone (.cm-bp-zone-clicked)
lives in the network graph's community-metrics panel (network.js), not
in the detail panel, and neither reset path redraws that panel. The
zone only cleared incidentally -- clearCommunityHighlight sweeps the
class document-wide and Reset All calls it one line before the
quartile call -- an undocumented coupling misattributed to the
community filter (only the quartile click ever adds the class; the
community row click adds .community-legend-active and .cm-active,
never the zone class). The fix defines window.clearQuartileHighlight
(remove the zone class; the caller owns filter state + chip) and
lights up the existing call site. Peer-dist and position genuinely
are self-correcting -- their visuals live in the detail row, which
renderTable destroys -- so their dead calls are deleted, not defined:
a real clear function for them would have no persistent DOM to clear.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: window.clearQuartileHighlight is not defined in js/app.js.
  C2 HARD FAIL: the function does not remove .cm-bp-zone-clicked.
  C3 HARD FAIL: resetAllFilters does not call clearQuartileHighlight()
     (the dead call site this review revives).
  C4 HARD FAIL: a dead peer-dist or position clear call still remains
     anywhere in js/app.js -- both were deleted in this review because
     their visuals die with the detail row; a re-added call would be a
     call to a function that does not exist.
  C5 HARD FAIL: the Escape clear-all path calls clearQuartileHighlight()
     or nulls _activeQuartileFilter -- Escape keeps quartile by design
     (339th review); only Reset All / insight actions clear it.

Usage:
  scripts/check_quartile_reset_clear.py
  scripts/check_quartile_reset_clear.py --static-only

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

ESC_START = "// Clear all filters and search"
ESC_END = "// If in search, blur it"


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

    # --- C1/C2: the shared clear exists and removes the zone class ----
    clear_fn = extract_function_body(app, "window.clearQuartileHighlight = function")
    if clear_fn is None:
        failures.append("C1 window.clearQuartileHighlight is not defined "
                        "in js/app.js -- resetAllFilters calls a function "
                        "that does not exist (typeof guard silently no-ops)")
    else:
        if "cm-bp-zone-clicked" not in clear_fn or "classList.remove" not in clear_fn:
            failures.append("C2 clearQuartileHighlight does not remove "
                            ".cm-bp-zone-clicked -- the network community-"
                            "metrics quartile zone stays clicked after "
                            "Reset All")

    # --- C3: Reset All calls it ---------------------------------------
    reset_fn = extract_function_body(app, "window.resetAllFilters = function")
    if reset_fn is None:
        failures.append("C3 resetAllFilters function not found in js/app.js")
    elif "clearQuartileHighlight()" not in reset_fn:
        failures.append("C3 resetAllFilters does not call "
                        "clearQuartileHighlight() -- the quartile-zone "
                        "visual survives Reset All")

    # --- C4: the two deleted dead calls stay deleted -------------------
    # The search is over js/app.js only, so the dead ids quoted here as
    # string literals cannot false-positive on this guard's own source.
    for dead in ("clearPeerDistHighlight()", "clearPositionHighlight()"):
        if dead in app:
            failures.append("C4 js/app.js still carries the dead call %s "
                            "-- the function is not defined and its visual "
                            "dies with the detail row; the call was deleted "
                            "in the 370th review" % dead)

    # --- C5: Escape must NOT clear quartile ----------------------------
    esc_start = app.find(ESC_START)
    esc_end = app.find(ESC_END, esc_start + 1) if esc_start >= 0 else -1
    if esc_start < 0 or esc_end < 0:
        failures.append("C5 Escape clear-all branch markers not found -- "
                        "cannot verify the kept-quartile invariant")
    else:
        branch = app[esc_start:esc_end]
        if "clearQuartileHighlight()" in branch:
            failures.append("C5 the Escape path calls clearQuartileHighlight "
                            "-- Escape keeps quartile by design (339th "
                            "review); only Reset All / insight actions "
                            "clear it")
        if re.search(r"window\._activeQuartileFilter\s*=\s*null", branch):
            failures.append("C5 the Escape path nulls _activeQuartileFilter "
                            "-- Escape keeps quartile by design (339th "
                            "review)")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: quartile-reset-clear: clearQuartileHighlight is defined "
          "and removes .cm-bp-zone-clicked; Reset All calls it; the "
          "peer-dist / position dead calls are gone; Escape keeps quartile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
