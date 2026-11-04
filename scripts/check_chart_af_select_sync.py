#!/usr/bin/env python3
"""Guard: chart-origin setters and chip dismissals must clear the af-* select.

Background (331st review, 2026-11-03): the 329th review fixed this
panel-sync gap for volatility alone (chart histogram clicks overwrote
an AF-origin bucket without touching af-vol), and the 330th fixed the
reset paths. Audit of the remaining six AF-mapped dimensions found the
same gap on every chart-origin setter in js/app.js: filterByDistribution
and filterByCompBracket overwrite _activeDistFilter (af-pay-band),
filterByConcTier overwrites _activeConcTier (af-conc), highlightSopBucket
overwrites _activeSopFilter (af-sop-tier), filterByGender overwrites
_activeGenderFilter (af-gender), filterByTenureQuartile overwrites
_activeTenureQuartile (af-tenure), filterByGovGrade overwrites
_activeGovGrade (af-gov) -- all without touching the af-* select, so the
panel kept showing the old AF value and the badge kept counting a filter
that no longer filtered, and dismissing the chart chip then left the
panel claiming an active filter that was not filtering.

The same audit found the chip-dismiss half of the gap: the six app.js
indicator chips (dist/conc/sop/gender/tenure/gov) are app.js-owned even
for AF-origin values (conc/tenure/gov/gender AF handlers create no chip
of their own, and sector clicks rebuild the pay-band/SoP AF chips via
the indicators), and their dismiss handlers nulled state without
clearing the select. The fix is window._clearAfSelects (330th helper,
sets .value directly without dispatching 'change') called
(window-guarded) from each setter and each dismiss handler with its
single select. Gender is special: the AF handler delegates to
filterByGender, so it passes fromAf=true and the setter skips its clear
for AF-origin calls (clearing there would wipe the just-chosen value);
chart/insight callers pass nothing and get the clear.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: any of the 7 chart-origin setters lacks a
     _clearAfSelects call with its expected select id (filterByGender
     must clear conditionally on !fromAf).
  C2 HARD FAIL: any of the 6 indicator dismiss handlers lacks a
     _clearAfSelects call with its expected select id.
  C3 HARD FAIL: handleGender in js/advanced-filters.js does not pass
     fromAf=true at both of its filterByGender call sites.

State variable -> AF select id, per the Advanced Filters handlers:
  _activeDistFilter -> af-pay-band
  _activeSopFilter -> af-sop-tier
  _activeTenureQuartile -> af-tenure
  _activeGovGrade -> af-gov
  _activeGenderFilter -> af-gender
  _activeConcTier -> af-conc
  (_activeVolatilityBucket -> af-vol: covered by the 329th _clearAfVolSelect
   calls in charts.js, not by this guard; _activeBoardFilter -> af-board
   has no chart-origin setter.)

Usage:
  scripts/check_chart_af_select_sync.py
  scripts/check_chart_af_select_sync.py --static-only

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

# marker -> expected af-* select id cleared by that function body.
SETTERS = {
    "window.filterByDistribution = function": "af-pay-band",
    "window.filterByCompBracket = function": "af-pay-band",
    "window.filterByConcTier = function": "af-conc",
    "window.highlightSopBucket = function": "af-sop-tier",
    "window.filterByGender = function": "af-gender",
    "window.filterByTenureQuartile = function": "af-tenure",
    "window.filterByGovGrade = function": "af-gov",
}
INDICATORS = {
    "function updateDistFilterIndicator()": "af-pay-band",
    "function updateConcFilterIndicator()": "af-conc",
    "function updateSopFilterIndicator()": "af-sop-tier",
    "function updateGenderFilterIndicator()": "af-gender",
    "function updateTenureFilterIndicator()": "af-tenure",
    "function updateGovFilterIndicator()": "af-gov",
}


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


def clears_select(body, select_id):
    """True if body calls _clearAfSelects with exactly [select_id]."""
    for m in re.finditer(r"_clearAfSelects\(\s*\[([\s\S]*?)\]\)", body):
        ids = re.findall(r"'(af-[a-z-]+)'", m.group(1))
        if ids == [select_id]:
            return True
    return False


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
        af = open(AF_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1: chart-origin setters ---------------------------------------
    for marker, select_id in SETTERS.items():
        body = extract_function_body(app, marker)
        if body is None:
            failures.append(f"C1 setter {marker} not found in js/app.js")
            continue
        if not clears_select(body, select_id):
            failures.append(
                f"C1 {marker} never calls _clearAfSelects(['{select_id}']) "
                f"(chart click overwrites AF state, panel select goes stale)")
        if marker == "window.filterByGender = function":
            if "fromAf" not in body or "!fromAf" not in body:
                failures.append(
                    "C1 filterByGender must gate its af-gender clear on "
                    "!fromAf (AF-origin calls pass fromAf=true)")

    # --- C2: chip-dismiss handlers ---------------------------------------
    for marker, select_id in INDICATORS.items():
        body = extract_function_body(app, marker)
        if body is None:
            failures.append(f"C2 indicator {marker} not found in js/app.js")
            continue
        if not clears_select(body, select_id):
            failures.append(
                f"C2 {marker} dismiss handler never calls "
                f"_clearAfSelects(['{select_id}']) (chip dismiss leaves "
                f"the AF select stale)")

    # --- C3: AF gender delegation passes fromAf --------------------------
    handle = extract_function_body(af, "function handleGender")
    if handle is None:
        failures.append("C3 handleGender not found in js/advanced-filters.js")
    else:
        fromaf_calls = re.findall(
            r"filterByGender\([^)]*,\s*true\s*\)", handle)
        total_calls = re.findall(r"filterByGender\(", handle)
        if len(fromaf_calls) != 2 or len(total_calls) != 2:
            failures.append(
                f"C3 handleGender has {len(total_calls)} filterByGender "
                f"calls, {len(fromaf_calls)} with fromAf=true; expected "
                f"2 and 2 (every AF-origin call must skip the setter's "
                f"chart-origin clear)")

    if failures:
        for f in failures:
            print("FAIL: chart-af-select-sync: " + f)
        return 1
    print("PASS: chart-af-select-sync: 7 chart setters + 6 chip dismissals "
          "clear their af-* select; AF gender delegation passes fromAf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
