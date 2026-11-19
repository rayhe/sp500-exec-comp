#!/usr/bin/env python3
"""Regression guard: volatility-sector chart click surfaces are keyboard-operable.

The 2026-10-10 5-critic panel audit for NEW failure-mode classes flagged
drawVolatilitySectorChart as the next missed click-without-keyboard surface
class (the 14:05 PT sector-gov pilot, the 11:34 PT gender-bar pilot, and the
10:06 PT anomaly pilot closed the same class on other charts):

  - the median .med-bar rects carry a click action (regular click filters
    the main table to the sector via the matching #sector-chips .chip,
    Shift+click navigates the scatter to the sector's most volatile
    company) plus a data-bearing hover tooltip (median volatility, IQR,
    company count), but had no tabindex/role/keydown.
  - the per-bar scatter nav icons (arrows, text elements with
    cursor:pointer) carry a click action
    (window.navigateToScatter(ticker, '_ceoVolatility',
    'total_compensation')) plus a data-bearing hover tooltip
    ('View <ticker> (<cv>% CV) in Scatter Plot'), but had no
    tabindex/role/keydown and no class at all.

The vol-sector pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to both surfaces:

  - roving tabindex, role="button"
  - data-bearing aria-labels (sector, median volatility, IQR, company
    count, "Press Enter to filter the table to this sector"; icon:
    ticker, CV, sector, "Press Enter to open the scatter.")
  - bar/icon focus fires the exact hover-tooltip path via a synthetic
    mouseover, blur hides it
  - Enter/Space on bars replays the regular-click path (hideChartTooltip
    + sector-chip click + scrollToTable + announce); on nav icons it
    replays the click path (navigateToScatter with the bound datum)
  - css/style.css carries the --accent :focus-visible ring for both
    classes (site convention); the old .med-bar cursor rule now also
    covers .vol-sector-bar

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the vol-sector pilot call is present for .vol-sector-bar.
     S2 the vol-sector pilot call is present for .vol-sector-nav-icon.
     S3 the pilots pass label + activate; the bar label carries the
        volatility data and the keyboard affordance; the icon label
        carries ticker + CV.
     S4 css/style.css has the :focus-visible --accent ring for both
        classes.
     S5 the pilot blocks are attribute-bound (no innerHTML).
     S6 the mouse click paths are preserved (chip filter on bars,
        navigateToScatter on icons).
     S7 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .vol-sector-bar and .vol-sector-nav-icon is role=button
        with a data-bearing aria-label mentioning "Press Enter"; roving
        tabindex (exactly one tabindex="0" per surface).
     R2 focusing a median bar shows the chart tooltip
        (.chart-tooltip.visible) -- the keyboard equivalent of the hover
        data; same for a nav icon.
     R3 pressing Enter on a focused median bar filters the table to the
        bar's sector exactly once (the sector chip becomes active and
        window.scrollToTable is called once) -- keyboard/click parity.
     R4 zero JS page errors.

Usage:
  scripts/check_vol_sector_keyboard.py              # static + render
  scripts/check_vol_sector_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

514th review (2026-11-18): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of silently passing).
Pre-fix defects, both 429th-review classes in one guard: a missing d3
shim made render_checks() return False, which main() ignored -- only
the None (playwright-missing) branch was handled -- so the guard
exited 0 with "ALL 7 CHECKS PASSED" although the docstring promises
exit 2 for a missing shim, and the render half never ran (the
483rd-shape silent-pass form; the 7/7 count itself is the tell, the
4 render checks never run). A transient render exception raised
before any R-check was uncaught (no retry wrapper) -- proved
in-process before the fix (~/workspace/sp500-514/pre514_proof.py:
Test A rc=0, "ALL 7 CHECKS PASSED", 0 R-checks; Test A2 rc=0
skip-on-statics; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). No live corroboration claimed for
this guard: no vol-sector canary failure is on record this cycle
(unlike header, 513th). The playwright-missing branch keeps its skip
shape (rc=0 on passing statics) and the docstring's exit-2 promise
for that branch is unchanged from the pre-fix guard, per the
486th/487th precedent. static_checks() now returns 2 on an
unreadable js/charts.js or css/style.css (the 493rd shape's rc
check). Slowest unadopted render guard by both readings this run:
freshest in-canary 8.5s vs summary_bar_keyboard 8.2s vs
voltenure_badge_prefix 7.9s in the 2026-11-18T22:46Z shard-3 run,
and the fresh standalone re-profile this run 14.70s vs 11.42s vs
11.10s -- both readings agree on vol-sector, so the pick is clean
per the 469th note (68) rule that the evidence base is the
multi-run history plus the re-profile, not one state reading. Shard
verified with drift_canary._guard_shard (432nd note):
vol_sector_keyboard in shard 3 (with the full check_ name; see note
(157) for the bare-name trap and note (161) for the .py-suffix trap).
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []

CHART_ID = "#volatility-sector-chart"
BAR_SEL = ".vol-sector-bar"
ICON_SEL = ".vol-sector-nav-icon"


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts, sel):
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(CHART_ID) +
        r"'\), '" + re.escape(sel) + r"', \{([\s\S]*?)\n    \}\);",
        charts)
    return m.group(0) if m else None


def static_checks():
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/charts.js: %s" % exc)
        return 2
    try:
        css = open(CSS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read css/style.css: %s" % exc)
        return 2

    bar_blk = pilot_block(charts, BAR_SEL)
    check("S1 vol-sector pilot present for .vol-sector-bar",
          bar_blk is not None,
          "" if bar_blk else "bar pilot block missing")

    ico_blk = pilot_block(charts, ICON_SEL)
    check("S2 vol-sector pilot present for .vol-sector-nav-icon",
          ico_blk is not None,
          "" if ico_blk else "nav-icon pilot block missing")

    s3 = (bar_blk is not None
          and "label:" in bar_blk and "activate:" in bar_blk
          and "median CEO pay volatility" in bar_blk
          and "Press Enter to filter the table to this sector" in bar_blk
          and "sector-chips .chip" in bar_blk
          and ico_blk is not None
          and "Press Enter to open the scatter" in ico_blk
          and "navigateToScatter(d.ticker" in ico_blk)
    check("S3 pilots pass label + activate; bar label carries the "
          "volatility data and the keyboard affordance; icon replays "
          "navigateToScatter",
          s3, "" if s3 else "label/activate incomplete in the pilot blocks")

    s4 = (re.search(r"#volatility-sector-chart \.vol-sector-bar:focus-visible", css) is not None
          and re.search(r"#volatility-sector-chart \.vol-sector-nav-icon:focus-visible", css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S4 css :focus-visible --accent ring covers .vol-sector-bar and "
          ".vol-sector-nav-icon",
          s4, "" if s4 else "focus rule missing or off-convention")

    s5 = ((bar_blk is None or "innerHTML" not in bar_blk)
          and (ico_blk is None or "innerHTML" not in ico_blk)
          and bar_blk is not None and ico_blk is not None)
    check("S5 pilot blocks are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML in a pilot block or block missing")

    s6 = re.search(
        r"function drawVolatilitySectorChart\([\s\S]*?\.on\('click'", charts) is not None
    check("S6 mouse .on('click') handlers preserved in drawVolatilitySectorChart",
          s6, "" if s6 else "a click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S7 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")
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
    d3 = get_d3_bytes()
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-proxy-server"])
            errors = []
            pg = browser.new_page(viewport={"width": 1440, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript", body=d3)

            pg.route("**/npm/d3@7*", d3_route)
            pg.route("**/unpkg.com/d3@7*", d3_route)
            pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, wait_until="load")
            pg.wait_for_function(
                "window.d3 && document.querySelectorAll('#volatility-sector-chart .vol-sector-bar').length >= 2 && "
                "document.querySelectorAll('#volatility-sector-chart .vol-sector-nav-icon').length >= 1",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: both surfaces are upgraded buttons with roving tabindex.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#volatility-sector-chart .vol-sector-bar')];
              const icons = [...document.querySelectorAll('#volatility-sector-chart .vol-sector-nav-icon')];
              const checkSet = (els, phrase) => els.length >= 1 &&
                els.every(e => e.getAttribute('role') === 'button' &&
                  (e.getAttribute('aria-label') || '').indexOf('Press Enter') >= 0 &&
                  (e.getAttribute('aria-label') || '').indexOf(phrase) >= 0) &&
                els.filter(e => e.getAttribute('tabindex') === '0').length === 1;
              return {nb: bars.length, ni: icons.length,
                      barsOk: checkSet(bars, 'median CEO pay volatility'),
                      iconsOk: checkSet(icons, '% CV')};
            }""")
            r1 = (r1info["barsOk"] and r1info["iconsOk"])
            check("R1 vol-sector bars + nav icons are role=button with "
                  "data-bearing aria-labels, one roving tabindex=0 per surface",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a median bar shows the chart tooltip; same for a nav icon.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#volatility-sector-chart .vol-sector-bar[tabindex="0"]');
              const icon = document.querySelector('#volatility-sector-chart .vol-sector-nav-icon[tabindex="0"]');
              if (!bar || !icon) return 'MISSING';
              bar.focus();
              const barOk = document.querySelector('.chart-tooltip.visible') !== null;
              icon.focus();
              return new Promise(res => setTimeout(() => res(
                (barOk ? 'BAR' : 'NO-BAR') + '|' +
                (document.querySelector('.chart-tooltip.visible') !== null ? 'ICON' : 'NO-ICON')), 400));
            }""")
            r2 = (r2ok == "BAR|ICON")
            check("R2 focus on a median bar and on a nav icon each shows "
                  "the chart tooltip",
                  r2, ("" if r2 else "state: %r" % (r2ok,)))

            # R3: Enter on a focused median bar filters the table exactly once
            # (sector chip becomes active, window.scrollToTable called once).
            r3setup = pg.evaluate("""() => {
              window.__stCalls = [];
              const orig = window.scrollToTable;
              if (typeof orig !== 'function') return 'NO_FN';
              window.scrollToTable = function() {
                window.__stCalls.push(1);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#volatility-sector-chart .vol-sector-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              const expected = (bar.getAttribute('aria-label') || '').split(':')[0];
              bar.focus();
              return 'OK|' + expected;
            }""")
            if not r3setup.startswith("OK|"):
                check("R3 Enter on median bar filters table to sector",
                      False, "setup: %r" % r3setup)
            else:
                expected = r3setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("""() => {
                  const act = document.querySelector('#sector-chips .chip.active');
                  return {st: window.__stCalls, active: act ? act.textContent : null};
                }""")
                r3 = (r3info["st"] == [1] and r3info["active"] == expected)
                check("R3 Enter filters the table to the bar's sector exactly "
                      "once (chip active, scrollToTable x1; keyboard/click parity)",
                      r3, ("" if r3 else "state: %r" % (r3info,)))

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
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
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
    fails = [n for n, ok, _ in results if not ok]
    if fails or ok is False:
        if fails:
            print("FAILED: " + ", ".join(fails))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("ALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
