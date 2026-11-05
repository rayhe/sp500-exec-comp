#!/usr/bin/env python3
"""Guard: the governance distribution highlight must exist and persist.

Background (350th review, 2026-11-05): the gov-dist chart had NO
highlight function at all -- its click/keyboard paths call
filterByGovGrade, which filtered the table and raised a chip but never
showed which bar was active (the Reset All and Escape paths already
called highlightGovChart(null) behind a typeof guard, a no-op until
now), and a gov filter restored from a deep link (govmin/govmax are
restored before chart init) showed no highlight on load at all.
Consequences, all in js/charts.js / js/app.js:
  (a) clicking a gov bar filtered the table with zero visual feedback
      on the chart itself;
  (b) the .gov-count-label labels never dimmed with their bar;
  (c) the gov chip dismiss and insightResetAndSort nulled the filter
      state without clearing any highlight (once the highlight exists,
      a dismiss would leave a phantom ring);
  (d) the hash restore used parseInt on govmin/govmax, truncating the
      A bucket's max 100.1 to 100, so the restored state no longer
      matched any chart bucket and the draw-time highlight never fired
      on a deep link.

The fix adds highlightGovChart (the highlightCeoCfoBucket convention:
null restores opacity 1 / no ring / labels 1, active gets opacity 1 +
chartStrokeColor() 1.5px ring, inactive dims to 0.3 with labels at
0.4), applies the active grade at draw time (bars + count labels),
wires filterByGovGrade to highlight with the post-toggle state, wires
the chip dismiss + insightResetAndSort clear paths to clear it, and
switches the hash restore to parseFloat.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: drawGovDistChart does not apply _activeGovGrade to bar
     opacity at draw time (active 1 / inactive 0.3 / none 1).
  C2 HARD FAIL: drawGovDistChart does not ring the active bar at draw
     time (chartStrokeColor, 1.5).
  C3 HARD FAIL: highlightGovChart(null) does not clear the bar stroke /
     stroke-width (phantom ring after clear).
  C4 HARD FAIL: highlightGovChart still uses the hardcoded '#fff' ring,
     or does not dim the .gov-count-label labels.
  C5 HARD FAIL: drawGovDistChart does not apply _activeGovGrade to the
     .gov-count-label opacity at draw time (active 1 / inactive 0.4 /
     none 1).
  C6 HARD FAIL: filterByGovGrade does not call highlightGovChart with
     the post-toggle state after renderTable.
  C7 HARD FAIL: the gov chip dismiss does not call highlightGovChart(null).
  C8 HARD FAIL: insightResetAndSort does not clear the gov highlight
     (stale ring after an insight action resets the filter).
  C9 HARD FAIL: the hash restore still uses parseInt on govmin/govmax
     (truncates the A bucket's 100.1 max, breaking the draw-time match).

Usage:
  scripts/check_gov_highlight.py
  scripts/check_gov_highlight.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
CHARTS_JS = f"{REPO}/js/charts.js"
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
        charts = open(CHARTS_JS, encoding="utf-8").read()
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    draw_body = extract_function_body(charts, "function drawGovDistChart")
    if draw_body is None:
        print("FAIL: C1 drawGovDistChart function not found in js/charts.js")
        return 1
    hl_body = extract_function_body(charts, "window.highlightGovChart = function")
    if hl_body is None:
        print("FAIL: C3 highlightGovChart function not found in js/charts.js")
        return 1

    # --- C1: draw-time bar opacity consults the active grade --------
    bar_start = draw_body.find(".attr('fill', function(b) { return b.color; })")
    bar_end = draw_body.find(".style('cursor', 'pointer')", bar_start + 1)
    if bar_start < 0 or bar_end < 0:
        failures.append("C1 Gov bar chain markers not found in "
                        "drawGovDistChart")
        bar_chain = ""
    else:
        bar_chain = draw_body[bar_start:bar_end]
        if "window._activeGovGrade" not in bar_chain:
            failures.append("C1 drawGovDistChart does not apply "
                            "_activeGovGrade to bar opacity at draw time "
                            "-- a redraw / deep link drops the highlight")
        elif "? 1 : 0.3" not in bar_chain:
            failures.append("C1 draw-time bar opacity does not dim "
                            "inactive bars to 0.3 (active 1 / inactive "
                            "0.3 / none 1)")

    # --- C2: draw-time ring on the active bar ------------------------
    if "attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5)" not in bar_chain:
        failures.append("C2 drawGovDistChart does not ring the active bar "
                        "at draw time (chartStrokeColor, 1.5)")

    # --- C3: highlight clear path clears the stroke -----------------
    null_idx = hl_body.find("if (min == null)")
    if null_idx < 0:
        failures.append("C3 highlightGovChart null branch not found")
    else:
        null_branch = hl_body[null_idx:null_idx + 400]
        if "attr('stroke', 'none')" not in null_branch:
            failures.append("C3 highlightGovChart(null) does not clear the "
                            "bar stroke -- phantom ring survives chip "
                            "dismiss / Reset All / Escape")
        if "attr('stroke-width', 0)" not in null_branch:
            failures.append("C3 highlightGovChart(null) does not clear the "
                            "bar stroke-width")

    # --- C4: highlight ring is theme-aware; labels dim --------------
    if "'#fff'" in hl_body:
        failures.append("C4 highlightGovChart still uses the hardcoded "
                        "'#fff' ring instead of chartStrokeColor()")
    if "chartStrokeColor()" not in hl_body:
        failures.append("C4 highlightGovChart does not use "
                        "chartStrokeColor() for the active ring")
    if ".gov-count-label" not in hl_body:
        failures.append("C4 highlightGovChart does not dim the "
                        ".gov-count-label labels with the bucket")

    # --- C5: draw-time count-label opacity ---------------------------
    lbl_start = draw_body.find("g.selectAll('.gov-count-label')")
    if lbl_start < 0:
        failures.append("C5 .gov-count-label chain not found in "
                        "drawGovDistChart")
    else:
        lbl_chain = draw_body[lbl_start:lbl_start + 1200]
        if "window._activeGovGrade" not in lbl_chain:
            failures.append("C5 drawGovDistChart does not apply "
                            "_activeGovGrade to .gov-count-label opacity at "
                            "draw time")
        elif "? 1 : 0.4" not in lbl_chain:
            failures.append("C5 draw-time .gov-count-label opacity does not "
                            "dim inactive labels to 0.4")

    # --- C6: filterByGovGrade highlights with post-toggle state -----
    setter_body = extract_function_body(app, "window.filterByGovGrade = function")
    if setter_body is None:
        failures.append("C6 filterByGovGrade function not found in js/app.js")
    else:
        if "highlightGovChart(" not in setter_body:
            failures.append("C6 filterByGovGrade does not call "
                            "highlightGovChart after setting the grade")
        elif "window._activeGovGrade ? window._activeGovGrade.min : null" not in setter_body:
            failures.append("C6 filterByGovGrade does not pass the "
                            "post-toggle state to highlightGovChart -- a "
                            "toggle-off click would re-highlight")

    # --- C7: gov chip dismiss clears the highlight ------------------
    chip_body = extract_function_body(app, "function updateGovFilterIndicator")
    if chip_body is None:
        failures.append("C7 updateGovFilterIndicator function not found in js/app.js")
    elif "highlightGovChart(null, null)" not in chip_body:
        failures.append("C7 the gov chip dismiss does not call "
                        "highlightGovChart(null) -- the bar stays ringed "
                        "while the filter is gone")

    # --- C8: insightResetAndSort clears the highlight ---------------
    irs_body = extract_function_body(app, "function insightResetAndSort")
    if irs_body is None:
        failures.append("C8 insightResetAndSort function not found in js/app.js")
    elif "highlightGovChart(null)" not in irs_body:
        failures.append("C8 insightResetAndSort does not clear the gov "
                        "highlight -- an insight action leaves the bars "
                        "ringed while the filter is gone")

    # --- C9: hash restore keeps the fractional bucket max ------------
    if "parseFloat(state.govmin)" not in app or "parseFloat(state.govmax)" not in app:
        failures.append("C9 the gov hash restore does not use parseFloat "
                        "for govmin/govmax")
    if "parseInt(state.govmin)" in app or "parseInt(state.govmax)" in app:
        failures.append("C9 the gov hash restore still uses parseInt -- the "
                        "A bucket's 100.1 max truncates to 100 and the "
                        "draw-time highlight never matches on a deep link")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: gov-highlight: draw re-applies the active grade (bars + "
          "labels), setter/chip/insight paths highlight and clear, hash "
          "restore keeps the fractional max")
    return 0


if __name__ == "__main__":
    sys.exit(main())
