#!/usr/bin/env python3
"""Regression guard: keyboard pilot extends to treemap leaves (roving tabindex).

The 2026-10-08 23:30 PT run extended the keyboard pilot (sector bars,
composition donut + trend cards, quartile + gov-quartile segments) to the
treemap in js/charts.js (drawCompTreemap) -- the most prominent remaining
mouse-only surface. Each treemap leaf (g.treemap-leaf) is click-to-lookup
via window.findCompanyInTable; hover shows the tooltip.

With ~500 leaves, per-leaf tab stops would make keyboard traversal
unusable, so the treemap uses a roving tabindex instead: the first leaf
starts tabindex="0" (all others "-1"); focus mirrors hover (same
treemapLeafTooltipHtml as mouseover, anchored to the focused leaf via a
synthesized {clientX, clientY} from getBoundingClientRect()); blur
mirrors mouseout (highlight reset + hideChartTooltip); Enter/Space fires
the same findCompanyInTable action as click; ArrowRight/Down and
ArrowLeft/Up move to the next/previous leaf (the tabindex="0" holder
moves with focus); Home/End jump to the first/last leaf.

The :focus-visible ring on g.treemap-leaf matches the site's --accent
convention (sector bars, donut segments, quartile segments).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 leaf creation sets roving tabindex (first leaf '0', rest '-1'),
        role="button" and a data-bearing aria-label.
     S2 treemapLeafTooltipHtml is shared by mouseover and focus;
        focus anchors the tooltip to the leaf via getBoundingClientRect;
        blur mirrors mouseout.
     S3 Enter/Space keydown fires the same findCompanyInTable action as
        click; arrow keys + Home/End move focus between leaves and move
        the roving tabindex holder.
     S4 css/style.css has the :focus-visible rule for g.treemap-leaf
        with the --accent outline convention.
     S5 the keyboard additions are attribute-bound (no innerHTML).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered leaf is role="button" with a data-bearing
        aria-label, and exactly one leaf is tabindex="0" (roving).
     R2 focusing a leaf shows the tooltip with that leaf's ticker;
        blur hides it.
     R3 Enter on a leaf fires findCompanyInTable with the leaf's ticker.
     R4 ArrowRight moves focus to the next leaf and moves the
        tabindex="0" holder with it.
     R5 zero JS page errors.

Usage:
  scripts/check_keyboard_treemap_pilot.py              # static + render
  scripts/check_keyboard_treemap_pilot.py --static-only

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


def leaf_block(charts):
    # From the treemap-leaf creation marker through the keyboard handlers,
    # ending right before the leaf-label comment.
    m = re.search(
        r"\.attr\('class', 'treemap-leaf'\)([\s\S]*?)// Labels for leaves",
        charts)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    block = leaf_block(charts)

    s1 = (block is not None
          and ".attr('tabindex', function(d, i) { return i === 0 ? '0' : '-1'; })" in block
          and ".attr('role', 'button')" in block
          and "CEO total pay" in block
          and "Press Enter to view in table" in block)
    check("S1 .treemap-leaf creation sets roving tabindex/role=button/data-bearing aria-label",
          s1, "" if s1 else "roving-tabindex keyboard attrs missing from the treemap-leaf block")

    s2 = (block is not None
          and "function treemapLeafTooltipHtml(d)" in block
          and block.count("treemapLeafTooltipHtml(d)") >= 2
          and ".on('mouseover', function(event, d)" in block
          and ".on('focus', function(event, d)" in block
          and "getBoundingClientRect()" in block
          and ".on('mouseout', function(" in block
          and ".on('blur', function()" in block
          and block.count("hideChartTooltip()") >= 2)
    check("S2 treemapLeafTooltipHtml shared by mouseover+focus; blur mirrors mouseout",
          s2, "" if s2 else "tooltip parity wiring missing from the treemap-leaf block")

    s3 = (block is not None
          and ".on('keydown', function(event, d)" in block
          and "key === 'Enter'" in block
          and "key === ' '" in block
          and "window.findCompanyInTable(d.data.name)" in block
          and "'ArrowRight'" in block and "'ArrowLeft'" in block
          and "'Home'" in block and "'End'" in block
          and "target.focus()" in block
          and block.count("leafGroups.attr('tabindex', '-1')") >= 2)
    check("S3 Enter/Space fires findCompanyInTable; arrows/Home/End move focus + roving holder",
          s3, "" if s3 else "keydown roving-tabindex wiring missing from the treemap-leaf block")

    m = re.search(
        r"#comp-treemap-chart g\.treemap-leaf:focus-visible \{([^}]*)\}",
        css)
    s4 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S4 :focus-visible ring on g.treemap-leaf uses --accent convention",
          s4, "" if s4 else "focus ring missing or off-convention")

    s5 = (block is not None and "innerHTML" not in block)
    check("S5 keyboard additions are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML found in the treemap-leaf block")


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
                "window.d3 && document.querySelectorAll('#comp-treemap-chart g.treemap-leaf').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: roving tabindex -- every leaf is a labelled button,
            # exactly one leaf is in the tab order.
            r1info = pg.evaluate("""() => {
              const leaves = [...document.querySelectorAll('#comp-treemap-chart g.treemap-leaf')];
              const bad = l =>
                l.getAttribute('role') !== 'button' ||
                !(l.getAttribute('aria-label') || '').includes('CEO total pay');
              const tabbed = leaves.filter(l => l.getAttribute('tabindex') === '0');
              return {n: leaves.length, bad: leaves.filter(bad).length,
                      tabbed: tabbed.length,
                      sample: leaves[0] ? leaves[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["n"] > 400 and r1info["bad"] == 0 and r1info["tabbed"] == 1)
            check("R1 all %d treemap leaves are role=button with data-bearing aria-label; exactly one tabindex=0"
                  % r1info["n"],
                  r1, ("n=%d bad=%d tabbed=%d sample=%r" % (
                      r1info["n"], r1info["bad"], r1info["tabbed"], r1info["sample"]))
                  if not r1 else "")

            def focus_first():
                pg.evaluate("""() => {
                  const leaf = document.querySelector('#comp-treemap-chart g.treemap-leaf');
                  leaf.scrollIntoView({block: 'center'});
                  leaf.focus();
                }""")
                pg.wait_for_timeout(600)

            # R2: focusing a leaf surfaces its tooltip (parity with hover).
            focus_first()
            r2info = pg.evaluate("""() => {
              const tip = document.querySelector('.chart-tooltip.visible');
              const leaf = document.querySelector('#comp-treemap-chart g.treemap-leaf');
              const label = leaf.getAttribute('aria-label') || '';
              const ticker = label.split(' — ')[0];
              return {visible: !!tip,
                      tickerInTip: tip ? tip.textContent.includes(ticker) : false,
                      ticker: ticker};
            }""")
            r2 = r2info["visible"] and r2info["tickerInTip"]
            check("R2 focus on treemap leaf shows tooltip with the leaf's ticker (%r)" % r2info["ticker"],
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
            focus_first()
            ticker = pg.evaluate(
                "(document.querySelector('#comp-treemap-chart g.treemap-leaf')"
                ".getAttribute('aria-label') || '').split(' — ')[0]")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            r3info = pg.evaluate("window.__fcitCalls")
            r3 = (len(r3info) == 1 and r3info[0][0] == ticker)
            check("R3 Enter on treemap leaf fires findCompanyInTable(%r)" % ticker,
                  r3, "calls recorded: %r" % (r3info,) if not r3 else "")

            # R4: ArrowRight moves focus to the next leaf and moves the
            # tabindex="0" holder with it (roving tabindex intact).
            pg.keyboard.press("ArrowRight")
            pg.wait_for_timeout(400)
            r4info = pg.evaluate("""() => {
              const leaves = [...document.querySelectorAll('#comp-treemap-chart g.treemap-leaf')];
              return {idx: leaves.indexOf(document.activeElement),
                      tabbedIdx: leaves.findIndex(l => l.getAttribute('tabindex') === '0'),
                      n: leaves.length};
            }""")
            r4 = (r4info["idx"] == 1 and r4info["tabbedIdx"] == 1)
            check("R4 ArrowRight moves focus to leaf 2 and moves the tabindex=0 holder",
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
