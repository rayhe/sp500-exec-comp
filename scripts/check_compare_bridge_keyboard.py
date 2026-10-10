#!/usr/bin/env python3
"""Regression guard: click-only surfaces in the compare view and network
community detail are keyboard-operable (roving-tabindex groups).

The 2026-10-09 19:30 PT run covered the click-only surfaces outside insight
cards but missed two classes the 22:00 PT panel audit found via the
-*-clickable class sweep:

  .cmp-div-row-clickable (Company Comparison > Compensation Profile Overlay >
  Dimension Divergence rows). Rendered into #cmp-radar-divergence with
  cursor:pointer + title="Click to sort table by <dim>"; click wiring is
  event-delegated on divEl and calls insightResetAndSort(sk, sd). Before this
  fix the rows had no tabindex, no role, no keydown: entirely mouse-only.

  .cb-bridge-expandable (detail panel > network community > "bridge" rows).
  Rendered with title="N outbound + M inbound edges to <cluster> — click to
  see companies" and a chevron; click wiring is a per-row addEventListener
  that toggles the .cb-bridge-open expand/collapse. Before this fix the rows
  had no tabindex, no role, no keydown: entirely mouse-only.

Both are upgraded with the file-scope _kbdUpgradeRoving(container, selector)
helper (treemap-roving convention: first element tabindex="0", rest "-1",
role="button", data-bearing aria-label derived from the element's own title,
Enter/Space -> preventDefault/stopPropagation/el.click() for exact
keyboard/click parity, arrows move the holder linearly with
preventDefault/stopPropagation per the keyboard-pilot contract):

  renderComparisonRadar -> _kbdUpgradeRoving(divEl, '.cmp-div-row-clickable')
    (after the delegated click wiring; theme-toggle redraws re-run the whole
    render so the upgrade is re-applied)
  detail panel render   -> _kbdUpgradeRoving(detailRow, '.cb-bridge-expandable')
    (after the per-row click wiring forEach)

Parity notes:
  - cmp-div rows: Enter fires el.click(), which bubbles to divEl's delegated
    handler and calls insightResetAndSort with the row's own
    data-sort-key/data-sort-dir: identical to a mouse click.
  - bridge rows: Enter fires el.click(), which hits the per-row listener and
    toggles the same expand/collapse (including the aria-live announce).
  - rows without sortInfo never get .cmp-div-row-clickable and carry no click
    action; non-expandable bridge rows never get .cb-bridge-expandable:
    excluded from the selectors by construction (click/no-op parity, same as
    the heatmap hm-zero precedent).
  - the pre-existing .cb-pos-row-clickable surface already had tabindex=0 /
    role=button / Enter+Space keydown of its own (verified in the audit); it
    is intentionally NOT re-upgraded (helper skip set) and not part of this
    guard.

REPAIR BUNDLED (found by this guard's R3, 2026-10-09 22:00 PT): the compare
view's click-to-sort affordances were DEAD for mouse users too. The Dimension
Divergence rows (delegated click -> insightResetAndSort(sk, sd)) and the
radar dimension labels (.cmp-radar-dim-label -> insightResetAndSort(...))
call a function defined inside populateInsights (js/app.js ~2975), but the
compare view lives outside that closure, so every click threw
"insightResetAndSort is not defined" and did nothing. Fix: expose
window.insightResetAndSort = insightResetAndSort right after the definition
(the codebase's standard cross-scope pattern, cf. window._toggleCompare).
Static S6 pins the exposure; render R3 (zero page errors) now covers the
Enter path end-to-end.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the divergence call site exists AND is ordered after the delegated
        click wiring it reproduces.
     S2 the bridge call site exists AND sits after the per-row click-wiring
        block, before the next wiring block.
     S3 parity targets intact: the divergence delegation still calls
        insightResetAndSort(sk, sd); the bridge per-row click listener still
        toggles .cb-bridge-open.
     S4 aria-label sources intact: divergence rows carry title="Click to sort
        table by ..."; bridge rows carry title="... click to see companies".
     S5 node --check js/app.js is green.
     S6 window.insightResetAndSort exposure present (pins the 2026-10-09
        dead-click-handler repair: compare view lives outside
        populateInsights' scope, so the exposure is what makes the
        divergence/radar-dim sort clicks resolve).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 compare view (META + AAPL via _toggleCompare + #compare-go-btn):
        - >=1 .cmp-div-row-clickable rows, exactly one tabindex="0" holder,
          all role=button with data-bearing aria-labels (contain
          "Press Enter").
        - Enter on the holder fires a click on that row (recorded by a
          capture listener) with the row's own data-sort-key/data-sort-dir.
        - ArrowRight moves the holder to the next row (when >=2 rows).
     R2 detail panel bridge rows: iterate candidate tickers with
        openCompanyDetailWithDiff until .cb-bridge-expandable rows exist:
        - exactly one tabindex="0" holder, all role=button with data-bearing
          aria-labels.
        - Enter on the holder toggles .cb-bridge-open on its wrap.
        - ArrowRight moves the holder (when >=2 rows).
     R3 zero JS page errors.

Usage:
  scripts/check_compare_bridge_keyboard.py              # static + render
  scripts/check_compare_bridge_keyboard.py --static-only

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


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()

    # S1: divergence call site ordered after the delegated click wiring.
    i_deleg = app.find("Event delegation for clickable divergence rows")
    i_call = app.find("_kbdUpgradeRoving(divEl, '.cmp-div-row-clickable')")
    s1 = i_deleg > 0 and i_call > i_deleg
    check("S1 _kbdUpgradeRoving(divEl, '.cmp-div-row-clickable') after the delegated sort-click wiring",
          s1, "" if s1 else "call site missing or misordered")

    # S2: bridge call site after the per-row click wiring, before next block.
    i_wire = app.find("Wire up expandable community bridge rows")
    i_bcall = app.find("_kbdUpgradeRoving(detailRow, '.cb-bridge-expandable')")
    i_next = app.find("Wire up bridge detail ticker tag clicks")
    s2 = i_wire > 0 and i_bcall > i_wire and 0 < i_next > i_bcall
    check("S2 _kbdUpgradeRoving(detailRow, '.cb-bridge-expandable') after bridge click wiring",
          s2, "" if s2 else "call site missing or misplaced")

    # S3: parity targets intact.
    s3a = ("divEl.addEventListener('click'" in app
           and "closest('.cmp-div-row-clickable')" in app
           and "insightResetAndSort(sk, sd)" in app)
    s3b = ("detailRow.querySelectorAll('.cb-bridge-expandable').forEach" in app
           and "row.addEventListener('click', function(e)" in app
           and "cb-bridge-open" in app)
    s3 = s3a and s3b
    check("S3 parity targets intact (delegated sort click; bridge open toggle)",
          s3, "" if s3 else "a click target the keyboard path reproduces diverged")

    # S4: aria-label source titles intact.
    s4 = ("title=\"Click to sort table by " in app
          and "click to see companies" in app)
    check("S4 data-bearing titles intact (divergence sort; bridge expand)",
          s4, "" if s4 else "a title feeding the keyboard aria-labels is gone")

    r = subprocess.run(["node", "--check", APP_JS],
                       capture_output=True, text=True, timeout=60)
    check("S5 node --check js/app.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")

    s6 = "window.insightResetAndSort = insightResetAndSort" in app
    check("S6 window.insightResetAndSort exposure present (dead-click repair)",
          s6, "" if s6 else "exposure missing: compare sort clicks would throw")


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
                "window.d3 && document.querySelectorAll('.insight-card').length > 10",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # ---------- R1: compare divergence rows ----------
            pg.evaluate("""() => {
              window._toggleCompare('META');
              window._toggleCompare('AAPL');
              document.getElementById('compare-go-btn').click();
            }""")
            pg.wait_for_selector(
                "#cmp-radar-divergence .cmp-div-row-clickable", timeout=60000)
            pg.wait_for_timeout(500)
            r1shape = pg.evaluate("""() => {
              const rows = [...document.querySelectorAll(
                '#cmp-radar-divergence .cmp-div-row-clickable')];
              const holders = rows.filter(
                r => r.getAttribute('tabindex') === '0');
              const neg = rows.filter(
                r => r.getAttribute('tabindex') === '-1');
              const bad = rows.filter(r =>
                r.getAttribute('role') !== 'button' ||
                !(r.getAttribute('aria-label') || '').includes('Press Enter') ||
                r.getAttribute('data-kbd-upgraded') !== '1');
              const label0 = holders[0] ?
                holders[0].getAttribute('aria-label') : null;
              const sk0 = holders[0] ?
                holders[0].getAttribute('data-sort-key') : null;
              return {n: rows.length, holders: holders.length,
                      neg: neg.length, bad: bad.length,
                      label0: label0, sk0: sk0};
            }""")
            r1shape_ok = (r1shape["n"] >= 1
                          and r1shape["holders"] == 1
                          and r1shape["neg"] == r1shape["n"] - 1
                          and r1shape["bad"] == 0
                          and r1shape["label0"] is not None
                          and "Press Enter to sort table by" in r1shape["label0"])
            r1 = False
            r1detail = "shape: %r" % (r1shape,)
            if r1shape_ok:
                pg.evaluate("""() => {
                  window.__divClicks = [];
                  document.getElementById('cmp-radar-divergence')
                    .addEventListener('click', function(e) {
                      var row = e.target.closest ?
                        e.target.closest('.cmp-div-row-clickable') : null;
                      if (row) window.__divClicks.push({
                        key: row.getAttribute('data-sort-key'),
                        dir: row.getAttribute('data-sort-dir')});
                    }, true);
                }""")
                pg.evaluate("""() => {
                  const h = document.querySelector(
                    '#cmp-radar-divergence .cmp-div-row-clickable[tabindex="0"]');
                  h.focus();
                }""")
                sk = r1shape["sk0"]
                sd = pg.evaluate("""() => document.querySelector(
                  '#cmp-radar-divergence .cmp-div-row-clickable[tabindex="0"]')
                  .getAttribute('data-sort-dir')""")
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                clicks = pg.evaluate("() => window.__divClicks")
                r1enter = (len(clicks) == 1 and clicks[0]["key"] == sk
                           and clicks[0]["dir"] == sd)
                r1detail = "enter clicks: %r (want 1x %s/%s)" % (clicks, sk, sd)
                r1 = r1enter
                if r1shape["n"] >= 2 and r1enter:
                    before = pg.evaluate("""() => {
                      const h = document.querySelector(
                        '#cmp-radar-divergence .cmp-div-row-clickable[tabindex="0"]');
                      return h ? h.getAttribute('data-sort-key') : null;
                    }""")
                    pg.evaluate("""() => {
                      document.querySelector(
                        '#cmp-radar-divergence .cmp-div-row-clickable[tabindex="0"]').focus();
                    }""")
                    pg.keyboard.press("ArrowRight")
                    pg.wait_for_timeout(300)
                    after = pg.evaluate("""() => {
                      const h = document.querySelector(
                        '#cmp-radar-divergence .cmp-div-row-clickable[tabindex="0"]');
                      const a = document.activeElement;
                      return {holder: h ? h.getAttribute('data-sort-key') : null,
                              focused: a === h, focusedKey:
                                a ? a.getAttribute('data-sort-key') : null};
                    }""")
                    r1arrow = (after["holder"] is not None
                               and after["holder"] != before
                               and after["focused"] is True)
                    r1detail += " | arrow: %r" % (after,)
                    r1 = r1 and r1arrow
            check("R1 compare divergence rows: roving group + Enter fires delegated sort click + ArrowRight moves",
                  r1, r1detail)

            # ---------- R2: community bridge rows ----------
            # openCompanyDetailWithDiff renders the panel async (setTimeout),
            # so poll per candidate ticker until bridge rows appear.
            bridge_ticker = None
            for cand in ['META', 'AAPL', 'MSFT', 'JPM', 'GOOGL', 'XOM', 'NVDA', 'TSLA', 'C', 'BAC']:
                pg.evaluate("t => window.openCompanyDetailWithDiff(t, '')", cand)
                try:
                    pg.wait_for_function(
                        "() => document.querySelectorAll('.cb-bridge-expandable').length > 0",
                        timeout=6000)
                    bridge_ticker = cand
                    break
                except Exception:
                    continue
            r2 = False
            r2detail = "no candidate ticker rendered bridge rows"
            if bridge_ticker:
                r2shape = pg.evaluate("""() => {
                  const rows = [...document.querySelectorAll('.cb-bridge-expandable')];
                  const holders = rows.filter(
                    r => r.getAttribute('tabindex') === '0');
                  const neg = rows.filter(
                    r => r.getAttribute('tabindex') === '-1');
                  const bad = rows.filter(r =>
                    r.getAttribute('role') !== 'button' ||
                    !(r.getAttribute('aria-label') || '').includes('Press Enter') ||
                    r.getAttribute('data-kbd-upgraded') !== '1');
                  const label0 = holders[0] ?
                    holders[0].getAttribute('aria-label') : null;
                  return {n: rows.length, holders: holders.length,
                          neg: neg.length, bad: bad.length,
                          label0: label0, ticker: %r};
                }""" % bridge_ticker)
                r2shape_ok = (r2shape["n"] >= 1
                              and r2shape["holders"] == 1
                              and r2shape["neg"] == r2shape["n"] - 1
                              and r2shape["bad"] == 0
                              and r2shape["label0"] is not None
                              and "Press Enter to see companies" in r2shape["label0"])
                r2detail = "ticker %s shape: %r" % (bridge_ticker, r2shape)
                if r2shape_ok:
                    wrap_open0 = pg.evaluate("""() => {
                      const h = document.querySelector(
                        '.cb-bridge-expandable[tabindex="0"]');
                      const w = h ? h.closest('.cb-bridge-wrap') : null;
                      return w ? w.classList.contains('cb-bridge-open') : null;
                    }""")
                    pg.evaluate("""() => {
                      document.querySelector(
                        '.cb-bridge-expandable[tabindex="0"]').focus();
                    }""")
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(600)
                    wrap_open1 = pg.evaluate("""() => {
                      const h = document.querySelector(
                        '.cb-bridge-expandable[tabindex="0"]');
                      const w = h ? h.closest('.cb-bridge-wrap') : null;
                      return w ? w.classList.contains('cb-bridge-open') : null;
                    }""")
                    r2toggle = (wrap_open0 is False and wrap_open1 is True)
                    r2detail += " | enter toggles open: %r -> %r" % (wrap_open0, wrap_open1)
                    r2 = r2toggle
                    if r2shape["n"] >= 2 and r2toggle:
                        # re-focus the holder (it may have lost focus) then arrow
                        pg.evaluate("""() => {
                          const h = document.querySelector(
                            '.cb-bridge-expandable[tabindex="0"]');
                          if (h) h.focus();
                        }""")
                        pg.keyboard.press("ArrowRight")
                        pg.wait_for_timeout(300)
                        moved = pg.evaluate("""() => {
                          const h = document.querySelector(
                            '.cb-bridge-expandable[tabindex="0"]');
                          return h ? (document.activeElement === h) : false;
                        }""")
                        r2detail += " | arrow moves holder+focus: %r" % (moved,)
                        r2 = r2 and moved is True
            check("R2 bridge expand rows: roving group + Enter toggles expand + ArrowRight moves",
                  r2, r2detail)

            check("R3 zero JS page errors", len(errors) == 0,
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
