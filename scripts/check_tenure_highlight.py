#!/usr/bin/env python3
"""Guard: the tenure-dist histogram highlight must exist and persist.

Background (353rd review, 2026-11-05): the CEO Tenure insight card's
inline histogram (.tenure-dist-bar-group) was the last inline histogram
with NO active styling at all -- its bar clicks call
filterByTenureQuartile, which filtered the table and raised a chip but
never showed which bracket was active (the Reset All path already
called highlightTenureBucket(null) behind a typeof guard, a no-op
because no such function existed -- a stale name), and a tenure filter
restored from a deep link or surviving a sector change showed no
highlight on redraw at all. Consequences, all in js/app.js /
js/advanced-filters.js:
  (a) clicking a tenure bracket filtered the table with zero visual
      feedback on the bars themselves;
  (b) the non-active brackets never dimmed, so the active one did not
      stand out;
  (c) the tenure chip dismiss, insightResetAndSort, and the AF tenure
      clear path nulled the filter state without clearing any highlight
      (once the highlight exists, a dismiss / insight action / AF clear
      would leave a phantom ring);
  (d) the AF-origin tenure filter set state directly without touching
      the chart, so a panel selection filtered with no bar feedback.

The fix adds highlightTenureBucket (the highlightCompDistBucket
convention: draw-time isActive styling in the builder + an in-place
function the setter and every clear path call), applies the active
quartile at draw time (active-bracket class + 2px outline in the
bracket color, non-active bars/labels dimmed to 0.3), wires
filterByTenureQuartile to highlight with the post-toggle state, wires
the chip dismiss + insightResetAndSort + AF set/clear paths, and gives
each group data-min / data-max / data-color / data-base-title so the
in-place function can match brackets without parsing onclick text.
The AF tenure bands ('0-3','3-10','10-20','20-999') are the same
ranges as the chart brackets, so AF-origin filters highlight correctly
-- unlike gov/vol, there is no band-mismatch gap here. Escape keeps
tenure by design (339th review), so it needs no clear call; the
highlight correctly stays with the kept filter.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the tenure histogram builder does not apply
     _activeTenureQuartile at draw time (exact min/max match with
     Infinity handling), or does not add the active-bracket class
     with a 2px outline in the bracket color.
  C2 HARD FAIL: the builder does not dim non-active bars/labels
     (opacity 0.3) at draw time.
  C3 HARD FAIL: the builder does not carry data-min / data-max /
     data-color / data-base-title on each bar group (the in-place
     highlight has nothing to match on).
  C4 HARD FAIL: window.highlightTenureBucket is not defined.
  C5 HARD FAIL: highlightTenureBucket does not clear the outline /
     opacity on the null path (phantom ring after clear).
  C6 HARD FAIL: filterByTenureQuartile does not call
     highlightTenureBucket with the post-toggle state after
     renderTable.
  C7 HARD FAIL: the tenure chip dismiss does not clear the
     highlight.
  C8 HARD FAIL: insightResetAndSort does not clear the tenure
     highlight (stale ring after an insight action resets the
     filter).
  C9 HARD FAIL: the AF tenure handler does not highlight on set
     (min, max) or clear on AF clear (null, null).
  C10 HARD FAIL: resetAllFilters does not call highlightTenureBucket
      (regression pin: the pre-existing typeof-guarded call must
      survive -- it is live now that the function exists).

Usage:
  scripts/check_tenure_highlight.py
  scripts/check_tenure_highlight.py --static-only

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
        app = open(APP_JS, encoding="utf-8").read()
        af = open(AF_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1/C2/C3: draw-time styling in the builder -----------------
    # The builder lives inside populateInsights; anchor on the active
    # state read and take the forEach span that follows it.
    tq_idx = app.find("var activeTq = window._activeTenureQuartile;")
    if tq_idx < 0:
        failures.append("C1 the tenure histogram builder does not read "
                        "window._activeTenureQuartile at draw time -- a "
                        "redraw / deep link drops the highlight")
        builder_span = ""
    else:
        builder_span = app[tq_idx:tq_idx + 2600]
        if "activeTq.max === Infinity ? b.max === 'Infinity'" not in builder_span:
            failures.append("C1 the builder does not match the active "
                            "quartile with exact min/max + Infinity "
                            "handling -- the 20+ bracket (max 'Infinity') "
                            "would never highlight")
        if "active-bracket" not in builder_span:
            failures.append("C1 the builder does not add the "
                            "active-bracket class to the active group")
        if "'outline:2px solid ' + b.color" not in builder_span:
            failures.append("C1 the builder does not outline the active "
                            "group in the bracket color at draw time")

    # --- C2: draw-time dimming --------------------------------------
    if builder_span:
        if "'opacity:0.3;'" not in builder_span:
            failures.append("C2 the builder does not dim non-active "
                            "bars/labels to 0.3 at draw time")
        elif "dimStyle" not in builder_span:
            failures.append("C2 the builder computes no dim style for "
                            "non-active brackets")

    # --- C3: data attributes for the in-place highlight -------------
    if builder_span:
        for attr in ('data-min="', 'data-max="', 'data-color="',
                     'data-base-title="'):
            if attr not in builder_span:
                failures.append("C3 the builder does not carry " + attr +
                                " on each bar group -- the in-place "
                                "highlight has nothing to match on")

    # --- C4/C5: the highlight function exists and clears ------------
    hl_body = extract_function_body(app, "window.highlightTenureBucket = function")
    if hl_body is None:
        failures.append("C4 window.highlightTenureBucket is not defined "
                        "in js/app.js -- Reset All calls it behind a "
                        "typeof guard, which stays a no-op")
    else:
        if "g.style.outline = ''" not in hl_body:
            failures.append("C5 highlightTenureBucket does not clear the "
                            "group outline on the null path -- phantom "
                            "ring survives chip dismiss / Reset All")
        if "style.opacity = isDimmed ? '0.3' : ''" not in hl_body:
            failures.append("C5 highlightTenureBucket does not restore "
                            "bar/label opacity on the null path -- dimmed "
                            "bars stay dimmed after the filter clears")
        if "classList.remove('active-bracket')" not in hl_body:
            failures.append("C5 highlightTenureBucket does not remove "
                            "the active-bracket class on clear")

    # --- C6: setter highlights with post-toggle state ---------------
    setter_body = extract_function_body(app, "window.filterByTenureQuartile = function")
    if setter_body is None:
        failures.append("C6 filterByTenureQuartile function not found in js/app.js")
    else:
        if setter_body.rfind("highlightTenureBucket(") < 0:
            failures.append("C6 filterByTenureQuartile does not call "
                            "highlightTenureBucket -- a bar click filters "
                            "with zero feedback until the next re-render")
        elif "window._activeTenureQuartile ? window._activeTenureQuartile.min : null" not in setter_body:
            failures.append("C6 filterByTenureQuartile does not pass the "
                            "post-toggle state -- a toggle-off click would "
                            "re-highlight instead of clearing")

    # --- C7: tenure chip dismiss clears the highlight ---------------
    chip_body = extract_function_body(app, "function updateTenureFilterIndicator")
    if chip_body is None:
        failures.append("C7 updateTenureFilterIndicator function not found in js/app.js")
    elif chip_body.rfind("highlightTenureBucket(null, null)") < 0:
        failures.append("C7 the tenure chip dismiss does not clear the "
                        "highlight -- the bracket stays ringed while the "
                        "filter is gone")

    # --- C8: insightResetAndSort clears the highlight ----------------
    irs_body = extract_function_body(app, "function insightResetAndSort")
    if irs_body is None:
        failures.append("C8 insightResetAndSort function not found in js/app.js")
    elif irs_body.rfind("highlightTenureBucket(null, null)") < 0:
        failures.append("C8 insightResetAndSort does not clear the tenure "
                        "highlight -- an insight action leaves the bracket "
                        "ringed while the filter is gone")

    # --- C9: AF handler highlights on set and clears on clear -------
    af_body = extract_function_body(af, "function handleTenure")
    if af_body is None:
        failures.append("C9 handleTenure function not found in js/advanced-filters.js")
    else:
        if af_body.rfind("highlightTenureBucket(min, max)") < 0:
            failures.append("C9 the AF tenure handler does not highlight "
                            "on set -- a panel selection filters with no "
                            "bar feedback")
        if af_body.rfind("highlightTenureBucket(null, null)") < 0:
            failures.append("C9 the AF tenure handler does not clear the "
                            "highlight on AF clear -- the bracket stays "
                            "ringed while the filter is gone")

    # --- C10: Reset All clears the highlight (regression pin) --------
    reset_body = extract_function_body(app, "window.resetAllFilters = function")
    if reset_body is None:
        failures.append("C10 resetAllFilters function not found in js/app.js")
    elif reset_body.rfind("highlightTenureBucket(null)") < 0:
        failures.append("C10 resetAllFilters no longer calls "
                        "highlightTenureBucket(null) -- a Reset would leave "
                        "the tenure bracket ringed behind the 'All filters "
                        "reset' announcement")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: tenure-highlight: draw re-applies the active quartile "
          "(bracket class + outline + dimming, data attrs present), "
          "setter/chip/insight/AF/Reset paths highlight and clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
