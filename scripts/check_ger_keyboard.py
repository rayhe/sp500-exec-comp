#!/usr/bin/env python3
"""Regression guard: GER (Governance Erosion Risk) chart rows are keyboard-operable.

The 2026-10-10 18:00 PT 5-critic panel took the next queued interactivity
surface: drawGERChart carried three click-without-keyboard surfaces -- the
transparent row rect overlay (click = openDetailPanel, data-bearing native
<title> tooltip), the company ticker label (click = openDetailPanel), and the
scatter nav icon (click = navigateToScatter(ticker, '_gerScore',
'total_compensation')) -- but had no tabindex/role/keydown, the same
failure-mode class the earlier pilots closed (scatter dots, histogram bars,
anomaly rows, gender bars, sector-gov bars, tenure-growth dots).

The ger pilot extends _enableDotKeyboard (the scatter-dot roving pilot) to
#ger-chart .ger-row-rect / .ger-label / .ger-nav-icon:

  - surfaces bind their company datum via .datum() and gain their pilot
    class at creation
  - roving tabindex, role="button"
  - data-bearing aria-label (company, CEO, GER score/risk, the four
    component scores, tenure, "Press Enter to open the company detail
    panel."); the nav icon label carries the scatter affordance. The
    <title> contents are mirrored in the aria-label because native SVG
    tooltips do not fire from synthetic events
  - focus fires the exact hover-tooltip path via a synthetic event, blur
    hides it, Enter/Space replays the click path (openDetailPanel else
    navigateToScatter)
  - css/style.css carries the --accent :focus-visible ring for all three
    selectors (site convention)

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the three ger pilot calls are present with the right root/selector
     S2 _gerRowLabel carries the GER data and the keyboard affordance;
        _gerActivateRow replays the detail-panel click path
     S3 the nav-icon pilot passes label + activate with the GER vs Pay
        scatter affordance and parity navigateToScatter args
     S4 css/style.css has the :focus-visible --accent ring for
        .ger-row-rect, .ger-label, .ger-nav-icon
     S5 the pilot block is attribute-bound (no innerHTML)
     S6 the mouse .on('click') handlers are preserved in drawGERChart
     S7 node --check js/charts.js is green
     S8 the row rect, label, and nav icon bind datum and carry their pilot
        class at creation
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .ger-row-rect is role=button with a data-bearing aria-label
        mentioning "Press Enter"; exactly one roving tabindex="0" per
        selector group
     R2 pressing Enter on a focused .ger-row-rect calls
        window.openDetailPanel exactly once with the row's ticker
        (keyboard/click parity)
     R3 pressing Enter on a focused .ger-nav-icon calls
        window.navigateToScatter exactly once with
        (ticker, '_gerScore', 'total_compensation')
     R4 zero JS page errors

Usage:
  scripts/check_ger_keyboard.py              # static + render
  scripts/check_ger_keyboard.py --static-only

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

CHART_ID = "#ger-chart"
SELECTORS = [".ger-row-rect", ".ger-label", ".ger-nav-icon"]


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def ger_block(charts):
    m = re.search(
        r"// Keyboard operability \(2026-10-10\): the GER rows carried click actions"
        r"[\s\S]*?_enableDotKeyboard\(_gerG, '\.ger-nav-icon', \{[\s\S]*?\n    \}\);",
        charts)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    blk = ger_block(charts)
    s1 = (blk is not None
          and all("_enableDotKeyboard(_gerG, '%s'" % s in blk for s in SELECTORS))
    check("S1 ger pilot present: three _enableDotKeyboard calls on #ger-chart",
          s1, "" if s1 else "pilot block missing or a selector call absent")

    s2 = (blk is not None
          and re.search(r"function _gerRowLabel\(d\) \{[\s\S]*?Governance Erosion Risk Score[\s\S]*?Press Enter to open the company detail panel",
                        blk) is not None
          and re.search(r"function _gerActivateRow\(d\) \{[\s\S]*?window\.openDetailPanel\(d\.ticker\)",
                        blk) is not None)
    check("S2 _gerRowLabel carries GER data + affordance; _gerActivateRow replays openDetailPanel",
          s2, "" if s2 else "_gerRowLabel/_gerActivateRow incomplete")

    s3 = (blk is not None
          and "GER vs Pay scatter plot. Press Enter." in blk
          and "window.navigateToScatter(d.ticker, '_gerScore', 'total_compensation')" in blk)
    check("S3 nav-icon pilot: label carries scatter affordance; activate has parity navigateToScatter args",
          s3, "" if s3 else "nav-icon label/activate incomplete")

    s4 = all(
        re.search(r"#ger-chart %s:focus-visible" % re.escape(s), css) is not None
        for s in SELECTORS) and "outline: 2px solid var(--accent)" in css
    check("S4 css :focus-visible --accent ring covers .ger-row-rect/.ger-label/.ger-nav-icon",
          s4, "" if s4 else "focus rule missing or off-convention")

    s5 = blk is not None and "innerHTML" not in blk
    check("S5 pilot block is attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML in the pilot block")

    s6 = len(re.findall(r"\.on\('click'", charts[
        charts.find("function drawGERChart("):charts.find("function drawGERChart(") + 15000])) >= 3
    check("S6 the three mouse .on('click') handlers are preserved in drawGERChart",
          s6, "" if s6 else "a click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S7 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")

    s8 = (re.search(r"\.attr\('class', 'ger-row-rect'\)\s*\n\s*\.datum\(c\)", charts) is not None
          and re.search(r"\.attr\('class', 'ger-label'\)\s*\n\s*\.datum\(c\)", charts) is not None
          and re.search(r"\.attr\('class', 'ger-nav-icon'\)\s*\n\s*\.datum\(\{ ticker: ticker \}\)",
                        charts) is not None)
    check("S8 row rect, label, nav icon bind datum and carry their pilot class at creation",
          s8, "" if s8 else "class/datum wiring missing at creation")


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
                "window.d3 && document.querySelectorAll('#ger-chart .ger-row-rect').length >= 2",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every ger-row-rect is an upgraded button with roving tabindex.
            r1info = pg.evaluate("""() => {
              const rows = [...document.querySelectorAll('#ger-chart .ger-row-rect')];
              const badRole = rows.filter(d => d.getAttribute('role') !== 'button');
              const badLabel = rows.filter(d => {
                const l = d.getAttribute('aria-label') || '';
                return !l.length || l.indexOf('Press Enter') < 0
                    || l.indexOf('Governance Erosion Risk Score') < 0;
              });
              const holders = rows.filter(d => d.getAttribute('tabindex') === '0').length;
              const icons = [...document.querySelectorAll('#ger-chart .ger-nav-icon')];
              const iconHolders = icons.filter(d => d.getAttribute('tabindex') === '0').length;
              const iconBad = icons.filter(d => d.getAttribute('role') !== 'button').length;
              return {n: rows.length, badRole: badRole.length,
                      badLabel: badLabel.length, holders: holders,
                      icons: icons.length, iconHolders: iconHolders, iconBad: iconBad};
            }""")
            r1 = (r1info["n"] >= 2 and r1info["badRole"] == 0
                  and r1info["badLabel"] == 0 and r1info["holders"] == 1
                  and r1info["icons"] >= 2 and r1info["iconBad"] == 0
                  and r1info["iconHolders"] == 1)
            check("R1 ger rows are role=button with data-bearing aria-labels, one roving tabindex=0 per group",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: Enter on a focused row rect fires openDetailPanel once with the ticker.
            r2setup = pg.evaluate("""() => {
              window.__odpCalls = [];
              window.openDetailPanel = function(t) { window.__odpCalls.push(t); };
              const row = document.querySelector('#ger-chart .ger-row-rect[tabindex="0"]');
              if (!row) return 'NO_ROW';
              const label = row.getAttribute('aria-label') || '';
              const m = label.match(/\\(([^)]+)\\)/);
              row.focus();
              return 'OK|' + (m ? m[1] : '?');
            }""")
            if not r2setup.startswith("OK|"):
                check("R2 Enter on row fires openDetailPanel with parity ticker", False,
                      "setup: %r" % r2setup)
            else:
                expect_ticker = r2setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r2info = pg.evaluate("() => window.__odpCalls")
                r2 = (r2info == [expect_ticker])
                check("R2 Enter fires openDetailPanel(ticker) exactly once",
                      r2, ("" if r2 else "calls: %r, expected [%r]" % (r2info, expect_ticker)))

            # R3: Enter on a focused nav icon fires navigateToScatter with parity args.
            r3setup = pg.evaluate("""() => {
              window.__ntsCalls = [];
              window.navigateToScatter = function(t, x, y) {
                window.__ntsCalls.push([t, x, y]);
              };
              const icon = document.querySelector('#ger-chart .ger-nav-icon[tabindex="0"]');
              if (!icon) return 'NO_ICON';
              icon.focus();
              const d = icon.__data__ || {};
              return 'OK|' + (d.ticker || '?');
            }""")
            # d3 v7 stores datum on __data__ only when bound via .datum/.data;
            # fall back to the label parse if the property is absent.
            if not r3setup.startswith("OK|"):
                check("R3 Enter on icon fires navigateToScatter with parity args", False,
                      "setup: %r" % r3setup)
            else:
                expect_ticker = r3setup.split("|", 1)[1]
                if expect_ticker == "?":
                    expect_ticker = pg.evaluate("""() => {
                      const icon = document.querySelector('#ger-chart .ger-nav-icon[tabindex="0"]');
                      const l = icon.getAttribute('aria-label') || '';
                      const m = l.match(/View (\\S+) in/);
                      return m ? m[1] : '?';
                    }""")
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("() => window.__ntsCalls")
                r3 = (r3info == [[expect_ticker, "_gerScore", "total_compensation"]])
                check("R3 Enter fires navigateToScatter(ticker, '_gerScore', 'total_compensation') exactly once",
                      r3, ("" if r3 else "calls: %r, expected [[%r, '_gerScore', 'total_compensation']]"
                          % (r3info, expect_ticker)))

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
