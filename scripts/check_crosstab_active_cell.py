#!/usr/bin/env python3
"""Guard: crosstab cells must show the active filter (373rd review).

Background (373rd review, 2026-11-07): closes the 360th run's
candidate (2). Crosstab cells were the last chart surface with no
highlight function: pctile / peer-dist visuals re-render from state,
and every other chart dim has a highlight* function, but clicking a
crosstab cell filtered the table and raised a chip while leaving the
cell itself unmarked, and a deep link / back-forward navigation into
a crosstab filter showed no active cell at all. The fix adds
window.highlightCrosstabCell (keyed by the data-crosstab-key the
three draw functions stamp on each data cell), stores the cell key
in _activeCrosstabFilter, serializes it as xkey=, restores it in
applyHashState and the init restore block, restores + else-clears it
in the hashchange handler, applies it at draw time in all three
draw functions, and clears it on every path that nulls the filter
(chip dismiss, Reset All, Escape, insight reset). The SoP x Vol
click handler also gains a cell label + key (it used to pass neither,
so its chip read "N companies" and its toggle-off compared a count).

Checks (all static - small JS/CSS reads, <2s):
  C1 HARD FAIL: highlightCrosstabCell is not defined on window.
  C2 HARD FAIL: a crosstab draw function does not stamp
     data-crosstab-key on its data cells (tenure-gov: / vol-gov: /
     sop-vol: prefixes keep the three tables' keys disjoint).
  C3 HARD FAIL: a crosstab draw function does not apply the highlight
     at draw time (a theme-toggle redraw would drop the ring).
  C4 HARD FAIL: filterTableByTickers does not store cellKey in the
     filter state or does not call highlightCrosstabCell.
  C5 HARD FAIL: serializeState does not emit xkey=, or
     applyHashState does not restore cellKey from state.xkey.
  C6 HARD FAIL: the init restore block does not apply the crosstab
     highlight for a restored filter (charts draw before
     applyHashState, so draw-time application never sees it).
  C7 HARD FAIL: the hashchange handler does not restore the crosstab
     highlight, or has no else-clear when the new hash drops it.
  C8 HARD FAIL: resetAllFilters does not clear the crosstab highlight
     (cells live outside the table, so the tbody wipe never does).
  C9 HARD FAIL: the Escape filter-clear branch does not clear the
     crosstab highlight.
 C10 HARD FAIL: insightResetAndSort does not clear the crosstab
     highlight (it nulls the filter state).
 C11 HARD FAIL: the crosstab chip's dismiss handler does not clear
     the crosstab highlight.
 C12 HARD FAIL: the .crosstab-cell.crosstab-active CSS rule is missing.
 C13 HARD FAIL: a crosstab click handler does not pass a cell key to
     filterTableByTickers.
 C14 HARD FAIL: the hashchange handler does not re-render the table
     when the new hash is empty (applyHashState early-returns on a
     null parse, so a back/forward navigation to a hashless URL would
     leave the stale filtered rows and footer behind nulled state and
     removed chips).

Usage:
  scripts/check_crosstab_active_cell.py
  scripts/check_crosstab_active_cell.py --static-only

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
APP_JS = f"{REPO}/js/app.js"
CHARTS_JS = f"{REPO}/js/charts.js"
STYLE_CSS = f"{REPO}/css/style.css"

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
        charts = open(CHARTS_JS, encoding="utf-8").read()
        css = open(STYLE_CSS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS/CSS sources: {exc}")
        return 2

    failures = []

    # --- C1: the highlight function exists ---------------------------
    if "window.highlightCrosstabCell = function(cellKey)" not in app:
        failures.append("C1 highlightCrosstabCell is not defined on window "
                        "in js/app.js -- crosstab cells have no in-place "
                        "highlight to call")

    # --- C2/C3/C13: the three draw functions -------------------------
    # The search is over js/charts.js only, so marker phrases quoted
    # here as string literals cannot false-positive on this guard's own
    # source (same convention as the 372nd escape-detail guard).
    draws = {
        "tenure-gov": ("function drawTenureGovCrossTab(companies)",
                       "tenure-gov:", "'tenure-gov:' + cellKey"),
        "vol-gov": ("function drawVolGovCrossTab(companies)",
                    "vol-gov:", "'vol-gov:' + cellKey"),
        "sop-vol": ("function drawSopVolCrossTab(companies)",
                    "sop-vol:", "'sop-vol:' + sopKey + '-' + volKey"),
    }
    for name, (sig, key_prefix, key_arg) in draws.items():
        body = extract_function_body(charts, sig)
        if body is None:
            failures.append(f"C2 {name} draw function not found in "
                            "js/charts.js")
            continue
        if f'data-crosstab-key="{key_prefix}' not in body:
            failures.append(f"C2 {name} draw function does not stamp "
                            f"data-crosstab-key=\"{key_prefix}...\" on its "
                            "data cells -- the highlight has nothing to "
                            "match on")
        if "window.highlightCrosstabCell" not in body:
            failures.append(f"C3 {name} draw function never calls "
                            "highlightCrosstabCell at draw time -- a "
                            "theme-toggle redraw would drop the ring")
        if key_arg not in body:
            failures.append(f"C13 {name} click handler does not pass a "
                            "cell key to filterTableByTickers -- the "
                            "filter state carries no cell identity")

    # --- C4: filterTableByTickers stores the key + highlights --------
    ftt = extract_function_body(app, "window.filterTableByTickers = function")
    if ftt is None:
        failures.append("C4 filterTableByTickers not found in js/app.js")
    else:
        if "cellKey: key" not in ftt and "cellKey:key" not in ftt:
            failures.append("C4 filterTableByTickers does not store cellKey "
                            "in _activeCrosstabFilter -- the highlight "
                            "cannot survive a redraw or a reload")
        if "highlightCrosstabCell" not in ftt:
            failures.append("C4 filterTableByTickers never calls "
                            "highlightCrosstabCell -- a cell click filters "
                            "without ringing the cell")

    # --- C5: hash round trip for the key ------------------------------
    ser = extract_function_body(app, "function serializeState()")
    if ser is None:
        failures.append("C5 serializeState not found in js/app.js")
    elif "xkey=" not in ser:
        failures.append("C5 serializeState does not emit xkey= -- a "
                        "restored crosstab filter rings no cell")
    ahs = extract_function_body(app, "function applyHashState(companies)")
    if ahs is None:
        failures.append("C5 applyHashState not found in js/app.js")
    elif "cellKey: state.xkey" not in ahs:
        failures.append("C5 applyHashState does not restore cellKey from "
                        "state.xkey -- the hash round trip drops the cell "
                        "identity")

    # --- C6: init restore applies the highlight ----------------------
    if "window._activeCrosstabFilter && window.highlightCrosstabCell" not in app:
        failures.append("C6 init restore block does not apply the crosstab "
                        "highlight for a restored filter -- charts draw "
                        "before applyHashState, so draw-time application "
                        "never sees it on a fresh deep-link load")

    # --- C7: hashchange restore + else-clear -------------------------
    hash_fn = extract_function_body(
        app, "window.addEventListener('hashchange', function()")
    if hash_fn is None:
        failures.append("C7 hashchange handler not found in js/app.js")
    else:
        if "highlightCrosstabCell(window._activeCrosstabFilter.cellKey)" not in hash_fn:
            failures.append("C7 hashchange handler does not restore the "
                            "crosstab highlight -- a back/forward "
                            "navigation into a crosstab deep link filters "
                            "with no active cell")
        if "highlightCrosstabCell(null)" not in hash_fn:
            failures.append("C7 hashchange handler has no crosstab "
                            "else-clear -- a navigation that drops the "
                            "filter would leave the ring behind")

    # --- C8: resetAllFilters clears ----------------------------------
    reset_fn = extract_function_body(app, "window.resetAllFilters = function")
    if reset_fn is None:
        failures.append("C8 resetAllFilters not found in js/app.js")
    elif "highlightCrosstabCell(null)" not in reset_fn:
        failures.append("C8 resetAllFilters does not clear the crosstab "
                        "highlight -- cells live outside the table, so "
                        "the tbody wipe never clears the ring")

    # --- C9: Escape filter-clear branch clears -----------------------
    esc_anchor = app.find("// 342nd review: highlight clears for the newly nulled")
    if esc_anchor < 0:
        failures.append("C9 Escape highlight-clear block not found in "
                        "js/app.js")
    elif "highlightCrosstabCell(null)" not in app[esc_anchor:esc_anchor + 2000]:
        failures.append("C9 Escape filter-clear branch does not clear the "
                        "crosstab highlight -- Escape would null the "
                        "filter while the cell stays ringed")

    # --- C10: insightResetAndSort clears ------------------------------
    ins_fn = extract_function_body(
        app, "function insightResetAndSort(sortKey, sortDir)")
    if ins_fn is None:
        failures.append("C10 insightResetAndSort not found in js/app.js")
    elif "highlightCrosstabCell(null)" not in ins_fn:
        failures.append("C10 insightResetAndSort does not clear the "
                        "crosstab highlight -- it nulls the filter state, "
                        "so the ring would linger behind a reset table")

    # --- C11: chip dismiss clears ------------------------------------
    chip_fn = extract_function_body(
        app, "function updateCrosstabFilterIndicator()")
    if chip_fn is None:
        failures.append("C11 updateCrosstabFilterIndicator not found in "
                        "js/app.js")
    elif "highlightCrosstabCell(null)" not in chip_fn:
        failures.append("C11 the crosstab chip dismiss handler does not "
                        "clear the highlight -- the cell would stay "
                        "ringed for a filter that no longer filters")

    # --- C12: the CSS rule -------------------------------------------
    if ".crosstab-cell.crosstab-active" not in css:
        failures.append("C12 .crosstab-cell.crosstab-active rule missing "
                        "from css/style.css -- the highlight class would "
                        "have no visual")

    # --- C13 is checked inside the draw loop above -------------------

    # --- C14: hashchange to an empty hash still re-renders -----------
    # (render check R3: the early return in applyHashState skipped its
    # trailing renderTable on a hashless URL, leaving stale filtered
    # rows + footer behind nulled state and removed chips.)
    if hash_fn is not None and "if (!parseHash()) renderTable(companies);" not in hash_fn:
        failures.append("C14 hashchange handler does not re-render the "
                        "table when the new hash is empty -- applyHashState "
                        "early-returns on a null parse, so a back/forward "
                        "navigation to a hashless URL leaves the stale "
                        "filtered rows and footer on screen")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: crosstab-active-cell: highlight function defined, all "
          "three draw functions stamp data-crosstab-key, apply it at draw "
          "time, and pass a cell key on click; filter stores the key, "
          "hash round-trips xkey, init + hashchange restore it, and "
          "chip / Reset All / Escape / insight-reset clear it; hashchange "
          "to an empty hash re-renders the table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
