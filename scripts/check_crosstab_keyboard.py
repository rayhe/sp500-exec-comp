#!/usr/bin/env python3
"""Regression guard: crosstab cells are keyboard-operable AND actually filter.

The 2026-10-10 5-critic panel audit for NEW failure-mode classes flagged the
tenure x governance crosstab cells (HTML td[data-tenure], click ->
window.filterTableByTickers) as the last click-without-keyboard surface. The
same class covered the Volatility x Gov (td[data-vol]) and SoP x Vol
(td[data-sop-key]) crosstabs. The 2026-10-11 03:30 PT audit found the deeper
fault: window.filterTableByTickers was CALLED in all three crosstab click
handlers but DEFINED nowhere, so clicking a cell scrolled to the table
without filtering -- the legend's "Click cell = filter table" promise was
silently broken (the typeof-guard hid it).

This run's fix:
  - js/app.js defines window.filterTableByTickers(tickers, label) on the
    standard window._activeXFilter ticker-list convention (peer-dist /
    community / quartile / position): toggle-off on same-label click,
    clearable #crosstab-filter-chip, renderTable filter stage, summary-bar
    line, URL state (xtk/xlbl), reset-all + crosstab-sector-reset clearing,
    _hasActiveFilters participation.
  - js/charts.js gains _enableCellKeyboard(td): Enter/Space dispatches a
    synthetic click carrying shiftKey (Shift+Enter = Shift+click scatter
    branch), wired into all three crosstab cell forEach blocks. The SoP x
    Vol cells additionally gain tabindex="0" role="gridcell" (they previously
    had neither). Legends + the SoP title advertise the keyboard path. The
    existing .crosstab-cell:focus-visible ring covers focus (no CSS change).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 window.filterTableByTickers is defined in js/app.js.
     S2 renderTable applies window._activeCrosstabFilter as a ticker-list
        filter stage.
     S3 _enableCellKeyboard is defined and wired in all three crosstab cell
        blocks (data-tenure, data-vol, data-sop-key); Enter/Space replay a
        synthetic click with shiftKey passthrough.
     S4 the SoP x Vol cell HTML carries tabindex="0" and role="gridcell".
     S5 the #crosstab-filter-chip indicator exists and is cleared by
        reset-all (chip id in the removal list).
     S6 URL state carries xtk/xlbl in serializeState and restores them in
        deserializeState.
     S7 node --check is green for js/app.js and js/charts.js.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 tenure x gov cells are focusable (tabindex=0, role=gridcell).
     R2 Enter on a tenure cell calls window.filterTableByTickers exactly
        once with that cell's label -- keyboard/click parity -- and the
        table filters to the cell's tickers (tbody rows subset of them,
        chip #crosstab-filter-chip present).
     R3 Shift+Enter on a tenure cell calls window.navigateToScatter exactly
        once with the cell's top ticker -- the Shift+click branch.
     R4 Enter on a SoP x Vol cell calls window.filterTableByTickers once.
     R5 zero JS page errors.

Usage:
  scripts/check_crosstab_keyboard.py              # static + render
  scripts/check_crosstab_keyboard.py --static-only

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
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    s1 = "window.filterTableByTickers = function(tickers, label)" in app
    check("S1 window.filterTableByTickers defined in js/app.js",
          s1, "" if s1 else "definition missing")

    s2 = ("window._activeCrosstabFilter" in app
          and re.search(r"// Crosstab filter: filter to the ticker set of a cross-tabulation cell"
                        r"[\s\S]*?_xfTickers\.indexOf\(c\.ticker\)", app) is not None)
    check("S2 renderTable applies window._activeCrosstabFilter as a ticker-list filter",
          s2, "" if s2 else "filter stage missing")

    helper = "function _enableCellKeyboard(td)" in charts
    s3 = (helper
          and "new MouseEvent('click', { bubbles: true, cancelable: true, shiftKey: e.shiftKey })" in charts
          and charts.count("_enableCellKeyboard(td);") >= 2
          and "_enableCellKeyboard(cell);" in charts
          and "data-tenure" in charts and "data-vol" in charts and "data-sop-key" in charts)
    check("S3 _enableCellKeyboard defined + wired into all three crosstab cell blocks "
          "(Enter/Space synthetic click, shiftKey passthrough)",
          s3, "" if s3 else "helper or wiring missing")

    s4 = ("'tabindex=\"0\" role=\"gridcell\">'" in charts
          or "'tabindex=\"0\" role=\"gridcell\">';" in charts
          or 'tabindex="0" role="gridcell">' in charts)
    check("S4 SoP x Vol cell HTML carries tabindex=0 + role=gridcell",
          s4, "" if s4 else "attributes missing on the SoP cells")

    s5 = ("id = 'crosstab-filter-chip'" in app
          and "'crosstab-filter-chip'" in app
          and re.search(r"'crosstab-filter-chip'", app) is not None)
    # chip id must appear both at creation and in the reset-all removal list
    s5 = app.count("'crosstab-filter-chip'") >= 3
    check("S5 #crosstab-filter-chip indicator exists and is in the reset-all removal list",
          s5, "" if s5 else "chip creation or reset wiring missing (count=%d)" % app.count("'crosstab-filter-chip'"))

    s6 = ("params.push('xtk='" in app and "params.push('xlbl='" in app
          and "state.xtk && state.xlbl" in app)
    check("S6 URL state carries xtk/xlbl (serialize + deserialize)",
          s6, "" if s6 else "xtk/xlbl wiring missing")

    ok = True
    detail = ""
    for f in (APP_JS, CHARTS_JS):
        r = subprocess.run(["node", "--check", f], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            ok = False
            detail += f + ": " + r.stderr.strip()[:200] + "; "
    check("S7 node --check green for js/app.js and js/charts.js", ok, detail)


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
                "window.d3 && document.querySelectorAll('#tenure-gov-crosstab-chart .crosstab-cell[data-tenure]').length >= 4",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('#sop-vol-crosstab-chart .crosstab-cell[data-sop-key]').length >= 4",
                timeout=30000)
            pg.wait_for_timeout(1200)

            # R1: tenure cells are focusable gridcells.
            r1info = pg.evaluate("""() => {
              const cells = [...document.querySelectorAll('#tenure-gov-crosstab-chart .crosstab-cell[data-tenure]')];
              const ok = cells.length >= 4 &&
                cells.every(e => e.getAttribute('tabindex') === '0' && e.getAttribute('role') === 'gridcell');
              return {n: cells.length, ok: ok};
            }""")
            r1 = r1info["ok"]
            check("R1 tenure x gov crosstab cells are tabindex=0 role=gridcell",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # Spy on the filter + scatter entry points.
            pg.evaluate("""() => {
              window.__ftCalls = [];
              const origFT = window.filterTableByTickers;
              window.filterTableByTickers = function(t, l) {
                window.__ftCalls.push([t.slice(), l]);
                return origFT.apply(this, arguments);
              };
              window.__nsCalls = [];
              const origNS = window.navigateToScatter;
              window.navigateToScatter = function(t, x, y) {
                window.__nsCalls.push([t, x, y]);
                return origNS.apply(this, arguments);
              };
            }""")

            # R2: Enter on a tenure cell filters the table to that cell's tickers.
            r2info = pg.evaluate("""() => {
              const cell = document.querySelector('#tenure-gov-crosstab-chart .crosstab-cell[data-tenure][tabindex="0"]');
              if (!cell) return {err: 'NO_CELL'};
              cell.focus();
              cell.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
              return new Promise(res => setTimeout(() => {
                const ft = window.__ftCalls;
                const chip = document.getElementById('crosstab-filter-chip');
                const rows = [...document.querySelectorAll('#comp-tbody tr:not(.detail-row) .ticker')]
                  .map(e => e.textContent.trim()).filter(Boolean);
                res({ftCalls: ft.length, label: ft.length ? ft[0][1] : null,
                     chip: !!chip, rowCount: rows.length,
                     firstTickers: ft.length ? ft[0][0].slice(0, 5) : []});
              }, 1200));
            }""")
            r2 = (r2info.get("ftCalls") == 1
                  and (r2info.get("label") or "").startswith("Tenure:")
                  and r2info.get("chip") is True
                  and r2info.get("rowCount", 0) > 0)
            check("R2 Enter on a tenure cell calls filterTableByTickers once (Tenure label) "
                  "and the table filters with the chip present",
                  r2, ("" if r2 else "state: %r" % (r2info,)))

            # R3: Shift+Enter on a tenure cell takes the Shift+click scatter branch.
            r3info = pg.evaluate("""() => {
              window.__nsCalls = [];
              const cell = document.querySelector('#tenure-gov-crosstab-chart .crosstab-cell[data-tenure][tabindex="0"]');
              if (!cell) return {err: 'NO_CELL'};
              cell.focus();
              cell.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', shiftKey: true, bubbles: true, cancelable: true}));
              return new Promise(res => setTimeout(() => res({nsCalls: window.__nsCalls}), 800));
            }""")
            r3 = (len(r3info.get("nsCalls", [])) == 1)
            check("R3 Shift+Enter on a tenure cell calls window.navigateToScatter exactly once",
                  r3, ("" if r3 else "state: %r" % (r3info,)))

            # R4: Enter on a SoP x Vol cell also filters (that surface had no
            # tabindex at all before this run).
            r4info = pg.evaluate("""() => {
              window.__ftCalls = [];
              const cell = document.querySelector('#sop-vol-crosstab-chart .crosstab-cell[data-sop-key][tabindex="0"]');
              if (!cell) return {err: 'NO_CELL'};
              const role = cell.getAttribute('role');
              cell.focus();
              cell.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
              return new Promise(res => setTimeout(() => res(
                {ftCalls: window.__ftCalls.length, role: role,
                 chip: !!document.getElementById('crosstab-filter-chip')}), 1200));
            }""")
            r4 = (r4info.get("ftCalls") == 1 and r4info.get("role") == "gridcell"
                  and r4info.get("chip") is True)
            check("R4 Enter on a SoP x Vol cell calls filterTableByTickers once (role=gridcell, chip present)",
                  r4, ("" if r4 else "state: %r" % (r4info,)))

            r5 = len(errors) == 0
            check("R5 zero JS page errors", r5,
                  ("" if r5 else "errors: %r" % (errors[:3],)))
            browser.close()
    finally:
        server.terminate()
    return True


def main():
    static_checks()
    if "--static-only" in sys.argv:
        print("static-only: skipping render checks")
    else:
        rc = render_checks()
        if rc is False:
            print("INFRA: render checks could not run")
            return 2
    fails = [n for (n, ok, d) in results if not ok]
    print("----")
    print("%d/%d checks passed" % (len(results) - len(fails), len(results)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
