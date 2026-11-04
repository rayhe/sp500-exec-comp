#!/usr/bin/env python3
"""Guard: reset paths that null AF-origin state must clear the af-* selects.

Background (330th review, 2026-11-03): three reset paths in js/app.js
nulled AF-origin filter state while leaving the Advanced Filters panel
selects untouched, so the panel kept showing the old value and the
af-count-badge kept counting a filter that no longer filtered -- the
panel-side mirror of the 326th chip bug:
  1. resetAllFilters nulled 7 AF dims (dist/pay-band, sop, tenure, gov,
     gender, conc, vol) without touching their selects.
  2. insightResetAndSort nulled the same 7 dims without touching theirs.
  3. sortTableByKey (metric-card click) nulled 5 AF dims (dist/pay-band,
     sop, conc, gender, tenure) without touching theirs.
  4. (338th review, 2026-11-04) findCompanyInTable (Top 10 chart click)
     nulled 4 AF dims (dist/pay-band, conc, sop, gender) without
     touching theirs -- the same class in a path the 330th guard did
     not cover.
  5. (339th review, 2026-11-04) the global Escape-key clear-all path
     (document keydown handler in js/app.js) nulled the same 4 AF dims
     without touching theirs -- the same class in a path neither the
     330th guard nor the 338th fix covered.
The fix is window._clearAfSelects in js/advanced-filters.js, called
(window-guarded) from each path with exactly the selects whose state
that path nulled. Board is deliberately excluded from every call: none
of the five paths nulls _activeBoardFilter, so the af-board select and
its badge count stay truthful. Gov/vol are likewise excluded from the
sortTableByKey call because that path keeps their state, and
tenure/gov/vol/board from the findCompanyInTable and Escape calls for
the same reason.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: _clearAfSelects is not defined in
     js/advanced-filters.js, does not clear .value, does not refresh
     the badge via updateAfBadge, or dispatches a 'change' event (the
     handlers would re-null already-nulled state and trigger extra
     table refreshes; the 329th _clearAfVolSelect precedent sets values
     directly instead).
  C2 HARD FAIL: resetAllFilters does not call _clearAfSelects with
     exactly the 7 selects for the AF states it nulls.
  C3 HARD FAIL: insightResetAndSort does not call _clearAfSelects with
     exactly the same 7 selects.
  C4 HARD FAIL: sortTableByKey does not call _clearAfSelects with
     exactly the 5 selects for the AF states it nulls, or includes a
     select whose state it keeps (gov/vol/board).
  C5 HARD FAIL (338th review): findCompanyInTable does not call
     _clearAfSelects with exactly the 4 selects for the AF states it
     nulls, or includes a select whose state it keeps
     (tenure/gov/vol/board).
  C6 HARD FAIL (339th review): the Escape-key clear-all branch does
     not call _clearAfSelects with exactly the same 4 selects, or
     includes a select whose state it keeps (tenure/gov/vol/board).
     The branch lives inside an anonymous document keydown listener,
     so it is located by its "// Clear all filters and search" comment
     rather than a function name.

State variable -> AF select id, per the Advanced Filters handlers:
  _activeDistFilter -> af-pay-band (pay-band handler sets the dist filter)
  _activeSopFilter -> af-sop-tier
  _activeTenureQuartile -> af-tenure
  _activeGovGrade -> af-gov
  _activeGenderFilter -> af-gender
  _activeConcTier -> af-conc
  _activeVolatilityBucket -> af-vol
  _activeBoardFilter -> af-board (excluded everywhere: never nulled)

Usage:
  scripts/check_af_select_reset_consistency.py
  scripts/check_af_select_reset_consistency.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on the pre-fix tree).
"""
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"
AF_JS = f"{REPO}/js/advanced-filters.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner

STATE_TO_AF_SELECT = {
    "_activeDistFilter": "af-pay-band",
    "_activeSopFilter": "af-sop-tier",
    "_activeTenureQuartile": "af-tenure",
    "_activeGovGrade": "af-gov",
    "_activeGenderFilter": "af-gender",
    "_activeConcTier": "af-conc",
    "_activeVolatilityBucket": "af-vol",
    "_activeBoardFilter": "af-board",
}

# AF states each reset path nulls (read from the function bodies below
# and cross-checked against this expectation; board never nulled).
RESET_EXPECTED_STATES = {
    "_activeDistFilter", "_activeSopFilter", "_activeTenureQuartile",
    "_activeGovGrade", "_activeGenderFilter", "_activeConcTier",
    "_activeVolatilityBucket",
}
SORT_EXPECTED_STATES = {
    "_activeDistFilter", "_activeSopFilter", "_activeGenderFilter",
    "_activeConcTier", "_activeTenureQuartile",
}
FIND_EXPECTED_STATES = {
    "_activeDistFilter", "_activeConcTier", "_activeSopFilter",
    "_activeGenderFilter",
}
# The Escape clear-all branch nulls exactly the same 4 AF-mapped states
# (plus non-AF states: sector, search, role, ratio, transition, team,
# yoy -- none of which has an af-* select, so they drop out of the
# STATE_TO_AF_SELECT filter below).
ESC_EXPECTED_STATES = FIND_EXPECTED_STATES


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


def clear_calls(body):
    """All _clearAfSelects([...]) id-lists inside body, as sets."""
    out = []
    for m in re.finditer(r"_clearAfSelects\(\s*\[([\s\S]*?)\]\)", body):
        out.append(set(re.findall(r"'(af-[a-z-]+)'", m.group(1))))
    return out


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
        af = open(AF_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1: helper definition ------------------------------------------
    helper = extract_function_body(af, "window._clearAfSelects = function")
    if helper is None:
        failures.append("C1 _clearAfSelects not defined in "
                        "js/advanced-filters.js")
    else:
        if ".value = ''" not in helper:
            failures.append("C1 _clearAfSelects does not set .value = ''")
        if "updateAfBadge()" not in helper:
            failures.append("C1 _clearAfSelects does not call updateAfBadge()")
        if "dispatchEvent" in helper or "dispatch('change'" in helper:
            failures.append("C1 _clearAfSelects dispatches a change event "
                            "(must set .value directly, cf. _clearAfVolSelect)")

    def check_path(label, marker, expected_states, code):
        body = extract_function_body(app, marker)
        if body is None:
            failures.append(f"{code} {label} function not found in js/app.js")
            return
        nulled = set(re.findall(
            r"window\.(_active\w+)\s*=\s*(?:null|false)", body))
        af_nulled = {s for s in nulled if s in STATE_TO_AF_SELECT}
        if af_nulled != expected_states:
            failures.append(
                f"{code} {label} nulls AF states {sorted(af_nulled)}; "
                f"expected {sorted(expected_states)} (guard expectation "
                f"drifted -- update the guard, do not silence it)")
            return
        expected_selects = {STATE_TO_AF_SELECT[s] for s in expected_states}
        calls = clear_calls(body)
        if not calls:
            failures.append(
                f"{code} {label} never calls _clearAfSelects (state "
                f"nulled, panel selects left stale)")
        elif len(calls) > 1:
            failures.append(
                f"{code} {label} calls _clearAfSelects {len(calls)} times "
                f"(expected exactly one)")
        elif calls[0] != expected_selects:
            failures.append(
                f"{code} {label} clears selects {sorted(calls[0])}; "
                f"expected exactly {sorted(expected_selects)} "
                f"(missing = stale panel value; extra = cleared select "
                f"whose filter is still active)")

    # --- C2/C3/C4/C5 -----------------------------------------------------
    check_path("resetAllFilters", "window.resetAllFilters = function",
               RESET_EXPECTED_STATES, "C2")
    check_path("insightResetAndSort", "function insightResetAndSort",
               RESET_EXPECTED_STATES, "C3")
    check_path("sortTableByKey", "function sortTableByKey",
               SORT_EXPECTED_STATES, "C4")
    check_path("findCompanyInTable", "window.findCompanyInTable = function",
               FIND_EXPECTED_STATES, "C5")

    # --- C6: Escape-key clear-all branch (anonymous listener) -----------
    esc_start = app.find("// Clear all filters and search")
    esc_end = app.find("// If in search, blur it", esc_start)
    if esc_start < 0 or esc_end < 0 or esc_end <= esc_start:
        failures.append("C6 Escape clear-all branch markers not found in "
                        "js/app.js (guard markers drifted -- update the "
                        "guard, do not silence it)")
    else:
        esc_body = app[esc_start:esc_end]
        nulled = set(re.findall(
            r"window\.(_active\w+)\s*=\s*(?:null|false)", esc_body))
        af_nulled = {s for s in nulled if s in STATE_TO_AF_SELECT}
        if af_nulled != ESC_EXPECTED_STATES:
            failures.append(
                f"C6 Escape clear-all nulls AF states {sorted(af_nulled)}; "
                f"expected {sorted(ESC_EXPECTED_STATES)} (guard expectation "
                f"drifted -- update the guard, do not silence it)")
        else:
            expected_selects = {STATE_TO_AF_SELECT[s]
                                for s in ESC_EXPECTED_STATES}
            calls = clear_calls(esc_body)
            if not calls:
                failures.append(
                    "C6 Escape clear-all never calls _clearAfSelects "
                    "(state nulled, panel selects left stale)")
            elif len(calls) > 1:
                failures.append(
                    f"C6 Escape clear-all calls _clearAfSelects "
                    f"{len(calls)} times (expected exactly one)")
            elif calls[0] != expected_selects:
                failures.append(
                    f"C6 Escape clear-all clears selects "
                    f"{sorted(calls[0])}; expected exactly "
                    f"{sorted(expected_selects)}")

    if failures:
        for f in failures:
            print("FAIL: af-select-reset-consistency: " + f)
        return 1
    print("PASS: af-select-reset-consistency: helper + 5 reset paths "
          "clear exactly the selects whose state they null")
    return 0


if __name__ == "__main__":
    sys.exit(main())
