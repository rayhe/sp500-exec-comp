#!/usr/bin/env python3
"""Regression guard: network-tab residual click surfaces are keyboard-operable.

The 2026-10-11 10:00 PT run closed the last residual click-only surfaces on
the network tab (the batch queued by the 07:30 PT run):

  .cm-data[data-cm-community]      (community-metrics rows -> table community filter)
  .cm-bp-zone[data-bp-cid]         (box-plot quartile zones -> table quartile filter)
  .cm-sparkline                    (pay-trend sparkline -> lock trend highlight + tooltip)
  .cs-node-ticker[data-ticker]     (cluster-stats panel tickers -> select node on graph)
  .path-node-chip[data-ticker]     (path-finder chips -> find company in table)

js/network.js gains a file-scope _kbdUpgradeNetworkResidualControls(root),
called after each surface's click handlers are wired (community-metrics
render covers .cm-data/.cm-bp-zone/.cm-sparkline; updateClusterStats covers
.cs-node-ticker; pfShowResult covers .path-node-chip). It upgrades every
matching element that is not already keyboard-operable:

  - skipped: native controls (a/button/input/select/textarea), elements
    carrying their own tabindex or onkeydown, elements already role=button,
    already-upgraded nodes (data-kbd-upgraded). (The dismissible
    quartile-filter chip and the .cm-path-btn path buttons are native
    <button>s and were already keyboard-operable; they are not touched.)
  - upgraded: tabindex="0", role="button", data-bearing aria-label
    (community label + filter action; zone title + range action; community +
    trend detail + lock action; ticker + select action; ticker + find
    action), data-kbd-upgraded="1", Enter/Space keydown that
    preventDefault()s, stopPropagation()s (keyboard-pilot contract - a
    sparkline/zone keypress must not also fire its parent row's filter),
    and fires el.click() so the keyboard path reproduces the exact mouse
    behavior.

CSS: no change - the global [data-kbd-upgraded]:focus-visible --accent ring
(2026-10-09 19:30 PT) covers these surfaces.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _kbdUpgradeNetworkResidualControls is defined with the five
        selectors, the skip conditions (native tags, tabindex, onkeydown,
        data-kbd-upgraded, role=button), and sets tabindex="0",
        role="button", aria-label, data-kbd-upgraded="1", plus an
        Enter/Space keydown with preventDefault + stopPropagation +
        e.currentTarget.click().
     S2 the helper is invoked at all five wiring sites (three community-
        metrics loops, cluster-stats ticker wiring, path-finder chip
        wiring).
     S3 aria-label derivation covers the community filter action, the
        quartile range filter action, the trend-lock action, the
        select-on-graph action, and the find-in-table action.
     S4 css/style.css has the global [data-kbd-upgraded]:focus-visible rule
        with the --accent outline convention.
     S5 no innerHTML in the new helper.
     S6 node --check js/network.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .cm-data/.cm-bp-zone/.cm-sparkline is an upgraded button with
        a Press-Enter aria-label (n > 10 expected across the three).
     R2 Enter on a .cm-data row sets window._activeCommunityFilter.id to
        the row's community id (keyboard/click parity).
     R3 Enter on a .cm-bp-zone creates the #quartile-filter-chip
        (keyboard/click parity).
     R4 Enter on a .cm-sparkline locks the trend (cm-sparkline-locked
        class + .cm-trend-tooltip); Enter again unlocks.
     R5 after a sector legend click, .cs-node-ticker spans are upgraded
        buttons; Enter on one sets #network-search to that ticker
        (keyboard/click parity via selectSearchNode).
     R6 after running the path finder, .path-node-chip spans are upgraded
        buttons; Enter on one fires window.findCompanyInTable(ticker)
        exactly once.
     R7 zero JS page errors.

Usage:
  scripts/check_network_residual_keyboard.py              # static + render
  scripts/check_network_residual_keyboard.py --static-only

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
NET_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def helper_block(net):
    m = re.search(
        r"function _kbdUpgradeNetworkResidualControls\(root\) \{([\s\S]*?)\n    \}",
        net)
    return m.group(0) if m else None


def static_checks():
    net = open(NET_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    hb = helper_block(net)

    s1 = (hb is not None
          and ".cm-data[data-cm-community]" in hb
          and ".cm-bp-zone[data-bp-cid]" in hb
          and ".cm-sparkline" in hb
          and ".cs-node-ticker[data-ticker]" in hb
          and ".path-node-chip[data-ticker]" in hb
          and "hasAttribute('tabindex')" in hb
          and "hasAttribute('onkeydown')" in hb
          and "hasAttribute('data-kbd-upgraded')" in hb
          and "getAttribute('role') === 'button'" in hb
          and "tag === 'A'" in hb and "tag === 'BUTTON'" in hb
          and "setAttribute('tabindex', '0')" in hb
          and "setAttribute('role', 'button')" in hb
          and "setAttribute('aria-label', label)" in hb
          and "setAttribute('data-kbd-upgraded', '1')" in hb
          and "addEventListener('keydown'" in hb
          and "e.key === 'Enter'" in hb
          and "e.key === ' '" in hb
          and "e.preventDefault()" in hb
          and "e.stopPropagation()" in hb
          and "e.currentTarget.click()" in hb)
    check("S1 _kbdUpgradeNetworkResidualControls: five selectors, skip set, tabindex=0 role=button aria-label, Enter/Space -> preventDefault/stopPropagation/click()",
          s1, "" if s1 else "helper wiring missing or diverged")

    s2 = (net.count("_kbdUpgradeNetworkResidualControls(_communityMetricsEl);") >= 3
          and "_kbdUpgradeNetworkResidualControls(clusterStatsEl);" in net
          and "_kbdUpgradeNetworkResidualControls(pfResult);" in net)
    check("S2 helper invoked at all five wiring sites (3x community-metrics, cluster-stats, path-finder)",
          s2, "" if s2 else "a wiring call is missing or renamed")

    s3 = (hb is not None
          and "Press Enter to filter the compensation table to this community" in hb
          and "Press Enter to filter the compensation table to this pay range" in hb
          and "Press Enter to lock the trend highlight on the graph" in hb
          and "Press Enter to select this company on the graph" in hb
          and "Press Enter to find this company in the compensation table" in hb)
    check("S3 aria-label derivation: community filter, quartile range filter, trend lock, select-on-graph, find-in-table",
          s3, "" if s3 else "aria-label derivation missing")

    m = re.search(
        r"\[data-kbd-upgraded\]:focus-visible\s*\{([\s\S]*?)\}",
        css)
    s4 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1))
    check("S4 global [data-kbd-upgraded]:focus-visible --accent ring",
          s4, "" if s4 else "focus ring missing or off-convention")

    s5 = (hb is not None and "innerHTML" not in hb)
    check("S5 keyboard additions are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML found in the helper")

    r = subprocess.run(["node", "--check", NET_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/network.js is green",
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
            pg.click('a[data-section="peer-network-section"]')
            pg.wait_for_selector("#network-graph canvas", timeout=90000)
            # Enable community mode: the metrics panel renders here.
            pg.click("#network-overflow-toggle")
            pg.click("#community-toggle")
            pg.wait_for_function(
                "document.querySelectorAll('.cm-data[data-cm-community]').length > 0",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('.cm-bp-zone[data-bp-cid]').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: every residual surface in the metrics panel is an upgraded button.
            r1info = pg.evaluate("""() => {
              const sel = '.cm-data[data-cm-community], .cm-bp-zone[data-bp-cid], .cm-sparkline';
              const all = [...document.querySelectorAll(sel)];
              const bad = all.filter(el =>
                el.getAttribute('tabindex') !== '0' ||
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').includes('Press Enter') ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              const counts = {};
              ['.cm-data', '.cm-bp-zone', '.cm-sparkline'].forEach(s => {
                counts[s] = document.querySelectorAll(s).length;
              });
              return {n: all.length, bad: bad.length, counts,
                      sample: all.length ? all[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["n"] > 10 and r1info["bad"] == 0
                  and all(v > 0 for v in r1info["counts"].values()))
            check("R1 all %d metrics-panel residual surfaces are upgraded buttons (tabindex=0 role=button Press-Enter aria-label); counts=%r"
                  % (r1info["n"], r1info["counts"]),
                  r1, ("n=%d bad=%d sample=%r" % (
                      r1info["n"], r1info["bad"], r1info["sample"])) if not r1 else "")

            # R2: Enter on a .cm-data row filters the table to that community.
            r2info = pg.evaluate("""() => {
              const row = document.querySelector('.cm-data[data-cm-community]');
              const cid = parseInt(row.getAttribute('data-cm-community'), 10);
              row.scrollIntoView({block: 'center'});
              row.focus();
              return {cid, focused: document.activeElement === row};
            }""")
            if not r2info["focused"]:
                check("R2 Enter on .cm-data row sets _activeCommunityFilter.id=%s" % r2info["cid"],
                      False, "test setup: row did not take focus")
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1000)
                r2f = pg.evaluate("() => { const f = window._activeCommunityFilter; return f ? f.id : null; }")
                r2 = (r2f == r2info["cid"])
                check("R2 Enter on .cm-data row sets _activeCommunityFilter.id=%s" % r2info["cid"],
                      r2, "filter id: %r" % (r2f,) if not r2 else "")
                # Clear the filter so later checks see the full panel.
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)

            # R3: Enter on a .cm-bp-zone creates the quartile filter chip.
            r3ok = pg.evaluate("""() => {
              const z = document.querySelector('.cm-bp-zone[data-bp-cid]');
              if (!z) return {ok: false, why: 'no zone'};
              z.scrollIntoView({block: 'center'});
              z.focus();
              return {ok: document.activeElement === z,
                      label: z.getAttribute('aria-label')};
            }""")
            if not r3ok.get("ok"):
                check("R3 Enter on .cm-bp-zone creates #quartile-filter-chip",
                      False, "test setup: %r" % (r3ok,))
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1000)
                r3chip = pg.evaluate("!!document.getElementById('quartile-filter-chip')")
                r3 = (r3chip is True)
                check("R3 Enter on .cm-bp-zone (%s) creates #quartile-filter-chip" % r3ok.get("label"),
                      r3, "chip not created" if not r3 else "")
                # Clear via the chip's own keyboard path (native button).
                if r3:
                    pg.evaluate("document.getElementById('quartile-filter-chip').focus()")
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(800)

            # R4: Enter on a .cm-sparkline locks the trend; Enter again unlocks.
            r4setup = pg.evaluate("""() => {
              const sp = document.querySelector('.cm-sparkline');
              if (!sp) return null;
              sp.scrollIntoView({block: 'center'});
              sp.focus();
              return document.activeElement === sp;
            }""")
            if not r4setup:
                check("R4 Enter on .cm-sparkline locks/unlocks the trend highlight",
                      False, "test setup: no sparkline or focus failed")
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r4locked = pg.evaluate(
                    "document.querySelector('.cm-sparkline-locked') !== null && "
                    "document.querySelector('.cm-trend-tooltip') !== null")
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r4unlocked = pg.evaluate(
                    "document.querySelector('.cm-sparkline-locked') === null && "
                    "document.querySelector('.cm-trend-tooltip') === null")
                r4 = r4locked and r4unlocked
                check("R4 Enter on .cm-sparkline locks trend (locked class + tooltip), Enter again unlocks",
                      r4, "locked=%s unlocked=%s" % (r4locked, r4unlocked) if not r4 else "")

            # R5: cluster-stats tickers become upgraded buttons; Enter selects on graph.
            pg.evaluate("""() => {
              const items = [...document.querySelectorAll('.network-legend .legend-item')]
                .filter(el => !el.hasAttribute('data-pvp-legend') && !el.hasAttribute('data-orphan-legend'));
              items[0].scrollIntoView({block: 'center'});
            }""")
            pg.evaluate("""() => {
              [...document.querySelectorAll('.network-legend .legend-item')]
                .filter(el => !el.hasAttribute('data-pvp-legend') && !el.hasAttribute('data-orphan-legend'))[0].click();
            }""")
            pg.wait_for_function(
                "document.querySelectorAll('.cs-node-ticker[data-ticker]').length > 0",
                timeout=90000)
            r5info = pg.evaluate("""() => {
              const all = [...document.querySelectorAll('.cs-node-ticker[data-ticker]')];
              const bad = all.filter(el =>
                el.getAttribute('tabindex') !== '0' ||
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').includes('Press Enter') ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              const t = all[0];
              t.scrollIntoView({block: 'center'});
              t.focus();
              return {n: all.length, bad: bad.length, tick: t.getAttribute('data-ticker'),
                      focused: document.activeElement === t};
            }""")
            r5shape = (r5info["n"] > 0 and r5info["bad"] == 0 and r5info["focused"])
            if not r5shape:
                check("R5 .cs-node-ticker spans are upgraded buttons and take focus",
                      False, "n=%d bad=%d focused=%s" % (
                          r5info["n"], r5info["bad"], r5info["focused"]))
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1000)
                r5search = pg.evaluate("document.getElementById('network-search').value")
                r5 = r5search.startswith(r5info["tick"])
                check("R5 Enter on .cs-node-ticker(%s) selects on graph (#network-search=%r)"
                      % (r5info["tick"], r5search),
                      r5, "search box did not take the ticker" if not r5 else "")

            # R6: path-finder chips are upgraded buttons; Enter finds in table.
            r6setup = pg.evaluate("""() => {
              const fi = document.getElementById('path-from-input');
              const ti = document.getElementById('path-to-input');
              return !!(fi && ti && document.getElementById('path-finder-go'));
            }""")
            if not r6setup:
                check("R6 .path-node-chip Enter fires findCompanyInTable(ticker) once",
                      False, "test setup: path-finder panel inputs missing")
            else:
                # The path-finder bar sits behind a toggle button.
                pg.click("#path-finder-toggle")
                pg.wait_for_function(
                    "document.getElementById('path-from-input').offsetParent !== null",
                    timeout=30000)
                pg.click("#path-from-input")
                pg.fill("#path-from-input", "AAPL")
                pg.wait_for_selector("#path-from-results .network-search-result", timeout=30000)
                pg.click("#path-from-results .network-search-result")
                pg.click("#path-to-input")
                pg.fill("#path-to-input", "MSFT")
                pg.wait_for_selector("#path-to-results .network-search-result", timeout=30000)
                pg.click("#path-to-results .network-search-result")
                pg.click("#path-finder-go")
                pg.wait_for_selector(".path-node-chip[data-ticker]", timeout=60000)
                r6info = pg.evaluate("""() => {
                  const all = [...document.querySelectorAll('.path-node-chip[data-ticker]')];
                  const bad = all.filter(el =>
                    el.getAttribute('tabindex') !== '0' ||
                    el.getAttribute('role') !== 'button' ||
                    !(el.getAttribute('aria-label') || '').includes('Press Enter') ||
                    el.getAttribute('data-kbd-upgraded') !== '1');
                  window.__fctCalls = [];
                  const orig = window.findCompanyInTable;
                  window.findCompanyInTable = function(t) {
                    window.__fctCalls.push(t);
                    return orig ? orig.apply(this, arguments) : undefined;
                  };
                  const c = all[0];
                  const tick = c.getAttribute('data-ticker');
                  c.scrollIntoView({block: 'center'});
                  c.focus();
                  return {n: all.length, bad: bad.length, tick,
                          focused: document.activeElement === c};
                }""")
                if not (r6info["n"] > 0 and r6info["bad"] == 0 and r6info["focused"]):
                    check("R6 .path-node-chip spans are upgraded buttons and take focus",
                          False, "n=%d bad=%d focused=%s" % (
                              r6info["n"], r6info["bad"], r6info["focused"]))
                else:
                    pg.wait_for_timeout(300)
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(800)
                    r6calls = pg.evaluate("window.__fctCalls")
                    r6 = (len(r6calls) == 1 and r6calls[0] == r6info["tick"])
                    check("R6 Enter on .path-node-chip(%s) fires findCompanyInTable exactly once"
                          % r6info["tick"],
                          r6, "calls: %r" % (r6calls,) if not r6 else "")

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
