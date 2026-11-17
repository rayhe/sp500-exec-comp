#!/usr/bin/env python3
"""Regression guard: volatility-tenure chart click surfaces are keyboard-operable.

The 2026-10-10 5-critic panel audit for NEW failure-mode classes flagged
drawVolatilityTenureChart as the next missed click-without-keyboard surface
class (the 19:33 PT vol-sector pilot, the 18:03 PT GER pilot, the 15:35 PT
tenure-growth pilot, the 14:05 PT sector-gov pilot, the 11:30 PT gender-bar
pilot, and the 10:06 PT anomaly pilot closed the same class on other
charts):

  - the bracket median bars carry a click action (regular click filters
    the main table to the tenure bracket via window._activeVolTenureBracket
    + renderTable + scrollToTable; Shift+click navigates the scatter to the
    bracket's most volatile CEO) plus a data-bearing hover tooltip (bracket
    label, CEO count, median/mean volatility, IQR, most volatile/most stable
    tickers), but had no tabindex/role/keydown and no class.
  - the per-company jitter dots (circles, cursor:pointer) carry a click
    action (window.navigateToScatter(ticker, '_ceoTenureYears',
    '_ceoVolatility')) plus a data-bearing hover tooltip (ticker, company,
    CEO, tenure, volatility, total comp), but had no tabindex/role/keydown,
    no class, and no bound datum.

The vol-tenure pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to both surfaces:

  - roving tabindex, role="button"
  - data-bearing aria-labels (bar: bracket label, median/mean volatility,
    IQR, CEO count, "Press Enter to filter the table to this tenure
    bracket"; dot: ticker, company, CEO, tenure, volatility CV, "Press
    Enter to view in the scatter plot.")
  - bar/dot focus fires the exact hover-tooltip path via a synthetic
    mouseover, blur hides it
  - Enter/Space on bars replays the regular-click path (hideChartTooltip
    + window._activeVolTenureBracket + renderTable + scrollToTable +
    announce); on dots it replays the click path (navigateToScatter with
    the bound datum)
  - css/style.css carries the --accent :focus-visible ring for both
    classes (site convention)

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the vol-tenure pilot call is present for .vol-tenure-bar.
     S2 the vol-tenure pilot call is present for .vol-tenure-dot.
     S3 the pilots pass label + activate; the bar label carries the
        volatility data and the keyboard affordance, and its activate
        replays the bracket-filter click path; the dot label carries the
        ticker and its activate replays navigateToScatter.
     S4 css/style.css has the :focus-visible --accent ring for both
        classes.
     S5 the pilot blocks are attribute-bound (no innerHTML).
     S6 the mouse click paths are preserved (bars + dots .on('click')).
     S7 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .vol-tenure-bar is role=button with a data-bearing
        aria-label mentioning "Press Enter" and volatility; every
        .vol-tenure-dot is role=button with a data-bearing aria-label
        mentioning "Press Enter" and CV; roving tabindex (exactly one
        tabindex="0" per surface).
     R2 focusing a bracket bar shows the chart tooltip
        (.chart-tooltip.visible); focusing a jitter dot shows it too --
        the keyboard equivalent of the hover data.
     R3 pressing Enter on a focused bracket bar filters the table to the
        bar's bracket exactly once (window._activeVolTenureBracket.label
        matches the bar's bracket and window.scrollToTable is called once)
        -- keyboard/click parity.
     R4 zero JS page errors.

Usage:
  scripts/check_vol_tenure_keyboard.py              # static + render
  scripts/check_vol_tenure_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

492nd review (2026-11-16): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping. Pre-fix
defects: main() ignored render_checks()'s return value except the
None case, so a missing d3 shim returned 0 with "ALL 7 CHECKS
PASSED" while the render half never ran (the silent-pass variant,
430th-review shape, although the docstring promises exit 2 for a
missing shim); a missing playwright install returned 0 the same way
(the None branch printed "SKIP: render checks unavailable; static
checks decide" and decided on the statics alone); and the INFRA
sentinel itself is truthy, so a render half returning INFRA would
have returned 0 the same way (latent silent pass, S4 form); and a
transient render exception raised before any R-check was uncaught
(no retry wrapper) -- proved in-process before the fix
(~/workspace/sp500-492/pre492_proof.py: Test A-live rc=0, "ALL 7
CHECKS PASSED", 0 R-checks; Test A2 rc=0, "ALL 7 CHECKS PASSED",
0 R-checks; Test A3 rc=0, "ALL 7 CHECKS PASSED", 0 R-checks;
Test B UNCATCHED RuntimeError on a simulated transient Chromium
launch stall). static_checks() gains the OSError-to-return-2 path
(488th template). The adopted main also closes the late-raise hole
the 483rd shape leaves open: a render half returning False with no
FAIL recorded (exception after passing R-checks) now returns 1 with
"render half failed (see INFRA lines above)" instead of printing
"ALL 7 CHECKS PASSED" and returning 0 -- the 489th shape, preferred
over the 486th-488th one (see the 489th note (107)).
render_checks() already returns an explicit bool on success, so no
None-on-success fix was needed (458th note (27) checked). Slowest
unadopted shard-4 render guard by the multi-run history plus the
re-profile: 16 shard-4 runs: median 11.7s / max 42.5s, and 11.87s
standalone (this run, clean, before the canary) vs
zero_row_single_dim_badge median 12.6s / max 38.2s and 9.26s
standalone -- vol-tenure leads the clean re-profile and the
all-time max; zero-row's only leads are the multi-run median and
the freshest state reading (11.5s vs 10.7s), per the 469th note (68)
rule that the evidence base is the multi-run history plus the
re-profile, not one state reading.
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

CHART_ID = "#volatility-tenure-chart"
BAR_SEL = ".vol-tenure-bar"
DOT_SEL = ".vol-tenure-dot"


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
        css = open(CSS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read a source file: %s" % exc)
        return 2

    bar_blk = pilot_block(charts, BAR_SEL)
    check("S1 vol-tenure pilot present for .vol-tenure-bar",
          bar_blk is not None,
          "" if bar_blk else "bar pilot block missing")

    dot_blk = pilot_block(charts, DOT_SEL)
    check("S2 vol-tenure pilot present for .vol-tenure-dot",
          dot_blk is not None,
          "" if dot_blk else "dot pilot block missing")

    s3 = (bar_blk is not None
          and "label:" in bar_blk and "activate:" in bar_blk
          and "median CEO pay volatility" in bar_blk
          and "Press Enter to filter the table to this tenure bracket" in bar_blk
          and "_activeVolTenureBracket" in bar_blk
          and dot_blk is not None
          and "Press Enter to view in the scatter plot" in dot_blk
          and "navigateToScatter(c.ticker" in dot_blk
          and "'_ceoTenureYears'" in dot_blk
          and "'_ceoVolatility'" in dot_blk)
    check("S3 pilots pass label + activate; bar label carries the "
          "volatility data and the keyboard affordance and replays the "
          "bracket-filter path; dot replays navigateToScatter",
          s3, "" if s3 else "label/activate incomplete in the pilot blocks")

    s4 = (re.search(r"#volatility-tenure-chart \.vol-tenure-bar:focus-visible", css) is not None
          and re.search(r"#volatility-tenure-chart \.vol-tenure-dot:focus-visible", css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S4 css :focus-visible --accent ring covers .vol-tenure-bar and "
          ".vol-tenure-dot",
          s4, "" if s4 else "focus rule missing or off-convention")

    s5 = ((bar_blk is None or "innerHTML" not in bar_blk)
          and (dot_blk is None or "innerHTML" not in dot_blk)
          and bar_blk is not None and dot_blk is not None)
    check("S5 pilot blocks are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML in a pilot block or block missing")

    fn = re.search(
        r"function drawVolatilityTenureChart\(companies\) \{([\s\S]*?)\nfunction _buildVolGovSectorChips",
        charts)
    s6 = fn is not None and fn.group(1).count(".on('click'") >= 2
    check("S6 mouse .on('click') handlers preserved in drawVolatilityTenureChart "
          "(bracket bars + jitter dots)",
          s6, "" if s6 else "a click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S7 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")


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
    if d3 is None:
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
                "window.d3 && document.querySelectorAll('#volatility-tenure-chart .vol-tenure-bar').length >= 2 && "
                "document.querySelectorAll('#volatility-tenure-chart .vol-tenure-dot').length >= 1",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: both surfaces are upgraded buttons with roving tabindex.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#volatility-tenure-chart .vol-tenure-bar')];
              const dots = [...document.querySelectorAll('#volatility-tenure-chart .vol-tenure-dot')];
              const checkSet = (els, phrase) => els.length >= 1 &&
                els.every(e => e.getAttribute('role') === 'button' &&
                  (e.getAttribute('aria-label') || '').indexOf('Press Enter') >= 0 &&
                  (e.getAttribute('aria-label') || '').indexOf(phrase) >= 0) &&
                els.filter(e => e.getAttribute('tabindex') === '0').length === 1;
              return {nb: bars.length, nd: dots.length,
                      barsOk: checkSet(bars, 'median CEO pay volatility'),
                      dotsOk: checkSet(dots, '% CV')};
            }""")
            r1 = (r1info["barsOk"] and r1info["dotsOk"])
            check("R1 vol-tenure bars + jitter dots are role=button with "
                  "data-bearing aria-labels, one roving tabindex=0 per surface",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a bracket bar shows the chart tooltip; same for a dot.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#volatility-tenure-chart .vol-tenure-bar[tabindex="0"]');
              const dot = document.querySelector('#volatility-tenure-chart .vol-tenure-dot[tabindex="0"]');
              if (!bar || !dot) return 'MISSING';
              bar.focus();
              const barOk = document.querySelector('.chart-tooltip.visible') !== null;
              dot.focus();
              return new Promise(res => setTimeout(() => res(
                (barOk ? 'BAR' : 'NO-BAR') + '|' +
                (document.querySelector('.chart-tooltip.visible') !== null ? 'DOT' : 'NO-DOT')), 400));
            }""")
            r2 = (r2ok == "BAR|DOT")
            check("R2 focus on a bracket bar and on a jitter dot each shows "
                  "the chart tooltip",
                  r2, ("" if r2 else "state: %r" % (r2ok,)))

            # R3: Enter on a focused bracket bar filters the table exactly
            # once (window._activeVolTenureBracket.label matches the bar's
            # bracket, window.scrollToTable called once).
            r3setup = pg.evaluate("""() => {
              window.__stCalls = [];
              const orig = window.scrollToTable;
              if (typeof orig !== 'function') return 'NO_FN';
              window.scrollToTable = function() {
                window.__stCalls.push(1);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#volatility-tenure-chart .vol-tenure-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              const expected = (bar.getAttribute('aria-label') || '').split(':')[0];
              bar.focus();
              return 'OK|' + expected;
            }""")
            if not r3setup.startswith("OK|"):
                check("R3 Enter on bracket bar filters table to the bracket",
                      False, "setup: %r" % r3setup)
            else:
                expected = r3setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r3info = pg.evaluate("""() => {
                  const b = window._activeVolTenureBracket;
                  return {st: window.__stCalls, label: b ? b.label : null};
                }""")
                r3 = (r3info["st"] == [1] and r3info["label"] == expected)
                check("R3 Enter filters the table to the bar's bracket exactly "
                      "once (bracket label set, scrollToTable x1; keyboard/click parity)",
                      r3, ("" if r3 else "state: %r, expected %r" % (r3info, expected)))

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
        print("static-only: skipping render checks")
        fails = [n for n, ok, _ in results if not ok]
        if fails:
            print("FAILED: " + ", ".join(fails))
            return 1
        print("\nALL %d CHECKS PASSED" % len(results))
        return 0
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
    print("\nALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
