#!/usr/bin/env python3
"""Guard: the CEO/CFO premium bucket highlight must survive redraws.

Background (349th review, 2026-11-05): the 347th review made the
CEO/CFO premium bar click a real table filter (filterByCeoCfoBucket,
_activeCeoCfoBucket, chip, URL state), but drawCeoCfoChart never got
the draw-time highlight treatment the other histograms already have
(ratio, YoY, comp-dist, conc-dist, SoP-dist all re-apply their active
bucket at draw). Consequences, all in js/charts.js:
  (a) redrawAllCharts (resize debounce, theme toggle) rebuilt the
      premium bars at a flat opacity 0.8, so the active filter's
      highlight silently dropped while the table stayed filtered, the
      chip stayed up, and the URL kept cfomin/cfomax;
  (b) mouseout reset every bar to a flat 0.8, so hovering the active
      bar then leaving dropped it to 0.8, and hovering an inactive bar
      then leaving lifted it to 0.8 instead of its dimmed 0.25;
  (c) highlightCeoCfoBucket(null) -- the clear path every reset path
      calls -- reset opacity only and left the ring on the previously
      active bar, a phantom ring after chip dismiss / Reset All /
      Escape / toggle-off; it also used a hardcoded '#fff' 2px ring
      instead of the theme-aware chartStrokeColor() 1.5px ring every
      other histogram highlight uses, and never dimmed the .cfo-count
      labels.

The fix applies the active bucket at draw time (bars + count labels),
makes mouseout restore the draw-time state, and makes
highlightCeoCfoBucket clear the stroke on the null path, use
chartStrokeColor()/1.5, and dim the count labels -- so draw-time and
post-draw highlighting agree exactly.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: drawCeoCfoChart does not apply _activeCeoCfoBucket
     to bar opacity at draw time (active 1 / inactive 0.25 / none 0.8).
  C2 HARD FAIL: drawCeoCfoChart does not ring the active bar at draw
     time (chartStrokeColor, 1.5).
  C3 HARD FAIL: the bar mouseout handler does not restore the
     draw-time highlight from _activeCeoCfoBucket (flat 0.8 reset).
  C4 HARD FAIL: highlightCeoCfoBucket(null) does not clear the bar
     stroke / stroke-width (phantom ring after clear).
  C5 HARD FAIL: highlightCeoCfoBucket still uses the hardcoded '#fff'
     ring, or does not dim the .cfo-count labels.
  C6 HARD FAIL: drawCeoCfoChart does not apply _activeCeoCfoBucket
     to the .cfo-count label opacity at draw time (active 1 / inactive
     0.4 / none 1).

Usage:
  scripts/check_ceocfo_highlight_persists.py
  scripts/check_ceocfo_highlight_persists.py --static-only

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
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    draw_body = extract_function_body(charts, "function drawCeoCfoChart")
    if draw_body is None:
        print("FAIL: C1 drawCeoCfoChart function not found in js/charts.js")
        return 1
    hl_body = extract_function_body(charts, "window.highlightCeoCfoBucket = function")
    if hl_body is None:
        print("FAIL: C4 highlightCeoCfoBucket function not found in js/charts.js")
        return 1

    # --- C1: draw-time bar opacity consults the active bucket -------
    bar_start = draw_body.find(".attr('rx', 3).attr('ry', 3)")
    bar_end = draw_body.find(".style('cursor', 'pointer')", bar_start + 1)
    if bar_start < 0 or bar_end < 0:
        failures.append("C1 CeoCfo bar chain markers not found in "
                        "drawCeoCfoChart")
    else:
        bar_chain = draw_body[bar_start:bar_end]
        if "window._activeCeoCfoBucket" not in bar_chain:
            failures.append("C1 drawCeoCfoChart does not apply "
                            "_activeCeoCfoBucket to bar opacity at draw "
                            "time -- a redraw drops the active highlight")
        elif "? 1 : 0.25" not in bar_chain:
            failures.append("C1 draw-time bar opacity does not dim "
                            "inactive bars to 0.25 (active 1 / inactive "
                            "0.25 / none 0.8)")

    # --- C2: draw-time ring on the active bar ------------------------
    if "attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5)" not in draw_body:
        failures.append("C2 drawCeoCfoChart does not ring the active bar "
                        "at draw time (chartStrokeColor, 1.5)")

    # --- C3: mouseout restores the draw-time highlight --------------
    mo = draw_body.find(".on('mouseout'")
    if mo < 0:
        failures.append("C3 CeoCfo bar mouseout handler not found")
    else:
        mo_end = draw_body.find(".on('click'", mo + 1)
        mo_body = draw_body[mo:mo_end if mo_end > 0 else len(draw_body)]
        if "window._activeCeoCfoBucket" not in mo_body:
            failures.append("C3 CeoCfo mouseout does not consult "
                            "_activeCeoCfoBucket -- hovering then leaving "
                            "clobbers the highlight")
        if re.search(r"\.attr\('opacity', 0\.8\)", mo_body):
            failures.append("C3 CeoCfo mouseout still resets bars to a "
                            "flat 0.8 instead of the draw-time state")

    # --- C4: highlight clear path clears the stroke -----------------
    null_idx = hl_body.find("if (minRatio == null)")
    if null_idx < 0:
        failures.append("C4 highlightCeoCfoBucket null branch not found")
    else:
        null_branch = hl_body[null_idx:null_idx + 400]
        if "attr('stroke', 'none')" not in null_branch:
            failures.append("C4 highlightCeoCfoBucket(null) does not "
                            "clear the bar stroke -- phantom ring survives "
                            "chip dismiss / Reset All / Escape")
        if "attr('stroke-width', 0)" not in null_branch:
            failures.append("C4 highlightCeoCfoBucket(null) does not "
                            "clear the bar stroke-width")

    # --- C5: highlight ring is theme-aware; labels dim --------------
    if "'#fff'" in hl_body:
        failures.append("C5 highlightCeoCfoBucket still uses the hardcoded "
                        "'#fff' ring instead of chartStrokeColor()")
    if "chartStrokeColor()" not in hl_body:
        failures.append("C5 highlightCeoCfoBucket does not use "
                        "chartStrokeColor() for the active ring")
    if ".cfo-count" not in hl_body:
        failures.append("C5 highlightCeoCfoBucket does not dim the "
                        ".cfo-count labels with the bucket")

    # --- C6: draw-time count-label opacity ---------------------------
    lbl_start = draw_body.find("g.selectAll('.cfo-count')")
    if lbl_start < 0:
        failures.append("C6 .cfo-count label chain not found in "
                        "drawCeoCfoChart")
    else:
        lbl_chain = draw_body[lbl_start:lbl_start + 1200]
        if "window._activeCeoCfoBucket" not in lbl_chain:
            failures.append("C6 drawCeoCfoChart does not apply "
                            "_activeCeoCfoBucket to .cfo-count opacity at "
                            "draw time")
        elif "? 1 : 0.4" not in lbl_chain:
            failures.append("C6 draw-time .cfo-count opacity does not dim "
                            "inactive labels to 0.4")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: ceocfo-highlight-persists: draw re-applies the active "
          "bucket (bars + labels), mouseout restores it, clear path "
          "removes the ring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
