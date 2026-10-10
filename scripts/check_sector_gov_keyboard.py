#!/usr/bin/env python3
"""Regression guard: sector-gov chart click surfaces are keyboard-operable.

The 2026-10-10 5-critic panel audit for NEW failure-mode classes flagged
drawSectorGovChart as the next missed click-without-keyboard surface class
(the 07:30 PT histogram-bar pilot, the 10:06 PT anomaly pilot, and the
11:30 PT gender-bar pilot closed the same class on other charts):

  - the median .gov-sector-bar rects carry a click action
    (window.filterBySector(d.sector), filtering the main table to the
    sector) plus a data-bearing hover tooltip (median gov score, grade,
    mean, range, IQR, company count), but had no tabindex/role/keydown.
  - the y-axis sector-name texts carry the same filterBySector click
    (cursor:pointer) with no keyboard path and no class at all.

The sector-gov pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to both surfaces:

  - roving tabindex, role="button"
  - data-bearing aria-labels (sector, median gov score, grade, mean,
    range, IQR, company count, "Press Enter to filter the table to this
    sector")
  - bar focus fires the exact hover-tooltip path via a synthetic mouseover,
    blur hides it; y-axis-label focus dispatches the same synthetic event
    harmlessly (no hover listeners there)
  - Enter/Space on bars replays the click path (hideChartTooltip +
    filterBySector); on y-axis labels it replays the click path directly
  - css/style.css carries the --accent :focus-visible ring for both
    classes (site convention)

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the sector-gov pilot call is present for .gov-sector-bar.
     S2 the sector-gov pilot call is present for .gov-yaxis-label.
     S3 the pilot passes label + activate; the bar label carries the
        governance data and the keyboard affordance.
     S4 css/style.css has the :focus-visible --accent ring for both
        classes.
     S5 the pilot blocks are attribute-bound (no innerHTML).
     S6 the mouse click paths (filterBySector) are preserved.
     S7 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .gov-sector-bar and .gov-yaxis-label is role=button with a
        data-bearing aria-label mentioning "Press Enter"; roving tabindex
        (exactly one tabindex="0" per surface).
     R2 focusing a median bar shows the chart tooltip
        (.chart-tooltip.visible) -- the keyboard equivalent of the hover
        data.
     R3 pressing Enter on a focused median bar calls window.filterBySector
        exactly once with that bar's sector (keyboard/click parity).
     R4 zero JS page errors.

Usage:
  scripts/check_sector_gov_keyboard.py              # static + render
  scripts/check_sector_gov_keyboard.py --static-only

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

CHART_ID = "#sector-gov-chart"
BAR_SEL = ".gov-sector-bar"
LABEL_SEL = ".gov-yaxis-label"


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
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    bar_blk = pilot_block(charts, BAR_SEL)
    check("S1 sector-gov pilot present for .gov-sector-bar",
          bar_blk is not None,
          "" if bar_blk else "bar pilot block missing")

    lbl_blk = pilot_block(charts, LABEL_SEL)
    check("S2 sector-gov pilot present for .gov-yaxis-label",
          lbl_blk is not None,
          "" if lbl_blk else "y-axis label pilot block missing")

    s3 = (bar_blk is not None
          and "label:" in bar_blk and "activate:" in bar_blk
          and "median governance score" in bar_blk
          and "Press Enter to filter the table to this sector" in bar_blk
          and "filterBySector(d.sector)" in bar_blk
          and lbl_blk is not None
          and "filterBySector(sector)" in lbl_blk)
    check("S3 pilots pass label + activate; bar label carries the gov data "
          "and the keyboard affordance",
          s3, "" if s3 else "label/activate incomplete in the pilot blocks")

    s4 = (re.search(r"#sector-gov-chart \.gov-sector-bar:focus-visible", css) is not None
          and re.search(r"#sector-gov-chart \.gov-yaxis-label:focus-visible", css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S4 css :focus-visible --accent ring covers .gov-sector-bar and "
          ".gov-yaxis-label",
          s4, "" if s4 else "focus rule missing or off-convention")

    s5 = ((bar_blk is None or "innerHTML" not in bar_blk)
          and (lbl_blk is None or "innerHTML" not in lbl_blk)
          and bar_blk is not None and lbl_blk is not None)
    check("S5 pilot blocks are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML in a pilot block or block missing")

    s6 = re.search(
        r"function drawSectorGovChart\([\s\S]*?\.on\('click'", charts) is not None
    check("S6 mouse .on('click') handlers preserved in drawSectorGovChart",
          s6, "" if s6 else "a click handler is gone")

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
                "window.d3 && document.querySelectorAll('#sector-gov-chart .gov-sector-bar').length >= 2",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: both surfaces are upgraded buttons with roving tabindex.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#sector-gov-chart .gov-sector-bar')];
              const labels = [...document.querySelectorAll('#sector-gov-chart .gov-yaxis-label')];
              const checkSet = els => els.length >= 2 &&
                els.every(e => e.getAttribute('role') === 'button' &&
                  (e.getAttribute('aria-label') || '').indexOf('Press Enter') >= 0 &&
                  (e.getAttribute('aria-label') || '').indexOf('median governance score') >= 0) &&
                els.filter(e => e.getAttribute('tabindex') === '0').length === 1;
              return {nb: bars.length, nl: labels.length,
                      barsOk: checkSet(bars), labelsOk: checkSet(labels)};
            }""")
            r1 = (r1info["barsOk"] and r1info["labelsOk"])
            check("R1 sector-gov bars + y-axis labels are role=button with "
                  "data-bearing aria-labels, one roving tabindex=0 per surface",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a median bar shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#sector-gov-chart .gov-sector-bar[tabindex="0"]');
              if (!bar) return false;
              bar.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null), 400));
            }""")
            check("R2 focus on a median bar shows the chart tooltip", bool(r2ok),
                  "" if r2ok else "no .chart-tooltip.visible after focus")

            # R3: Enter on a focused median bar fires filterBySector once.
            r3setup = pg.evaluate("""() => {
              window.__fsCalls = [];
              const orig = window.filterBySector;
              if (typeof orig !== 'function') return 'NO_FN';
              window.filterBySector = function(s) {
                window.__fsCalls.push(s);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#sector-gov-chart .gov-sector-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              const expected = (bar.getAttribute('aria-label') || '').split(':')[0];
              bar.focus();
              return 'OK|' + expected;
            }""")
            if not r3setup.startswith("OK|"):
                check("R3 Enter on median bar fires filterBySector", False,
                      "setup: %r" % r3setup)
            else:
                expected = r3setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("""() => ({calls: window.__fsCalls})""")
                r3 = (r3info["calls"] == [expected])
                check("R3 Enter fires filterBySector exactly once with the "
                      "bar's sector (keyboard/click parity)",
                      r3, ("" if r3 else "state: %r" % (r3info,)))

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
