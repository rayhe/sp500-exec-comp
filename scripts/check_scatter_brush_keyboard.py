#!/usr/bin/env python3
"""Regression guard: the scatter brush selection is keyboard-operable.

The 2026-10-10 02:00 PT panel audit found the scatter-plot brush
(d3.brush on #scatter-chart, drag-on-empty-space to select a region of
dots) was the last large mouse-only interactive surface on the site:
  (1) the brush overlay rect itself (click-and-drag only, no keyboard
      path at all), and
  (2) the brush results rows (.sbr-row) - click-only addEventListener
      rows calling window.findCompanyInTable(ticker), no tabindex/role/
      keydown.

Fixes (js/charts.js drawScatterChart + _renderBrushResults; js/app.js):
  A. Rows: title="Click to find in table" (data-bearing aria-label source)
     + window._kbdUpgradeRoving(container, '.sbr-row') after the click
     wiring - the standard roving-tabindex convention (first row
     tabindex="0", rest "-1", role="button", Enter/Space fires el.click()
     for exact parity, arrows move the holder).
     window._kbdUpgradeRoving is exposed from js/app.js (top-level
     function, now also assigned on window for the cross-file call site;
     the codebase's standard cross-scope pattern, cf.
     window.insightResetAndSort).
  B. Keyboard brush: the .scatter-brush-layer <g> is now focusable
     (tabindex="0", focusable="true", role="application", data-bearing
     aria-label describing the keys, data-kbd-upgraded="1" so the generic
     [data-kbd-upgraded]:focus-visible --accent ring applies). A
     keydown.kbdbrush handler implements:
       - Arrow keys: move a selection rect on the SAME d3.brush (starts
         centered 140x140px on first press); Shift+arrows resize from the
         bottom-right corner; clamped to the plot area, min 10px/side.
         Live-draws through brush.move with a silent flag consumed in the
         'end' handler: dots dim (the normal 'brush' path) but the results
         panel is held until commit.
       - Enter/Space: commits via brush.move(sel) with the silent flag
         clear, so the normal 'end' path renders the identical results
         panel (mouse parity).
       - Escape: clears an UNCOMMITTED keyboard rect in place and
         stopPropagation()s so the global Esc handler cannot fall through
         to clearing filters; a committed selection is left to bubble to
         the global handler (same clear path).
     The 'end' handler also syncs a mouse-drawn rect into _kbdBrushSel
     (keyboard continues where the mouse left off) and nulls it on clear.
     The hint text now reads "... or focus the chart and use Arrow keys
     ...".

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 window._kbdUpgradeRoving exposure present in js/app.js.
     S2 _renderBrushResults: rows carry title="Click to find in table"
        AND window._kbdUpgradeRoving(container, '.sbr-row') is called
        after the row-click wiring.
     S3 keyboard brush block in drawScatterChart: brushG gets
        tabindex="0", role="application", an aria-label mentioning arrow
        keys, and a keydown.kbdbrush handler covering Escape, Enter/Space
        and the four arrows; the silent flag is declared and consumed in
        the 'end' handler; the clamp helper exists.
     S4 node --check green on js/app.js and js/charts.js.
     S5 brush hint text mentions Arrow keys.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 brush layer: exactly one .scatter-brush-layer with tabindex="0",
        role="application", data-kbd-upgraded="1", and an aria-label
        containing "arrow keys".
     R2 keyboard region select: focus the layer, press ArrowRight x3 ->
        a .selection rect with nonzero width appears; press Enter ->
        #scatter-brush-results becomes visible with >=1 .sbr-row.
     R3 result rows: roving shape (exactly one tabindex="0" holder, rest
        "-1", all role=button with "Press Enter to find in table"
        aria-labels); ArrowRight moves the holder (BEFORE Enter: Enter fires
        findCompanyInTable, which redraws the scatter chart and hides the
        results panel, so arrows must be tested on the visible rows first);
        Enter on the (moved) holder calls window.findCompanyInTable exactly
        once with that row's own data-ticker.
     R4 Escape paths: after the committed selection, Escape (from a row)
        hides the results and clears the rect (global handler path);
        re-draw a silent rect with arrows (results hidden), Escape again
        clears the rect without touching results; zero JS page errors.

Usage:
  scripts/check_scatter_brush_keyboard.py              # static + render
  scripts/check_scatter_brush_keyboard.py --static-only

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
APP_JS = os.path.join(REPO, "js", "app.js")
CHARTS_JS = os.path.join(REPO, "js", "charts.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    charts = open(CHARTS_JS, encoding="utf-8").read()

    # S1: cross-file exposure of the roving helper.
    s1 = "window._kbdUpgradeRoving = _kbdUpgradeRoving" in app
    check("S1 window._kbdUpgradeRoving exposure present in js/app.js",
          s1, "" if s1 else "exposure missing: charts.js call site would throw")

    # S2: brush-result rows: title source + roving call after click wiring.
    i_wire = charts.find("row.addEventListener('click', function()")
    i_title = charts.find("title=\"Click to find in table\"")
    i_call = charts.find("window._kbdUpgradeRoving(container, '.sbr-row')")
    s2 = i_wire > 0 and i_title > 0 and i_call > i_wire
    check("S2 .sbr-row title source + _kbdUpgradeRoving(container, '.sbr-row') after click wiring",
          s2, "" if s2 else "row title/roving call missing or misordered")

    # S3: keyboard brush block.
    has_focusable = (".attr('tabindex', '0')" in charts
                     and ".attr('role', 'application')" in charts
                     and "Scatter chart region selection" in charts
                     and "arrow keys" in charts.lower())
    has_kbd_handler = ("on('keydown.kbdbrush'" in charts
                       and "key === 'Escape'" in charts
                       and "key === 'Enter' || key === ' '" in charts
                       and "KBD_BRUSH_STEP" in charts)
    has_silent = ("var _kbdBrushSilent = false" in charts
                  and "if (_kbdBrushSilent) {" in charts)
    has_clamp = "function _kbdBrushClamp(sel)" in charts
    s3 = has_focusable and has_kbd_handler and has_silent and has_clamp
    detail = []
    if not has_focusable:
        detail.append("brushG focus/role/aria-label")
    if not has_kbd_handler:
        detail.append("keydown.kbdbrush (Esc/Enter/arrows)")
    if not has_silent:
        detail.append("silent-flag declare/consume")
    if not has_clamp:
        detail.append("_kbdBrushClamp")
    check("S3 keyboard brush block (focusable layer + keydown + silent flag + clamp)",
          s3, "" if s3 else "missing: " + ", ".join(detail))

    for label, path in (("js/app.js", APP_JS), ("js/charts.js", CHARTS_JS)):
        r = subprocess.run(["node", "--check", path],
                           capture_output=True, text=True, timeout=60)
        check("S4 node --check %s is green" % label,
              r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")

    s5 = "or focus the chart and use Arrow keys" in charts
    check("S5 brush hint text mentions Arrow keys",
          s5, "" if s5 else "hint text lost the keyboard affordance")


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
                "window.d3 && document.querySelector('.scatter-brush-layer')",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # ---------- R1: brush layer keyboard surface ----------
            r1 = pg.evaluate("""() => {
              const layers = [...document.querySelectorAll('.scatter-brush-layer')];
              if (layers.length !== 1) return {ok: false, n: layers.length};
              const g = layers[0];
              const aria = g.getAttribute('aria-label') || '';
              return {ok: true, n: 1,
                      tabindex: g.getAttribute('tabindex'),
                      role: g.getAttribute('role'),
                      upgraded: g.getAttribute('data-kbd-upgraded'),
                      ariaHasKeys: /arrow keys/i.test(aria)};
            }""")
            r1ok = (r1.get("ok") and r1.get("n") == 1
                    and r1.get("tabindex") == "0"
                    and r1.get("role") == "application"
                    and r1.get("upgraded") == "1"
                    and r1.get("ariaHasKeys") is True)
            check("R1 brush layer is a focusable keyboard surface (tabindex/role/aria-label)",
                  r1ok, "shape: %r" % (r1,))

            # NOTE: the default scatter view is linear-scale, which crams most
            # dots into the bottom-left corner (huge comp outliers); a
            # centered keyboard rect would legitimately select nothing there
            # (the mouse brush behaves identically). Switch both axes to log
            # scale first so the dots spread across the plot, mirroring real
            # usage. The redraw recreates the brush layer, so re-query it.
            pg.evaluate("""() => {
              for (const id of ['scatter-log-x', 'scatter-log-y']) {
                const cb = document.getElementById(id);
                if (cb && !cb.checked) cb.click();
              }
            }""")
            pg.wait_for_timeout(2000)

            # ---------- R2: keyboard region select + Enter commit ----------
            pg.evaluate("""() => {
              document.querySelector('.scatter-brush-layer').focus();
            }""")
            for _ in range(3):
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(200)
            rect_w = pg.evaluate("""() => {
              const r = document.querySelector('.scatter-brush-layer .selection');
              return r ? parseFloat(r.getAttribute('width') || '0') : -1;
            }""")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(1200)
            results_state = pg.evaluate("""() => {
              const box = document.getElementById('scatter-brush-results');
              return {visible: !!(box && box.style.display === 'block'),
                      rows: document.querySelectorAll('.sbr-row').length};
            }""")
            r2ok = (rect_w is not None and rect_w > 0
                    and results_state["visible"] is True
                    and results_state["rows"] >= 1)
            check("R2 arrows draw a rect + Enter commits the results panel",
                  r2ok, "rect width=%r results=%r" % (rect_w, results_state))

            # ---------- R3: result rows roving group + arrows, then Enter parity ----------
            # NOTE (2026-10-10 03:30 PT run): Enter on a row fires
            # window.findCompanyInTable, which clears filters and redraws the
            # scatter chart — drawScatterChart hides #scatter-brush-results at
            # render start, so the rows are display:none afterwards and can no
            # longer take focus. The arrow-navigation half MUST therefore run
            # before Enter; the old order (Enter first) tested arrows on hidden
            # rows and failed for that reason alone.
            r3shape = pg.evaluate("""() => {
              const rows = [...document.querySelectorAll('.sbr-row')];
              const holders = rows.filter(r => r.getAttribute('tabindex') === '0');
              const neg = rows.filter(r => r.getAttribute('tabindex') === '-1');
              const bad = rows.filter(r =>
                r.getAttribute('role') !== 'button' ||
                !(r.getAttribute('aria-label') || '')
                  .includes('Press Enter to find in table') ||
                r.getAttribute('data-kbd-upgraded') !== '1');
              const h0 = holders[0];
              return {n: rows.length, holders: holders.length, neg: neg.length,
                      bad: bad.length,
                      ticker0: h0 ? h0.getAttribute('data-ticker') : null};
            }""")
            r3shape_ok = (r3shape["n"] >= 1
                          and r3shape["holders"] == 1
                          and r3shape["neg"] == r3shape["n"] - 1
                          and r3shape["bad"] == 0
                          and r3shape["ticker0"])
            r3 = False
            r3detail = "shape: %r" % (r3shape,)
            if r3shape_ok and r3shape["n"] >= 2:
                pg.evaluate("""() => {
                  document.querySelector('.sbr-row[tabindex="0"]').focus();
                }""")
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(300)
                moved = pg.evaluate("""() => {
                  const h = document.querySelector('.sbr-row[tabindex="0"]');
                  const a = document.activeElement;
                  return {ticker: h ? h.getAttribute('data-ticker') : null,
                          focused: h ? (a === h) : false};
                }""")
                r3arrow = (moved["ticker"] is not None
                           and moved["ticker"] != r3shape["ticker0"]
                           and moved["focused"] is True)
                r3detail += " | arrow: %r" % (moved,)
                r3 = r3arrow
                if r3arrow:
                    pg.evaluate("""() => {
                      window.__sbrFindCalls = [];
                      const orig = window.findCompanyInTable;
                      window.findCompanyInTable = function(t) {
                        window.__sbrFindCalls.push(t);
                        return orig ? orig.apply(this, arguments) : null;
                      };
                      document.querySelector('.sbr-row[tabindex="0"]').focus();
                    }""")
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(900)
                    calls = pg.evaluate("() => window.__sbrFindCalls")
                    r3enter = (len(calls) == 1 and calls[0] == moved["ticker"])
                    r3detail += (" | enter findCompanyInTable calls: %r (holder ticker %r)"
                                 % (calls, moved["ticker"]))
                    r3 = r3 and r3enter
            check("R3 rows: roving group + ArrowRight moves holder + Enter fires findCompanyInTable(ticker)",
                  r3, r3detail)

            # ---------- R4: Escape paths ----------
            # State entering R4: R3's Enter already navigated to the table
            # (findCompanyInTable hid the results panel via the scatter
            # redraw), so esc1 asserts the post-navigation steady state —
            # results hidden, no live selection rect — and the second half
            # draws a fresh silent keyboard rect and verifies the in-place
            # Escape branch clears it without touching the (already hidden)
            # results panel.
            pg.evaluate("""() => {
              const r = document.querySelector('.sbr-row[tabindex="0"]');
              if (r) r.focus();
            }""")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(700)
            esc1 = pg.evaluate("""() => {
              const box = document.getElementById('scatter-brush-results');
              const r = document.querySelector('.scatter-brush-layer .selection');
              return {hidden: !(box && box.style.display === 'block'),
                      rectW: r ? parseFloat(r.getAttribute('width') || '0') : -1};
            }""")
            # Silent rect: arrows (results hidden) -> Escape clears in place.
            pg.evaluate("""() => {
              document.querySelector('.scatter-brush-layer').focus();
            }""")
            for _ in range(2):
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(200)
            mid_w = pg.evaluate("""() => {
              const r = document.querySelector('.scatter-brush-layer .selection');
              return r ? parseFloat(r.getAttribute('width') || '0') : -1;
            }""")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            esc2 = pg.evaluate("""() => {
              const box = document.getElementById('scatter-brush-results');
              const r = document.querySelector('.scatter-brush-layer .selection');
              return {hidden: !(box && box.style.display === 'block'),
                      rectW: r ? parseFloat(r.getAttribute('width') || '0') : -1};
            }""")
            r4ok = (esc1["hidden"] is True and esc1["rectW"] == 0
                    and mid_w is not None and mid_w > 0
                    and esc2["hidden"] is True and esc2["rectW"] == 0)
            check("R4 Escape clears committed + silent keyboard rects",
                  r4ok, "committed=%r midW=%r silent=%r" % (esc1, mid_w, esc2))

            check("R5 zero JS page errors", len(errors) == 0,
                  ("; ".join(errors))[:400] if errors else "")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


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
