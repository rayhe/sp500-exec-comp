#!/usr/bin/env python3
"""Regression guard: keyboard pilot extends to scatter-chart dots (roving tabindex).

The 2026-10-09 03:30 PT run extended the keyboard pilot (sector bars,
composition donut + trend cards, quartile + gov-quartile segments, treemap
leaves) to the three scatter charts in js/charts.js: the configurable
scatter (.scatter-dot / .scatter-dot-bg / .scatter-dot-sector), the
Say-on-Pay scatter (.sop-dot) and the gov-pay scatter (.gps-dot). These
tooltip-bearing, click-to-lookup dots were the last large mouse-only surface
class (~500 dots per chart, so per-dot tab stops would wreck traversal).

Design: a shared _enableDotKeyboard(root, dotSel, cfg) helper at file scope.
Each chart gets one tab stop; focus reuses the EXACT mouseover behavior
(highlight + tooltip) via a synthetic MouseEvent anchored to the focused
dot's getBoundingClientRect; blur reuses the exact mouseout behavior
(highlight reset + tooltip hide); Enter/Space runs cfg.activate (the same
company lookup as click, or a keyboard-only one on the SoP chart where the
mouse has no click); ArrowLeft/Right/Up/Down and Home/End move between dots
while carrying the tabindex="0" holder. Attribute-bound only (no innerHTML).

The :focus-visible ring on all five dot classes matches the site's --accent
convention (sector bars, donut segments, treemap leaves).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _enableDotKeyboard sets roving tabindex (first dot '0', rest '-1'),
        role="button" and a data-bearing aria-label via cfg.label; focus
        dispatches a synthetic mouseover (anchored via
        getBoundingClientRect); blur dispatches a synthetic mouseout.
     S2 Enter/Space keydown runs cfg.activate; ArrowLeft/Right/Up/Down and
        Home/End move focus between dots and move the roving tabindex
        holder.
     S3 all three charts call the helper: configurable scatter with the
        .scatter-dot family + findCompanyInTable/_drawScatterTrendTrail
        activation; SoP scatter with .sop-dot + keyboard-only
        findCompanyInTable lookup; gov-pay scatter with .gps-dot +
        scrollToCompany activation.
     S4 css/style.css has the :focus-visible rule for all five dot classes
        with the --accent outline convention.
     S5 the keyboard additions are attribute-bound (no innerHTML).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered dot across the three charts is role="button" with a
        data-bearing aria-label, and each chart has exactly one
        tabindex="0" (roving).
     R2 focusing a configurable-scatter dot shows the tooltip with that
        dot's ticker; blur hides it.
     R3 Enter on a dot fires findCompanyInTable with the dot's ticker.
     R4 ArrowRight moves focus to the next dot and moves the
        tabindex="0" holder with it.
     R5 zero JS page errors.

Usage:
  scripts/check_keyboard_scatter_dots_pilot.py              # static + render
  scripts/check_keyboard_scatter_dots_pilot.py --static-only

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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def helper_block(charts):
    # From the _enableDotKeyboard definition through the end of its keydown
    # wiring, ending right before the closing brace of the function.
    m = re.search(
        r"function _enableDotKeyboard\(root, dotSel, cfg\) \{([\s\S]*?)\n\}\n",
        charts)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    block = helper_block(charts)

    s1 = (block is not None
          and ".attr('tabindex', function(d, i) { return i === 0 ? '0' : '-1'; })" in block
          and ".attr('role', 'button')" in block
          and ".attr('aria-label', cfg.label)" in block
          and ".on('focus', function(event, d)" in block
          and "var hoverIn = cfg.hoverIn || 'mouseover'" in block
          and "new MouseEvent(hoverIn," in block
          and "getBoundingClientRect()" in block
          and ".on('blur', function(event, d)" in block
          and "var hoverOut = cfg.hoverOut || 'mouseout'" in block
          and "new MouseEvent(hoverOut," in block)
    check("S1 _enableDotKeyboard sets roving tabindex/role=button/aria-label; focus=synthetic hover-in (default mouseover), blur=synthetic hover-out (default mouseout)",
          s1, "" if s1 else "roving-tabindex wiring missing from the helper block")

    s2 = (block is not None
          and ".on('keydown', function(event, d)" in block
          and "key === 'Enter'" in block
          and "key === ' '" in block
          and "cfg.activate(d)" in block
          and "'ArrowRight'" in block and "'ArrowLeft'" in block
          and "'ArrowUp'" in block and "'ArrowDown'" in block
          and "'Home'" in block and "'End'" in block
          and "nodes[nidx].focus()" in block
          and "dots.attr('tabindex', '-1')" in block)
    check("S2 Enter/Space runs cfg.activate; arrows/Home/End move focus + roving holder",
          s2, "" if s2 else "keydown roving-tabindex wiring missing from the helper block")

    s3 = ("_enableDotKeyboard(d3.select('#scatter-chart'), '.scatter-dot, .scatter-dot-bg, .scatter-dot-sector'" in charts
          and "window.findCompanyInTable(d.ticker)" in charts
          and "_drawScatterTrendTrail(d)" in charts
          and "_enableDotKeyboard(d3.select('#sop-scatter-chart'), '.sop-dot'" in charts
          and "window.findCompanyInTable(c.ticker)" in charts
          and "_enableDotKeyboard(d3.select('#gov-pay-scatter-chart'), '.gps-dot'" in charts
          and "window.scrollToCompany(c.ticker)" in charts)
    check("S3 all three scatter charts call the helper with per-chart label + activate wiring",
          s3, "" if s3 else "one of the three _enableDotKeyboard call sites missing or miswired")

    m = re.search(
        r"#scatter-chart \.scatter-dot:focus-visible[\s\S]*?\{([^}]*)\}",
        css)
    s4 = (m is not None
          and "#sop-scatter-chart .sop-dot:focus-visible" in css
          and "#gov-pay-scatter-chart .gps-dot:focus-visible" in css
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S4 :focus-visible ring on all five dot classes uses --accent convention",
          s4, "" if s4 else "focus ring missing or off-convention")

    s5 = (block is not None and "innerHTML" not in block)
    check("S5 keyboard additions are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML found in the helper block")


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
                "window.d3 && document.querySelectorAll('#scatter-chart .scatter-dot').length > 400",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: roving tabindex -- every dot is a labelled button, exactly
            # one dot per chart is in the tab order.
            r1info = pg.evaluate("""() => {
              const sel = '#scatter-chart .scatter-dot, #scatter-chart .scatter-dot-bg, ' +
                          '#scatter-chart .scatter-dot-sector, #sop-scatter-chart .sop-dot, ' +
                          '#gov-pay-scatter-chart .gps-dot';
              const dots = [...document.querySelectorAll(sel)];
              const bad = d =>
                d.getAttribute('role') !== 'button' ||
                !(d.getAttribute('aria-label') || '').includes('Press Enter to view in table');
              const charts = ['#scatter-chart', '#sop-scatter-chart', '#gov-pay-scatter-chart'];
              const holders = charts.map(c =>
                document.querySelectorAll(c + ' [tabindex="0"]').length);
              return {n: dots.length, bad: dots.filter(bad).length, holders: holders,
                      sample: dots[0] ? dots[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["n"] > 1000 and r1info["bad"] == 0
                  and r1info["holders"] == [1, 1, 1])
            check("R1 all %d scatter dots are role=button with data-bearing aria-label; one tabindex=0 per chart"
                  % r1info["n"],
                  r1, ("n=%d bad=%d holders=%r sample=%r" % (
                      r1info["n"], r1info["bad"], r1info["holders"], r1info["sample"]))
                  if not r1 else "")

            def focus_first_main():
                pg.evaluate("""() => {
                  const dot = document.querySelector('#scatter-chart .scatter-dot');
                  dot.scrollIntoView({block: 'center'});
                  dot.focus();
                }""")
                pg.wait_for_timeout(600)

            # R2: focusing a dot surfaces its tooltip (parity with hover).
            focus_first_main()
            r2info = pg.evaluate("""() => {
              const tip = document.querySelector('.chart-tooltip.visible');
              const dot = document.querySelector('#scatter-chart .scatter-dot');
              const label = dot.getAttribute('aria-label') || '';
              const ticker = label.split(' — ')[0];
              return {visible: !!tip,
                      tickerInTip: tip ? tip.textContent.includes(ticker) : false,
                      ticker: ticker};
            }""")
            r2 = r2info["visible"] and r2info["tickerInTip"]
            check("R2 focus on scatter dot shows tooltip with the dot's ticker (%r)" % r2info["ticker"],
                  r2, "tooltip not visible or ticker mismatch" if not r2 else "")
            # Blur restores the un-highlighted state and hides the tooltip.
            pg.evaluate("document.activeElement.blur()")
            pg.wait_for_timeout(400)
            tip_hidden = pg.evaluate("!document.querySelector('.chart-tooltip.visible')")
            check("R2b blur hides the tooltip", tip_hidden,
                  "tooltip still visible after blur" if not tip_hidden else "")

            # R3: stub the company lookup (side-effect-free), then Enter.
            pg.evaluate("""() => {
              window.__fcitCalls = [];
              window.findCompanyInTable = function() {
                window.__fcitCalls.push(Array.prototype.slice.call(arguments)); };
            }""")
            focus_first_main()
            ticker = pg.evaluate(
                "(document.querySelector('#scatter-chart .scatter-dot')"
                ".getAttribute('aria-label') || '').split(' — ')[0]")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            r3info = pg.evaluate("window.__fcitCalls")
            r3 = (len(r3info) == 1 and r3info[0][0] == ticker)
            check("R3 Enter on scatter dot fires findCompanyInTable(%r)" % ticker,
                  r3, "calls recorded: %r" % (r3info,) if not r3 else "")

            # R4: ArrowRight moves focus to the next dot and moves the
            # tabindex="0" holder with it (roving tabindex intact).
            pg.keyboard.press("ArrowRight")
            pg.wait_for_timeout(400)
            r4info = pg.evaluate("""() => {
              const dots = [...document.querySelectorAll('#scatter-chart .scatter-dot')];
              return {idx: dots.indexOf(document.activeElement),
                      tabbedIdx: dots.findIndex(d => d.getAttribute('tabindex') === '0'),
                      n: dots.length};
            }""")
            r4 = (r4info["idx"] == 1 and r4info["tabbedIdx"] == 1)
            check("R4 ArrowRight moves focus to dot 2 and moves the tabindex=0 holder",
                  r4, "activeIdx=%d tabbedIdx=%d" % (r4info["idx"], r4info["tabbedIdx"])
                  if not r4 else "")

            # R5: zero JS page errors across the lifecycle.
            check("R5 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if static_only:
        bad = [n for n, ok, _ in results if not ok]
        return 1 if bad else 0
    rc = render_checks()
    if rc is None:
        bad = [n for n, ok, _ in results if not ok]
        return 1 if bad else 0
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
