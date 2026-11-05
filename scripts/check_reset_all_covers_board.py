#!/usr/bin/env python3
"""Guard: resetAllFilters must actually reset the board filter.

Background (344th review, 2026-11-04): window.resetAllFilters in
js/app.js (the Reset All button) nulled 21 filter dimensions but
never _activeBoardFilter, never removed board-filter-chip, and never
cleared the af-board panel select -- while announcing the
unconditional 'All filters reset'. The board filter is real: it hides
table rows via the _refreshTable post-process in
js/advanced-filters.js (and pre-filters _sp500RenderTable), so a
Reset that kept it left a stuck, still-filtering dimension behind a
false announcement -- the same false-announcement class the 343rd
review fixed for Escape, now on the one path whose name promises
everything. The AF panel's own Clear already nulls board
unconditionally, so a global Reset clearing less than the scoped
button was strictly weaker, not a deliberate keep (unlike Escape /
insight / sort / findCompany, which still keep board by design and
still exclude af-board). A second facet: _hasActiveFilters omitted
board, so a board-only state hid the Reset button entirely, leaving
no Reset affordance for exactly that state.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: resetAllFilters cannot be located in js/app.js.
  C2 HARD FAIL: resetAllFilters does not null _activeBoardFilter.
  C3 HARD FAIL: resetAllFilters' chip-removal list does not name
     board-filter-chip (state cleared, chip left stale).
  C4 HARD FAIL: resetAllFilters does not pass 'af-board' to
     _clearAfSelects (state cleared, panel select left stale).
  C5 HARD FAIL: _hasActiveFilters does not count
     _activeBoardFilter (board-only state hides the Reset button).
  C6 HARD FAIL: resetAllFilters no longer announces
     'All filters reset' -- the fix makes the announcement true
     (board is now cleared), it must not be weakened instead.

Usage:
  scripts/check_reset_all_covers_board.py
  scripts/check_reset_all_covers_board.py --static-only

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
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1/C2/C3/C4/C6: resetAllFilters -------------------------------
    reset_body = extract_function_body(app, "window.resetAllFilters = function")
    if reset_body is None:
        print("FAIL: reset-all-covers-board: C1 resetAllFilters function "
              "not found in js/app.js")
        return 1
    if not re.search(r"window\._activeBoardFilter\s*=\s*null", reset_body):
        failures.append("C2 resetAllFilters does not null _activeBoardFilter "
                        "(board filter survives a Reset All)")
    m = re.search(r"Clear filter chips\s*\n\s*\[([\s\S]*?)\]", reset_body)
    if not m:
        failures.append("C3 resetAllFilters chip-removal list not found")
    elif "board-filter-chip" not in m.group(1):
        failures.append("C3 resetAllFilters chip-removal list omits "
                        "board-filter-chip (state cleared, chip left stale)")
    calls = re.findall(r"_clearAfSelects\(\s*\[([\s\S]*?)\]\)", reset_body)
    if not calls:
        failures.append("C4 resetAllFilters never calls _clearAfSelects")
    elif not any("'af-board'" in c for c in calls):
        failures.append("C4 resetAllFilters does not clear the af-board "
                        "select (state cleared, panel value left stale)")
    if "announce('All filters reset')" not in reset_body:
        failures.append("C6 resetAllFilters no longer announces "
                        "'All filters reset' (the fix makes it true; "
                        "do not weaken the announcement instead)")

    # --- C5: _hasActiveFilters counts board -----------------------------
    vis_body = extract_function_body(app, "window._hasActiveFilters = function")
    if vis_body is None:
        failures.append("C5 _hasActiveFilters function not found in js/app.js")
    elif "_activeBoardFilter" not in vis_body:
        failures.append("C5 _hasActiveFilters does not count "
                        "_activeBoardFilter (board-only state hides the "
                        "Reset button)")

    if failures:
        for f in failures:
            print("FAIL: reset-all-covers-board: " + f)
        return 1
    print("PASS: reset-all-covers-board: resetAllFilters nulls board, "
          "removes its chip, clears af-board, counts it for visibility, "
          "and keeps the (now true) announcement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
