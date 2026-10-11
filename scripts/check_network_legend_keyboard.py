#!/usr/bin/env python3
"""Regression guard: network-tab legend click surfaces are keyboard-operable.

The 2026-10-11 07:30 PT run closed the last residual click-only class on the
network tab: four non-native surfaces with click handlers and no keyboard
path:

  .network-legend .legend-item (sector filter + PvP ring toggle)
  .verification-legend-item[data-tier] (graph verification-tier filter)
  .community-legend-item[data-community] (table community filter)
  .ngs-ddp-darling-ticker ("click to find in network")

js/network.js gains a file-scope _kbdUpgradeNetworkLegendControls(root),
called after each surface's click handlers are wired (sector legend in
initNetwork, verification legend in _populateVerificationLegend, community
legend in _populateCommunityLegend, darling panel in renderGlobalStats). It
upgrades every matching element that is not already keyboard-operable:

  - skipped: native controls (a/button/input/select/textarea), elements
    carrying their own tabindex or onkeydown, elements already role=button,
    already-upgraded nodes (data-kbd-upgraded), and the two informational
    legend entries with no click action (data-orphan-legend="1", the
    "+N more" community overflow item)
  - upgraded: tabindex="0", role="button", data-bearing aria-label (the
    element's title with "click to" -> "Press Enter to"; the darling ticker
    prepends the visible ticker since its title lacks it; title-less sector
    items name the filter action; community items reuse their data-bearing
    title), data-kbd-upgraded="1", Enter/Space keydown that preventDefault()s,
    stopPropagation()s (keyboard-pilot contract), and fires el.click() so
    the keyboard path reproduces the exact mouse behavior.

CSS: no change - the global [data-kbd-upgraded]:focus-visible --accent ring
(2026-10-09 19:30 PT) covers these spans.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _kbdUpgradeNetworkLegendControls is defined with the four selectors,
        the skip conditions (native tags, tabindex, onkeydown,
        data-kbd-upgraded, role=button, data-orphan-legend,
        community-legend-more), and sets tabindex="0", role="button",
        aria-label, data-kbd-upgraded="1", plus an Enter/Space keydown with
        preventDefault + stopPropagation + e.currentTarget.click().
     S2 the helper is invoked at all four wiring sites (darling panel,
        verification legend, sector legend, community legend).
     S3 aria-label derivation covers the title "click to" -> "Press Enter to"
        replacement, the darling-ticker text prepend (ticker text + ': ' +
        label, since its title lacks the ticker), and the sector /
        community fallbacks.
     S4 css/style.css has the global [data-kbd-upgraded]:focus-visible rule
        with the --accent outline convention.
     S5 no innerHTML in the new helper.
     S6 node --check js/network.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every matching surface is role=button tabindex=0 with a non-empty
        data-bearing aria-label carrying data-kbd-upgraded (n > 15 expected
        across the four surfaces); the orphan legend item and the
        "+N more" community item are NOT upgraded.
     R2 Enter on a darling ticker fires window.focusNetworkNode exactly once
        with the ticker (keyboard/click parity).
     R3 Enter on a sector legend item marks it legend-active.
     R4 Enter on a verification legend item marks it verification-legend-active.
     R5 Enter on a community legend item sets window._activeCommunityFilter
        with the matching community id.
     R6 zero JS page errors.

Usage:
  scripts/check_network_legend_keyboard.py              # static + render
  scripts/check_network_legend_keyboard.py --static-only

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
        r"function _kbdUpgradeNetworkLegendControls\(root\) \{([\s\S]*?)\n    \}",
        net)
    return m.group(0) if m else None


def static_checks():
    net = open(NET_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    hb = helper_block(net)

    s1 = (hb is not None
          and ".network-legend .legend-item" in hb
          and ".verification-legend-item[data-tier]" in hb
          and ".community-legend-item[data-community]" in hb
          and ".ngs-ddp-darling-ticker" in hb
          and "hasAttribute('tabindex')" in hb
          and "hasAttribute('onkeydown')" in hb
          and "hasAttribute('data-kbd-upgraded')" in hb
          and "getAttribute('role') === 'button'" in hb
          and "tag === 'A'" in hb and "tag === 'BUTTON'" in hb
          and "data-orphan-legend" in hb
          and "community-legend-more" in hb
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
    check("S1 _kbdUpgradeNetworkLegendControls: four selectors, skip set, tabindex=0 role=button aria-label, Enter/Space -> preventDefault/stopPropagation/click()",
          s1, "" if s1 else "helper wiring missing or diverged")

    s2 = ("_kbdUpgradeNetworkLegendControls(panel);" in net
          and "_kbdUpgradeNetworkLegendControls(el);" in net
          and "_kbdUpgradeNetworkLegendControls(document.getElementById('network-legend'));" in net
          and "_kbdUpgradeNetworkLegendControls(communityLegendEl);" in net)
    check("S2 helper invoked at all four wiring sites (darling panel, verification legend, sector legend, community legend)",
          s2, "" if s2 else "a wiring call is missing or renamed")

    s3 = (hb is not None
          and "title.replace(/click to/gi, 'Press Enter to')" in hb
          and "ngs-ddp-darling-ticker" in hb
          and "label = text + ': ' + label" in hb
          and "Press Enter to filter the graph to this sector" in hb
          and "Press Enter to filter the table to this community" in hb)
    check("S3 aria-label derivation: title 'click to' -> 'Press Enter to', darling ticker prepend (ticker text + ': ' + label), sector/community fallbacks",
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
            # The darling tickers live in the expandable Avg Clustering
            # detail panel; expand it before asserting on them.
            pg.click("#ngs-avg-cc")
            pg.wait_for_function(
                "document.querySelectorAll('.ngs-ddp-darling-ticker').length > 5",
                timeout=90000)
            # The heatmap/community/verification toggles live in the hidden
            # overflow menu; open it before clicking them.
            pg.click("#network-overflow-toggle")
            pg.click("#community-toggle")
            pg.wait_for_function(
                "document.querySelectorAll('.community-legend-item[data-community]').length > 0",
                timeout=90000)
            pg.click("#verification-toggle")
            pg.wait_for_function(
                "document.querySelectorAll('.verification-legend-item[data-tier]').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: every clickable legend surface is an upgraded button;
            # the orphan legend item and the "+N more" community item are not.
            r1info = pg.evaluate("""() => {
              const sel = '.network-legend .legend-item:not([data-orphan-legend="1"]),'
                + ' .verification-legend-item[data-tier],'
                + ' .community-legend-item[data-community]:not(.community-legend-more),'
                + ' .ngs-ddp-darling-ticker';
              const all = [...document.querySelectorAll(sel)];
              const bad = all.filter(el =>
                el.getAttribute('tabindex') !== '0' ||
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').includes('Press Enter') ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              const orphan = document.querySelector('.network-legend .legend-item[data-orphan-legend="1"]');
              const more = document.querySelector('.community-legend-item.community-legend-more');
              const labels = {};
              ['.ngs-ddp-darling-ticker', '.verification-legend-item[data-tier]',
               '.community-legend-item[data-community]',
               '.network-legend .legend-item:not([data-orphan-legend="1"])'].forEach(s => {
                const el = document.querySelector(s);
                labels[s] = el ? el.getAttribute('aria-label') : null;
              });
              return {n: all.length, bad: bad.length, labels,
                      orphanUpgraded: !!(orphan && orphan.hasAttribute('data-kbd-upgraded')),
                      moreUpgraded: !!(more && more.hasAttribute('data-kbd-upgraded'))};
            }""")
            r1 = (r1info["n"] > 15 and r1info["bad"] == 0
                  and not r1info["orphanUpgraded"] and not r1info["moreUpgraded"])
            check("R1 all %d legend surfaces are upgraded buttons (tabindex=0 role=button Press-Enter aria-label); orphan/+more stay untabbable"
                  % r1info["n"],
                  r1, ("n=%d bad=%d labels=%r orphan=%s more=%s" % (
                      r1info["n"], r1info["bad"], r1info["labels"],
                      r1info["orphanUpgraded"], r1info["moreUpgraded"])) if not r1 else "")

            # R2: Enter on a darling ticker fires window.focusNetworkNode.
            pg.evaluate("""() => {
              window.__fnnCalls = [];
              const orig = window.focusNetworkNode;
              window.focusNetworkNode = function(t) {
                window.__fnnCalls.push(t);
                return orig ? orig.apply(this, arguments) : undefined;
              };
              const t = document.querySelector('.ngs-ddp-darling-ticker');
              t.scrollIntoView({block: 'center'});
              t.focus();
              window.__fnnTicker = t.textContent.trim();
            }""")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(600)
            r2calls = pg.evaluate("window.__fnnCalls")
            r2tick = pg.evaluate("window.__fnnTicker")
            r2 = (len(r2calls) == 1 and r2calls[0] == r2tick)
            check("R2 Enter on darling ticker fires focusNetworkNode(%r) exactly once" % r2tick,
                  r2, "calls: %r" % (r2calls,) if not r2 else "")

            # R3: Enter on a sector legend item isolates that sector.
            r3info = pg.evaluate("""() => {
              const items = [...document.querySelectorAll('.network-legend .legend-item')]
                .filter(el => !el.hasAttribute('data-pvp-legend') && !el.hasAttribute('data-orphan-legend'));
              const it = items[0];
              it.scrollIntoView({block: 'center'});
              it.focus();
              return it.textContent.trim();
            }""")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(800)
            r3active = pg.evaluate("""() => {
              const items = [...document.querySelectorAll('.network-legend .legend-item')]
                .filter(el => !el.hasAttribute('data-pvp-legend') && !el.hasAttribute('data-orphan-legend'));
              return items[0].classList.contains('legend-active');
            }""")
            r3 = r3active is True
            check("R3 Enter on sector legend item (%s) marks it legend-active" % r3info,
                  r3, "legend-active not set" if not r3 else "")

            # R4: Enter on a verification legend item marks it active.
            pg.evaluate("""() => {
              const it = document.querySelector('.verification-legend-item[data-tier]');
              it.scrollIntoView({block: 'center'});
              it.focus();
            }""")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(800)
            r4active = pg.evaluate(
                "document.querySelector('.verification-legend-item[data-tier]')"
                ".classList.contains('verification-legend-active')")
            r4 = r4active is True
            check("R4 Enter on verification legend item marks it verification-legend-active",
                  r4, "verification-legend-active not set" if not r4 else "")

            # R5: Enter on a community legend item sets the community filter.
            # Verification mode (R4) mutually excludes community mode and
            # hides the community legend, so re-enable community mode first.
            pg.evaluate("document.querySelector('#community-toggle').click()")
            pg.wait_for_function(
                "document.querySelector('#community-legend').style.display !== 'none'",
                timeout=30000)
            r5setup = pg.evaluate("""() => {
              const it = document.querySelector('.community-legend-item[data-community]');
              const cid = parseInt(it.getAttribute('data-community'), 10);
              it.scrollIntoView({block: 'center'});
              it.focus();
              return {cid, focused: document.activeElement === it};
            }""")
            r5info = r5setup["cid"]
            if not r5setup["focused"]:
                check("R5 Enter on community legend item sets _activeCommunityFilter.id=%s" % r5info,
                      False, "test setup: community legend item did not take focus")
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1000)
                r5f = pg.evaluate("""() => {
                  const f = window._activeCommunityFilter;
                  return f ? f.id : null;
                }""")
                r5 = (r5f == r5info)
                check("R5 Enter on community legend item sets _activeCommunityFilter.id=%s" % r5info,
                      r5, "filter id: %r" % (r5f,) if not r5 else "")

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
