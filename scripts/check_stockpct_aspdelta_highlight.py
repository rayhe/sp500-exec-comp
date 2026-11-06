#!/usr/bin/env python3
"""Guard: the equity-mix and peer-delta histogram highlights must exist.

Background (354th review, 2026-11-05): highlightStockPctBucket and
highlightAspDeltaBucket were the last two referenced-but-undefined
highlight functions on the site. The Reset All and Escape paths
already called both with null behind typeof guards, and the escape
guard (check_escape_clear_completeness.py C4) lists them as highlight
clears for nulled dims that have one -- but no such functions existed,
so every one of those calls was a no-op. The two sort-contextual
histograms (.eq-dist-bar-group in renderStockPctSortSummary,
.asp-dist-bar-group in renderAspDeltaSortSummary) already baked the
active tier into the render (outline + dimmed bars), so a click
re-render showed the highlight; the gap was the in-place half:
  (a) no function existed for the guarded Reset / Escape calls to
      invoke, so the codebase carried dead clear paths;
  (b) insightResetAndSort nulled _activeStockPctTier and
      _activeAspDeltaTier without clearing any highlight -- the same
      stale-highlight class the 350th/352nd/353rd reviews fixed there
      for gov/vol/gender/tenure;
  (c) the bar groups carried no data-min / data-max / data-color /
      data-base-title, so an in-place function had nothing to match
      on except parsing onclick text.

The fix adds the data attributes to both builders (leaving the
draw-time styling untouched) and defines window.
highlightStockPctBucket / window.highlightAspDeltaBucket on the
highlightTenureBucket pattern: exact min/max match (Infinity /
-Infinity tiers for asp-delta parse from their string form), active
group gets the active-bracket class + 2px tier-color outline at 1px
offset, non-active bars dim to 0.3, null clears every group. Styling
replicates the render-time state exactly (bar-only dimming, no label
dim, no border radius), so a highlight call and a re-render of the
same state look identical. The setters need no call -- unlike the
tenure insight-card histogram, these live in the sort summary, which
renderTable re-renders from state on every click -- and there is no
AF handler for either dim. Wiring: insightResetAndSort clears both
(the one reset path that lacked the calls); Reset All and Escape
already called both (now live).

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the equity builder does not apply the active tier at
     draw time (exact min/max match, active-bracket class, 2px
     outline in the tier color).
  C2 HARD FAIL: the equity builder does not dim non-active bars to
     0.3 at draw time.
  C3 HARD FAIL: the equity builder does not carry data-min / data-max
     / data-color / data-base-title on each bar group.
  C4 HARD FAIL: the asp-delta builder does not apply the active tier
     at draw time (exact min/max match incl. Infinity tiers,
     active-bracket class, 2px outline in the tier color).
  C5 HARD FAIL: the asp-delta builder does not dim non-active bars to
     0.3 at draw time, or does not carry the four data attributes.
  C6 HARD FAIL: window.highlightStockPctBucket is not defined, or
     does not clear the outline / active-bracket class / bar opacity
     on the null path.
  C7 HARD FAIL: window.highlightAspDeltaBucket is not defined, or
     does not clear the outline / active-bracket class / bar opacity
     on the null path.
  C8 HARD FAIL: resetAllFilters does not call both highlights
     (regression pin: the pre-existing typeof-guarded calls must
     survive -- they are live now that the functions exist).
  C9 HARD FAIL: the Escape clear-all branch does not call both
     highlights (regression pin, same as C8).
  C10 HARD FAIL: insightResetAndSort does not clear both highlights
      (stale ring after an insight action resets the filter).

Usage:
  scripts/check_stockpct_aspdelta_highlight.py
  scripts/check_stockpct_aspdelta_highlight.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
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


def check_highlight_body(failures, tag, body):
    """C6/C7 shared assertions on one highlight function body."""
    if "g.style.outline = ''" not in body:
        failures.append(tag + " does not clear the group outline on "
                        "the null path -- phantom ring survives Reset "
                        "All / Escape / insight reset")
    if "classList.remove('active-bracket')" not in body:
        failures.append(tag + " does not remove the active-bracket "
                        "class on clear")
    if "style.opacity = isDimmed ? '0.3' : ''" not in body:
        failures.append(tag + " does not restore bar opacity on the "
                        "null path -- dimmed bars stay dimmed after "
                        "the filter clears")
    if "g.style.outline = '2px solid '" not in body:
        failures.append(tag + " does not outline the active group "
                        "with a 2px solid outline")
    if "querySelectorAll('.eq-dist-bar-group')" not in body and \
            "querySelectorAll('.asp-dist-bar-group')" not in body:
        failures.append(tag + " does not select its bar groups")


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1/C2/C3: equity builder draw-time styling + data attrs -----
    eq_idx = app.find("var activeT = window._activeStockPctTier;")
    if eq_idx < 0:
        failures.append("C1 the equity histogram builder does not read "
                        "window._activeStockPctTier at draw time -- a "
                        "redraw / deep link drops the highlight")
        eq_span = ""
    else:
        eq_span = app[eq_idx:eq_idx + 2600]
        if "activeT.min === t.min && activeT.max === t.max" not in eq_span:
            failures.append("C1 the equity builder does not match the "
                            "active tier with exact min/max -- the "
                            "top tier (max 100.1) would never highlight")
        if "active-bracket" not in eq_span:
            failures.append("C1 the equity builder does not add the "
                            "active-bracket class to the active group")
        if "'outline:2px solid ' + t.color" not in eq_span:
            failures.append("C1 the equity builder does not outline the "
                            "active group in the tier color at draw time")
        if "? 1 : 0.3" not in eq_span:
            failures.append("C2 the equity builder does not dim "
                            "non-active bars to 0.3 at draw time")
        for attr in ('data-min="', 'data-max="', 'data-color="',
                     'data-base-title="'):
            if attr not in eq_span:
                failures.append("C3 the equity builder does not carry " +
                                attr + " on each bar group -- the "
                                "in-place highlight has nothing to match "
                                "on")

    # --- C4/C5: asp-delta builder draw-time styling + data attrs -----
    asp_idx = app.find("var isActive = window._activeAspDeltaTier &&")
    if asp_idx < 0:
        failures.append("C4 the asp-delta histogram builder does not read "
                        "window._activeAspDeltaTier at draw time")
        asp_span = ""
    else:
        asp_span = app[asp_idx:asp_idx + 2600]
        if "window._activeAspDeltaTier.min === t.min && window._activeAspDeltaTier.max === t.max" not in asp_span:
            failures.append("C4 the asp-delta builder does not match the "
                            "active tier with exact min/max -- the "
                            "Infinity tiers would never highlight")
        if "active-bracket" not in asp_span:
            failures.append("C4 the asp-delta builder does not add the "
                            "active-bracket class to the active group")
        if "'outline:2px solid ' + t.color" not in asp_span:
            failures.append("C4 the asp-delta builder does not outline "
                            "the active group in the tier color at draw "
                            "time")
        if "? 1 : 0.3" not in asp_span:
            failures.append("C5 the asp-delta builder does not dim "
                            "non-active bars to 0.3 at draw time")
        for attr in ('data-min="', 'data-max="', 'data-color="',
                     'data-base-title="'):
            if attr not in asp_span:
                failures.append("C5 the asp-delta builder does not carry " +
                                attr + " on each bar group -- the "
                                "in-place highlight has nothing to match "
                                "on")

    # --- C6: highlightStockPctBucket exists and clears ---------------
    sp_body = extract_function_body(app, "window.highlightStockPctBucket = function")
    if sp_body is None:
        failures.append("C6 window.highlightStockPctBucket is not defined "
                        "in js/app.js -- Reset All / Escape call it "
                        "behind a typeof guard, which stays a no-op")
    else:
        check_highlight_body(failures, "C6 highlightStockPctBucket", sp_body)

    # --- C7: highlightAspDeltaBucket exists and clears ---------------
    ad_body = extract_function_body(app, "window.highlightAspDeltaBucket = function")
    if ad_body is None:
        failures.append("C7 window.highlightAspDeltaBucket is not defined "
                        "in js/app.js -- Reset All / Escape call it "
                        "behind a typeof guard, which stays a no-op")
    else:
        check_highlight_body(failures, "C7 highlightAspDeltaBucket", ad_body)

    # --- C8: resetAllFilters calls both (regression pin) -------------
    reset_body = extract_function_body(app, "window.resetAllFilters = function")
    if reset_body is None:
        failures.append("C8 resetAllFilters function not found in js/app.js")
    else:
        if reset_body.rfind("highlightStockPctBucket(null)") < 0:
            failures.append("C8 resetAllFilters no longer calls "
                            "highlightStockPctBucket(null) -- a Reset "
                            "would leave the equity tier ringed behind "
                            "the 'All filters reset' announcement")
        if reset_body.rfind("highlightAspDeltaBucket(null)") < 0:
            failures.append("C8 resetAllFilters no longer calls "
                            "highlightAspDeltaBucket(null) -- a Reset "
                            "would leave the peer-delta tier ringed "
                            "behind the 'All filters reset' announcement")

    # --- C9: Escape branch calls both (regression pin) ---------------
    esc_start = app.find("// Clear all filters and search")
    esc_end = app.find("// If in search, blur it", esc_start + 1) \
        if esc_start >= 0 else -1
    if esc_start < 0 or esc_end < 0:
        failures.append("C9 Escape clear-all branch markers not found "
                        "in js/app.js")
    else:
        branch = app[esc_start:esc_end]
        if "highlightStockPctBucket(null)" not in branch:
            failures.append("C9 Escape branch no longer calls "
                            "highlightStockPctBucket(null)")
        if "highlightAspDeltaBucket(null)" not in branch:
            failures.append("C9 Escape branch no longer calls "
                            "highlightAspDeltaBucket(null)")

    # --- C10: insightResetAndSort clears both ------------------------
    irs_body = extract_function_body(app, "function insightResetAndSort")
    if irs_body is None:
        failures.append("C10 insightResetAndSort function not found in "
                        "js/app.js")
    else:
        if irs_body.rfind("highlightStockPctBucket(null, null)") < 0:
            failures.append("C10 insightResetAndSort does not clear the "
                            "equity highlight -- an insight action leaves "
                            "the tier ringed while the filter is gone")
        if irs_body.rfind("highlightAspDeltaBucket(null, null)") < 0:
            failures.append("C10 insightResetAndSort does not clear the "
                            "peer-delta highlight -- an insight action "
                            "leaves the tier ringed while the filter is "
                            "gone")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: stockpct-aspdelta-highlight: both builders carry data "
          "attrs + draw-time styling, both highlight functions exist "
          "and clear, Reset / Escape / insight paths call both")
    return 0


if __name__ == "__main__":
    sys.exit(main())
