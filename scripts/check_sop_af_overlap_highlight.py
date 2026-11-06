#!/usr/bin/env python3
"""Guard: AF-origin SoP filters must highlight their chart buckets.

Background (357th review, 2026-11-05): the Advanced Filters SoP bands
differ from the SoP chart buckets, and the SoP highlight used an exact
min/max match -- so an AF-origin filter filtered the table and raised a
chip but the chart showed nothing:
  sop: AF 0-50 / 50-70 / 70-85 / 85-90 / 90-101 vs chart buckets 0-50 /
       50-60 / 60-70 / 70-80 / 80-85 / 85-90 / 90-95 / 95-100.1
       (50-70 spans 50-60 and 60-70; 70-85 spans 70-80 and 80-85;
       90-101 spans 90-95 and 95-100.1; only 0-50 and 85-90 matched
       exactly before). handleSopTier never called the highlight at all,
       so even the two exact bands showed nothing from the AF panel.
The gov/vol/conc dims got the same treatment in the 355th review; SoP
was queued then and is closed here.

The fix switches highlightSopDistBucket (bars + count labels) and the
draw-time styling in drawSopDistChart to the shared rangesOverlap
predicate in js/charts.js (strict inequalities, so a chart-origin
range still matches exactly one bucket), wires handleSopTier in
js/advanced-filters.js to highlight on set and clear on select-clear,
makes clearAdvancedFilters clear the highlight only for an AF-origin
SoP tier it nulled (a surviving chart-origin bucket keeps its ring),
and switches the renderSopSortSummary mini-histogram in js/app.js from
exact to overlap (inline strict predicate -- app.js loads before
charts.js, so it cannot call the shared helper at parse time).

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: highlightSopDistBucket does not use rangesOverlap
     (bars + labels), or still uses an exact min/max match.
  C2 HARD FAIL: highlightSopDistBucket does not reset stroke-width
     to 0 on its null / non-match branches -- a bar ringed by one
     filter keeps a stale 1.5 width after the next filter (DOM claims
     a ring the eye cannot see).
  C3 HARD FAIL: draw-time SoP styling does not use rangesOverlap
     against the active filter state (bars + labels) -- a resize or
     theme toggle rebuild drops an AF-origin highlight.
  C4 HARD FAIL: handleSopTier does not highlight on set (AF band
     min/max).
  C5 HARD FAIL: handleSopTier does not clear the highlight on
     select-clear.
  C6 HARD FAIL: clearAdvancedFilters does not clear the SoP highlight
     for exactly the AF-origin tier it nulled (unconditional clear
     would strip a surviving chart-origin ring; no clear leaves a
     phantom).
  C7 HARD FAIL: the renderSopSortSummary mini-histogram still uses an
     exact min/max match instead of overlap, or its active outline does
     not ride the bar group (it used to ride the inner bar in the bar's
     own color with no offset, so even an exact-match active bucket
     showed no ring).
  C8 HARD FAIL: the SoP chip dismiss does not clear the highlight
     (regression pin -- it has cleared since the 331st review).

Usage:
  scripts/check_sop_af_overlap_highlight.py
  scripts/check_sop_af_overlap_highlight.py --static-only

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

    # --- C1: SoP highlight uses overlap, not exact ----------------
    sop_hl = extract_function_body(charts, "window.highlightSopDistBucket = function")
    if sop_hl is None:
        failures.append("C1 highlightSopDistBucket function not found in js/charts.js")
    else:
        if "rangesOverlap(d.min, d.max, minPct, maxPct)" not in sop_hl:
            failures.append("C1 highlightSopDistBucket does not match via "
                            "rangesOverlap -- an AF-origin SoP tier shows "
                            "no highlight")
        if "d.min === minPct && d.max === maxPct" in sop_hl:
            failures.append("C1 highlightSopDistBucket still uses an exact "
                            "min/max match -- AF SoP bands (50-70, 70-85, "
                            "90-101) never match the chart buckets")

    # --- C2: SoP highlight resets stroke-width --------------------
    if sop_hl is not None:
        null_idx = sop_hl.find("if (minPct == null)")
        if null_idx < 0:
            failures.append("C2 highlightSopDistBucket null branch not found")
        else:
            null_branch = sop_hl[null_idx:null_idx + 300]
            if "attr('stroke-width', 0)" not in null_branch:
                failures.append("C2 highlightSopDistBucket(null) does not "
                                "reset stroke-width -- a previously ringed "
                                "bar keeps a stale 1.5 width")
        else_idx = sop_hl.find("} else {")
        if else_idx < 0:
            failures.append("C2 highlightSopDistBucket non-match branch not found")
        else:
            # The else branch runs to the end of the function body, so
            # search the remainder (a fixed window would cut off before
            # the reset when the branch carries a long comment).
            else_branch = sop_hl[else_idx:]
            if "attr('stroke-width', 0)" not in else_branch:
                failures.append("C2 highlightSopDistBucket non-match branch "
                                "does not reset stroke-width -- re-highlighting "
                                "to another tier leaves the old bars' widths")

    # --- C3: draw-time SoP styling uses overlap -------------------
    sop_draw = extract_function_body(charts, "function drawSopDistChart")
    if sop_draw is None:
        failures.append("C3 drawSopDistChart function not found in js/charts.js")
    else:
        if "rangesOverlap(b.min, b.max, sf.min, sf.max)" not in sop_draw:
            failures.append("C3 drawSopDistChart does not re-apply the active "
                            "SoP filter via rangesOverlap -- a redraw drops "
                            "an AF-origin highlight")

    # --- C4: AF handler highlights on set -------------------------
    sop_h = extract_function_body(af, "function handleSopTier")
    if sop_h is None:
        failures.append("C4 handleSopTier function not found in js/advanced-filters.js")
    elif "highlightSopDistBucket(min, max)" not in sop_h:
        failures.append("C4 handleSopTier does not highlight the SoP chart "
                        "with the AF band on set")

    # --- C5: AF handler clears on select-clear --------------------
    if sop_h is not None and "highlightSopDistBucket(null, null)" not in sop_h:
        failures.append("C5 handleSopTier does not clear the SoP highlight "
                        "on select-clear -- phantom ring after AF clear")

    # --- C6: AF Clear clears only AF-origin SoP highlights --------
    clear_body = extract_function_body(af, "function clearAdvancedFilters")
    if clear_body is None:
        failures.append("C6 clearAdvancedFilters function not found in js/advanced-filters.js")
    else:
        if "clearedAfSop" not in clear_body or "highlightSopDistBucket(null, null)" not in clear_body:
            failures.append("C6 clearAdvancedFilters does not clear the "
                            "SoP highlight for AF-origin tiers it nulled "
                            "(or does not gate it on the _isAf flag) -- an "
                            "AF Clear leaves a phantom ring, or an "
                            "unconditional clear would strip a surviving "
                            "chart-origin ring")

    # --- C7: mini-histogram uses overlap, not exact ---------------
    mini = extract_function_body(app, "function renderSopSortSummary")
    if mini is None:
        failures.append("C7 renderSopSortSummary function not found in js/app.js")
    else:
        if "b.min < sf.max && b.max > sf.min" not in mini:
            failures.append("C7 renderSopSortSummary mini-histogram does not "
                            "match via overlap -- an AF-origin SoP tier "
                            "leaves every mini-bar dimmed with none outlined")
        if "_activeSopFilter.min === b.min" in mini:
            failures.append("C7 renderSopSortSummary mini-histogram still "
                            "uses an exact min/max match -- AF SoP bands "
                            "(50-70, 70-85, 90-101) never match a bucket")
        if "opacity:' + opacity + outline + '" not in mini:
            failures.append("C7 renderSopSortSummary mini-histogram does not "
                            "carry the active outline on the bar group -- "
                            "the ring would be invisible even for an active "
                            "bucket")

    # --- C8: SoP chip dismiss clears the highlight ----------------
    sop_ind = extract_function_body(app, "function updateSopFilterIndicator")
    if sop_ind is None:
        failures.append("C8 updateSopFilterIndicator function not found in js/app.js")
    elif "highlightSopDistBucket(null)" not in sop_ind:
        failures.append("C8 the SoP chip dismiss does not call "
                        "highlightSopDistBucket(null) -- the bars stay "
                        "ringed while the filter is gone")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: sop-af-overlap-highlight: highlightSopDistBucket + draw-time "
          "styling + mini-histogram use overlap, AF handler highlights on "
          "set and clears on select-clear / AF Clear (AF-origin only), "
          "SoP highlight resets stroke-width on clear / non-match, chip "
          "dismiss clears")
    return 0


if __name__ == "__main__":
    sys.exit(main())
