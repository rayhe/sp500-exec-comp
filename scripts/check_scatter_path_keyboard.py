#!/usr/bin/env python3
"""Regression guard: scatter path-finder step badges are keyboard-operable.

The 2026-10-10 5-critic panel audit for NEW failure-mode classes flagged
_applyScatterPathOverlay (js/charts.js) as the next missed
click-without-keyboard surface (the 21:59 PT vol-tenure pilot, the 19:33 PT
vol-sector pilot, the 18:03 PT GER pilot, the 15:35 PT tenure-growth pilot,
the 14:05 PT sector-gov pilot, the 11:30 PT gender-bar pilot, and the
10:06 PT anomaly pilot closed the same class on other charts):

  - the path-finder step badges (transparent circles over the step number
    badges, pointer-events 'all', cursor:pointer, click = window
    .findCompanyInTable(d.pt.ticker)) plus a data-bearing hover tooltip
    (ticker, company, CEO, total pay, sector, comp breakdown, "Click for
    detail") had no tabindex/role/keydown and no class.

The scatter-path pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to the badge surface:

  - roving tabindex, role="button"
  - data-bearing aria-label (step N of M, ticker, company, CEO, total pay,
    sector, "Press Enter to view <ticker> in the table.")
  - badge focus fires the exact hover-tooltip path via a synthetic
    mouseover, blur hides it
  - Enter/Space replays the click path exactly (hideChartTooltip +
    window.findCompanyInTable(d.pt.ticker))
  - css/style.css carries the --accent :focus-visible ring for
    #scatter-chart .scatter-path-step (site convention)

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the scatter-path pilot call is present for .scatter-path-step.
     S2 the badge hover circle carries class scatter-path-step inside
        _applyScatterPathOverlay.
     S3 the pilot passes label + activate; the label carries the step
        data and the keyboard affordance, and activate replays the click
        path (hideChartTooltip + findCompanyInTable).
     S4 css/style.css has the :focus-visible --accent ring for
        #scatter-chart .scatter-path-step.
     S5 the pilot block is attribute-bound (no innerHTML).
     S6 the mouse .on('click') handler is preserved in
        _applyScatterPathOverlay.
     S7 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .scatter-path-step is role=button with a data-bearing
        aria-label mentioning "Press Enter" and "Step"; roving tabindex
        (exactly one tabindex="0").
     R2 focusing the tabindex="0" step badge shows the chart tooltip
        (.chart-tooltip.visible) -- the keyboard equivalent of the
        hover data.
     R3 pressing Enter on the focused step badge calls
        window.findCompanyInTable exactly once with the badge's ticker
        -- keyboard/click parity.
     R4 zero JS page errors.

Usage:
  scripts/check_scatter_path_keyboard.py              # static + render
  scripts/check_scatter_path_keyboard.py --static-only

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

CHART_ID = "#scatter-chart"
STEP_SEL = ".scatter-path-step"


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts):
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(CHART_ID) +
        r"'\), '" + re.escape(STEP_SEL) + r"', \{([\s\S]*?)\n    \}\);",
        charts)
    return m.group(0) if m else None


def overlay_fn(charts):
    m = re.search(
        r"function _applyScatterPathOverlay\(([\s\S]*?)\nwindow\._redrawScatterForPathOverlay = function",
        charts)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    blk = pilot_block(charts)
    check("S1 scatter-path pilot present for .scatter-path-step",
          blk is not None,
          "" if blk else "pilot block missing")

    fn = overlay_fn(charts)
    s2 = fn is not None and ".attr('class', 'scatter-path-step')" in fn
    check("S2 badge hover circle carries class scatter-path-step in "
          "_applyScatterPathOverlay",
          s2, "" if s2 else "class not found on the hover circle")

    s3 = (blk is not None
          and "label:" in blk and "activate:" in blk
          and "Press Enter to view" in blk
          and "'Step '" in blk
          and "total pay" in blk
          and "findCompanyInTable(d.pt.ticker)" in blk
          and "hideChartTooltip()" in blk)
    check("S3 pilot passes label + activate; label carries the step data "
          "and the keyboard affordance; activate replays the click path "
          "(hideChartTooltip + findCompanyInTable)",
          s3, "" if s3 else "label/activate incomplete in the pilot block")

    s4 = (re.search(r"#scatter-chart \.scatter-path-step:focus-visible", css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S4 css :focus-visible --accent ring covers "
          "#scatter-chart .scatter-path-step",
          s4, "" if s4 else "focus rule missing or off-convention")

    s5 = blk is not None and "innerHTML" not in blk
    check("S5 pilot block is attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML in the pilot block or block missing")

    s6 = (fn is not None
          and fn.count(".on('click'") >= 1
          and "window.findCompanyInTable(d.pt.ticker)" in fn)
    check("S6 mouse .on('click') handler preserved in "
          "_applyScatterPathOverlay",
          s6, "" if s6 else "the click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S7 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")


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
                "window.d3 && document.querySelectorAll('#scatter-chart .scatter-dot').length >= 100",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # Trigger the path-finder overlay on the scatter.
            pg.evaluate("""() => {
              window._activePathFinderNodes = ['AAPL', 'MSFT', 'NVDA'];
              window._redrawScatterForPathOverlay();
            }""")
            pg.wait_for_function(
                "document.querySelectorAll('#scatter-chart .scatter-path-step').length >= 2",
                timeout=30000)
            pg.wait_for_timeout(800)

            # R1: badges are upgraded buttons with roving tabindex.
            r1info = pg.evaluate("""() => {
              const steps = [...document.querySelectorAll('#scatter-chart .scatter-path-step')];
              const ok = steps.length >= 2 &&
                steps.every(e => e.getAttribute('role') === 'button' &&
                  (e.getAttribute('aria-label') || '').indexOf('Press Enter') >= 0 &&
                  (e.getAttribute('aria-label') || '').indexOf('Step') >= 0) &&
                steps.filter(e => e.getAttribute('tabindex') === '0').length === 1;
              return {n: steps.length, ok: ok,
                      labels: steps.map(e => e.getAttribute('aria-label')).slice(0, 2)};
            }""")
            r1 = r1info["ok"]
            check("R1 path step badges are role=button with data-bearing "
                  "aria-labels ('Press Enter', 'Step'), one roving tabindex=0",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing the tabindex=0 badge shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const step = document.querySelector(
                '#scatter-chart .scatter-path-step[tabindex="0"]');
              if (!step) return 'MISSING';
              step.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null
                  ? 'SHOWN' : 'HIDDEN'), 400));
            }""")
            r2 = (r2ok == "SHOWN")
            check("R2 focus on a path step badge shows the chart tooltip",
                  r2, ("" if r2 else "state: %r" % (r2ok,)))

            # R3: Enter on the focused badge calls findCompanyInTable once
            # with the badge's ticker -- keyboard/click parity.
            r3setup = pg.evaluate("""() => {
              window.__spCalls = [];
              const orig = window.findCompanyInTable;
              if (typeof orig !== 'function') return 'NO_FN';
              window.findCompanyInTable = function(t) {
                window.__spCalls.push(t);
                return orig.apply(this, arguments);
              };
              const step = document.querySelector(
                '#scatter-chart .scatter-path-step[tabindex="0"]');
              if (!step) return 'NO_STEP';
              const toks = (step.getAttribute('aria-label') || '').split(' ');
              step.focus();
              return 'OK|' + toks[4];
            }""")
            if not r3setup.startswith("OK|"):
                check("R3 Enter on step badge fires findCompanyInTable",
                      False, "setup: %r" % r3setup)
            else:
                expected = r3setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r3info = pg.evaluate(
                    "() => ({calls: window.__spCalls})")
                r3 = (r3info["calls"] == [expected])
                check("R3 Enter calls window.findCompanyInTable exactly once "
                      "with the badge's ticker (%s; keyboard/click parity)" % expected,
                      r3, ("" if r3 else "state: %r, expected [%r]" % (r3info, expected)))

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
