#!/usr/bin/env python3
"""Guard: the CEO/CFO premium bar click must actually filter the table.

Background (347th review, 2026-11-05): the CEO/CFO premium histogram
in js/charts.js showed "Click to filter table" in its bar tooltip, but
the click only highlighted the bucket (dimmed the other bars) -- the
table never filtered. Every other histogram on the site (ratio, comp
dist, conc, YoY, SoP, gender, pctile, stock-%, asp-delta, peer-dist,
crosstab) filters the table from its bars; the premium chart was the
one exception, and the 345th/346th reviews had to special-case it as a
highlight-only dimension in Reset All and Escape (its toggle state was
not a filter, so _hasActiveFilters deliberately did not count it and
the Reset button hid for a highlight-only state).

The fix makes the click a real filter, following the
filterByConcTier pattern exactly: window.filterByCeoCfoBucket in
js/app.js toggles _activeCeoCfoBucket, re-sorts by _ceoCfoPremium,
renders a dismissible ceocfo-filter-chip, re-renders the table,
highlights the bucket, pushes URL state (cfomin/cfomax/cfolbl), and
announces. The chart click handler and its keyboard activate both
delegate to the setter (with the old highlight-only toggle kept as a
fallback if the setter is unavailable). The filter is threaded through
every reset/restore path the other chart filters use, so it cannot go
stale: renderTable, filter-dims badge, screen-reader announcement,
_hasActiveFilters (Reset button visibility), sortTableByKey,
insightResetAndSort, findCompanyInTable, resetAllFilters, Escape,
hashchange reset, and both hash-restore sites.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the CeoCfo chart click handler (or its keyboard
     activate) does not delegate to window.filterByCeoCfoBucket --
     the tooltip would overpromise again.
  C2 HARD FAIL: app.js does not define filterByCeoCfoBucket, or its
     indicator does not create the ceocfo-filter-chip.
  C3 HARD FAIL: renderTable does not filter on _activeCeoCfoBucket /
     _ceoCfoPremium.
  C4 HARD FAIL: _hasActiveFilters does not count _activeCeoCfoBucket
     (Reset button would hide while the filter still hides rows).
  C5 HARD FAIL: one of sortTableByKey / insightResetAndSort /
     findCompanyInTable / Escape / resetAllFilters / hashchange reset
     does not null the state and remove the chip.
  C6 HARD FAIL: serializeState does not emit cfomin/cfomax/cfolbl, or
     the hash restore does not read them (shared/bookmarked URLs
     would drop the filter).
  C7 HARD FAIL: the combined-filter badge or the table announcement
     does not name the premium filter.
  C8 HARD FAIL: a hash-restore site does not re-apply the bucket
     highlight or re-render the chip (restored filter with no visible
     affordance, the 324th-review class).

Usage:
  scripts/check_ceocfo_filter_table.py
  scripts/check_ceocfo_filter_table.py --static-only

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
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1: chart click + keyboard activate delegate to the setter ---
    n_delegate = charts.count(
        "window.filterByCeoCfoBucket(b.min, b.max, b.label)")
    if n_delegate < 2:
        failures.append(
            "C1 CeoCfo chart does not delegate to "
            "window.filterByCeoCfoBucket (click + keyboard activate "
            f"expected, found {n_delegate}) -- the tooltip would "
            "overpromise 'Click to filter table' again")

    # --- C2: setter + chip indicator exist ---------------------------
    if "window.filterByCeoCfoBucket = function" not in app:
        failures.append("C2 app.js does not define "
                        "window.filterByCeoCfoBucket")
    if "function updateCeoCfoFilterIndicator" not in app:
        failures.append("C2 app.js does not define "
                        "updateCeoCfoFilterIndicator")
    elif "chip.id = 'ceocfo-filter-chip'" not in app:
        failures.append("C2 CeoCfo indicator does not create chip "
                        "'ceocfo-filter-chip'")

    # --- C3: renderTable filters on the premium bucket ---------------
    render_body = extract_function_body(app, "function renderTable")
    if render_body is None:
        failures.append("C3 renderTable function not found in js/app.js")
    elif ("_activeCeoCfoBucket" not in render_body
          or "_ceoCfoPremium" not in render_body):
        failures.append("C3 renderTable does not filter on "
                        "_activeCeoCfoBucket / _ceoCfoPremium")

    # --- C4: _hasActiveFilters counts the bucket ---------------------
    has_body = extract_function_body(app, "window._hasActiveFilters = function")
    if has_body is None:
        failures.append("C4 _hasActiveFilters function not found")
    elif "window._activeCeoCfoBucket" not in has_body:
        failures.append("C4 _hasActiveFilters does not count "
                        "_activeCeoCfoBucket (Reset button hides while "
                        "the filter still hides rows)")

    # --- C5: every reset path nulls state + removes the chip ---------
    paths = [
        ("sortTableByKey", extract_function_body(app, "function sortTableByKey")),
        ("insightResetAndSort", extract_function_body(app, "function insightResetAndSort")),
        ("findCompanyInTable", extract_function_body(app, "window.findCompanyInTable = function")),
        ("resetAllFilters", extract_function_body(app, "window.resetAllFilters = function")),
    ]
    for name, body in paths:
        if body is None:
            failures.append(f"C5 {name} function not found in js/app.js")
            continue
        if not re.search(r"window\._activeCeoCfoBucket\s*=\s*null", body):
            failures.append(f"C5 {name} does not null _activeCeoCfoBucket")
        if "'ceocfo-filter-chip'" not in body:
            failures.append(f"C5 {name} does not remove chip "
                            "'ceocfo-filter-chip'")
    esc_start = app.find("// Clear all filters and search")
    esc_end = app.find("// If in search, blur it", esc_start + 1) if esc_start >= 0 else -1
    if esc_start < 0 or esc_end < 0:
        failures.append("C5 Escape clear-all branch markers not found")
    else:
        esc = app[esc_start:esc_end]
        if not re.search(r"window\._activeCeoCfoBucket\s*=\s*null", esc):
            failures.append("C5 Escape branch does not null "
                            "_activeCeoCfoBucket")
        if "'ceocfo-filter-chip'" not in esc:
            failures.append("C5 Escape branch does not remove chip "
                            "'ceocfo-filter-chip'")
    hc_start = app.find("// Listen for browser back/forward")
    hc_apply = app.find("applyHashState(companies);", hc_start + 1) if hc_start >= 0 else -1
    if hc_start < 0 or hc_apply < 0:
        failures.append("C5 hashchange reset block markers not found")
    else:
        hc = app[hc_start:hc_apply]
        if not re.search(r"window\._activeCeoCfoBucket\s*=\s*null", hc):
            failures.append("C5 hashchange reset does not null "
                            "_activeCeoCfoBucket")
        if "'ceocfo-filter-chip'" not in hc:
            failures.append("C5 hashchange reset does not remove chip "
                            "'ceocfo-filter-chip'")

    # --- C6: URL serialize + restore ---------------------------------
    ser_body = extract_function_body(app, "function serializeState()")
    if ser_body is None:
        failures.append("C6 serializeState function not found")
    else:
        for p in ("cfomin=", "cfomax=", "cfolbl="):
            if p not in ser_body:
                failures.append(f"C6 serializeState does not emit {p}")
    if "state.cfomin" not in app or "state.cfolbl" not in app:
        failures.append("C6 hash restore does not read cfomin/cfolbl")

    # --- C7: badge + announcement name the filter --------------------
    # 401st review: the badge part now carries the colon ('CEO/CFO: '
    # + label) so it matches the lone chip -- the old pinned literal
    # 'CEO/CFO ' (no colon) was the defect this review fixed.
    if "filterParts.push('CEO/CFO: '" not in app:
        failures.append("C7 combined-filter badge does not name the "
                        "CEO/CFO premium filter")
    if "announceMsg += ', CEO/CFO premium: '" not in app:
        failures.append("C7 table announcement does not name the "
                        "CEO/CFO premium filter")

    # --- C8: hash-restore sites re-apply highlight + chip ------------
    n_hl = app.count("highlightCeoCfoBucket(window._activeCeoCfoBucket.min, "
                     "window._activeCeoCfoBucket.max)")
    if n_hl < 2:
        failures.append("C8 fewer than 2 hash-restore sites re-apply the "
                        f"premium highlight (found {n_hl})")
    n_chip = app.count("updateCeoCfoFilterIndicator()")
    if n_chip < 3:
        failures.append("C8 fewer than 3 updateCeoCfoFilterIndicator() call "
                        f"sites (setter + 2 restores, found {n_chip})")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: ceocfo-filter-table: bar click filters the table, chip + "
          "URL + badge + announcement wired, all reset/restore paths cover it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
