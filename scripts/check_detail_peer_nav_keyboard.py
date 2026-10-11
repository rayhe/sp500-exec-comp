#!/usr/bin/env python3
"""Regression guard: detail-panel peer navigation/filter surfaces are
keyboard-operable (roving-tabindex group).

The 2026-10-11 14:00 PT run closed the last click-only class in the expanded
company detail panel. Three peer/network surfaces had addEventListener('click')
wiring on plain spans/divs with no tabindex, no role, no keydown - entirely
mouse-only:

  .peer-dist-col[data-peer-tickers]  (peer distribution histogram columns,
                                      click to filter the table by comp bucket)
  .peer-pay-row[data-ticker]         (peer pay rows, click to find the peer
                                      in the table; .peer-pay-self unwired)
  .reach-peer-ticker[data-ticker]    (reach peer ticker spans, click to find
                                      the peer in the table)

The fix extends the file-scope _kbdUpgradeRoving(container, selector) helper
(treemap-roving convention) with one roving-tabindex group over the detailRow
in document order, covering the three selectors:

  '.peer-dist-col[data-peer-tickers]:not([data-peer-tickers=""]), '
  '.peer-pay-row[data-ticker]:not(.peer-pay-self), '
  '.reach-peer-ticker[data-ticker]'

Zero-count dist columns carry no click action (empty tickers -> early return
in the click handler) and self peer-pay rows are unwired, so both are
excluded from the selector (click/no-op parity). Roving holder gets
tabindex="0", rest "-1"; role="button"; data-bearing aria-label (the
element's own title with "click to" -> "Press Enter to"; visible text when
there is no title, e.g. bare reach-peer-ticker spans); data-kbd-upgraded="1";
Enter/Space -> preventDefault/stopPropagation/el.click() so the keyboard
path reproduces the exact mouse behavior. Arrow keys move the holder
linearly, preventDefault()ed + stopPropagation()ed so the global
ArrowLeft/Right table-page shortcut and the detail panel's own prev/next
company navigation cannot double-fire.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the three-class _kbdUpgradeRoving(detailRow, ...) call exists,
        placed after the reach-peer-ticker click wiring (inside the detail
        render path) and covering the dist-col / peer-pay-row /
        reach-peer-ticker selectors.
     S2 click/no-op parity: the selector excludes zero-count dist columns
        (:not([data-peer-tickers=""])) and unwired self pay rows
        (:not(.peer-pay-self)).
     S3 exactly one _kbdUpgradeRoving definition exists (no
        duplicate-definition shadowing).
     S4 node --check js/app.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 on a company detail with peers, the three selectors form one
        roving group: exactly one tabindex="0" holder, all role=button
        with "Press Enter" aria-labels and data-kbd-upgraded="1";
        zero-count dist columns and self pay rows carry no tabindex.
     R2 Enter on a peer-pay row calls window.findCompanyInTable exactly
        once with the row's ticker (keyboard/click parity).
     R3 Enter on a non-empty peer-dist column sets
        window._activePeerDistFilter to its tickers; Enter again clears it
        (toggle parity with the click handler).
     R4 zero JS page errors.

Usage:
  scripts/check_detail_peer_nav_keyboard.py              # static + render
  scripts/check_detail_peer_nav_keyboard.py --static-only

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

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


SELECTOR = ('.peer-dist-col[data-peer-tickers]:not([data-peer-tickers=""]), '
            '.peer-pay-row[data-ticker]:not(.peer-pay-self), '
            '.reach-peer-ticker[data-ticker]')


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()

    defs = re.findall(r"^function _kbdUpgradeRoving\(container, selector\) \{$",
                      app, re.MULTILINE)
    s3 = len(defs) == 1
    check("S3 exactly one _kbdUpgradeRoving definition (no duplicate-definition shadowing)",
          s3, "" if s3 else "found %d definitions" % len(defs))

    call = "_kbdUpgradeRoving(detailRow, '" + SELECTOR + "');"
    i_call = app.find(call)
    # Reach-peer-ticker wiring must precede the upgrade call (the call site
    # sits right after that wiring block in the detail render path).
    i_wire = app.find("detailRow.querySelectorAll('.reach-peer-ticker[data-ticker]').forEach")
    s1 = (i_call != -1 and i_wire != -1 and i_wire < i_call)
    check("S1 roving-upgrade call for dist-col / peer-pay-row / reach-peer-ticker "
          "after the reach-peer-ticker click wiring",
          s1, "" if s1 else "call missing or misplaced")

    # verify the exclusions sit inside the actual upgrade call's selector
    if i_call != -1:
        callseg = app[i_call:i_call + len(call)]
        s2 = (':not([data-peer-tickers=""])' in callseg
              and ':not(.peer-pay-self)' in callseg
              and '.peer-pay-row[data-ticker]:not(.peer-pay-self)' in callseg
              and '.reach-peer-ticker[data-ticker]' in callseg)
    else:
        s2 = False
    check("S2 click/no-op parity: selector excludes zero-count dist columns "
          "and unwired self peer-pay rows",
          s2, "" if s2 else "exclusion selectors missing from the upgrade call")

    r = subprocess.run(["node", "--check", APP_JS],
                       capture_output=True, text=True, timeout=60)
    check("S4 node --check js/app.js is green",
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

            # Open a company detail that renders peer nav surfaces.
            peer_ticker = None
            for cand in ['META', 'AAPL', 'MSFT', 'JPM', 'GOOGL', 'XOM', 'NVDA', 'TSLA', 'C', 'BAC']:
                pg.evaluate("t => window.openCompanyDetailWithDiff(t, '')", cand)
                try:
                    pg.wait_for_function(
                        "() => document.querySelectorAll("
                        "'.peer-pay-row[data-ticker]:not(.peer-pay-self),"
                        " .peer-dist-col[data-peer-tickers]:not([data-peer-tickers=\"\"]),"
                        " .reach-peer-ticker[data-ticker]').length >= 3",
                        timeout=6000)
                    peer_ticker = cand
                    break
                except Exception:
                    continue
            if not peer_ticker:
                check("R1 roving group shape over the three peer nav surfaces",
                      False, "no candidate ticker rendered peer nav surfaces")
                check("R2 Enter on peer-pay row calls window.findCompanyInTable once",
                      False, "no detail to test")
                check("R3 Enter on dist column toggles window._activePeerDistFilter",
                      False, "no detail to test")
                check("R4 zero JS page errors", len(errors) == 0,
                      "" if not errors else "; ".join(errors[:3]))
                browser.close()
                return True

            pg.wait_for_timeout(800)

            r1info = pg.evaluate("""() => {
              const sel = '.peer-pay-row[data-ticker]:not(.peer-pay-self),' +
                '.peer-dist-col[data-peer-tickers]:not([data-peer-tickers=""]),' +
                '.reach-peer-ticker[data-ticker]';
              const els = [...document.querySelectorAll(sel)];
              const holders = els.filter(e => e.getAttribute('tabindex') === '0');
              const neg = els.filter(e => e.getAttribute('tabindex') === '-1');
              const bad = els.filter(e =>
                e.getAttribute('role') !== 'button' ||
                !(e.getAttribute('aria-label') || '').includes('Press Enter') ||
                e.getAttribute('data-kbd-upgraded') !== '1');
              // exclusions: zero-count dist cols + self pay rows must be untabbable
              const zeroCols = [...document.querySelectorAll(
                '.peer-dist-col[data-peer-tickers=""]')];
              const selfRows = [...document.querySelectorAll(
                '.peer-pay-row.peer-pay-self')];
              const leaked = zeroCols.concat(selfRows).filter(
                e => e.hasAttribute('tabindex'));
              const holderSel = holders[0] ? holders[0].className : null;
              const holderLabel = holders[0] ?
                holders[0].getAttribute('aria-label') : null;
              return {n: els.length, holders: holders.length, neg: neg.length,
                      bad: bad.length, leaked: leaked.length,
                      holderSel: holderSel, holderLabel: holderLabel};
            }""")
            r1 = (r1info["n"] >= 3
                  and r1info["holders"] == 1
                  and r1info["neg"] == r1info["n"] - 1
                  and r1info["bad"] == 0
                  and r1info["leaked"] == 0)
            check("R1 one roving group over the three peer nav surfaces "
                  "(1 holder, role=button, Press-Enter labels, zero-count/self excluded)",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # Spy on the peer-row navigation entry point.
            pg.evaluate("""() => {
              window.__fcitCalls = [];
              const orig = window.findCompanyInTable;
              window.findCompanyInTable = function(t) {
                window.__fcitCalls.push(t);
                return orig.apply(this, arguments);
              };
            }""")
            r2info = pg.evaluate("""() => {
              const row = document.querySelector(
                '.peer-pay-row[data-ticker]:not(.peer-pay-self)');
              if (!row) return {err: 'NO_ROW'};
              const t = row.getAttribute('data-ticker');
              row.dispatchEvent(new KeyboardEvent('keydown',
                {key: 'Enter', bubbles: true, cancelable: true}));
              return {ticker: t, calls: window.__fcitCalls.slice()};
            }""")
            # findCompanyInTable re-renders the table; re-open the detail for R3.
            r2 = (r2info.get("calls") == [r2info.get("ticker")]
                  and len(r2info.get("ticker") or "") > 0)
            check("R2 Enter on a peer-pay row calls window.findCompanyInTable "
                  "exactly once with the row's ticker",
                  r2, ("" if r2 else "state: %r" % (r2info,)))

            pg.evaluate("t => window.openCompanyDetailWithDiff(t, '')", peer_ticker)
            pg.wait_for_function(
                "() => document.querySelectorAll("
                "'.peer-dist-col[data-peer-tickers]:not([data-peer-tickers=\"\"])').length > 0",
                timeout=6000)
            pg.wait_for_timeout(800)
            r3info = pg.evaluate("""() => {
              const col = document.querySelector(
                '.peer-dist-col[data-peer-tickers]:not([data-peer-tickers=""])');
              if (!col) return {err: 'NO_COL'};
              const expected = col.getAttribute('data-peer-tickers').split(',');
              window._activePeerDistFilter = null;
              col.dispatchEvent(new KeyboardEvent('keydown',
                {key: 'Enter', bubbles: true, cancelable: true}));
              const after = window._activePeerDistFilter;
              const setOk = after && after.tickers &&
                after.tickers.length === expected.length &&
                after.tickers.every((t, i) => t === expected[i]);
              col.dispatchEvent(new KeyboardEvent('keydown',
                {key: 'Enter', bubbles: true, cancelable: true}));
              const cleared = window._activePeerDistFilter === null;
              return {setOk: !!setOk, cleared: !!cleared,
                      nTickers: expected.length};
            }""")
            r3 = r3info.get("setOk") and r3info.get("cleared")
            check("R3 Enter on a non-empty dist column sets "
                  "window._activePeerDistFilter, Enter again clears it",
                  r3, ("" if r3 else "state: %r" % (r3info,)))

            r4 = len(errors) == 0
            check("R4 zero JS page errors",
                  r4, ("" if r4 else "; ".join(errors[:3])))
            browser.close()
    finally:
        server.terminate()
    return True


def main():
    static_checks()
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("STATIC-ONLY: %d/%d passed" % (len(results) - len(failed), len(results)))
        sys.exit(1 if failed else 0)
    render_checks()
    failed = [r for r in results if not r[1]]
    print("TOTAL: %d/%d passed" % (len(results) - len(failed), len(results)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
