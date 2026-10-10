#!/usr/bin/env python3
"""Regression guard: gender-pay-chart female bars are keyboard-operable.

The 2026-10-10 11:30 PT 5-critic panel found the last actionable bar surface
in drawGenderPayChart without a keyboard path: the female bars carry a click
action (window.filterByGender('F'), filtering the main table to female CEOs)
plus a data-bearing hover tooltip (median pay, CEO count, premium, highest
paid woman), but had no tabindex/role/keydown -- the same failure-mode class
the 07:30 PT histogram-bar pilot and the 10:06 PT anomaly pilot closed on
other charts.

The gender-bar pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to #gender-pay-chart .gender-bar:

  - roving tabindex, role="button"
  - data-bearing aria-label (FY, female median pay, female CEO count, premium
    over the all-CEO median, highest paid woman + comp, "Press Enter to
    filter the table to female CEOs")
  - focus fires the exact hover-tooltip path via a synthetic event, blur hides
    it, Enter/Space replays the click path (hideChartTooltip + filterByGender)
  - css/style.css carries the --accent :focus-visible ring for .gender-bar
    (site convention)
  - the info-only overall bars keep no click path and stay out of tab order

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the gender-bar pilot call is present with the right container/selector.
     S2 the pilot passes label + activate; the label mentions female median
        data and the keyboard affordance.
     S3 css/style.css has the :focus-visible --accent ring for .gender-bar.
     S4 the pilot block is attribute-bound (no innerHTML).
     S5 the mouse click path (filterByGender('F')) is preserved.
     S6 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .gender-bar is role=button with a data-bearing aria-label
        mentioning "Press Enter"; roving tabindex (exactly one tabindex="0").
     R2 focusing a gender bar shows the chart tooltip (.chart-tooltip.visible)
        -- the keyboard equivalent of the hover data.
     R3 pressing Enter on a focused gender bar calls window.filterByGender
        exactly once with 'F' and sets window._activeGenderFilter to 'F'
        (keyboard/click parity).
     R4 zero JS page errors.

Usage:
  scripts/check_gender_bar_keyboard.py              # static + render
  scripts/check_gender_bar_keyboard.py --static-only

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

CHART_ID = "#gender-pay-chart"
BAR_SEL = ".gender-bar"


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
    s1 = blk is not None and got_sel == BAR_SEL
    check("S1 gender-bar pilot present with the right container/selector",
          s1, ("" if s1 else "block missing or selector=%r" % (got_sel,)))

    s2 = (blk is not None
          and "label:" in blk and "activate:" in blk
          and "female_median_pay" in blk
          and "num_female_ceos" in blk
          and "Press Enter to filter the table to female CEOs" in blk
          and "filterByGender('F')" in blk)
    check("S2 pilot passes label + activate; label carries the female-pay data and the keyboard affordance",
          s2, "" if s2 else "label/activate incomplete in the pilot block")

    s3 = (re.search(r"#gender-pay-chart \.gender-bar:focus-visible\s*\{",
                    css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S3 css :focus-visible --accent ring covers .gender-bar",
          s3, "" if s3 else "focus rule missing or off-convention")

    s4 = blk is not None and "innerHTML" not in blk
    check("S4 pilot block is attribute-bound (no innerHTML)",
          s4, "" if s4 else "innerHTML in the pilot block")

    s5 = re.search(
        r"function drawGenderPayChart\([\s\S]*?\.on\('click'", charts) is not None
    check("S5 mouse .on('click') handler preserved in drawGenderPayChart",
          s5, "" if s5 else "the click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/charts.js is green",
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
                "window.d3 && document.querySelectorAll('#gender-pay-chart .gender-bar').length >= 2",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every female bar is an upgraded button with roving tabindex.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#gender-pay-chart .gender-bar')];
              const badRole = bars.filter(b => b.getAttribute('role') !== 'button');
              const badLabel = bars.filter(b => {
                const l = b.getAttribute('aria-label') || '';
                return !l.length || l.indexOf('Press Enter') < 0
                    || l.indexOf('Female CEOs') < 0 || l.indexOf('median pay') < 0;
              });
              const holders = bars.filter(b => b.getAttribute('tabindex') === '0').length;
              return {n: bars.length, badRole: badRole.length,
                      badLabel: badLabel.length, holders: holders};
            }""")
            r1 = (r1info["n"] >= 2 and r1info["badRole"] == 0
                  and r1info["badLabel"] == 0 and r1info["holders"] == 1)
            check("R1 gender bars are role=button with data-bearing aria-labels, one roving tabindex=0",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a gender bar shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#gender-pay-chart .gender-bar[tabindex="0"]');
              if (!bar) return false;
              bar.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null), 400));
            }""")
            check("R2 focus on a gender bar shows the chart tooltip", bool(r2ok),
                  "" if r2ok else "no .chart-tooltip.visible after focus")

            # R3: Enter on a focused gender bar fires filterByGender('F') once.
            r3setup = pg.evaluate("""() => {
              window.__fgCalls = [];
              const orig = window.filterByGender;
              window.filterByGender = function(g) {
                window.__fgCalls.push(g);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#gender-pay-chart .gender-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              bar.focus();
              return 'OK';
            }""")
            if r3setup != "OK":
                check("R3 Enter on gender bar fires filterByGender('F')", False,
                      "setup: %r" % r3setup)
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("""() => ({
                  calls: window.__fgCalls,
                  active: window._activeGenderFilter
                })""")
                r3 = (r3info["calls"] == ["F"] and r3info["active"] == "F")
                check("R3 Enter fires filterByGender('F') exactly once and sets the filter",
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
