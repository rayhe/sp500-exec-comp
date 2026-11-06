#!/usr/bin/env python3
"""Guard: AF-origin pay bands must highlight their comp-dist chart buckets.

Background (358th review, 2026-11-06): the Advanced Filters pay bands
differ from the comp-dist chart buckets, and the comp-dist highlight
used an exact min match -- so an AF-origin filter filtered the table
and raised a chip but the chart showed nothing or half the range:
  pay band: AF 0-5M / 5-10M / 10-15M / 15-25M / 25-50M / 50M+
       vs chart buckets 0-5M / 5-10M / 10-15M / 15-20M / 20-30M /
       30-50M / 50-75M / 75M+
       (15-25M spans 15-20M and 20-30M; 25-50M spans 20-30M and
       30-50M but starts at no bucket min, so exact-min matched
       NOTHING; 50M+ spans 50-75M and 75M+; only 0-5M, 5-10M and
       10-15M matched exactly before). handlePayBand never called
       the highlight at all, so even the three exact bands showed
       nothing from the AF panel.
The gov/vol/conc dims got the same treatment in the 355th review and
SoP in the 357th; the pay band was queued then and is closed here.

The fix switches highlightCompDistBucket (bars + count labels) and the
draw-time styling in drawCompDistChart to the shared rangesOverlap
predicate in js/charts.js (strict inequalities, so a chart-origin
bracket still matches exactly one bucket), wires handlePayBand in
js/advanced-filters.js to highlight on set and clear on select-clear,
makes clearAdvancedFilters clear the highlight only for an AF-origin
pay band it nulled (a surviving chart-origin bracket keeps its ring),
switches the renderCompDistSummary mini-histogram in js/app.js from
exact to overlap (inline strict predicate -- app.js loads before
charts.js, so it cannot call the shared helper at parse time), passes
max alongside min at the three app.js highlight call sites, and clears
the highlight on dist-chip dismiss.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: highlightCompDistBucket does not use rangesOverlap
     (bars + labels), or its two-arg form is missing.
  C2 HARD FAIL: highlightCompDistBucket does not reset stroke-width
     to 0 on its null / non-match branches -- a bar ringed by one
     filter keeps a stale 1.5 width after the next filter (DOM claims
     a ring the eye cannot see).
  C3 HARD FAIL: draw-time comp-dist styling does not use
     rangesOverlap against the active filter state (bars + labels +
     mouseout) -- a resize or theme toggle rebuild drops an
     AF-origin highlight.
  C4 HARD FAIL: handlePayBand does not highlight on set (AF band
     min/max).
  C5 HARD FAIL: handlePayBand does not clear the highlight on
     select-clear.
  C6 HARD FAIL: clearAdvancedFilters does not clear the pay-band
     highlight for exactly the AF-origin band it nulled (unconditional
     clear would strip a surviving chart-origin ring; no clear leaves
     a phantom).
  C7 HARD FAIL: the renderCompDistSummary mini-histogram still uses an
     exact min/max match instead of overlap.
  C8 HARD FAIL: the dist chip dismiss does not clear the highlight
     (regression pin -- the bars stay ringed while the filter is gone).
  C9 HARD FAIL: an app.js highlight call site still passes min only
     (a min-only call falls back to exact-min, so an AF band restored
     from hash would show nothing for $25-50M).

Usage:
  scripts/check_payband_af_overlap_highlight.py
  scripts/check_payband_af_overlap_highlight.py --static-only

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
AF_JS = f"{REPO}/js/advanced-filters.js"

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
        af = open(AF_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1: comp-dist highlight uses overlap, not exact ------------
    hl = extract_function_body(charts, "window.highlightCompDistBucket = function")
    if hl is None:
        failures.append("C1 highlightCompDistBucket function not found in js/charts.js")
    else:
        # The extracted body starts at the opening brace, so the
        # signature itself is checked against the full source.
        if "window.highlightCompDistBucket = function(minComp, maxComp)" not in charts:
            failures.append("C1 highlightCompDistBucket does not take a "
                            "(minComp, maxComp) pair -- the AF pay band "
                            "cannot be matched by overlap")
        if "rangesOverlap(d.min, d.max, minComp, maxComp)" not in hl:
            failures.append("C1 highlightCompDistBucket does not match via "
                            "rangesOverlap -- an AF-origin pay band shows "
                            "no highlight (25-50M matches no bucket min)")
        if hl.count("rangesOverlap(d.min, d.max, minComp, maxComp)") < 2:
            failures.append("C1 highlightCompDistBucket does not use "
                            "rangesOverlap for both bars and count labels")

    # --- C2: comp-dist highlight resets stroke-width ----------------
    if hl is not None:
        null_idx = hl.find("if (minComp == null)")
        if null_idx < 0:
            failures.append("C2 highlightCompDistBucket null branch not found")
        else:
            null_branch = hl[null_idx:null_idx + 300]
            if "attr('stroke-width', 0)" not in null_branch:
                failures.append("C2 highlightCompDistBucket(null) does not "
                                "reset stroke-width -- a previously ringed "
                                "bar keeps a stale 1.5 width")
        else_idx = hl.find("} else {")
        if else_idx < 0:
            failures.append("C2 highlightCompDistBucket non-match branch not found")
        else:
            else_branch = hl[else_idx:]
            # The bars branch resets via the ternary (isActive ? 1.5 : 0),
            # which is the same reset as the SoP form's literal 0.
            if "attr('stroke-width', 0)" not in else_branch and "attr('stroke-width', isActive ? 1.5 : 0)" not in else_branch:
                failures.append("C2 highlightCompDistBucket non-match branch "
                                "does not reset stroke-width -- re-highlighting "
                                "to another band leaves the old bars' widths")

    # --- C3: draw-time comp-dist styling uses overlap ---------------
    draw = extract_function_body(charts, "function drawCompDistChart")
    if draw is None:
        failures.append("C3 drawCompDistChart function not found in js/charts.js")
    else:
        if draw.count("rangesOverlap(b.min, b.max, af.min, af.max)") < 4:
            failures.append("C3 drawCompDistChart does not re-apply the "
                            "active pay-band filter via rangesOverlap in "
                            "all four spots (bar opacity, bar stroke, "
                            "mouseout, count labels) -- a redraw drops an "
                            "AF-origin highlight")
        if "b.min === af.min" in draw:
            failures.append("C3 drawCompDistChart still uses an exact "
                            "b.min === af.min match -- AF pay bands "
                            "(15-25M, 25-50M, 50M+) never match the chart "
                            "buckets")

    # --- C4: AF handler highlights on set ---------------------------
    pb = extract_function_body(af, "function handlePayBand")
    if pb is None:
        failures.append("C4 handlePayBand function not found in js/advanced-filters.js")
    elif "highlightCompDistBucket(min, max)" not in pb:
        failures.append("C4 handlePayBand does not highlight the comp-dist "
                        "chart with the AF band on set")

    # --- C5: AF handler clears on select-clear ----------------------
    if pb is not None and "highlightCompDistBucket(null, null)" not in pb:
        failures.append("C5 handlePayBand does not clear the comp-dist "
                        "highlight on select-clear -- phantom ring after "
                        "AF clear")

    # --- C6: AF Clear clears only AF-origin pay highlights ----------
    clear_body = extract_function_body(af, "function clearAdvancedFilters")
    if clear_body is None:
        failures.append("C6 clearAdvancedFilters function not found in js/advanced-filters.js")
    else:
        if "clearedAfPay" not in clear_body or "highlightCompDistBucket(null, null)" not in clear_body:
            failures.append("C6 clearAdvancedFilters does not clear the "
                            "pay-band highlight for AF-origin bands it "
                            "nulled (or does not gate it on the _isAfPay "
                            "flag) -- an AF Clear leaves a phantom ring, "
                            "or an unconditional clear would strip a "
                            "surviving chart-origin ring")

    # --- C7: mini-histogram uses overlap, not exact -----------------
    mini = extract_function_body(app, "function renderCompDistSummary")
    if mini is None:
        failures.append("C7 renderCompDistSummary function not found in js/app.js")
    else:
        if "b.min < activeMax && maxVal > activeMin" not in mini:
            failures.append("C7 renderCompDistSummary mini-histogram does "
                            "not match via overlap -- an AF-origin pay "
                            "band leaves every mini-bar dimmed with none "
                            "outlined")
        if "b.min === activeMin && maxVal === activeMax" in mini:
            failures.append("C7 renderCompDistSummary mini-histogram still "
                            "uses an exact min/max match -- AF pay bands "
                            "(15-25M, 25-50M, 50M+) never match a bucket")

    # --- C8: dist chip dismiss clears the highlight -----------------
    ind = extract_function_body(app, "function updateDistFilterIndicator")
    if ind is None:
        failures.append("C8 updateDistFilterIndicator function not found in js/app.js")
    elif "highlightCompDistBucket(null)" not in ind:
        failures.append("C8 the dist chip dismiss does not call "
                        "highlightCompDistBucket(null) -- the bars stay "
                        "ringed while the filter is gone")

    # --- C9: no min-only highlight call sites remain in app.js ------
    if "highlightCompDistBucket(window._activeDistFilter.min)" in app:
        failures.append("C9 an app.js call site still passes min only to "
                        "highlightCompDistBucket -- the single-arg fallback "
                        "is exact-min, so a hash-restored $25-50M band "
                        "shows nothing")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: payband-af-overlap-highlight: highlightCompDistBucket + "
          "draw-time styling + mini-histogram use overlap, AF handler "
          "highlights on set and clears on select-clear / AF Clear "
          "(AF-origin only), highlight resets stroke-width on clear / "
          "non-match, chip dismiss clears, all call sites pass min+max")
    return 0


if __name__ == "__main__":
    sys.exit(main())
