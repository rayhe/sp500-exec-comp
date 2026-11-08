#!/usr/bin/env python3
"""Guard: the data table keeps filtering when d3 failed to load.

Background (381st review, 2026-11-07): the site treats a failed d3 CDN
bundle as a supported degraded state (markChartsUnavailable,
window._d3Available: "The data table and company details still work"),
but three table-filter paths still depended on the chart layer:
  (1) the ten window.highlight* functions in js/charts.js dereference
  d3 on their first statement, and filter setters call them with only
  an existence check. filterByRatioBucket calls highlightCompDistBucket
  / highlightConcDistBucket BEFORE renderTable, so with d3 unavailable
  the click threw ReferenceError, set state (_activeRatioBucket) but
  never re-rendered the table: the footer stayed at 518, no chip
  appeared, no rmin/rmax reached the hash, and the user saw nothing
  happen. filterByCompBracket survived only by accident (its highlight
  call sits AFTER renderTable).
  (2) setActiveSector calls window._redrawSectorAwareCharts before the
  table re-renders; it redraws d3 charts unguarded, so a sector-chip
  click threw the same way.
  (3) advanced-filters.js refreshes the table from window.compData,
  falling back to the chart-layer window._chartData -- but app.js kept
  compData in a top-level let, so window.compData never existed, and
  with d3 unavailable initCharts never runs so _chartData stays unset:
  every AF select set state, chip and badge but silently re-rendered
  nothing.
  (4) toggleTheme calls redrawAllCharts on every theme switch, and its
  body dereferences _chartData.trends with no null check: with d3
  unavailable _chartData stays null, so every theme toggle threw
  (the theme itself still switched, since the attribute is set first).
The fix: a `if (typeof d3 === 'undefined') return;` first statement
in all ten highlight functions and in _redrawSectorAwareCharts, a
matching guard at the top of redrawAllCharts, plus
`window.compData = comp;` in loadData so the AF refresh path has a
chart-independent dataset.

Checks:
  C1 HARD FAIL: a charts.js highlight function does not carry the
     d3-availability guard before its first d3 dereference.
  C2 HARD FAIL: _redrawSectorAwareCharts does not carry the same guard
     before its first chart draw.
  C3 HARD FAIL: a highlight function body still dereferences d3 before
     the guard (guard present but not first).
  C4 HARD FAIL: loadData does not expose window.compData, so the AF
     refresh path depends on the chart-layer _chartData alone.
  C5 HARD FAIL: redrawAllCharts does not guard on d3 availability /
     _chartData presence before its first _chartData use -- toggleTheme
     calls it on every theme switch, so a d3 outage made every theme
     toggle throw (reading 'trends' of null _chartData).
Render (headless Chromium, d3 requests aborted to simulate the outage):
  R1 ratio-bar click filters the table to the bucket count with zero
     page errors.
  R2 sector-chip click filters the table with zero page errors.
  R3 AF governance select filters the table with zero page errors.
  R4 theme toggle switches the theme with zero page errors.
  R5 zero page errors across the render half.

Usage:
  scripts/check_d3_outage_table_filters.py
  scripts/check_d3_outage_table_filters.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import re
import socket
import subprocess
import sys
import time

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
APP_JS = os.path.join(REPO, "js", "app.js")

HIGHLIGHT_FNS = [
    "highlightRatioBucket",
    "highlightYoYBucket",
    "highlightSopDistBucket",
    "highlightSectorBar",
    "highlightCompDistBucket",
    "highlightGenderChart",
    "highlightCeoCfoBucket",
    "highlightConcDistBucket",
    "highlightGovChart",
    "highlightVolatilityBucket",
]

GUARD = "if (typeof d3 === 'undefined') return;"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


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


def static_checks():
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/charts.js: %s" % exc)
        return 2
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    for fn in HIGHLIGHT_FNS:
        body = extract_function_body(charts, "window.%s = function" % fn)
        if body is None:
            check("C1 %s exists in charts.js" % fn, False, "definition not found")
            continue
        guard_idx = body.find(GUARD)
        d3_idx = body.find("d3.")
        check("C1 %s guards on d3 availability" % fn,
              guard_idx >= 0,
              "guard missing" if guard_idx < 0 else "")
        if guard_idx >= 0:
            check("C3 %s guard precedes first d3 use" % fn,
                  d3_idx < 0 or guard_idx < d3_idx,
                  "d3 used at %d before guard at %d" % (d3_idx, guard_idx)
                  if d3_idx >= 0 and guard_idx > d3_idx else "")

    body = extract_function_body(charts, "window._redrawSectorAwareCharts = function")
    if body is None:
        check("C2 _redrawSectorAwareCharts exists in charts.js", False,
              "definition not found")
    else:
        guard_idx = body.find(GUARD)
        draw_idx = body.find("drawCompDistChart(")
        check("C2 _redrawSectorAwareCharts guards on d3 availability",
              guard_idx >= 0, "guard missing" if guard_idx < 0 else "")
        if guard_idx >= 0:
            check("C3 _redrawSectorAwareCharts guard precedes first draw",
                  draw_idx < 0 or guard_idx < draw_idx,
                  "draw at %d before guard at %d" % (draw_idx, guard_idx)
                  if draw_idx >= 0 and guard_idx > draw_idx else "")

    # C4: loadData exposes the dataset on window so the AF refresh path
    # does not depend on the chart-layer _chartData alone.
    load_body = extract_function_body(app, "async function loadData()")
    c4_ok = load_body is not None and "window.compData = comp;" in load_body
    check("C4 loadData exposes window.compData", c4_ok,
          "" if c4_ok else ("loadData not found" if load_body is None
                            else "window.compData assignment missing from loadData"))

    # C5: redrawAllCharts no-ops without d3 / uninitialized _chartData.
    redraw_body = extract_function_body(charts, "function redrawAllCharts()")
    if redraw_body is None:
        check("C5 redrawAllCharts exists in charts.js", False,
              "definition not found")
    else:
        guard_ok = ("if (typeof d3 === 'undefined' || !_chartData) return;"
                    in redraw_body)
        check("C5 redrawAllCharts guards on d3 / _chartData", guard_ok,
              "" if guard_ok else "guard missing")
        if guard_ok:
            g_idx = redraw_body.find("if (typeof d3 === 'undefined'")
            # First code use is the drawSectorChart call (the guard's own
            # comment mentions _chartData.trends, so a raw substring
            # search for it would false-fail on the comment).
            t_idx = redraw_body.find("drawSectorChart(_chartData")
            check("C5 redrawAllCharts guard precedes first _chartData use",
                  t_idx < 0 or g_idx < t_idx,
                  "use at %d before guard at %d" % (t_idx, g_idx)
                  if t_idx >= 0 and g_idx > t_idx else "")
    return 0


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def render_checks():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: render checks need playwright (pip install playwright)")
        return None

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            errors = []
            pg = browser.new_page(viewport={"width": 1280, "height": 800})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.route("**/d3*", lambda r: r.abort())
            pg.route("**/d3js.org/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            # R1: ratio-bar click filters the table with d3 unavailable.
            pg.click('th[data-sort="pay_ratio"]')
            pg.wait_for_selector(
                "#table-summary-bar .ratio-dist-bar-group", timeout=8000)
            pg.evaluate("""() => {
                const bars = [...document.querySelectorAll(
                    '#table-summary-bar .ratio-dist-bar-group')];
                const t = bars.find(b => b.getAttribute('onclick')
                    === 'filterByRatioBucket(100,200)');
                if (t) t.click();
            }""")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            check("R1 ratio-bar click filters table with d3 unavailable",
                  n1 == 175, "footer count=%s (want 175)" % n1)

            # R2: sector-chip click filters the table with d3 unavailable.
            pg.evaluate("() => { location.hash = ''; }")
            pg.wait_for_timeout(800)
            pg.locator(".chip", has_text="Information Technology").first.click()
            pg.wait_for_timeout(1200)
            n2 = footer_count()
            check("R2 sector-chip click filters table with d3 unavailable",
                  0 < n2 < 518, "footer count=%s" % n2)

            # R3: AF governance select filters the table with d3 unavailable.
            pg.evaluate("() => { location.hash = ''; }")
            pg.wait_for_timeout(800)
            pg.click("#advanced-filters-toggle")
            pg.wait_for_timeout(400)
            pg.evaluate("""() => {
                const d = document.querySelector(
                    'details.af-cat[data-cat="gov"]');
                if (d) d.open = true;
            }""")
            pg.select_option("#af-gov", "A")
            pg.wait_for_timeout(1200)
            n3 = footer_count()
            chip3 = pg.evaluate("() => !!document.getElementById('gov-filter-chip')")
            check("R3 AF gov select filters table with d3 unavailable",
                  0 < n3 < 518 and chip3,
                  "footer count=%s chip=%s" % (n3, chip3))

            # R4: theme toggle switches the theme with d3 unavailable.
            theme_before = pg.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            pg.click("#theme-toggle")
            pg.wait_for_timeout(500)
            theme_after = pg.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            check("R4 theme toggle switches theme with d3 unavailable",
                  theme_before != theme_after,
                  "theme %r -> %r" % (theme_before, theme_after))

            check("R5 zero page errors across the render half",
                  len(errors) == 0, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return (n1 == 175 and 0 < n2 < 518 and 0 < n3 < 518 and chip3
                    and theme_before != theme_after and len(errors) == 0)
    finally:
        server.terminate()


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = render_checks()
    if ok is None:
        print("render checks skipped")
        failed = [r for r in results if not r[1]]
        return 1 if failed else 0
    failed = [r for r in results if not r[1]]
    if failed or not ok:
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
