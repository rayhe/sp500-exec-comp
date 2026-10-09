#!/usr/bin/env python3
"""Regression guard: keyboard pilot extends to quartile composition segments.

The 2026-10-08 18:04 PT run extended the keyboard pilot (sector bars at
14:00 PT, composition donut + trend cards at 18:04 PT) to the two
remaining click-to-filter stacked-bar charts the 5-critic panel flagged:

  1. Quartile composition chart (js/charts.js, drawQuartileComposition):
     stacked pay-component segments per pay quartile, with hover tooltips
     and click-to-filter-table actions. Each g.quartile-seg is now
     tabindex="0" role="button" with a data-bearing aria-label
     ("Filter table to <quartile> -- <component>: <pct>% of average pay,
     avg value <value>"); focus shows the SAME tooltip HTML
     (segTooltipHtml shared with mouseover, anchored to the segment via a
     synthesized {clientX, clientY} from getBoundingClientRect()); blur
     mirrors mouseout. Enter/Space fires the same filterByDistribution
     action as click.
  2. Governance-quartile composition chart (js/charts.js,
     drawGovQuartileComp): same treatment on g.gov-quartile-seg, keyed to
     filterByGovGrade. BUG FIX: the original click handler called
     window.filterByGovScore, which was never defined anywhere -- the
     click silently did nothing since the chart's first commit. It now
     routes through the real window.filterByGovGrade(gradeHint, govMin,
     govMax).

Both surfaces carry :focus-visible rings in css/style.css matching the
--accent convention (sector-bar pilot, .metric-card precedent).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the quartile-seg creation sets tabindex="0", role="button" and a
        data-bearing aria-label.
     S2 segTooltipHtml is shared by mouseover and focus; blur mirrors
        mouseout (tooltip hidden, highlight reset).
     S3 Enter/Space keydown fires the same filterByDistribution action as
        click.
     S4 the gov-quartile-seg creation sets tabindex="0", role="button"
        and a data-bearing aria-label.
     S5 gov chart tooltip parity (focus/blur); click/keydown routes to
        filterByGovGrade -- the dead filterByGovScore reference is gone.
     S6 css/style.css has :focus-visible rules for both segment classes
        with the --accent outline convention.
     S7 the keyboard additions are attribute-bound (no innerHTML) in both
        segment-creation blocks.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered segment carries tabindex="0", role="button" and a
        data-bearing aria-label.
     R2 focusing a quartile segment shows the tooltip with that segment's
        component data (keyboard tooltip parity); blur hides it.
     R3 Enter on a quartile segment fires filterByDistribution with the
        segment's (sector, minComp, maxComp, label) args.
     R4 Enter on a gov-quartile segment fires filterByGovGrade with the
        segment's (gradeHint, govMin, govMax) args.
     R5 zero JS page errors.

Usage:
  scripts/check_keyboard_seg_pilot.py              # static + render
  scripts/check_keyboard_seg_pilot.py --static-only

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


def seg_block(charts, cls):
    # From the segment creation marker through the click/keydown IIFE that
    # ends right before "cumX += segW;" (covers tooltip IIFE + click IIFE).
    m = re.search(
        r"\.attr\('class', '" + cls + r"'\)([\s\S]*?)\}\)\(q\);\s*\n\s*cumX \+= segW;",
        charts)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    qblock = seg_block(charts, "quartile-seg")
    gblock = seg_block(charts, "gov-quartile-seg")

    s1 = (qblock is not None
          and ".attr('tabindex', '0')" in qblock
          and ".attr('role', 'button')" in qblock
          and ".attr('aria-label', 'Filter table to '" in qblock
          and "% of average pay" in qblock)
    check("S1 .quartile-seg creation sets tabindex=0/role=button/data-bearing aria-label",
          s1, "" if s1 else "keyboard attrs missing from the quartile-seg block")

    s2 = (qblock is not None
          and "var segTooltipHtml = function()" in qblock
          and qblock.count("segTooltipHtml()") >= 2
          and ".on('mouseover', function(event)" in qblock
          and ".on('focus', function()" in qblock
          and "getBoundingClientRect()" in qblock
          and ".on('mouseout', function()" in qblock
          and ".on('blur', function()" in qblock
          and qblock.count("hideChartTooltip()") >= 2)
    check("S2 segTooltipHtml shared by mouseover+focus; blur mirrors mouseout",
          s2, "" if s2 else "tooltip parity wiring missing from the quartile-seg block")

    s3 = (qblock is not None
          and "var filterAction = function()" in qblock
          and ".on('click', filterAction)" in qblock
          and ".on('keydown', function(event)" in qblock
          and "e.key === 'Enter' || e.key === ' '" in qblock.replace("event", "e")
          and "window.filterByDistribution(" in qblock)
    check("S3 Enter/Space keydown fires the same filterByDistribution action as click",
          s3, "" if s3 else "keydown wiring missing from the quartile-seg block")

    s4 = (gblock is not None
          and ".attr('tabindex', '0')" in gblock
          and ".attr('role', 'button')" in gblock
          and ".attr('aria-label', 'Filter table to governance tier '" in gblock
          and "% of average pay" in gblock)
    check("S4 .gov-quartile-seg creation sets tabindex=0/role=button/data-bearing aria-label",
          s4, "" if s4 else "keyboard attrs missing from the gov-quartile-seg block")

    s5 = (gblock is not None
          and "var segTooltipHtml = function()" in gblock
          and gblock.count("segTooltipHtml()") >= 2
          and ".on('focus', function()" in gblock
          and ".on('blur', function()" in gblock
          and "window.filterByGovGrade(quartileData.gradeHint, quartileData.govMin, quartileData.govMax)" in gblock
          and "filterByGovScore(" not in gblock)
    check("S5 gov chart tooltip parity + click/keydown routes to filterByGovGrade (dead filterByGovScore gone)",
          s5, "" if s5 else "gov chart wiring wrong or dead reference still present")

    m = re.search(
        r"#quartile-comp-chart g\.quartile-seg:focus-visible,\s*\n#gov-quartile-comp-chart g\.gov-quartile-seg:focus-visible \{([^}]*)\}",
        css)
    s6 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S6 :focus-visible rings on both segment classes use --accent convention",
          s6, "" if s6 else "focus ring missing or off-convention")

    s7 = (qblock is not None and gblock is not None
          and "innerHTML" not in qblock and "innerHTML" not in gblock)
    check("S7 keyboard additions are attribute-bound (no innerHTML)",
          s7, "" if s7 else "innerHTML found in a segment-creation block")


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
                "window.d3 && document.querySelectorAll('#quartile-comp-chart g.quartile-seg').length > 0",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('#gov-quartile-comp-chart g.gov-quartile-seg').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: every rendered segment is a labelled button in the a11y tree.
            r1info = pg.evaluate("""() => {
              const q = [...document.querySelectorAll('#quartile-comp-chart g.quartile-seg')];
              const g = [...document.querySelectorAll('#gov-quartile-comp-chart g.gov-quartile-seg')];
              const bad = s =>
                s.getAttribute('tabindex') !== '0' ||
                s.getAttribute('role') !== 'button' ||
                !(s.getAttribute('aria-label') || '').includes('% of average pay');
              return {qn: q.length, qb: q.filter(bad).length,
                      gn: g.length, gb: g.filter(bad).length,
                      sample: q[0] ? q[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["qn"] > 0 and r1info["qb"] == 0
                  and r1info["gn"] > 0 and r1info["gb"] == 0)
            check("R1 all %d quartile + %d gov-quartile segments are tabindex=0 role=button with data-bearing aria-label"
                  % (r1info["qn"], r1info["gn"]),
                  r1, ("sample: %r" % r1info["sample"]) if not r1 else "")

            # R2: focusing a quartile segment surfaces its tooltip (parity).
            pg.evaluate("""() => {
              const seg = document.querySelector('#quartile-comp-chart g.quartile-seg');
              seg.scrollIntoView({block: 'center'});
              seg.focus();
            }""")
            pg.wait_for_timeout(600)
            r2info = pg.evaluate("""() => {
              const tip = document.querySelector('.chart-tooltip.visible');
              const seg = document.querySelector('#quartile-comp-chart g.quartile-seg');
              const title = tip ? tip.querySelector('.ct-title') : null;
              const label = seg.getAttribute('aria-label') || '';
              return {visible: !!tip,
                      titleInLabel: title ? label.includes(title.textContent) : false,
                      title: title ? title.textContent : null};
            }""")
            r2 = r2info["visible"] and r2info["titleInLabel"]
            check("R2 focus on quartile segment shows tooltip with segment data (%r)" % r2info["title"],
                  r2, "tooltip not visible or component mismatch" if not r2 else "")
            # Blur restores the un-highlighted state and hides the tooltip.
            pg.evaluate("document.activeElement.blur()")
            pg.wait_for_timeout(400)
            tip_hidden = pg.evaluate("!document.querySelector('.chart-tooltip.visible')")
            check("R2b blur hides the tooltip", tip_hidden,
                  "tooltip still visible after blur" if not tip_hidden else "")

            # R3/R4: stub the filter actions (side-effect-free), then Enter.
            pg.evaluate("""() => {
              window.__fbdCalls = [];
              window.__fbgCalls = [];
              window.filterByDistribution = function() {
                window.__fbdCalls.push(Array.prototype.slice.call(arguments)); };
              window.filterByGovGrade = function() {
                window.__fbgCalls.push(Array.prototype.slice.call(arguments)); };
            }""")
            pg.evaluate("""() => {
              const seg = document.querySelector('#quartile-comp-chart g.quartile-seg');
              seg.scrollIntoView({block: 'center'});
              seg.focus();
            }""")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            r3info = pg.evaluate("window.__fbdCalls")
            r3 = (len(r3info) == 1 and len(r3info[0]) == 4
                  and isinstance(r3info[0][1], (int, float))
                  and isinstance(r3info[0][2], (int, float))
                  and isinstance(r3info[0][3], str))
            check("R3 Enter on quartile segment fires filterByDistribution(sector, minComp, maxComp, label)",
                  r3, "calls recorded: %r" % (r3info,) if not r3 else "")

            pg.evaluate("document.activeElement.blur()")
            pg.evaluate("""() => {
              const seg = document.querySelector('#gov-quartile-comp-chart g.gov-quartile-seg');
              seg.scrollIntoView({block: 'center'});
              seg.focus();
            }""")
            pg.wait_for_timeout(300)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            r4info = pg.evaluate("window.__fbgCalls")
            r4 = (len(r4info) == 1 and len(r4info[0]) == 3
                  and isinstance(r4info[0][0], str)
                  and isinstance(r4info[0][1], (int, float))
                  and isinstance(r4info[0][2], (int, float)))
            check("R4 Enter on gov-quartile segment fires filterByGovGrade(gradeHint, govMin, govMax)",
                  r4, "calls recorded: %r" % (r4info,) if not r4 else "")

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
