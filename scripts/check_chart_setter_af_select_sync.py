#!/usr/bin/env python3
"""Guard: chart-origin setters for AF-mapped dims must clear the af-* select.

Background (340th review, 2026-11-04): closes the 337th run's candidate
(3) -- the reverse-direction audit of the AF Clear select-clearing.
AF Clear clears all af-* selects unconditionally, which is currently
harmless only because every chart-origin setter already clears the
select for its own dimension (the 329th/331st fixes). A future setter
that forgets the clear would re-open the panel-sync gap: the panel
would keep showing an AF value while the table filters on the chart
value, and the af-count-badge would count a filter that no longer
filters. This guard pins the setter side of that invariant so the
regression fails loudly instead of silently.

Chart-origin setters, one per AF-mapped dimension (verified by a full
assignment-site inventory across js/*.js; no other non-null assignment
to these state variables exists outside the allowlist in C4):
  dist/pay-band -> filterByDistribution, filterByCompBracket (app.js)
  conc          -> filterByConcTier (app.js)
  sop           -> highlightSopBucket (app.js)
  gender        -> filterByGender, non-AF path only (app.js)
  tenure        -> filterByTenureQuartile (app.js)
  gov           -> filterByGovGrade (app.js)
  vol           -> volatility-dist bar click + keyboard activate
                   (charts.js; uses the dedicated _clearAfVolSelect
                   helper from the 329th review, not _clearAfSelects)
  board         -> NO chart setter exists (337th review); the only
                   non-null assignment is handleBoard in
                   advanced-filters.js, so af-board is never stale
                   from a chart path.
Every other chart click routes through one of these setters (charts.js
calls filterByDistribution / filterByCompBracket / filterByConcTier /
highlightSopBucket / filterByGender); the vol-tenure bracket setters
in charts.js are NOT AF-mapped (no af-vol-tenure select exists) and
touch no AF-mapped variable, so they are excluded, not covered.
applyHashState (URL restore) is allowlisted but not covered: at
initial load the selects start empty, so a restored flag-less
(chart-origin) state cannot disagree with a select; the popstate path
is a separate question and is deliberately out of scope here.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: _clearAfSelects or _clearAfVolSelect is not defined in
     js/advanced-filters.js, does not clear .value, does not refresh
     the badge via updateAfBadge, or dispatches a 'change' event (the
     handlers would re-null the just-set chart state; the 329th
     precedent sets values directly instead).
  C2 HARD FAIL: any of the 7 app.js chart setters does not call
     _clearAfSelects with exactly its dimension's select, or calls it
     more than once. filterByGender's call must additionally be gated
     on !fromAf (the AF path must not clear the select it just set).
  C3 HARD FAIL: either charts.js volatility-bucket setter (bar click,
     keyboard activate) is not followed within 12 lines by a
     _clearAfVolSelect() call.
  C4 HARD FAIL: any non-null assignment to an AF-mapped state variable
     in js/*.js whose enclosing function is not in the allowlist
     (7 app.js setters, applyHashState, 8 advanced-filters.js AF
     handlers, charts.js vol setters). A future setter trips C4 even
     before C2/C3 run -- update the guard with the new setter, do not
     silence it.
  C5 HARD FAIL: any non-null assignment to _activeBoardFilter outside
     handleBoard in js/advanced-filters.js (board has no chart setter).

State variable -> AF select id, per the Advanced Filters handlers:
  _activeDistFilter -> af-pay-band
  _activeSopFilter -> af-sop-tier
  _activeTenureQuartile -> af-tenure
  _activeGovGrade -> af-gov
  _activeGenderFilter -> af-gender
  _activeConcTier -> af-conc
  _activeVolatilityBucket -> af-vol
  _activeBoardFilter -> af-board

Usage:
  scripts/check_chart_setter_af_select_sync.py
  scripts/check_chart_setter_af_select_sync.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a tree with a setter's clear removed).
"""
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"
AF_JS = f"{REPO}/js/advanced-filters.js"
CHARTS_JS = f"{REPO}/js/charts.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner

AF_MAPPED = {
    "_activeDistFilter": "af-pay-band",
    "_activeSopFilter": "af-sop-tier",
    "_activeTenureQuartile": "af-tenure",
    "_activeGovGrade": "af-gov",
    "_activeGenderFilter": "af-gender",
    "_activeConcTier": "af-conc",
    "_activeVolatilityBucket": "af-vol",
    "_activeBoardFilter": "af-board",
}

# app.js chart setter -> the select it must clear (exactly one call).
SETTER_TO_SELECT = {
    "window.filterByDistribution = function": "af-pay-band",
    "window.filterByCompBracket = function": "af-pay-band",
    "window.filterByConcTier = function": "af-conc",
    "window.highlightSopBucket = function": "af-sop-tier",
    "window.filterByGender = function": "af-gender",
    "window.filterByTenureQuartile = function": "af-tenure",
    "window.filterByGovGrade = function": "af-gov",
}

# Enclosing-function allowlist for C4, by file: every non-null
# assignment to an AF-mapped variable must live in one of these.
ALLOWLIST = {
    "app.js": {
        "filterByDistribution", "filterByCompBracket", "filterByConcTier",
        "highlightSopBucket", "filterByGender", "filterByTenureQuartile",
        "filterByGovGrade", "applyHashState",
    },
    "advanced-filters.js": {
        "handlePayBand", "handleSopTier", "handleTenure", "handleGov",
        "handleBoard", "handleGender", "handleConc", "handleVol",
    },
    # charts.js vol setters are anonymous callbacks; C3 covers them by
    # proximity, so C4 allows _activeVolatilityBucket there only.
    "charts.js": {"__vol_setter__"},
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


def enclosing_function(lines, idx):
    """Nearest preceding named-function header, or None."""
    for j in range(idx, max(0, idx - 300), -1):
        m = re.search(
            r"(?:window\.([A-Za-z0-9_]+)|function ([A-Za-z0-9_]+))"
            r"\s*=\s*function|function ([A-Za-z0-9_]+)\s*\(",
            lines[j])
        if m:
            return m.group(1) or m.group(2) or m.group(3)
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
        charts = open(CHARTS_JS, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1: helper definitions -----------------------------------------
    for helper_name in ("window._clearAfSelects = function",
                        "window._clearAfVolSelect = function"):
        helper = extract_function_body(af, helper_name)
        if helper is None:
            failures.append(f"C1 {helper_name} not defined in "
                            "js/advanced-filters.js")
            continue
        if ".value = ''" not in helper:
            failures.append(f"C1 {helper_name} does not set .value = ''")
        if "updateAfBadge()" not in helper:
            failures.append(f"C1 {helper_name} does not call updateAfBadge()")
        if "dispatchEvent" in helper:
            failures.append(f"C1 {helper_name} dispatches an event "
                            "(must set .value directly, cf. 329th review)")

    # --- C2: app.js chart setters ---------------------------------------
    for marker, select in SETTER_TO_SELECT.items():
        body = extract_function_body(app, marker)
        if body is None:
            failures.append(f"C2 {marker} not found in js/app.js")
            continue
        calls = clear_calls(body)
        if not calls:
            failures.append(f"C2 {marker} never calls _clearAfSelects "
                            f"(chart value would leave {select} stale)")
        elif len(calls) > 1:
            failures.append(f"C2 {marker} calls _clearAfSelects "
                            f"{len(calls)} times (expected exactly one)")
        elif calls[0] != {select}:
            failures.append(f"C2 {marker} clears selects "
                            f"{sorted(calls[0])}; expected exactly "
                            f"['{select}']")
        if "filterByGender" in marker:
            # The AF path (fromAf=true) must not clear the select it
            # just set; the chart path must. Assert the gate textually.
            m = re.search(r"if\s*\(\s*!fromAf[^)]*\)\s*"
                          r"if\s*\(typeof window\._clearAfSelects",
                          body)
            if not m and "!fromAf" not in body:
                failures.append("C2 filterByGender _clearAfSelects call is "
                                "not gated on !fromAf (AF path would clear "
                                "its own just-set select)")

    # --- C3: charts.js vol setters --------------------------------------
    charts_lines = charts.split("\n")
    vol_sites = [i for i, ln in enumerate(charts_lines)
                 if re.search(r"_activeVolatilityBucket\s*=\s*\{", ln)]
    if len(vol_sites) != 2:
        failures.append(f"C3 expected exactly 2 volatility-bucket setters "
                        f"in js/charts.js, found {len(vol_sites)} (guard "
                        f"expectation drifted -- update the guard, do not "
                        f"silence it)")
    for i in vol_sites:
        window = "\n".join(charts_lines[i:i + 13])
        if "_clearAfVolSelect()" not in window:
            failures.append(f"C3 charts.js:{i + 1} volatility-bucket "
                            "setter has no _clearAfVolSelect() call within "
                            "12 lines (af-vol would keep a stale AF value)")

    # --- C4: assignment-site allowlist ----------------------------------
    for fname, src in (("app.js", app), ("advanced-filters.js", af),
                       ("charts.js", charts)):
        lines = src.split("\n")
        for i, ln in enumerate(lines):
            for var in AF_MAPPED:
                if not re.search(var + r"\s*=\s*[^=]", ln):
                    continue
                if re.search(var + r"\s*=\s*(null|false)\b", ln):
                    continue  # nulling is a reset path, covered elsewhere
                fn = enclosing_function(lines, i)
                if fname == "charts.js":
                    # Anonymous vol callbacks: allowed only for the vol
                    # variable, and only when C3's proximity check passed.
                    if var != "_activeVolatilityBucket":
                        failures.append(
                            f"C4 {fname}:{i + 1} assigns AF-mapped {var} "
                            f"outside any allowlisted setter (a chart "
                            f"path that never clears its af select)")
                    continue
                if fn not in ALLOWLIST[fname]:
                    failures.append(
                        f"C4 {fname}:{i + 1} assigns AF-mapped {var} in "
                        f"function {fn!r}, not in the allowlist (a new "
                        f"setter that must clear its af select -- update "
                        f"the guard, do not silence it)")

    # --- C5: board has no chart setter ----------------------------------
    for fname, src in (("app.js", app), ("charts.js", charts)):
        for i, ln in enumerate(src.split("\n")):
            if (re.search(r"_activeBoardFilter\s*=\s*[^=]", ln)
                    and not re.search(r"_activeBoardFilter\s*=\s*"
                                      r"(null|false)\b", ln)):
                failures.append(f"C5 {fname}:{i + 1} assigns "
                                "_activeBoardFilter outside handleBoard "
                                "(board has no chart setter by design)")

    if failures:
        for f in failures:
            print("FAIL: chart-setter-af-select-sync: " + f)
        return 1
    print("PASS: chart-setter-af-select-sync: 7 app.js setters + 2 "
          "charts.js vol setters clear their af select; assignment-site "
          "allowlist clean; board has no chart setter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
