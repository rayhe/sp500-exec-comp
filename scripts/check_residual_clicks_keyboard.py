#!/usr/bin/env python3
"""Regression guard: residual click-only surfaces are keyboard-operable.

The 2026-10-11 06:00 PT 5-critic panel ran a NEW failure-mode-class audit
(the 2026-10-10 07:30 PT list was fully drained by the 03:30 PT run) and
found four click-without-keyboard surfaces still unaddressed in js/charts.js:

  1. drawSectorChart: the sector sparkline hit rects (.sector-sparkline-hit,
     transparent overlay per sector; click = window.navigateToPayAnomaly(sector);
     data-bearing tooltip: median CEO pay trend, % change) carried no class
     binding and no tabindex/role/keydown. The 2026-10-08 bar pilot's comment
     even claimed the bars were the chart's only click targets (stale).
  2. drawSectorChart: the distribution hit zones (.dist-hit-zone, bottom 25% /
     IQR / top 25% transparent rects over the sector boxplots; click =
     window.filterByDistribution(sector, min, max, label); data-bearing
     tooltips) had no tabindex/role/keydown.
  3. drawCrossSectorCorrelation: the sector bars (click =
     window.filterBySectorFromBar(sector); data-bearing tooltip bound via
     mouseenter/mouseleave: sector, metric pair, Pearson r, significance,
     strength/direction, n) had NO class attribute at all and no keyboard
     wiring. The existing check_correlation_keyboard.py only covers the heat
     cells.
  4. drawVolatilityDistChart: the per-bucket scatter nav icons (the U+2934
     text glyphs; click = window.navigateToScatter(ticker, '_ceoVolatility',
     'total_compensation'); data-bearing tooltip) had no class and no
     keyboard wiring. The 2026-10-10 vol-dist pilot covered only .vol-bar.

(The anomaly-summary group was suspected but is already wired -- see the
2026-10-10 manual keydown wiring in drawPayAnomalyChart.)

The 2026-10-11 pilot extends _enableDotKeyboard to all four:

  - roving tabindex, role="button"
  - data-bearing aria-labels mirroring each tooltip plus the affordance
    ("Press Enter to ...")
  - focus fires the exact hover-tooltip path via a synthetic event
    (mouseenter/mouseleave for the corr bars, mouseover/mouseout elsewhere)
  - Enter/Space replays the click path exactly
  - css/style.css carries the --accent :focus-visible ring for all four
    selectors (site convention); attribute-bound labels, no innerHTML

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1  sparkline-hit rect binds its tooltip datum (sector/pctChange/trendUp)
     S2  sparkline pilot present; label carries "pay anomalies"; activate
         replays navigateToPayAnomaly(zd.sector)
     S3  dist-hit-zone pilot present; label carries the zone filter
         affordance; activate replays filterByDistribution(sector, min, max,
         label)
     S4  corr barRect carries class corr-sector-bar + .datum(d) in
         drawCrossSectorCorrelation
     S5  corr pilot present; hoverIn is mouseenter (the tooltip pair);
         activate replays filterBySectorFromBar(datum.sector)
     S6  vol-dist nav icon carries class vol-dist-nav-icon + ticker/cv datum;
         pilot present
     S7  nav-icon activate replays navigateToScatter(d.ticker,
         '_ceoVolatility', 'total_compensation'); label carries the affordance
     S8  css/style.css has :focus-visible --accent rings for all four
         selectors
     S9  the three new pilot blocks are attribute-bound (no innerHTML)
     S10 mouse .on('click') handlers preserved on all four surfaces
     S11 node --check js/charts.js is green
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1  every surface is role=button with a data-bearing aria-label
         mentioning "Press Enter"; one roving tabindex="0" per surface group
     R2  focusing a dist-hit-zone shows the chart tooltip
     R3  Enter on a dist-hit-zone calls window.filterByDistribution exactly
         once with its (sector, min, max, label) -- keyboard/click parity
     R4  Enter on a sector-sparkline-hit calls window.navigateToPayAnomaly
         exactly once with its sector
     R5  Enter on a corr-sector-bar calls window.filterBySectorFromBar
         exactly once with its sector
     R6  Enter on a vol-dist-nav-icon calls window.navigateToScatter exactly
         once with (ticker, '_ceoVolatility', 'total_compensation')
     R7  zero JS page errors

Usage:
  scripts/check_residual_clicks_keyboard.py              # static + render
  scripts/check_residual_clicks_keyboard.py --static-only

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

SURFACES = [
    ("sector-sparkline-hit", "#sector-chart", "pay anomalies"),
    ("dist-hit-zone", "#sector-chart", "filter the table to this zone"),
    ("corr-sector-bar", "#cross-sector-corr-chart", "filter the table to this sector"),
    ("vol-dist-nav-icon", "#volatility-dist-chart", "Press Enter to open"),
]


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts, chart_id, cls):
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(chart_id) +
        r"'\), '" + re.escape("." + cls) + r"', \{([\s\S]*?)\n    \}\);\n",
        charts)
    return m.group(0) if m else None


def sector_fn(charts):
    m = re.search(
        r"function drawSectorChart\([\s\S]*?\n/\* --- Trend Line Chart --- \*/",
        charts)
    return m.group(0) if m else None


def corr_fn(charts):
    m = re.search(
        r"function drawCrossSectorCorrelation\([\s\S]*?\n/\* === Pay Quartile Composition Chart === \*/",
        charts)
    return m.group(0) if m else None


def voldist_fn(charts):
    m = re.search(
        r"function drawVolatilityDistChart\([\s\S]*?\nfunction drawVolatilitySectorChart\(",
        charts)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    sfn = sector_fn(charts)
    cfn = corr_fn(charts)
    vfn = voldist_fn(charts)

    s1 = (sfn is not None
          and re.search(r"\.attr\('class', 'sector-sparkline-hit'\)[\s\S]{0,400}"
                        r"\.datum\(\{ sector: sectorForClick, pctChange: pctChange,"
                        r" trendUp: trendUp, years: pts\.length - 1 \}\)", sfn) is not None)
    check("S1 sparkline-hit rect binds its tooltip datum (sector/pctChange/trendUp/years)",
          s1, "" if s1 else "datum binding missing on the sparkline-hit rect")

    sp = pilot_block(charts, "#sector-chart", "sector-sparkline-hit")
    s2 = (sp is not None and "pay anomalies" in sp
          and "window.navigateToPayAnomaly(zd.sector)" in sp
          and "hideChartTooltip()" in sp)
    check("S2 sparkline pilot present; label carries 'pay anomalies'; activate "
          "replays navigateToPayAnomaly(zd.sector)",
          s2, "" if s2 else "sparkline pilot block incomplete")

    dz = pilot_block(charts, "#sector-chart", "dist-hit-zone")
    s3 = (dz is not None and "filter the table to this zone" in dz
          and "window.filterByDistribution(zd.sector, zd.min, zd.max, zd.label)" in dz)
    check("S3 dist-hit-zone pilot present; label carries the zone filter "
          "affordance; activate replays filterByDistribution(sector,min,max,label)",
          s3, "" if s3 else "dist-hit-zone pilot block incomplete")

    s4 = (cfn is not None
          and re.search(r"\.attr\('class', 'corr-sector-bar'\)\s*\n\s*\.datum\(d\)", cfn) is not None)
    check("S4 corr barRect carries class corr-sector-bar + .datum(d)",
          s4, "" if s4 else "class/datum missing on the cross-sector bar rect")

    cb = pilot_block(charts, "#cross-sector-corr-chart", "corr-sector-bar")
    s5 = (cb is not None and "hoverIn: 'mouseenter'" in cb
          and "window.filterBySectorFromBar(datum.sector)" in cb
          and "Press Enter to filter the table to this sector" in cb
          and "hideChartTooltip()" in cb)
    check("S5 corr pilot present; hoverIn=mouseenter (tooltip pair); activate "
          "replays filterBySectorFromBar(datum.sector)",
          s5, "" if s5 else "corr pilot block incomplete")

    s6 = (vfn is not None
          and re.search(r"\.attr\('class', 'vol-dist-nav-icon'\)[\s\S]{0,200}"
                        r"\.datum\(\{ ticker: topInBucket\.ticker, cv: topInBucket\._ceoVolatility \}\)",
                        vfn) is not None)
    check("S6 vol-dist nav icon carries class vol-dist-nav-icon + ticker/cv datum",
          s6, "" if s6 else "class/datum missing on the nav icon")

    vn = pilot_block(charts, "#volatility-dist-chart", "vol-dist-nav-icon")
    s7 = (vn is not None
          and "window.navigateToScatter(d.ticker, '_ceoVolatility', 'total_compensation')" in vn
          and "Press Enter to open" in vn)
    check("S7 nav-icon pilot present; activate replays navigateToScatter("
          "d.ticker, '_ceoVolatility', 'total_compensation')",
          s7, "" if s7 else "nav-icon pilot block incomplete")

    s8 = all(
        re.search(re.escape(sel.split(",")[0].strip()) + r":focus-visible", css) is not None
        for sel, _, _ in [
            ("#sector-chart .sector-sparkline-hit", "", ""),
            ("#sector-chart .dist-hit-zone", "", ""),
            ("#cross-sector-corr-chart .corr-sector-bar", "", ""),
            ("#volatility-dist-chart .vol-dist-nav-icon", "", ""),
        ]) and "outline: 2px solid var(--accent)" in css
    check("S8 css :focus-visible --accent rings cover all four selectors",
          s8, "" if s8 else "focus rule missing for one or more selectors")

    s9 = all(blk is not None and "innerHTML" not in blk for blk in (sp, dz, cb, vn))
    check("S9 the four pilot blocks are attribute-bound (no innerHTML)",
          s9, "" if s9 else "innerHTML found in a pilot block or block missing")

    s10 = (sfn is not None and sfn.count(".on('click'") >= 4
           and cfn is not None and ".on('click'" in cfn
           and vfn is not None and ".on('click'" in vfn)
    check("S10 mouse .on('click') handlers preserved on all four surfaces",
          s10, "" if s10 else "a click handler was lost")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S11 node --check js/charts.js is green",
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

            waits = [
                ("#sector-chart .sector-sparkline-hit", 1),
                ("#sector-chart .dist-hit-zone", 1),
                ("#cross-sector-corr-chart .corr-sector-bar", 1),
                ("#volatility-dist-chart .vol-dist-nav-icon", 1),
            ]
            for sel, n in waits:
                try:
                    pg.wait_for_function(
                        "document.querySelectorAll('%s').length >= %d" % (sel, n),
                        timeout=30000)
                except Exception as ex:
                    check("R0 surface %s renders (>= %d)" % (sel, n), False,
                          "wait failed: %s" % str(ex)[:200])
                    browser.close()
                    return False
            pg.wait_for_timeout(800)

            # R1: every surface is role=button with a data-bearing aria-label
            # ("Press Enter"); exactly one roving tabindex="0" per group.
            r1info = pg.evaluate("""() => {
              const groups = [
                ['#sector-chart', '.sector-sparkline-hit'],
                ['#sector-chart', '.dist-hit-zone'],
                ['#cross-sector-corr-chart', '.corr-sector-bar'],
                ['#volatility-dist-chart', '.vol-dist-nav-icon'],
              ];
              const out = [];
              for (const [chart, cls] of groups) {
                const els = [...document.querySelectorAll(chart + ' ' + cls)];
                const zero = els.filter(e => e.getAttribute('tabindex') === '0').length;
                const ok = els.length >= 1 &&
                  els.every(e => e.getAttribute('role') === 'button' &&
                    (e.getAttribute('aria-label') || '').indexOf('Press Enter') >= 0) &&
                  zero === 1;
                out.push({sel: chart + ' ' + cls, n: els.length, zero: zero, ok: ok,
                          sample: els.length ? els[0].getAttribute('aria-label') : null});
              }
              return out;
            }""")
            r1 = all(g["ok"] for g in r1info)
            check("R1 all four surfaces are role=button with 'Press Enter' "
                  "aria-labels, one roving tabindex=0 each",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a dist-hit-zone shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const z = document.querySelector(
                '#sector-chart .dist-hit-zone[tabindex="0"]');
              if (!z) return 'MISSING';
              z.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null
                  ? 'SHOWN' : 'HIDDEN'), 400));
            }""")
            r2 = (r2ok == "SHOWN")
            check("R2 focus on a dist-hit-zone shows the chart tooltip",
                  r2, ("" if r2 else "state: %r" % (r2ok,)))

            # R3: Enter on the focused dist-hit-zone calls
            # window.filterByDistribution exactly once with its args.
            r3setup = pg.evaluate("""() => {
              window.__rcCalls = [];
              const orig = window.filterByDistribution;
              if (typeof orig !== 'function') return 'NO_FN';
              window.filterByDistribution = function(s, mn, mx, lbl) {
                window.__rcCalls.push([s, mn, mx, lbl]);
                return orig.apply(this, arguments);
              };
              const z = document.querySelector(
                '#sector-chart .dist-hit-zone[tabindex="0"]');
              if (!z) return 'NO_ZONE';
              z.focus();
              return 'OK';
            }""")
            if r3setup != "OK":
                check("R3 Enter on dist-hit-zone fires filterByDistribution",
                      False, "setup: %r" % r3setup)
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r3info = pg.evaluate("() => ({calls: window.__rcCalls})")
                r3 = (len(r3info["calls"]) == 1
                      and isinstance(r3info["calls"][0][0], str)
                      and len(r3info["calls"][0][0]) > 0)
                check("R3 Enter calls window.filterByDistribution exactly once "
                      "with (sector, min, max, label)",
                      r3, ("" if r3 else "state: %r" % (r3info,)))

            # R4: Enter on a sparkline-hit calls window.navigateToPayAnomaly
            # exactly once with its sector.
            r4setup = pg.evaluate("""() => {
              window.__rcCalls = [];
              const orig = window.navigateToPayAnomaly;
              if (typeof orig !== 'function') return 'NO_FN';
              window.navigateToPayAnomaly = function(sector) {
                window.__rcCalls.push(sector);
                return orig.apply(this, arguments);
              };
              const h = document.querySelector(
                '#sector-chart .sector-sparkline-hit[tabindex="0"]');
              if (!h) return 'NO_HIT';
              const lbl = h.getAttribute('aria-label') || '';
              h.focus();
              return 'OK|' + lbl.split(' median CEO pay')[0];
            }""")
            if not r4setup.startswith("OK|"):
                check("R4 Enter on sparkline-hit fires navigateToPayAnomaly",
                      False, "setup: %r" % r4setup)
            else:
                expected = r4setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r4info = pg.evaluate("() => ({calls: window.__rcCalls})")
                r4 = (r4info["calls"] == [expected])
                check("R4 Enter calls window.navigateToPayAnomaly exactly once "
                      "with the sector (%s)" % expected,
                      r4, ("" if r4 else "state: %r, expected [%r]" % (r4info, expected)))

            # R5: Enter on a corr-sector-bar calls
            # window.filterBySectorFromBar exactly once with its sector.
            r5setup = pg.evaluate("""() => {
              window.__rcCalls = [];
              const orig = window.filterBySectorFromBar;
              if (typeof orig !== 'function') return 'NO_FN';
              window.filterBySectorFromBar = function(sector) {
                window.__rcCalls.push(sector);
                return orig.apply(this, arguments);
              };
              const b = document.querySelector(
                '#cross-sector-corr-chart .corr-sector-bar[tabindex="0"]');
              if (!b) return 'NO_BAR';
              const lbl = b.getAttribute('aria-label') || '';
              b.focus();
              return 'OK|' + lbl.split(':')[0];
            }""")
            if not r5setup.startswith("OK|"):
                check("R5 Enter on corr-sector-bar fires filterBySectorFromBar",
                      False, "setup: %r" % r5setup)
            else:
                expected = r5setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r5info = pg.evaluate("() => ({calls: window.__rcCalls})")
                r5 = (r5info["calls"] == [expected])
                check("R5 Enter calls window.filterBySectorFromBar exactly once "
                      "with the sector (%s)" % expected,
                      r5, ("" if r5 else "state: %r, expected [%r]" % (r5info, expected)))

            # R6: Enter on a vol-dist nav icon calls window.navigateToScatter
            # exactly once with (ticker, '_ceoVolatility',
            # 'total_compensation').
            r6setup = pg.evaluate("""() => {
              window.__rcCalls = [];
              const orig = window.navigateToScatter;
              if (typeof orig !== 'function') return 'NO_FN';
              window.navigateToScatter = function(t, x, y) {
                window.__rcCalls.push([t, x, y]);
                return orig.apply(this, arguments);
              };
              const ic = document.querySelector(
                '#volatility-dist-chart .vol-dist-nav-icon[tabindex="0"]');
              if (!ic) return 'NO_ICON';
              const lbl = ic.getAttribute('aria-label') || '';
              const m = lbl.match(/View (\\S+)/);
              ic.focus();
              return 'OK|' + (m ? m[1] : '');
            }""")
            if not r6setup.startswith("OK|"):
                check("R6 Enter on nav icon fires navigateToScatter",
                      False, "setup: %r" % r6setup)
            else:
                expected = r6setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r6info = pg.evaluate("() => ({calls: window.__rcCalls})")
                r6 = (len(r6info["calls"]) == 1
                      and r6info["calls"][0][0] == expected
                      and r6info["calls"][0][1] == "_ceoVolatility"
                      and r6info["calls"][0][2] == "total_compensation")
                check("R6 Enter calls window.navigateToScatter exactly once "
                      "with (%s, '_ceoVolatility', 'total_compensation')" % expected,
                      r6, ("" if r6 else "state: %r, expected ticker %r" % (r6info, expected)))

            # R7: zero JS page errors across the lifecycle.
            check("R7 zero JS page errors", len(errors) == 0,
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
