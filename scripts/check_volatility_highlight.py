#!/usr/bin/env python3
"""Guard: the volatility distribution highlight must exist and persist.

Background (350th review, 2026-11-05): the volatility-dist chart had NO
highlight function at all -- its click/keyboard setters set
_activeVolatilityBucket and re-rendered the table, but the bars never
showed which bucket was active (the Reset All and Escape paths already
called highlightVolatilityBucket(null) behind a typeof guard, a no-op
until now), and redrawAllCharts (resize / theme toggle) rebuilt the
bars at a flat 0.85. Consequences, all in js/charts.js:
  (a) clicking a volatility bar filtered the table with zero visual
      feedback on the chart itself;
  (b) mouseout reset every bar to a flat 0.85, so hovering the active
      bar then leaving dropped it to 0.85, and hovering an inactive bar
      then leaving lifted it to 0.85 instead of its dimmed 0.25;
  (c) the .vol-count labels never dimmed with their bar.

The fix adds highlightVolatilityBucket (the highlightCeoCfoBucket
convention: null restores 0.85 / no ring / labels 1, active gets opacity
1 + chartStrokeColor() 1.5px ring, inactive dims to 0.25 with labels at
0.4), applies the active bucket at draw time (bars + count labels),
makes mouseout restore the draw-time state, wires the click/keyboard
paths to highlight, and wires the chip dismiss + insightResetAndSort
clear paths to clear it.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: drawVolatilityDistChart does not apply
     _activeVolatilityBucket to bar opacity at draw time (active 1 /
     inactive 0.25 / none 0.85).
  C2 HARD FAIL: drawVolatilityDistChart does not ring the active bar at
     draw time (chartStrokeColor, 1.5).
  C3 HARD FAIL: the bar mouseout handler does not restore the
     draw-time highlight from _activeVolatilityBucket (flat 0.85 reset).
  C4 HARD FAIL: highlightVolatilityBucket(null) does not clear the bar
     stroke / stroke-width (phantom ring after clear).
  C5 HARD FAIL: highlightVolatilityBucket still uses the hardcoded '#fff'
     ring, or does not dim the .vol-count labels.
  C6 HARD FAIL: drawVolatilityDistChart does not apply
     _activeVolatilityBucket to the .vol-count label opacity at draw
     time (active 1 / inactive 0.4 / none 1).
  C7 HARD FAIL: the click and keyboard paths do not call
     highlightVolatilityBucket after setting the bucket.
  C8 HARD FAIL: insightResetAndSort does not clear the volatility
     highlight (stale ring after an insight action resets the filter).

Usage:
  scripts/check_volatility_highlight.py
  scripts/check_volatility_highlight.py --static-only

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

    draw_body = extract_function_body(charts, "function drawVolatilityDistChart")
    if draw_body is None:
        print("FAIL: C1 drawVolatilityDistChart function not found in js/charts.js")
        return 1
    hl_body = extract_function_body(charts, "window.highlightVolatilityBucket = function")
    if hl_body is None:
        print("FAIL: C4 highlightVolatilityBucket function not found in js/charts.js")
        return 1

    # --- C1: draw-time bar opacity consults the active bucket -------
    bar_start = draw_body.find(".attr('opacity', function(b)")
    bar_end = draw_body.find(".style('cursor', 'pointer')", bar_start + 1)
    if bar_start < 0 or bar_end < 0:
        failures.append("C1 Volatility bar chain markers not found in "
                        "drawVolatilityDistChart")
    else:
        bar_chain = draw_body[bar_start:bar_end]
        if "window._activeVolatilityBucket" not in bar_chain:
            failures.append("C1 drawVolatilityDistChart does not apply "
                            "_activeVolatilityBucket to bar opacity at draw "
                            "time -- a redraw drops the active highlight")
        elif "? 1 : 0.25" not in bar_chain:
            failures.append("C1 draw-time bar opacity does not dim "
                            "inactive bars to 0.25 (active 1 / inactive "
                            "0.25 / none 0.85)")

    # --- C2: draw-time ring on the active bar ------------------------
    if "attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5)" not in (bar_chain if bar_start >= 0 and bar_end >= 0 else ""):
        failures.append("C2 drawVolatilityDistChart does not ring the active "
                        "bar at draw time (chartStrokeColor, 1.5)")

    # --- C3: mouseout restores the draw-time highlight --------------
    mo = draw_body.find(".on('mouseout'")
    if mo < 0:
        failures.append("C3 Volatility bar mouseout handler not found")
    else:
        mo_end = draw_body.find(".on('click'", mo + 1)
        mo_body = draw_body[mo:mo_end if mo_end > 0 else len(draw_body)]
        if "window._activeVolatilityBucket" not in mo_body:
            failures.append("C3 Volatility mouseout does not consult "
                            "_activeVolatilityBucket -- hovering then leaving "
                            "clobbers the highlight")
        if re.search(r"\.attr\('opacity', 0\.85\)", mo_body):
            failures.append("C3 Volatility mouseout still resets bars to a "
                            "flat 0.85 instead of the draw-time state")

    # --- C4: highlight clear path clears the stroke -----------------
    null_idx = hl_body.find("if (min == null)")
    if null_idx < 0:
        failures.append("C4 highlightVolatilityBucket null branch not found")
    else:
        null_branch = hl_body[null_idx:null_idx + 400]
        if "attr('stroke', 'none')" not in null_branch:
            failures.append("C4 highlightVolatilityBucket(null) does not "
                            "clear the bar stroke -- phantom ring survives "
                            "chip dismiss / Reset All / Escape")
        if "attr('stroke-width', 0)" not in null_branch:
            failures.append("C4 highlightVolatilityBucket(null) does not "
                            "clear the bar stroke-width")

    # --- C5: highlight ring is theme-aware; labels dim --------------
    if "'#fff'" in hl_body:
        failures.append("C5 highlightVolatilityBucket still uses the hardcoded "
                        "'#fff' ring instead of chartStrokeColor()")
    if "chartStrokeColor()" not in hl_body:
        failures.append("C5 highlightVolatilityBucket does not use "
                        "chartStrokeColor() for the active ring")
    if ".vol-count" not in hl_body:
        failures.append("C5 highlightVolatilityBucket does not dim the "
                        ".vol-count labels with the bucket")

    # --- C6: draw-time count-label opacity ---------------------------
    lbl_start = draw_body.find("g.selectAll('.vol-count')")
    if lbl_start < 0:
        failures.append("C6 .vol-count label chain not found in "
                        "drawVolatilityDistChart")
    else:
        lbl_chain = draw_body[lbl_start:lbl_start + 1200]
        if "window._activeVolatilityBucket" not in lbl_chain:
            failures.append("C6 drawVolatilityDistChart does not apply "
                            "_activeVolatilityBucket to .vol-count opacity at "
                            "draw time")
        elif "? 1 : 0.4" not in lbl_chain:
            failures.append("C6 draw-time .vol-count opacity does not dim "
                            "inactive labels to 0.4")

    # --- C7: click + keyboard paths call the highlight --------------
    if draw_body.count("highlightVolatilityBucket(b.min, b.max)") < 2:
        failures.append("C7 the volatility click and keyboard paths do not "
                        "both call highlightVolatilityBucket(b.min, b.max) "
                        "after setting the bucket")

    # --- C8: insightResetAndSort clears the highlight ---------------
    irs_body = extract_function_body(app, "function insightResetAndSort")
    if irs_body is None:
        failures.append("C8 insightResetAndSort function not found in js/app.js")
    elif "highlightVolatilityBucket(null)" not in irs_body:
        failures.append("C8 insightResetAndSort does not clear the "
                        "volatility highlight -- an insight action leaves "
                        "the bars ringed while the filter is gone")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: volatility-highlight: draw re-applies the active bucket "
          "(bars + labels), mouseout restores it, click/keyboard highlight, "
          "clear paths remove the ring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
