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
        tabindex="0" DOT (roving). The holder count is scoped to the dot
        classes: #scatter-chart also hosts the keyboard brush layer and
        the transient trend-trail year dots, which are separate tab stops
        by design (whole-container count went stale 2026-10-10).
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

498th review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of printing no summary
and returning 0). static_checks() gains the OSError-to-return-2 path
(488th template). Pre-fix defects, both 429th-review classes in one
guard: main() ignored render_checks()'s return value, so a missing d3
shim exited 0 while the render half never ran (the silent-pass
variant, 430th-review shape, although the docstring promises exit 2
for a missing shim); a missing playwright install likewise exited 0
on the statics alone (the silent-pass variant, although the docstring
promises exit 2 for playwright missing); and a transient render
exception raised before any R-check was uncaught (no retry wrapper)
-- proved in-process before the fix
(~/workspace/sp500-498/pre498_proof.py: Test A-live rc=0,
0 R-checks; Test A2 rc=0, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (no canary live concurrently this
run at proof time; the monkeypatch touches no shared state). The
playwright-missing branch keeps its skip shape (rc=0 on passing
statics) and the docstring's exit-2 promise for that branch is
unchanged from the pre-fix guard, per the 486th/487th precedent.
render_checks() already returns an explicit bool on success (458th
note (27) checked). The adopted main adds the "N/N checks passed"
summary line in the 493rd shape (the pre-fix main printed no
summary). Slowest unadopted shard-2 render guard by the multi-run
history plus the re-profile: 53 shard-2 runs: scatter_dots median
13.2s / mean 18.23s / max 55.6s vs voltenure_chip_part_spans median
11.2s / mean 13.42s / max 42.1s vs tenure_chip_combined_label median
10.6s / mean 12.82s / max 28.7s; freshest state reading tenure 16.7s
vs scatter_dots 12.1s vs voltenure 12.5s (2026-11-17T10:34Z shard-2
run); clean standalone re-profile this run scatter_dots 37.50s rc=0
11/11 vs tenure 9.65s rc=0 9/9 vs voltenure 8.68s rc=0 8/8 --
scatter_dots leads the median, the mean, the max, and the re-profile
(tenure leads only the freshest state), so the pick stands on the
multi-run history plus the re-profile, per the 469th note (68) rule.
Shard 2 is the stalest shard (last run 2026-11-17T10:34Z vs shard 3
13:13Z, shard 4 14:37Z, shard 1 17:06Z), continuing the re-baseline
sequence 493rd shard 1, 494th shard 2, 495th shard 3, 496th shard 4,
497th shard 1. sector_trend_fy_label and composition_fy_detail stay
queued next for shard 2.
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

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
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
        css = open(CSS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/charts.js or css/style.css: %s" % exc)
        return 2
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
                "window.d3 && document.querySelectorAll('#scatter-chart .scatter-dot').length > 400",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: roving tabindex -- every dot is a labelled button, exactly
            # one dot per chart is in the tab order.
            # NOTE (2026-10-10 drift-canary repair): the holder count is
            # scoped to the dot classes, not the whole chart container.
            # #scatter-chart legitimately hosts additional tabindex="0"
            # surfaces: the keyboard brush layer
            # (.scatter-brush-layer[tabindex="0"], added 2026-10-10 03:30 PT)
            # and the transient trend-trail year dots (added 2026-10-10
            # 06:00 PT) -- separate tab stops by design, not roving-group
            # violations.
            r1info = pg.evaluate("""() => {
              const sel = '#scatter-chart .scatter-dot, #scatter-chart .scatter-dot-bg, ' +
                          '#scatter-chart .scatter-dot-sector, #sop-scatter-chart .sop-dot, ' +
                          '#gov-pay-scatter-chart .gps-dot';
              const dots = [...document.querySelectorAll(sel)];
              const bad = d =>
                d.getAttribute('role') !== 'button' ||
                !(d.getAttribute('aria-label') || '').includes('Press Enter to view in table');
              const charts = ['#scatter-chart', '#sop-scatter-chart', '#gov-pay-scatter-chart'];
              const dotHolderSel = {
                '#scatter-chart': '.scatter-dot[tabindex="0"], .scatter-dot-bg[tabindex="0"], .scatter-dot-sector[tabindex="0"]',
                '#sop-scatter-chart': '.sop-dot[tabindex="0"]',
                '#gov-pay-scatter-chart': '.gps-dot[tabindex="0"]'
              };
              const holders = charts.map(c =>
                document.querySelectorAll(c + ' ' + dotHolderSel[c]).length);
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
    failed = [r for r in results if not r[1]]
    if failed or ok is False:
        if failed:
            print("FAILED: " + ", ".join(r[0] for r in failed))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
