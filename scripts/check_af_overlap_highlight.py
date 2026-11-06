#!/usr/bin/env python3
"""Guard: AF-origin gov/vol/conc filters must highlight their chart buckets.

Background (355th review, 2026-11-05): the Advanced Filters select bands
differ from the chart buckets, and every gov / volatility / concentration
highlight used an exact min/max match -- so an AF-origin filter filtered
the table and raised a chip but the chart showed nothing:
  gov: AF A 80-100 / B 65-79.999 / C 50-64.999 / D 35-49.999 / F 0-34.999
       vs chart buckets 80-100.1 / 65-80 / 50-65 / 35-50 / 20-35 / 0-20
       (F spans TWO chart buckets; A misses by the 100.1 sentinel)
  vol: AF 0-10 / 10-25 / 25-50 / 50+ vs chart 0-5 / 5-10 / 10-20 /
       20-40 / 40-60 / 60-80 / 80+ (every AF band spans 2-3 buckets)
  conc: AF 0-30 / 30-40 / 40-50 / 50-60 / 60+ vs chart 0-25 / 25-30 /
        30-35 / 35-40 / 40-45 / 45-50 / 50-60 / 60-101 (60+ misses by
        the 101 sentinel; 50-60 is the one band that already matched)
Tenure and gender were exact, so they were done (353rd / 352nd); this
is the shared overlap-match fix the 350th review queued for gov/vol
and the 354th review queued for conc.

The fix adds a shared rangesOverlap(bucketMin, bucketMax, filterMin,
filterMax) predicate in js/charts.js (strict inequalities, so a
chart-origin range still matches exactly one bucket -- buckets are
contiguous and half-open), switches the three highlight functions and
their draw-time styling (bars + rings + count labels, plus the vol
mouseout restore) to it, wires handleGov / handleVol / handleConc in
js/advanced-filters.js to highlight on set and clear on select-clear,
makes clearAdvancedFilters clear the highlight only for dims it nulled
as AF-origin (a surviving chart-origin filter keeps its ring), and
adds the missing highlight clear to the conc chip dismiss (the gov/vol
dismisses already had theirs since the 350th review).

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: rangesOverlap helper missing, or its predicate is not
     the strict-inequality overlap (a <= / >= would let a chart bucket
     match its neighbour).
  C2 HARD FAIL: highlightGovChart does not use rangesOverlap (bars +
     labels), or still uses an exact min/max match.
  C3 HARD FAIL: highlightVolatilityBucket does not use rangesOverlap
     (bars + labels), or still uses an exact min/max match.
  C4 HARD FAIL: highlightConcDistBucket does not use rangesOverlap
     (rects + labels), or still uses an exact min/max match.
  C5 HARD FAIL: draw-time gov / vol / conc styling does not use
     rangesOverlap against the active filter state.
  C6 HARD FAIL: handleGov / handleVol / handleConc do not highlight on
     set (AF band min/max).
  C7 HARD FAIL: handleGov / handleVol / handleConc do not clear the
     highlight on select-clear.
  C8 HARD FAIL: clearAdvancedFilters does not clear the highlights for
     exactly the AF-origin dims it nulled (unconditional clear would
     strip a surviving chart-origin ring; no clear leaves a phantom).
  C9 HARD FAIL: the conc chip dismiss does not clear the highlight.
  C10 HARD FAIL: the volatility bar mouseout does not restore via
      rangesOverlap (a hovered bar in an AF-origin band would reset to
      a flat 0.85 instead of its ringed/dimmed state).
  C11 HARD FAIL: highlightConcDistBucket does not reset stroke-width
      to 0 on its null / non-match branches -- a bar ringed by one
      filter keeps a stale 1.5 width after the next filter (DOM claims
      a ring the eye cannot see).

Usage:
  scripts/check_af_overlap_highlight.py
  scripts/check_af_overlap_highlight.py --static-only

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

    # --- C1: the shared overlap predicate -------------------------
    hl_helper = extract_function_body(charts, "function rangesOverlap")
    if hl_helper is None:
        failures.append("C1 rangesOverlap helper not found in js/charts.js")
    else:
        if "bucketMin < filterMax && bucketMax > filterMin" not in hl_helper:
            failures.append("C1 rangesOverlap predicate is not the strict "
                            "overlap (bucketMin < filterMax && bucketMax > "
                            "filterMin)")
        if "<=" in hl_helper or ">=" in hl_helper:
            failures.append("C1 rangesOverlap uses <= / >= -- a chart "
                            "bucket would match its neighbour and a "
                            "chart-origin filter would ring two bars")

    # --- C2: gov highlight uses overlap, not exact ----------------
    gov_hl = extract_function_body(charts, "window.highlightGovChart = function")
    if gov_hl is None:
        failures.append("C2 highlightGovChart function not found in js/charts.js")
    else:
        if "rangesOverlap(b.min, b.max, min, max)" not in gov_hl:
            failures.append("C2 highlightGovChart does not match via "
                            "rangesOverlap -- an AF-origin gov band shows "
                            "no highlight")
        if "b.min === min && b.max === max" in gov_hl:
            failures.append("C2 highlightGovChart still uses an exact "
                            "min/max match -- AF gov bands (80-100 vs "
                            "80-100.1, F spanning two buckets) never match")

    # --- C3: volatility highlight uses overlap, not exact ---------
    vol_hl = extract_function_body(charts, "window.highlightVolatilityBucket = function")
    if vol_hl is None:
        failures.append("C3 highlightVolatilityBucket function not found in js/charts.js")
    else:
        if "rangesOverlap(b.min, b.max, min, max)" not in vol_hl:
            failures.append("C3 highlightVolatilityBucket does not match via "
                            "rangesOverlap -- an AF-origin vol band shows "
                            "no highlight")
        if "b.min === min && b.max === max" in vol_hl:
            failures.append("C3 highlightVolatilityBucket still uses an exact "
                            "min/max match -- AF vol bands span 2-3 chart "
                            "buckets each and never match")

    # --- C4: conc highlight uses overlap, not exact --------------
    conc_hl = extract_function_body(charts, "window.highlightConcDistBucket = function")
    if conc_hl is None:
        failures.append("C4 highlightConcDistBucket function not found in js/charts.js")
    else:
        if "rangesOverlap(d.min, d.max, minPct, maxPct)" not in conc_hl:
            failures.append("C4 highlightConcDistBucket does not match via "
                            "rangesOverlap -- an AF-origin conc tier shows "
                            "no highlight")
        if "d.min === minPct && d.max === maxPct" in conc_hl:
            failures.append("C4 highlightConcDistBucket still uses an exact "
                            "min/max match -- AF conc bands (0-30, 60+) "
                            "never match the chart buckets")

    # --- C5: draw-time styling uses overlap ----------------------
    gov_draw = extract_function_body(charts, "function drawGovDistChart")
    vol_draw = extract_function_body(charts, "function drawVolatilityDistChart")
    conc_draw = extract_function_body(charts, "function drawConcDistChart")
    if gov_draw is None:
        failures.append("C5 drawGovDistChart function not found in js/charts.js")
    elif "rangesOverlap(b.min, b.max, gf.min, gf.max)" not in gov_draw:
        failures.append("C5 drawGovDistChart does not re-apply the active "
                        "gov grade via rangesOverlap -- a redraw drops an "
                        "AF-origin highlight")
    if vol_draw is None:
        failures.append("C5 drawVolatilityDistChart function not found in js/charts.js")
    elif "rangesOverlap(b.min, b.max, vb.min, vb.max)" not in vol_draw:
        failures.append("C5 drawVolatilityDistChart does not re-apply the "
                        "active vol bucket via rangesOverlap -- a redraw "
                        "drops an AF-origin highlight")
    if conc_draw is None:
        failures.append("C5 drawConcDistChart function not found in js/charts.js")
    elif "rangesOverlap(b.min, b.max, activeTier.min, activeTier.max)" not in conc_draw:
        failures.append("C5 drawConcDistChart does not re-apply the active "
                        "conc tier via rangesOverlap -- a redraw drops an "
                        "AF-origin highlight")

    # --- C6: AF handlers highlight on set ------------------------
    gov_h = extract_function_body(af, "function handleGov")
    vol_h = extract_function_body(af, "function handleVol")
    conc_h = extract_function_body(af, "function handleConc")
    if gov_h is None:
        failures.append("C6 handleGov function not found in js/advanced-filters.js")
    elif "highlightGovChart(g.min, g.max)" not in gov_h:
        failures.append("C6 handleGov does not highlight the gov chart with "
                        "the AF band on set")
    if vol_h is None:
        failures.append("C6 handleVol function not found in js/advanced-filters.js")
    elif "highlightVolatilityBucket(min, max)" not in vol_h:
        failures.append("C6 handleVol does not highlight the vol chart with "
                        "the AF band on set")
    if conc_h is None:
        failures.append("C6 handleConc function not found in js/advanced-filters.js")
    elif "highlightConcDistBucket(min, max)" not in conc_h:
        failures.append("C6 handleConc does not highlight the conc chart with "
                        "the AF band on set")

    # --- C7: AF handlers clear on select-clear -------------------
    if gov_h is not None and "highlightGovChart(null)" not in gov_h:
        failures.append("C7 handleGov does not clear the gov highlight on "
                        "select-clear -- phantom ring after AF clear")
    if vol_h is not None and "highlightVolatilityBucket(null)" not in vol_h:
        failures.append("C7 handleVol does not clear the vol highlight on "
                        "select-clear -- phantom ring after AF clear")
    if conc_h is not None and "highlightConcDistBucket(null, null)" not in conc_h:
        failures.append("C7 handleConc does not clear the conc highlight on "
                        "select-clear -- phantom ring after AF clear")

    # --- C8: AF Clear clears only AF-origin highlights -----------
    clear_body = extract_function_body(af, "function clearAdvancedFilters")
    if clear_body is None:
        failures.append("C8 clearAdvancedFilters function not found in js/advanced-filters.js")
    else:
        for flag, call, dim in [
            ("clearedAfGov", "highlightGovChart(null)", "gov"),
            ("clearedAfConc", "highlightConcDistBucket(null, null)", "conc"),
            ("clearedAfVol", "highlightVolatilityBucket(null)", "vol"),
        ]:
            if flag not in clear_body or call not in clear_body:
                failures.append("C8 clearAdvancedFilters does not clear the "
                                f"{dim} highlight for AF-origin filters it "
                                "nulled (or does not gate it on the _isAf "
                                "flag) -- an AF Clear leaves a phantom ring, "
                                "or an unconditional clear would strip a "
                                "surviving chart-origin ring")
        if "_isAf" not in clear_body:
            failures.append("C8 clearAdvancedFilters does not gate its "
                            "highlight clears on _isAf origin")

    # --- C9: conc chip dismiss clears the highlight --------------
    conc_ind = extract_function_body(app, "function updateConcFilterIndicator")
    if conc_ind is None:
        failures.append("C9 updateConcFilterIndicator function not found in js/app.js")
    elif "highlightConcDistBucket(null, null)" not in conc_ind:
        failures.append("C9 the conc chip dismiss does not call "
                        "highlightConcDistBucket(null, null) -- the bars "
                        "stay ringed while the filter is gone")

    # --- C10: vol mouseout restores via overlap ------------------
    if vol_draw is not None:
        mo = vol_draw.find(".on('mouseout'")
        if mo < 0:
            failures.append("C10 volatility bar mouseout handler not found")
        else:
            mo_end = vol_draw.find(".on('click'", mo + 1)
            mo_body = vol_draw[mo:mo_end if mo_end > 0 else len(vol_draw)]
            if "rangesOverlap(b.min, b.max, vb.min, vb.max)" not in mo_body:
                failures.append("C10 volatility mouseout does not restore "
                                "via rangesOverlap -- hovering a bar in an "
                                "AF-origin band then leaving resets it to a "
                                "flat 0.85 instead of its ringed state")

    # --- C11: conc highlight resets stroke-width -----------------
    if conc_hl is not None:
        null_idx = conc_hl.find("if (minPct == null)")
        if null_idx < 0:
            failures.append("C11 highlightConcDistBucket null branch not found")
        else:
            null_branch = conc_hl[null_idx:null_idx + 300]
            if "attr('stroke-width', 0)" not in null_branch:
                failures.append("C11 highlightConcDistBucket(null) does not "
                                "reset stroke-width -- a previously ringed "
                                "bar keeps a stale 1.5 width")
        else_idx = conc_hl.find("} else {")
        if else_idx < 0:
            failures.append("C11 highlightConcDistBucket non-match branch not found")
        else:
            # The else branch runs to the end of the function body, so
            # search the remainder (a fixed window would cut off before
            # the reset when the branch carries a long comment).
            else_branch = conc_hl[else_idx:]
            if "attr('stroke-width', 0)" not in else_branch:
                failures.append("C11 highlightConcDistBucket non-match branch "
                                "does not reset stroke-width -- re-highlighting "
                                "to another tier leaves the old bars' widths")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: af-overlap-highlight: rangesOverlap is strict, the three "
          "highlight functions + draw-time styling + vol mouseout use it, "
          "AF handlers highlight on set and clear on select-clear / "
          "AF Clear (AF-origin only), conc chip dismiss clears, conc "
          "highlight resets stroke-width on clear / non-match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
