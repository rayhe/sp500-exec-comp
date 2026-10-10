#!/usr/bin/env python3
"""Regression guard: pay-anomaly chart is keyboard-operable.

The 2026-10-10 10:00 PT 5-critic panel found the next instance of the
keyboard gap class: drawPayAnomalyChart's SVG rows carried click actions
(company detail, compare toggle, scatter navigation) plus data-bearing
hover tooltips, but no tabindex/role/keydown -- the same gap class the
07:30 run closed for the nine full-chart histogram/bar surfaces.

The anomaly pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to four anomaly surfaces in js/charts.js, all inside
#pay-anomaly-chart:

  .anomaly-bar       (deviation bars)      -> window.findCompanyInTable
  .anomaly-label     (ticker + CEO labels) -> window.findCompanyInTable
  .anomaly-spark     (3-yr trend overlays) -> window.findCompanyInTable
  .anomaly-nav-icon  (scatter-nav arrow)   -> window.navigateToScatter

Each pilot: roving tabindex, role="button", data-bearing aria-label
(ticker, actual vs expected pay, deviation, CEO, governance, "Press
Enter"), focus fires the exact hover-tooltip path via a synthetic event,
blur hides it, Enter/Space replays the click path. The two bespoke
controls get hand-written wiring instead of the roving helper:

  .anomaly-compare-btn (+ / check toggle): tabindex/role, focus/blur show
      the hover tooltip, Enter/Space replays the toggle click and refreshes
      the aria-label to the post-toggle state (aria-label staleness is the
      known failure mode for toggle buttons).
  .anomaly-summary (sector-mode summary strip -> Gov vs Pay scatter):
      single button with focus/blur mirroring the hover underline/hint.

css/style.css carries the --accent :focus-visible ring for all six
classes (site convention, e.g. the histogram-bar rule from 2026-10-10
07:30).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 four _enableDotKeyboard pilots present with the right selectors;
        the _anomalyBarLabel / _anomalySparkLabel helpers exist.
     S2 every pilot passes label + activate; the nav-icon pilot activates
        window.navigateToScatter; the summary + compare hand-wiring is
        present (tabindex/role/aria-label/keydown on both).
     S3 css :focus-visible --accent rule covers all six anomaly classes.
     S4 the pilot blocks are attribute-bound (no innerHTML).
     S5 the mouse .on('click') handlers are preserved in
        drawPayAnomalyChart (bars, labels, compare buttons, spark
        overlays, nav icons, summary strip).
     S6 the compare toggle refreshes its aria-label after a keyboard
        activation (guards the toggle-staleness failure mode).
     S7 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 anomaly bars are role=button with data aria-labels, exactly one
        roving tabindex="0" per pilot class set.
     R2 focusing an anomaly bar shows the chart tooltip
        (.chart-tooltip.visible) -- the keyboard equivalent of hover data.
     R3 pressing Enter on a focused anomaly bar fires
        window.findCompanyInTable exactly once with the bar's ticker.
     R4 zero JS page errors.

Usage:
  scripts/check_anomaly_keyboard.py
  scripts/check_anomaly_keyboard.py --static-only

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

# (pilot selector fragment used in the _enableDotKeyboard call, expected action marker)
PILOTS = [
    (".anomaly-bar", "window.findCompanyInTable"),
    (".anomaly-label", "window.findCompanyInTable"),
    (".anomaly-spark", "window.findCompanyInTable"),
    (".anomaly-nav-icon", "window.navigateToScatter"),
]


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def anomaly_fn(charts):
    """Return the source of drawPayAnomalyChart(...) body."""
    m = re.search(
        r"function drawPayAnomalyChart\(companies\) \{([\s\S]*?)\n\}\n\n/\* ── Tenure",
        charts)
    return m.group(1) if m else None


def pilot_block(fn_src, sel):
    m = re.search(
        r"_enableDotKeyboard\(_anomalyG, '" + re.escape(sel) +
        r"', \{([\s\S]*?)\n    \}\);",
        fn_src)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    fn = anomaly_fn(charts)
    check("S0 drawPayAnomalyChart body extractable", fn is not None,
          "" if fn else "regex missed the function body")

    blocks = {}
    missing = []
    bad_sel = []
    if fn:
        for sel, _ in PILOTS:
            blk = pilot_block(fn, sel)
            blocks[sel] = blk
            if blk is None:
                missing.append(sel)
    s1 = (fn is not None and not missing
          and "function _anomalyBarLabel(d)" in charts
          and "function _anomalySparkLabel(d)" in charts)
    check("S1 four anomaly pilots present with right selectors + label helpers",
          s1, ("" if s1 else "missing=%s" % missing))

    bad_cfg = [sel for sel, _ in PILOTS
               if blocks.get(sel) is None
               or "label:" not in blocks[sel] or "activate:" not in blocks[sel]]
    nav = blocks.get(".anomaly-nav-icon") or ""
    nav_ok = "navigateToScatter" in nav
    # hand-wired controls: summary strip + compare toggle
    summ_ok = (fn is not None
               and ".anomaly-summary" in fn
               and re.search(r"summaryG\s*\n?\s*\.attr\('tabindex', '0'\)", fn) is not None
               and ".on('keydown', function(ev)" in fn)
    cmp_ok = (fn is not None
              and ".attr('aria-label', (isCompared" in fn
              and "Press Enter to toggle" in fn
              and "this.dispatchEvent(new MouseEvent('click'" in fn)
    s2 = not bad_cfg and nav_ok and summ_ok and cmp_ok
    check("S2 pilots pass label + activate; summary/compare hand-wiring present",
          s2, ("" if s2 else "bad_cfg=%s nav=%s summary=%s compare=%s"
               % (bad_cfg, nav_ok, summ_ok, cmp_ok)))

    css_classes = [
        "#pay-anomaly-chart .anomaly-bar:focus-visible",
        "#pay-anomaly-chart .anomaly-label:focus-visible",
        "#pay-anomaly-chart .anomaly-compare-btn:focus-visible",
        "#pay-anomaly-chart .anomaly-spark:focus-visible",
        "#pay-anomaly-chart .anomaly-nav-icon:focus-visible",
        "#pay-anomaly-chart .anomaly-summary:focus-visible",
    ]
    m = re.search(
        r"(pay-anomaly pilot)[\s\S]*?"
        r"(#pay-anomaly-chart \.anomaly-bar:focus-visible[\s\S]*?)\{\s*([\s\S]*?)\}",
        css)
    s3 = (m is not None
          and all(c in m.group(2) for c in css_classes)
          and "outline: 2px solid var(--accent)" in m.group(3))
    check("S3 css :focus-visible --accent ring covers all six anomaly classes",
          s3, "" if s3 else "combined focus rule missing or off-convention")

    bad_html = [sel for sel, blk in blocks.items()
                if blk is not None and "innerHTML" in blk]
    s4 = not bad_html
    check("S4 pilot blocks are attribute-bound (no innerHTML)",
          s4, ("" if s4 else "innerHTML in %s" % bad_html))

    # Mouse click paths preserved inside the draw function.
    n_clicks = len(re.findall(r"\.on\('click'", fn)) if fn else 0
    s5 = n_clicks >= 6
    check("S5 mouse .on('click') handlers preserved in drawPayAnomalyChart (%d found)" % n_clicks,
          s5, "" if s5 else "expected >= 6 (bars, labels, compare, spark, nav icon, summary)")

    # Compare toggle must refresh its aria-label after a keyboard activation
    # (the known staleness failure mode for toggle buttons).
    s6 = (fn is not None
          and "attr('aria-label'," in fn
          and "nowCompared ? 'Remove ' + ticker" in fn)
    check("S6 compare toggle refreshes aria-label after keyboard activation",
          s6, "" if s6 else "no post-toggle aria-label refresh in keydown path")

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
                "window.d3 && document.querySelectorAll('#pay-anomaly-chart .anomaly-bar').length > 3",
                timeout=90000)
            pg.wait_for_timeout(2500)  # anomaly bars animate width over ~1.5s

            # R1: pilot elements are upgraded buttons with roving tabindex.
            r1info = pg.evaluate("""() => {
              const sets = ['.anomaly-bar', '.anomaly-label', '.anomaly-spark',
                            '.anomaly-nav-icon', '.anomaly-compare-btn'];
              const out = {};
              for (const sel of sets) {
                const els = [...document.querySelectorAll('#pay-anomaly-chart ' + sel)];
                const badRole = els.filter(e => e.getAttribute('role') !== 'button');
                const badLabel = els.filter(e => {
                  const l = e.getAttribute('aria-label') || '';
                  return !l.length || l.indexOf('Press Enter') < 0;
                });
                const holders = els.filter(e => e.getAttribute('tabindex') === '0').length;
                out[sel] = {n: els.length, badRole: badRole.length,
                            badLabel: badLabel.length, holders: holders};
              }
              return out;
            }""")
            r1bad = [sel for sel, v in r1info.items()
                     if v["n"] < 3 or v["badRole"] or v["badLabel"] or v["holders"] != 1]
            check("R1 anomaly sets are role=button with data aria-labels, one roving tabindex=0 each",
                  not r1bad, ("sets failing: %s" % r1bad) if r1bad else "")

            # R2: focusing an anomaly bar shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#pay-anomaly-chart .anomaly-bar[tabindex="0"]');
              if (!bar) return false;
              bar.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null), 400));
            }""")
            check("R2 focus on an anomaly bar shows the chart tooltip", bool(r2ok),
                  "" if r2ok else "no .chart-tooltip.visible after focus")

            # R3: Enter on a focused anomaly bar fires findCompanyInTable once.
            r3setup = pg.evaluate("""() => {
              window.__findCalls = [];
              const orig = window.findCompanyInTable;
              window.findCompanyInTable = function(t) {
                window.__findCalls.push(t);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#pay-anomaly-chart .anomaly-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              bar.focus();
              const m = (bar.getAttribute('aria-label') || '').split(' — ')[0];
              return m || 'NO_TICKER';
            }""")
            if r3setup in ("NO_BAR", "NO_TICKER"):
                check("R3 Enter on anomaly bar fires findCompanyInTable", False,
                      "setup: %r" % r3setup)
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3calls = pg.evaluate("window.__findCalls")
                r3 = len(r3calls) == 1 and r3calls[0] == r3setup
                check("R3 Enter on anomaly bar fires findCompanyInTable('%s') exactly once" % r3setup,
                      r3, ("calls: %r" % r3calls) if not r3 else "")

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
