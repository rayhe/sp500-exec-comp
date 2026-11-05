#!/usr/bin/env python3
"""Guard: the gender pay gap chart highlight must exist and persist.

Background (352nd review, 2026-11-05): the gender chart had NO
highlight function at all -- its click/keyboard paths call
filterByGender('F'), which filtered the table and raised a chip but
never showed which bars were active (the Reset All and Escape paths
already called highlightGenderChart(null) behind a typeof guard, a
no-op until now), and a female filter restored from a deep link or
surviving a resize / theme toggle showed no highlight on redraw at
all. Consequences, all in js/charts.js / js/app.js:
  (a) clicking a female bar filtered the table with zero visual
      feedback on the chart itself;
  (b) the overall bars and their value labels never dimmed with the
      female bars (they had no class to target at all);
  (c) the gender chip dismiss, insightResetAndSort, and
      findCompanyInTable nulled the filter state without clearing any
      highlight (once the highlight exists, a dismiss / insight action
      / Top 10 click would leave a phantom ring);
  (d) hovering a bar and moving out reset it to a flat 0.85, dropping
      an active female bar off full opacity and lifting a dimmed
      overall bar off 0.25.

The fix adds highlightGenderChart (the highlightVolatilityBucket
convention: null / 'M' restores opacity 0.85 / no ring / labels 1,
'F' rings the female bars with opacity 1 + chartStrokeColor() 1.5px
ring and dims the overall bars to 0.25 with their labels at 0.4),
applies the active gender at draw time (female + overall bars and
overall labels), wires filterByGender to highlight with the
post-toggle state, wires the chip dismiss + insightResetAndSort +
findCompanyInTable clear paths to clear it, and restores the
draw-time state on mouseout. 'M' has no bar to ring, so the function
keys on 'F' only; unlike gov/vol the AF-origin gender filter IS exact
('F'), so an AF-origin 'F' highlights correctly.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: drawGenderPayChart does not apply
     _activeGenderFilter to the female-bar opacity at draw time
     (active 1 / none 0.85), or to the overall-bar opacity (active
     0.25 / none 0.85).
  C2 HARD FAIL: drawGenderPayChart does not ring the active female
     bar at draw time (chartStrokeColor, 1.5).
  C3 HARD FAIL: highlightGenderChart(null) does not clear the bar
     stroke / stroke-width (phantom ring after clear).
  C4 HARD FAIL: highlightGenderChart still uses the hardcoded '#fff'
     ring, or does not dim the .gender-label-overall labels.
  C5 HARD FAIL: drawGenderPayChart does not apply _activeGenderFilter
     to the .gender-label-overall opacity at draw time (active 0.4 /
     none 1).
  C6 HARD FAIL: filterByGender does not call highlightGenderChart
     with the post-toggle state after renderTable.
  C7 HARD FAIL: the gender chip dismiss does not call
     highlightGenderChart(null).
  C8 HARD FAIL: insightResetAndSort does not clear the gender
     highlight (stale ring after an insight action resets the filter).
  C9 HARD FAIL: findCompanyInTable does not clear the gender
     highlight (it nulls the gender state but keeps gov/vol, so
     unlike those dims it needs its own clear here).
  C10 HARD FAIL: the female-bar mouseout still resets to a flat 0.85
      instead of restoring the draw-time state.

Usage:
  scripts/check_gender_highlight.py
  scripts/check_gender_highlight.py --static-only

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

    draw_body = extract_function_body(charts, "function drawGenderPayChart")
    if draw_body is None:
        print("FAIL: C1 drawGenderPayChart function not found in js/charts.js")
        return 1
    hl_body = extract_function_body(charts, "window.highlightGenderChart = function")
    if hl_body is None:
        print("FAIL: C3 highlightGenderChart function not found in js/charts.js")
        return 1

    # --- C1: draw-time bar opacity consults the active gender -------
    # Female bars: class attr through the cursor style (opacity fn and
    # ring .each() both live in that span).
    fem_start = draw_body.find(".attr('class', 'gender-bar')")
    fem_end = draw_body.find(".style('cursor', 'pointer')", fem_start + 1)
    if fem_start < 0 or fem_end < 0:
        failures.append("C1 female-bar chain markers not found in "
                        "drawGenderPayChart")
        fem_chain = ""
    else:
        fem_chain = draw_body[fem_start:fem_end]
        if "window._activeGenderFilter" not in fem_chain:
            failures.append("C1 drawGenderPayChart does not apply "
                            "_activeGenderFilter to female-bar opacity at "
                            "draw time -- a redraw / deep link drops the "
                            "highlight")
        elif "? 1 : 0.85" not in fem_chain:
            failures.append("C1 draw-time female-bar opacity is not "
                            "active 1 / none 0.85")
    # Overall bars: class attr through the Female bars comment (the
    # opacity fn lives in that span).
    ov_start = draw_body.find(".attr('class', 'gender-bar-overall')")
    ov_end = draw_body.find("// Female bars", ov_start + 1)
    if ov_start < 0 or ov_end < 0:
        failures.append("C1 overall-bar chain markers not found in "
                        "drawGenderPayChart")
    else:
        ov_chain = draw_body[ov_start:ov_end]
        if "window._activeGenderFilter" not in ov_chain:
            failures.append("C1 drawGenderPayChart does not apply "
                            "_activeGenderFilter to overall-bar opacity at "
                            "draw time")
        elif "? 0.25 : 0.85" not in ov_chain:
            failures.append("C1 draw-time overall-bar opacity is not "
                            "active 0.25 / none 0.85")

    # --- C2: draw-time ring on the active female bar -----------------
    if "attr('stroke', chartStrokeColor()).attr('stroke-width', 1.5)" not in fem_chain:
        failures.append("C2 drawGenderPayChart does not ring the active "
                        "female bar at draw time (chartStrokeColor, 1.5)")

    # --- C3: highlight clear path clears the stroke -----------------
    null_idx = hl_body.find("if (gender !== 'F')")
    if null_idx < 0:
        failures.append("C3 highlightGenderChart null branch not found")
    else:
        null_branch = hl_body[null_idx:null_idx + 450]
        if "attr('stroke', 'none')" not in null_branch:
            failures.append("C3 highlightGenderChart(null) does not clear "
                            "the bar stroke -- phantom ring survives chip "
                            "dismiss / Reset All / Escape")
        if "attr('stroke-width', 0)" not in null_branch:
            failures.append("C3 highlightGenderChart(null) does not clear "
                            "the bar stroke-width")

    # --- C4: highlight ring is theme-aware; labels dim --------------
    if "'#fff'" in hl_body:
        failures.append("C4 highlightGenderChart still uses the hardcoded "
                        "'#fff' ring instead of chartStrokeColor()")
    if "chartStrokeColor()" not in hl_body:
        failures.append("C4 highlightGenderChart does not use "
                        "chartStrokeColor() for the active ring")
    if ".gender-label-overall" not in hl_body:
        failures.append("C4 highlightGenderChart does not dim the "
                        ".gender-label-overall labels with the bars")

    # --- C5: draw-time overall-label opacity -------------------------
    lbl_start = draw_body.find(".attr('class', 'gender-label-overall')")
    if lbl_start < 0:
        failures.append("C5 .gender-label-overall chain not found in "
                        "drawGenderPayChart")
    else:
        lbl_chain = draw_body[lbl_start:lbl_start + 700]
        if "window._activeGenderFilter" not in lbl_chain:
            failures.append("C5 drawGenderPayChart does not apply "
                            "_activeGenderFilter to .gender-label-overall "
                            "opacity at draw time")
        elif "? 0.4 : 1" not in lbl_chain:
            failures.append("C5 draw-time .gender-label-overall opacity "
                            "does not dim active labels to 0.4")

    # --- C6: filterByGender highlights with post-toggle state -------
    setter_body = extract_function_body(app, "window.filterByGender = function")
    if setter_body is None:
        failures.append("C6 filterByGender function not found in js/app.js")
    else:
        if "highlightGenderChart(" not in setter_body:
            failures.append("C6 filterByGender does not call "
                            "highlightGenderChart after setting the gender")
        elif "window._activeGenderFilter === 'F' ? 'F' : null" not in setter_body:
            failures.append("C6 filterByGender does not pass the "
                            "post-toggle state to highlightGenderChart -- a "
                            "toggle-off click would re-highlight, and an "
                            "'M' filter would ring the female bars")

    # --- C7: gender chip dismiss clears the highlight ---------------
    chip_body = extract_function_body(app, "function updateGenderFilterIndicator")
    if chip_body is None:
        failures.append("C7 updateGenderFilterIndicator function not found in js/app.js")
    elif "highlightGenderChart(null)" not in chip_body:
        failures.append("C7 the gender chip dismiss does not call "
                        "highlightGenderChart(null) -- the bars stay ringed "
                        "while the filter is gone")

    # --- C8: insightResetAndSort clears the highlight ---------------
    irs_body = extract_function_body(app, "function insightResetAndSort")
    if irs_body is None:
        failures.append("C8 insightResetAndSort function not found in js/app.js")
    elif "highlightGenderChart(null)" not in irs_body:
        failures.append("C8 insightResetAndSort does not clear the gender "
                        "highlight -- an insight action leaves the bars "
                        "ringed while the filter is gone")

    # --- C9: findCompanyInTable clears the highlight ----------------
    fct_body = extract_function_body(app, "window.findCompanyInTable = function")
    if fct_body is None:
        failures.append("C9 findCompanyInTable function not found in js/app.js")
    elif "highlightGenderChart(null)" not in fct_body:
        failures.append("C9 findCompanyInTable does not clear the gender "
                        "highlight -- it nulls the gender state but keeps "
                        "gov/vol, so a Top 10 click leaves a phantom ring")

    # --- C10: female-bar mouseout restores draw-time state ----------
    click_idx = draw_body.find(".on('click', function() {", fem_start + 1)
    if fem_start < 0 or click_idx < 0:
        failures.append("C10 female-bar chain (to click handler) not found "
                        "in drawGenderPayChart")
    else:
        wide_chain = draw_body[fem_start:click_idx]
        mo_idx = wide_chain.find("mouseout")
        if mo_idx < 0:
            failures.append("C10 female-bar mouseout handler not found in "
                            "drawGenderPayChart")
        else:
            mo_chain = wide_chain[mo_idx:mo_idx + 500]
            if "window._activeGenderFilter" not in mo_chain:
                failures.append("C10 the female-bar mouseout still resets "
                                "to a flat 0.85 instead of restoring the "
                                "draw-time state -- a hovered active bar "
                                "drops off full opacity after mouseout")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: gender-highlight: draw re-applies the active gender "
          "(female + overall bars, overall labels), setter/chip/insight/"
          "Top-10 paths highlight and clear, mouseout restores state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
