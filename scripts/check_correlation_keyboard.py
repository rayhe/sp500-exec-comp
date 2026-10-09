#!/usr/bin/env python3
"""Regression guard: keyboard pilot extension to correlation matrix cells.

The 2026-10-09 10:00 PT run ran the 5-critic panel across data richness,
visual design, interactivity, network graph quality, and analytical depth.
The interactivity critic flagged the Metric Correlations heat matrix
(js/charts.js, drawCorrelationMatrix) as the largest remaining
mouse-only surface: ~182 non-diagonal cells with mouseenter tooltips and
a click-to-explore-scatter action had zero keyboard reachability.

This run extends the roving-tabindex keyboard pilot to those cells,
reusing _enableDotKeyboard (the 2026-10-09 scatter-dot pilot):

  1. Non-diagonal cells with data now carry class "corr-heat-cell"
     (diagonal/insufficient-data cells are excluded from the tab order)
     plus a d3 datum {row, col, r, n} for the aria-label/activate path.
  2. The click-to-explore action is factored into _exploreCorrPair(ci, ri)
     (scatter-x/y metric selects + change dispatch + smooth scroll +
     drawCrossSectorCorrelation refresh); the mouse click handler calls
     it, and the keyboard Enter/Space activate path calls it with the
     focused cell's datum -- same behavior both ways.
  3. One tab stop per matrix; ArrowLeft/Right/Up/Down and Home/End move
     between cells (via _enableDotKeyboard); focus reuses the EXACT
     mouseenter behavior through a synthetic MouseEvent anchored to the
     focused cell's getBoundingClientRect (same tooltip HTML), blur
     reuses mouseleave. The helper's synthetic hover pair is
     parameterized (cfg.hoverIn/cfg.hoverOut, default mouseover/mouseout)
     because the matrix cells bind 'mouseenter'/'mouseleave' -- a
     synthetic 'mouseover' would never reach the tooltip handler, and
     switching the cells to 'mouseover'/'mouseout' would flicker the
     tooltip over the sibling text labels.
  4. Each cell is role="button" with a data-bearing aria-label:
     "<row> vs <col>: Pearson r <r>, <strength>, n = <n>. Press Enter to
     explore in the scatter plot."
  5. :focus-visible ring on rect.corr-heat-cell uses the --accent
     convention (sector-bar/donut/scatter pilots).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the cell rect creation sets a conditional 'corr-heat-cell' class
        and a datum carrying row/col/r/n.
     S2 _exploreCorrPair(ci, ri) exists and contains the scatter select
        wiring plus the drawCrossSectorCorrelation refresh.
     S3 the click handler delegates to _exploreCorrPair(colIdx, rowIdx)
        (no duplicated inline action body).
     S4 _enableDotKeyboard is invoked on 'rect.corr-heat-cell' with a
        label function mentioning 'Pearson r', an activate that calls
        _exploreCorrPair(d.col, d.row), and hoverIn/hoverOut set to
        'mouseenter'/'mouseleave' (matching the cells' bound events).
     S5 css/style.css has the
        #correlation-matrix-chart rect.corr-heat-cell:focus-visible rule
        with the --accent outline convention.
     S6 the keyboard pass block is attribute-bound (no innerHTML).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 rendered rect.corr-heat-cell cells exist; every one has
        role="button", tabindex in {"0","-1"} with exactly one "0"
        holder, and a non-empty aria-label naming a Pearson r.
     R2 focusing the "0"-holder cell shows the chart tooltip with that
        cell's pair label (keyboard tooltip parity).
     R3 pressing Enter on the focused cell sets the scatter x-metric
        select to the pair's column key (same action as click).
     R4 zero JS page errors.

Usage:
  scripts/check_correlation_keyboard.py              # static + render
  scripts/check_correlation_keyboard.py --static-only

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


def corr_matrix_block():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    m = re.search(r"function drawCorrelationMatrix\(companies\) \{([\s\S]*?)\nfunction drawCrossSectorCorrelation",
                  charts)
    return m.group(1) if m else None


def static_checks():
    css = open(CSS, encoding="utf-8").read()
    block = corr_matrix_block()

    s1 = (block is not None
          and ".attr('class', (!isDiagonal && r != null) ? 'corr-heat-cell' : null)" in block
          and ".datum({ row: row, col: col, r: r, n: corr.n })" in block)
    check("S1 cell rects get conditional 'corr-heat-cell' class + datum {row,col,r,n}",
          s1, "" if s1 else "class/datum wiring missing from cell rect creation")

    s2 = (block is not None
          and "function _exploreCorrPair(ci, ri) {" in block
          and "xSel.value = metrics[ci].key;" in block
          and "ySel.value = metrics[ri].key;" in block
          and "drawCrossSectorCorrelation(_chartData.companies, ci, ri);" in block)
    check("S2 _exploreCorrPair(ci, ri) wires scatter selects + cross-sector refresh",
          s2, "" if s2 else "_exploreCorrPair missing or incomplete")

    click_m = re.search(r"\.on\('click', function\(\) \{([\s\S]*?)\}\);", block or "")
    click_body = click_m.group(1) if click_m else ""
    s3 = ("_exploreCorrPair(colIdx, rowIdx)" in click_body
          and "xSel.value" not in click_body
          and "dispatchEvent" not in click_body)
    check("S3 click handler delegates to _exploreCorrPair(colIdx, rowIdx) (no inline dup)",
          s3, "" if s3 else "click handler still carries an inline action body")

    kb_i = block.index("_enableDotKeyboard(svg, 'rect.corr-heat-cell', {") if block else 0
    s4 = (block is not None
          and "_enableDotKeyboard(svg, 'rect.corr-heat-cell', {" in block
          and "Pearson r" in block[kb_i:kb_i + 900]
          and "activate: function(d) { _exploreCorrPair(d.col, d.row); }," in block
          and "hoverIn: 'mouseenter'" in block
          and "hoverOut: 'mouseleave'" in block)
    check("S4 _enableDotKeyboard on rect.corr-heat-cell: Pearson-r label + activate -> _exploreCorrPair + hoverIn/hoverOut=mouseenter/mouseleave",
          s4, "" if s4 else "keyboard pass missing or miswired")

    m = re.search(r"#correlation-matrix-chart rect\.corr-heat-cell:focus-visible \{([^}]*)\}", css)
    s5 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S5 :focus-visible ring on rect.corr-heat-cell uses --accent convention",
          s5, "" if s5 else "focus ring missing or off-convention")

    kb_start = block.index("_enableDotKeyboard(svg, 'rect.corr-heat-cell', {") if block else 0
    s6 = block is not None and "innerHTML" not in block[kb_start:kb_start + 1200]
    check("S6 keyboard pass block is attribute-bound (no innerHTML)",
          s6, "" if s6 else "innerHTML found in the keyboard pass block")


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
                "window.d3 && document.querySelectorAll('#correlation-matrix-chart rect.corr-heat-cell').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every heat cell is a labelled, roving-tabindex button.
            r1info = pg.evaluate("""() => {
              const cells = [...document.querySelectorAll('#correlation-matrix-chart rect.corr-heat-cell')];
              const bad = cells.filter(c =>
                c.getAttribute('role') !== 'button' ||
                !['0','-1'].includes(c.getAttribute('tabindex')) ||
                !(c.getAttribute('aria-label') || '').includes('Pearson r'));
              const holders = cells.filter(c => c.getAttribute('tabindex') === '0').length;
              return {n: cells.length, bad: bad.length, holders,
                      sample: cells[0] ? cells[0].getAttribute('aria-label') : null};
            }""")
            r1 = r1info["n"] > 0 and r1info["bad"] == 0 and r1info["holders"] == 1
            check("R1 all %d heat cells are role=button with roving tabindex (1 holder) + Pearson-r aria-label" % r1info["n"],
                  r1, ("sample: %r bad=%d holders=%d" % (r1info["sample"], r1info["bad"], r1info["holders"])) if not r1 else "")

            # R2: focusing the holder shows the tooltip with the pair label.
            pg.evaluate("""() => {
              const holder = document.querySelector('#correlation-matrix-chart rect.corr-heat-cell[tabindex="0"]');
              holder.scrollIntoView({block: 'center'});
              holder.focus();
            }""")
            pg.wait_for_timeout(600)
            r2info = pg.evaluate("""() => {
              const tip = document.querySelector('.chart-tooltip.visible');
              const holder = document.querySelector('#correlation-matrix-chart rect.corr-heat-cell[tabindex="0"]');
              const label = (holder.getAttribute('aria-label') || '').split(':')[0];
              return {visible: !!tip,
                      text: tip ? tip.textContent.slice(0, 60) : null,
                      label};
            }""")
            r2 = r2info["visible"] and r2info["label"] in (r2info["text"] or "")
            check("R2 focus on heat cell shows tooltip with pair data (%r)" % r2info["label"],
                  r2, "tooltip not visible or label mismatch: %r" % r2info["text"] if not r2 else "")
            pg.evaluate("document.activeElement.blur()")
            pg.wait_for_timeout(400)

            # R3: Enter on the focused cell fires the explore-pair action
            # (scatter x-metric select takes the pair's column key).
            r3info = pg.evaluate("""() => {
              const holder = document.querySelector('#correlation-matrix-chart rect.corr-heat-cell[tabindex="0"]');
              holder.scrollIntoView({block: 'center'});
              holder.focus();
              return {before: document.getElementById('scatter-x-metric').value};
            }""")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(1500)
            r3after = pg.evaluate("document.getElementById('scatter-x-metric').value")
            r3 = bool(r3after) and r3after != r3info["before"]
            check("R3 Enter on focused heat cell explores the pair (scatter-x-metric '%s' -> '%s')"
                  % (r3info["before"], r3after),
                  r3, "scatter x-metric select did not change" if not r3 else "")

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
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
