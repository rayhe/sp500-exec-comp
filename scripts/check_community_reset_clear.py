#!/usr/bin/env python3
"""Guard: Reset All / insight actions must clear the community filter's visuals.

Background (356th review, 2026-11-05): Reset All nulled
_activeCommunityFilter and removed the community chip, but the filter's
three visuals all live outside the table, so renderTable's tbody wipe
never touches them:
  1. network legend item keeps .community-legend-active
  2. community-metrics quartile zone keeps .cm-bp-zone-clicked
  3. scatter keeps its median crosshairs + floating "Community: X" label
     (drawn at scatter-draw time only; neither reset path redraws the
     scatter, and neither nulled _activeCommunityScatterTickers)
The insight path already removed the two classes inline (app.js ~3270)
but also never redrew the scatter or nulled the ticker set. Root cause
of the blind spot: resetAllFilters already called
window.clearCommunityHighlight() -- but that function was never defined
anywhere, so the typeof guard silently no-op'd and the call sites looked
covered. (Its peer-dist / quartile / position siblings are the same kind
of dead call, but those visuals self-correct: the detail panel is wiped
by renderTable's tbody.innerHTML = '', so they re-render from state on
the next open. Community's three visuals do not.)
The fix defines window.clearCommunityHighlight in js/app.js (clear the
two classes, null the scatter ticker set, redraw the scatter only when
a community scatter was actually showing -- a blind redraw would
clobber brush/zoom state on every Reset), lights up the existing
resetAllFilters call, and adds the call to insightResetAndSort's
community branch. Escape deliberately keeps community (343rd review),
so it must NOT call this.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: window.clearCommunityHighlight is not defined in js/app.js.
  C2 HARD FAIL: the function does not remove .community-legend-active.
  C3 HARD FAIL: the function does not remove .cm-bp-zone-clicked.
  C4 HARD FAIL: the function does not null _activeCommunityScatterTickers.
  C5 HARD FAIL: the function does not redraw the scatter
     (drawScatterChart) when a community scatter was showing, or the
     redraw is unconditional (would clobber brush/zoom on every Reset).
  C6 HARD FAIL: resetAllFilters does not call clearCommunityHighlight
     (the dead call site this review revives).
  C7 HARD FAIL: insightResetAndSort does not call clearCommunityHighlight
     in its community branch.
  C8 HARD FAIL: the Escape clear-all path calls clearCommunityHighlight
     or nulls _activeCommunityFilter -- Escape keeps community by design
     (343rd review); only the two reset paths may clear it.
  C9 HARD FAIL: the VMRK _index_note in data/compensation.json does not
     record the 2026-11-05 live EDGAR re-check (still no post-merger
     DEF 14A; new filings today were a 144 and an 8-K only).

Usage:
  scripts/check_community_reset_clear.py
  scripts/check_community_reset_clear.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import json
import os
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"
COMP_JSON = f"{REPO}/data/compensation.json"

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
        print(f"INFRA: cannot read js/app.js: {exc}")
        return 2

    failures = []

    # --- C1: the shared clear exists --------------------------------
    clear_fn = extract_function_body(app, "window.clearCommunityHighlight = function")
    if clear_fn is None:
        failures.append("C1 window.clearCommunityHighlight is not defined "
                        "in js/app.js -- resetAllFilters calls a function "
                        "that does not exist (typeof guard silently no-ops)")
        # Without the function the C2-C5 checks are vacuous; skip them
        # but still run the call-site checks below.
    else:
        # --- C2: legend class removed -------------------------------
        if "community-legend-active" not in clear_fn:
            failures.append("C2 clearCommunityHighlight does not remove "
                            ".community-legend-active -- the network legend "
                            "stays highlighted after Reset All")
        # --- C3: quartile-zone class removed ------------------------
        if "cm-bp-zone-clicked" not in clear_fn:
            failures.append("C3 clearCommunityHighlight does not remove "
                            ".cm-bp-zone-clicked -- the community-metrics "
                            "quartile zone stays clicked after Reset All")
        # --- C4: scatter ticker set nulled --------------------------
        if "_activeCommunityScatterTickers = null" not in clear_fn:
            failures.append("C4 clearCommunityHighlight does not null "
                            "_activeCommunityScatterTickers -- the scatter "
                            "crosshair condition still sees a live set")
        # --- C5: scatter redrawn, but only when showing ------------
        if "drawScatterChart" not in clear_fn:
            failures.append("C5 clearCommunityHighlight never redraws the "
                            "scatter -- the median crosshairs + floating "
                            "label survive every reset (draw-time only)")
        elif "hadScatter" not in clear_fn and "hadLegend" not in clear_fn:
            failures.append("C5 clearCommunityHighlight redraws the scatter "
                            "unconditionally -- a blind redraw on every "
                            "Reset clobbers brush/zoom state")

    # --- C6: Reset All calls it ------------------------------------
    reset_fn = extract_function_body(app, "window.resetAllFilters = function")
    if reset_fn is None:
        failures.append("C6 resetAllFilters function not found in js/app.js")
    elif "clearCommunityHighlight()" not in reset_fn:
        failures.append("C6 resetAllFilters does not call "
                        "clearCommunityHighlight() -- the community visuals "
                        "survive Reset All")

    # --- C7: insightResetAndSort calls it ---------------------------
    insight_fn = extract_function_body(app, "function insightResetAndSort")
    if insight_fn is None:
        failures.append("C7 insightResetAndSort function not found in js/app.js")
    elif "clearCommunityHighlight()" not in insight_fn:
        failures.append("C7 insightResetAndSort does not call "
                        "clearCommunityHighlight() -- the scatter "
                        "crosshairs + label survive insight actions")

    # --- C8: Escape must NOT clear community ------------------------
    # The Escape clear-all block is the only other reset path; it keeps
    # community by design (343rd review) and announces it as kept.
    esc_idx = app.find("Filters cleared; still active: ")
    if esc_idx < 0:
        failures.append("C8 Escape announcement not found -- cannot verify "
                        "the kept-dims invariant")
    else:
        esc_region = app[max(0, esc_idx - 6000):esc_idx + 3000]
        if "clearCommunityHighlight()" in esc_region:
            failures.append("C8 the Escape path calls clearCommunityHighlight "
                            "-- Escape keeps community by design (343rd "
                            "review); only Reset All / insight actions clear it")
        if "_activeCommunityFilter = null" in esc_region:
            failures.append("C8 the Escape path nulls _activeCommunityFilter "
                            "-- Escape keeps community by design (343rd review)")

    # --- C9: VMRK re-check recorded ---------------------------------
    try:
        comp = json.load(open(COMP_JSON, encoding="utf-8"))
        vmrk = next((c for c in comp["companies"] if c.get("ticker") == "VMRK"), None)
        if vmrk is None:
            failures.append("C9 VMRK record missing from data/compensation.json")
        elif "Re-checked 2026-11-05" not in (vmrk.get("_index_note") or ""):
            failures.append("C9 VMRK _index_note does not record the "
                            "2026-11-05 live EDGAR re-check (still no "
                            "post-merger DEF 14A)")
    except (OSError, ValueError, KeyError) as exc:
        print(f"INFRA: cannot read data/compensation.json: {exc}")
        return 2

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: community-reset-clear: clearCommunityHighlight is defined "
          "and clears legend + quartile-zone classes, nulls the scatter "
          "ticker set and conditionally redraws the scatter; Reset All and "
          "insightResetAndSort call it; Escape keeps community; VMRK "
          "2026-11-05 EDGAR re-check recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
