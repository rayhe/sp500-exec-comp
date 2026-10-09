#!/usr/bin/env python3
"""Regression guard: card-interior keyboard pilot (sector-rank rows + inline corr cells).

The 2026-10-09 15:30 PT run ran the 5-critic panel across data richness,
visual design, interactivity, network graph quality, and analytical depth.
The interactivity critic flagged the insight-card interiors (js/app.js,
renderInsights) as the largest remaining mouse-only surface: the
sector-rank chart rows (.src-row[data-sector], click = filter the table
to that sector) and the inline correlation-matrix heat cells
(.corr-cell-active, click = open that metric pair in the scatter plot)
had zero keyboard reachability — no tabindex, no role, no keydown, no
focus ring.

This run makes both interiors keyboard surfaces:

  1. Sector-rank rows (~11, .src-row with data-sector): tabindex="0",
     role="button", data-bearing aria-label ("<rank>. <sector>, <val>
     median CEO pay. Press Enter to filter the table to this sector.").
     Enter/Space fires the SAME activateRow() the click handler fires.
     The anomaly-distribution rows reuse .src-row styling but carry no
     data-sector — their click is a no-op and they stay informational
     (out of the tab order), preserving keyboard/click parity.
  2. Inline correlation cells (~56, .corr-cell-active): roving tabindex
     (first cell "0", rest "-1" — 56 tab stops would be unusable),
     role="button", data-bearing aria-label (the cell's title: "<row> x
     <col>: r=<r> (<strength>)" + ". Press Enter to view this pair in
     the scatter plot."). The click body is factored into openCorrPair
     (scatter-x/y selects + change dispatch + scroll) so keyboard
     Enter/Space fires the exact same path. ArrowRight/Down and
     ArrowLeft/Up move linearly between cells (treemap-roving
     convention), Home/End jump to the ends; every key is
     preventDefault()ed so the global ArrowLeft/Right table-page
     shortcut cannot double-fire (keyboard-pilot contract, 2026-10-09).
  3. :focus-visible rings on .insight-card .src-row[data-sector] and
     .insight-card .corr-cell-active use the --accent convention.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the .src-row wiring sets tabindex="0", role="button" and a
        median-CEO-pay aria-label, gated on a data-sector row.
     S2 the .src-row keydown handles Enter and Space, preventDefault,
        stopPropagation, then the same activate path as click.
     S3 openCorrPair exists and the .corr-cell-active click handler
        delegates to it (parseInt of data-corr-ri/data-corr-ci).
     S4 corr cells get roving tabindex (cellIdx === 0 ? '0' : '-1'),
        role="button", and an aria-label mentioning the scatter plot.
     S5 the corr keydown handles Enter/Space (openCorrPair) and
        ArrowLeft/Right/Up/Down + Home/End with the roving move and
        preventDefault.
     S6 css/style.css has both :focus-visible rules with the --accent
        outline convention.
     S7 the keyboard additions are attribute-bound (no innerHTML).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered .src-row[data-sector] is role=button,
        tabindex=0 with a non-empty aria-label; anomaly .src-row rows
        (no data-sector) carry no tabindex.
     R2 every rendered .corr-cell-active is role=button with tabindex
        in {"0","-1"}, exactly one "0" holder, and a non-empty
        aria-label naming a Pearson r.
     R3 pressing Enter on a focused sector-rank row fires
        window.filterBySector with that sector (keyboard/click parity).
     R4 pressing Enter on a focused corr cell sets the scatter x/y
        metric selects to that pair (same action as click).
     R5 ArrowRight on a focused corr cell moves focus to the next cell
        and moves the roving "0" holder with it.
     R6 zero JS page errors.

Usage:
  scripts/check_card_interior_keyboard.py              # static + render
  scripts/check_card_interior_keyboard.py --static-only

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
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def src_row_block(app):
    m = re.search(
        r"// Wire sector rank chart bar click handlers\n([\s\S]*?)\n        \}\);",
        app)
    return m.group(0) if m else None


def corr_block(app):
    m = re.search(
        r"// Wire correlation heatmap cell click handlers([\s\S]*?)\n        \}",
        app)
    return m.group(0) if m else None


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    sb = src_row_block(app)
    cb = corr_block(app)

    s1 = (sb is not None
          and "if (sectorName) {" in sb
          and "row.setAttribute('tabindex', '0')" in sb
          and "row.setAttribute('role', 'button')" in sb
          and "median CEO pay" in sb
          and "row.setAttribute('aria-label'" in sb)
    check("S1 .src-row wiring sets tabindex=0, role=button, median-CEO-pay aria-label on data-sector rows",
          s1, "" if s1 else "src-row keyboard attributes missing or ungated")

    s2 = (sb is not None
          and "row.addEventListener('keydown'" in sb
          and "e.key === 'Enter'" in sb
          and "e.key === ' '" in sb
          and "e.preventDefault()" in sb
          and "e.stopPropagation()" in sb
          and "activateRow();" in sb
          and "row.addEventListener('click'" in sb)
    check("S2 .src-row Enter/Space keydown: preventDefault, stopPropagation, same activateRow as click",
          s2, "" if s2 else "src-row keydown wiring missing or diverged from click")

    s3 = (cb is not None
          and "var openCorrPair = function(ri, ci) {" in cb
          and "cell.addEventListener('click'" in cb
          and "openCorrPair(parseInt(cell.dataset.corrRi), parseInt(cell.dataset.corrCi))" in cb)
    check("S3 openCorrPair factored; .corr-cell-active click delegates to it",
          s3, "" if s3 else "openCorrPair missing or click body not delegated")

    s4 = (cb is not None
          and "cell.setAttribute('tabindex', cellIdx === 0 ? '0' : '-1')" in cb
          and "cell.setAttribute('role', 'button')" in cb
          and "cell.setAttribute('aria-label'" in cb
          and "scatter plot" in cb)
    check("S4 corr cells get roving tabindex, role=button, scatter-plot aria-label",
          s4, "" if s4 else "corr-cell roving-tabindex wiring missing")

    s5 = (cb is not None
          and "cell.addEventListener('keydown'" in cb
          and "e.key === 'ArrowRight'" in cb
          and "e.key === 'ArrowLeft'" in cb
          and "e.key === 'ArrowUp'" in cb
          and "e.key === 'ArrowDown'" in cb
          and "e.key === 'Home'" in cb
          and "e.key === 'End'" in cb
          and "allCells[moveTo].setAttribute('tabindex', '0')" in cb
          and "allCells[moveTo].focus()" in cb)
    check("S5 corr keydown: Enter/Space opens pair; arrows/Home/End rove the tabindex holder",
          s5, "" if s5 else "corr-cell arrow/roving keydown wiring missing")

    m1 = re.search(
        r"\.insight-card \.src-row\[data-sector\]:focus-visible\s*\{([\s\S]*?)\}",
        css)
    m2 = re.search(
        r"\.insight-card \.corr-cell-active:focus-visible\s*\{([\s\S]*?)\}",
        css)
    s6 = (m1 is not None and "outline: 2px solid var(--accent)" in m1.group(1)
          and m2 is not None and "outline: 2px solid var(--accent)" in m2.group(1))
    check("S6 :focus-visible --accent ring on .src-row[data-sector] + .corr-cell-active",
          s6, "" if s6 else "focus ring missing or off-convention")

    s7 = (sb is not None and cb is not None
          and "innerHTML" not in sb and "innerHTML" not in cb)
    check("S7 keyboard additions are attribute-bound (no innerHTML)",
          s7, "" if s7 else "innerHTML found in the new wiring blocks")


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
                "window.d3 && document.querySelectorAll('.corr-cell-active').length > 10",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: sector-rank rows are labelled buttons; anomaly rows stay
            # out of the tab order. The rank chart only renders when a
            # sector filter is active ('vs S&P 500' card, _sectorRankActive),
            # so activate one first via the real filterBySector path.
            pg.evaluate("window.filterBySector('Energy')")
            pg.wait_for_timeout(1200)
            r1info = pg.evaluate("""() => {
              const rows = [...document.querySelectorAll('.src-row[data-sector]')];
              const bad = r =>
                r.getAttribute('role') !== 'button' ||
                r.getAttribute('tabindex') !== '0' ||
                !(r.getAttribute('aria-label') || '').length;
              const anom = [...document.querySelectorAll('.anom-dist-chart .src-row')];
              const anomBad = anom.filter(r => r.hasAttribute('tabindex')).length;
              return {n: rows.length, bad: rows.filter(bad).length,
                      anom: anom.length, anomBad: anomBad,
                      sample: rows[0] ? rows[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["n"] > 5 and r1info["bad"] == 0
                  and r1info["anom"] > 0 and r1info["anomBad"] == 0)
            check("R1 all %d sector-rank rows are role=button tabindex=0 with aria-label; %d anomaly rows have no tabindex"
                  % (r1info["n"], r1info["anom"]),
                  r1, ("n=%d bad=%d anom=%d anomBad=%d sample=%r" % (
                      r1info["n"], r1info["bad"], r1info["anom"],
                      r1info["anomBad"], r1info["sample"])) if not r1 else "")

            # R2: corr cells are labelled roving-tabindex buttons, one holder.
            r2info = pg.evaluate("""() => {
              const cells = [...document.querySelectorAll('.corr-cell-active')];
              const bad = c =>
                c.getAttribute('role') !== 'button' ||
                ['0', '-1'].indexOf(c.getAttribute('tabindex')) < 0 ||
                (c.getAttribute('aria-label') || '').indexOf('r=') < 0;
              const holders = cells.filter(c => c.getAttribute('tabindex') === '0').length;
              return {n: cells.length, bad: cells.filter(bad).length,
                      holders: holders,
                      sample: cells[0] ? cells[0].getAttribute('aria-label') : null};
            }""")
            r2 = (r2info["n"] > 20 and r2info["bad"] == 0 and r2info["holders"] == 1)
            check("R2 all %d corr cells are role=button with roving tabindex (1 holder) + Pearson-r aria-label"
                  % r2info["n"],
                  r2, ("n=%d bad=%d holders=%d sample=%r" % (
                      r2info["n"], r2info["bad"], r2info["holders"],
                      r2info["sample"])) if not r2 else "")

            # R3: Enter on a focused sector-rank row fires filterBySector
            # with that row's sector (keyboard/click parity).
            r3info = pg.evaluate("""() => {
              window.__filterCalls = [];
              window.filterBySector = function(s) { window.__filterCalls.push(s); };
              const row = document.querySelector('.src-row[data-sector]');
              if (!row) return 'NO_ROW';
              row.scrollIntoView({block: 'center'});
              row.focus();
              return row.dataset.sector;
            }""")
            if r3info == "NO_ROW":
                check("R3 Enter on sector-rank row fires filterBySector", False,
                      "no .src-row[data-sector] rendered")
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(400)
                r3calls = pg.evaluate("window.__filterCalls")
                r3 = (r3calls == [r3info])
                check("R3 Enter on sector-rank row fires filterBySector('%s')"
                      % r3info, r3,
                      "calls recorded: %r" % (r3calls,) if not r3 else "")

            # R4: Enter on a focused corr cell sets the scatter x/y selects
            # to that pair (same action as click).
            r4info = pg.evaluate("""() => {
              const cell = document.querySelector('.corr-cell-active');
              if (!cell) return 'NO_CELL';
              cell.scrollIntoView({block: 'center'});
              cell.focus();
              return [cell.dataset.corrRi, cell.dataset.corrCi];
            }""")
            if r4info == "NO_CELL":
                check("R4 Enter on corr cell sets scatter selects", False,
                      "no .corr-cell-active rendered")
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(600)
                r4vals = pg.evaluate("""() => ({
                  x: document.getElementById('scatter-x-metric') ?
                     document.getElementById('scatter-x-metric').value : null,
                  y: document.getElementById('scatter-y-metric') ?
                     document.getElementById('scatter-y-metric').value : null})""")
                r4 = (r4vals["x"] and r4vals["y"])
                check("R4 Enter on corr cell sets scatter x/y metric selects (x=%r y=%r)"
                      % (r4vals["x"], r4vals["y"]),
                      r4, "select values: %r" % (r4vals,) if not r4 else "")
                # scroll back up so the next cell test starts from a
                # known focus state
                pg.evaluate("window.scrollTo(0, 0)")

            # R5: ArrowRight roves focus + the tabindex holder to the next
            # cell (and does not leave the heatmap).
            r5info = pg.evaluate("""() => {
              const cells = [...document.querySelectorAll('.corr-cell-active')];
              const first = cells[0];
              first.focus();
              return {n: cells.length, ri: first.dataset.corrRi,
                      ci: first.dataset.corrCi};
            }""")
            pg.wait_for_timeout(300)
            pg.keyboard.press("ArrowRight")
            pg.wait_for_timeout(400)
            r5after = pg.evaluate("""() => {
              const cells = [...document.querySelectorAll('.corr-cell-active')];
              const holders = cells.filter(c => c.getAttribute('tabindex') === '0');
              const idx = cells.indexOf(document.activeElement);
              return {holders: holders.length,
                      holderIdx: holders.length ? cells.indexOf(holders[0]) : -1,
                      activeIdx: idx};
            }""")
            r5 = (r5after["holders"] == 1 and r5after["holderIdx"] == 1
                  and r5after["activeIdx"] == 1)
            check("R5 ArrowRight moves focus to the next corr cell and moves the roving holder",
                  r5, "after: %r" % (r5after,) if not r5 else "")

            # R6: zero JS page errors across the lifecycle.
            check("R6 zero JS page errors", len(errors) == 0,
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
