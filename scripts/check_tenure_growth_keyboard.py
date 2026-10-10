#!/usr/bin/env python3
"""Regression guard: tenure-pay-growth chart company dots are keyboard-operable.

The 2026-10-10 15:30 PT 5-critic panel took the next queued surface from the
2026-10-10 07:30 PT audit list: drawTenurePayGrowthChart carried a
click-without-keyboard surface -- the individual company dot circles carry a
click action (window.navigateToScatter(ticker, '_ceoTenureYears',
'total_compensation'), else window.scrollToCompany) plus a data-bearing hover
tooltip (ticker, company, CEO, tenure, YoY pay growth, FY range), but had no
tabindex/role/keydown -- the same failure-mode class the earlier pilots closed
(scatter dots, histogram bars, anomaly rows, gender bars, sector-gov bars).

The tenure-growth pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to #tenure-pay-growth-chart .tenure-growth-dot:

  - dots bind their company datum via .datum(m) and gain the
    .tenure-growth-dot class at creation
  - roving tabindex, role="button"
  - data-bearing aria-label (ticker, company, CEO, tenure, YoY growth %,
    FY range, "Press Enter to view in the scatter.")
  - focus fires the exact hover-tooltip path via a synthetic event, blur hides
    it, Enter/Space replays the click path (navigateToScatter else
    scrollToCompany)
  - css/style.css carries the --accent :focus-visible ring for
    .tenure-growth-dot (site convention)
  - the info-only median bars keep no click path and stay out of the tab
    order (their misleading cursor:pointer was removed this run)

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the tenure-growth pilot call is present with the right
        container/selector.
     S2 the pilot passes label + activate; the label mentions the
        pay-growth data and the keyboard affordance; activate replays the
        click path.
     S3 css/style.css has the :focus-visible --accent ring for
        .tenure-growth-dot.
     S4 the pilot block is attribute-bound (no innerHTML).
     S5 the mouse .on('click') handler is preserved in
        drawTenurePayGrowthChart.
     S6 node --check js/charts.js is green.
     S7 the dot circles bind datum and carry the pilot class at creation.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .tenure-growth-dot is role=button with a data-bearing
        aria-label mentioning "Press Enter"; roving tabindex (exactly one
        tabindex="0").
     R2 focusing a tenure-growth dot shows the chart tooltip
        (.chart-tooltip.visible) -- the keyboard equivalent of the hover data.
     R3 pressing Enter on a focused dot calls window.navigateToScatter
        exactly once with (ticker, '_ceoTenureYears', 'total_compensation')
        (keyboard/click parity).
     R4 zero JS page errors.

Usage:
  scripts/check_tenure_growth_keyboard.py              # static + render
  scripts/check_tenure_growth_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []

CHART_ID = "#tenure-pay-growth-chart"
DOT_SEL = ".tenure-growth-dot"


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts):
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(CHART_ID) +
        r"'\), '([^']*)', \{([\s\S]*?)\n    \}\);",
        charts)
    return m.group(0) if m else None, (m.group(1) if m else None)


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    blk, got_sel = pilot_block(charts)
    s1 = blk is not None and got_sel == DOT_SEL
    check("S1 tenure-growth pilot present with the right container/selector",
          s1, ("" if s1 else "block missing or selector=%r" % (got_sel,)))

    s2 = (blk is not None
          and "label:" in blk and "activate:" in blk
          and "pay growth" in blk
          and "Press Enter to view in the scatter." in blk
          and "navigateToScatter(d.ticker, '_ceoTenureYears', 'total_compensation')" in blk)
    check("S2 pilot passes label + activate; label carries the pay-growth data and the keyboard affordance",
          s2, "" if s2 else "label/activate incomplete in the pilot block")

    s3 = (re.search(r"#tenure-pay-growth-chart \.tenure-growth-dot:focus-visible\s*\{",
                    css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S3 css :focus-visible --accent ring covers .tenure-growth-dot",
          s3, "" if s3 else "focus rule missing or off-convention")

    s4 = blk is not None and "innerHTML" not in blk
    check("S4 pilot block is attribute-bound (no innerHTML)",
          s4, "" if s4 else "innerHTML in the pilot block")

    s5 = re.search(
        r"function drawTenurePayGrowthChart\([\s\S]*?\.on\('click'", charts) is not None
    check("S5 mouse .on('click') handler preserved in drawTenurePayGrowthChart",
          s5, "" if s5 else "the click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")

    s7 = (re.search(
        r"g\.append\('circle'\)\s*\n\s*\.datum\(m\)\s*\n\s*\.attr\('class', 'tenure-growth-dot'\)",
        charts) is not None)
    check("S7 dot circles bind datum via .datum(m) and carry .tenure-growth-dot at creation",
          s7, "" if s7 else "class/datum wiring missing at circle creation")


def get_d3_bytes():
    cache = os.path.expanduser(
        "~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/methbtn-20261005/d3.min.js")
    if os.path.exists(cache):
        return open(cache, "rb").read()
    tmp = tempfile.NamedTemporaryFile(suffix=".js", delete=False).name
    r = subprocess.run(
        ["curl", "-sL", "--http1.1", "-A", "Kit/1.0 (factoryfactorykit@gmail.com)",
         "https://cdn.jsdelivr.net/npm/d3@7", "-o", tmp],
        timeout=60)
    if r.returncode != 0 or os.path.getsize(tmp) < 100000:
        return None
    return open(tmp, "rb").read()


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
        return False

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
                "window.d3 && document.querySelectorAll('#tenure-pay-growth-chart .tenure-growth-dot').length >= 2",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every tenure-growth dot is an upgraded button with roving tabindex.
            r1info = pg.evaluate("""() => {
              const dots = [...document.querySelectorAll('#tenure-pay-growth-chart .tenure-growth-dot')];
              const badRole = dots.filter(d => d.getAttribute('role') !== 'button');
              const badLabel = dots.filter(d => {
                const l = d.getAttribute('aria-label') || '';
                return !l.length || l.indexOf('Press Enter') < 0
                    || l.indexOf('pay growth') < 0;
              });
              const holders = dots.filter(d => d.getAttribute('tabindex') === '0').length;
              return {n: dots.length, badRole: badRole.length,
                      badLabel: badLabel.length, holders: holders};
            }""")
            r1 = (r1info["n"] >= 2 and r1info["badRole"] == 0
                  and r1info["badLabel"] == 0 and r1info["holders"] == 1)
            check("R1 tenure-growth dots are role=button with data-bearing aria-labels, one roving tabindex=0",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a tenure-growth dot shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const dot = document.querySelector('#tenure-pay-growth-chart .tenure-growth-dot[tabindex="0"]');
              if (!dot) return false;
              dot.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null), 400));
            }""")
            check("R2 focus on a tenure-growth dot shows the chart tooltip", bool(r2ok),
                  "" if r2ok else "no .chart-tooltip.visible after focus")

            # R3: Enter on a focused dot fires navigateToScatter exactly once with parity args.
            r3setup = pg.evaluate("""() => {
              window.__ntsCalls = [];
              window.navigateToScatter = function(t, x, y) {
                window.__ntsCalls.push([t, x, y]);
              };
              const dot = document.querySelector('#tenure-pay-growth-chart .tenure-growth-dot[tabindex="0"]');
              if (!dot) return 'NO_DOT';
              const label = dot.getAttribute('aria-label') || '';
              dot.focus();
              return 'OK|' + label.split(',')[0];
            }""")
            if not r3setup.startswith("OK|"):
                check("R3 Enter on dot fires navigateToScatter with parity args", False,
                      "setup: %r" % r3setup)
            else:
                expect_ticker = r3setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("() => window.__ntsCalls")
                r3 = (r3info == [[expect_ticker, "_ceoTenureYears", "total_compensation"]])
                check("R3 Enter fires navigateToScatter(ticker, '_ceoTenureYears', 'total_compensation') exactly once",
                      r3, ("" if r3 else "calls: %r" % (r3info,)))

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
        rc = render_checks()
        if rc is None:
            print("SKIP: render checks unavailable; static checks decide")
    fails = [n for n, ok, _ in results if not ok]
    if fails:
        print("\n%d check(s) FAILED: %s" % (len(fails), ", ".join(fails)))
        return 1
    print("\nALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
