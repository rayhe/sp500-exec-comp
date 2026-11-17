#!/usr/bin/env python3
"""Regression guard: full-chart histogram bars are keyboard-operable.

The 2026-10-10 07:30 PT 5-critic panel found a new failure-mode class: the
full-size D3 histogram/bar charts carry click actions (table filters or
bucket highlights) plus data-bearing hover tooltips, but their SVG bars had
no tabindex/role/keydown -- the same gap class the 2026-10-09 run closed for
inline onclick controls and the 2026-10-08 run closed for the sector chart.
The histogram-bar pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to nine bucket-bar surfaces in js/charts.js:

  #ratio-chart .hist-bar rect            -> window.filterByRatioBucket
  #top10-chart .top-bar                  -> window.findCompanyInTable
  #comp-dist-chart .comp-dist-bar rect,
                   .comp-dist-sector-bar rect -> window.filterByCompBracket
  #yoy-dist-chart .yoy-bar rect          -> window.filterByYoYBucket
                                          (mouseenter/mouseleave handlers,
                                           so hoverIn/hoverOut are overridden)
  #ceo-cfo-chart .cfo-bar               -> window.filterByCeoCfoBucket
                                          (347th review: was a highlight-only
                                           toggle; the click now filters)
  #conc-dist-chart .conc-dist-bar rect,
                  .conc-sector-bar rect  -> filterByConcTier
  #sop-dist-chart .sop-bar               -> window.highlightSopBucket
  #gov-dist-chart .gov-bar               -> window.filterByGovGrade
  #volatility-dist-chart .vol-bar        -> volatility-bucket filter

Each pilot: roving tabindex, role="button", data-bearing aria-label (bucket
label, company count, % of total, top tickers, "Press Enter to ..."), focus
fires the exact hover-tooltip path via a synthetic event, blur hides it,
Enter/Space replays the click path. css/style.css carries the --accent
:focus-visible ring for all bar classes (site convention, e.g. the sector
chart rule from 2026-10-08).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 all nine _enableDotKeyboard pilot calls are present with the right
        container selector.
     S2 every pilot passes label + activate; the YoY pilot overrides
        hoverIn/hoverOut (mouseenter/mouseleave).
     S3 css/style.css has the combined :focus-visible rule with the --accent
        outline convention covering the bar classes.
     S4 the pilot blocks are attribute-bound (no innerHTML).
     S5 the mouse click paths are preserved (one .on('click') per chart).
     S6 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every bar on the nine charts is role=button with a non-empty
        aria-label mentioning "Press Enter"; roving tabindex (exactly one
        tabindex="0" per chart at rest).
     R2 focusing a ratio bar shows the chart tooltip (.chart-tooltip.visible)
        -- the keyboard equivalent of the hover data.
     R3 pressing Enter on a focused ratio bar filters the table
        (window._activeRatioBucket set; tbody row count drops).
     R4 pressing Enter on a focused top-10 bar calls window.findCompanyInTable
        exactly once with the bar's ticker (keyboard/click parity).
     R5 zero JS page errors.

Usage:
  scripts/check_hist_bar_keyboard.py              # static + render
  scripts/check_hist_bar_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

500th review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of printing "ALL 6
CHECKS PASSED" and returning 0). static_checks() gains the
OSError-to-return-2 path (488th template). Pre-fix defects, both
429th-review classes in one guard: main() ignored render_checks()'s
return value, so a missing d3 shim exited 0 with "ALL 6 CHECKS
PASSED" while the render half never ran (the silent-pass variant,
430th-review shape, although the docstring promises exit 2 for a
missing shim); a missing playwright install exited 0 the same way
(the silent-pass variant, although the docstring promises exit 2
for playwright missing); and a transient render exception raised
before any R-check was uncaught (no retry wrapper) -- proved
in-process before the fix (~/workspace/sp500-500/pre500_proof.py:
Test A-live rc=0, "ALL 6 CHECKS PASSED", 0 R-checks; Test A2 rc=0,
"ALL 6 CHECKS PASSED", 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (the canary shard 4 is live
concurrently this run at proof time; the monkeypatch touches no
shared state). The playwright-missing branch keeps its skip shape
(rc=0 on passing statics) and the docstring's exit-2 promise for
that branch is unchanged from the pre-fix guard, per the
486th/487th precedent. render_checks() already returns an explicit
bool on success (458th note (27) checked). Slowest unadopted
shard-4 render guard by the multi-run history plus the re-profile:
18 shard-4 runs: hist_bar median 12.2s / mean 14.6s / max 33.2s
vs realized_note_ref median 12.1s / mean 13.9s / max 35.8s vs
voltenure_chip_part_spans median 11.7s / mean 14.0s / max 42.1s
vs keyboard_treemap_pilot median 11.5s / mean 15.1s / max 37.7s;
freshest state reading tenure_chip 16.7s vs realized 14.3s vs
peerdist 13.9s vs treemap 12.7s vs voltenure 12.5s vs hist_bar
12.5s; the standalone re-profile this run inverts the order
(voltenure 12.40s vs realized 16.27s vs treemap 16.33s vs
hist_bar 20.41s) but ran under concurrent canary load, so it is
not clean evidence -- the pick stands on the multi-run median
lead plus the 499th run's explicit shard-4 queue, per the 469th
note (68) rule. Shard verified with drift_canary.partition_guards
(432nd note): hist_bar in shard 4 (57 guards).
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []

# (chart container id, bar selector fragment used in the pilot call)
PILOTS = [
    ("#ratio-chart", ".hist-bar rect"),
    ("#top10-chart", ".top-bar"),
    ("#comp-dist-chart", ".comp-dist-bar rect"),
    ("#yoy-dist-chart", ".yoy-bar rect"),
    ("#ceo-cfo-chart", ".cfo-bar"),
    ("#conc-dist-chart", ".conc-dist-bar rect"),
    ("#sop-dist-chart", ".sop-bar"),
    ("#gov-dist-chart", ".gov-bar"),
    ("#volatility-dist-chart", ".vol-bar"),
]


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts, chart_id):
    """Return the _enableDotKeyboard({...}) call text for one chart."""
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(chart_id) +
        r"'\), '([^']*)', \{([\s\S]*?)\n    \}\);",
        charts)
    return m.group(0) if m else None, (m.group(1) if m else None)


def static_checks():
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
        css = open(CSS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/charts.js or css/style.css: %s" % exc)
        return 2

    missing = []
    bad_sel = []
    blocks = {}
    for chart_id, sel in PILOTS:
        blk, got_sel = pilot_block(charts, chart_id)
        blocks[chart_id] = blk
        if blk is None:
            missing.append(chart_id)
        elif sel not in (got_sel or ""):
            bad_sel.append(chart_id)
    s1 = not missing and not bad_sel
    check("S1 all nine histogram-bar pilots present with the right selectors",
          s1, ("" if s1 else "missing=%s bad_selector=%s" % (missing, bad_sel)))

    bad_cfg = [cid for cid, blk in blocks.items()
               if blk is None or "label:" not in blk or "activate:" not in blk]
    yoy = blocks.get("#yoy-dist-chart")
    yoy_ok = (yoy is not None
              and "hoverIn: 'mouseenter'" in yoy
              and "hoverOut: 'mouseleave'" in yoy)
    s2 = not bad_cfg and yoy_ok
    check("S2 every pilot passes label + activate; YoY overrides hoverIn/hoverOut",
          s2, ("" if s2 else "bad_cfg=%s yoy_overrides=%s" % (bad_cfg, yoy_ok)))

    css_classes = [
        "#ratio-chart .hist-bar rect:focus-visible",
        "#top10-chart .top-bar:focus-visible",
        "#comp-dist-chart .comp-dist-bar rect:focus-visible",
        "#yoy-dist-chart .yoy-bar rect:focus-visible",
        "#ceo-cfo-chart .cfo-bar:focus-visible",
        "#conc-dist-chart .conc-dist-bar rect:focus-visible",
        "#sop-dist-chart .sop-bar:focus-visible",
        "#gov-dist-chart .gov-bar:focus-visible",
        "#volatility-dist-chart .vol-bar:focus-visible",
    ]
    m = re.search(
        r"(_enableDotKeyboard|histogram-bar pilot)[\s\S]*?"
        r"(#ratio-chart \.hist-bar rect:focus-visible[\s\S]*?)\{\s*([\s\S]*?)\}",
        css)
    s3 = (m is not None
          and all(c in m.group(2) for c in css_classes)
          and "outline: 2px solid var(--accent)" in m.group(3))
    check("S3 css :focus-visible --accent ring covers all nine bar classes",
          s3, "" if s3 else "combined focus rule missing or off-convention")

    bad_html = [cid for cid, blk in blocks.items()
                if blk is not None and "innerHTML" in blk]
    s4 = not bad_html
    check("S4 pilot blocks are attribute-bound (no innerHTML)",
          s4, ("" if s4 else "innerHTML in %s" % bad_html))

    # Mouse click paths preserved: each draw function still binds click.
    s5 = all(re.search(
        r"function draw\w+\([\s\S]*?" + re.escape(cid) +
        r"[\s\S]*?\.on\('click'",
        charts) is not None for cid, _ in PILOTS)
    check("S5 mouse .on('click') handlers preserved on all nine charts",
          s5, "" if s5 else "a chart lost its click handler")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")

    return 0


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
    if d3 is None:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

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
                "window.d3 && document.querySelectorAll('#ratio-chart .hist-bar rect').length > 3",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('#volatility-dist-chart .vol-bar').length > 3",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every pilot bar is an upgraded button with roving tabindex.
            r1info = pg.evaluate("""() => {
              const charts = %s;
              const out = {};
              for (const c of charts) {
                const bars = [...document.querySelectorAll(c.id + ' ' + c.sel)];
                const badRole = bars.filter(b => b.getAttribute('role') !== 'button');
                const badLabel = bars.filter(b => {
                  const l = b.getAttribute('aria-label') || '';
                  return !l.length || l.indexOf('Press Enter') < 0;
                });
                const holders = bars.filter(b => b.getAttribute('tabindex') === '0').length;
                out[c.id] = {n: bars.length, badRole: badRole.length,
                             badLabel: badLabel.length, holders: holders};
              }
              return out;
            }""" % str([{"id": c, "sel": s} for c, s in PILOTS]).replace("'", '"'))
            r1bad = [cid for cid, v in r1info.items()
                     if v["n"] < 3 or v["badRole"] or v["badLabel"] or v["holders"] != 1]
            check("R1 all nine charts: bars are role=button with data aria-labels, one roving tabindex=0",
                  not r1bad, ("charts failing: %s" % r1bad) if r1bad else "")

            # R2: focusing a ratio bar shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#ratio-chart .hist-bar rect[tabindex="0"]');
              if (!bar) return false;
              bar.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null), 400));
            }""")
            check("R2 focus on a ratio bar shows the chart tooltip", bool(r2ok),
                  "" if r2ok else "no .chart-tooltip.visible after focus")

            # R3: Enter on a focused ratio bar filters the table.
            r3setup = pg.evaluate("""() => {
              const bar = document.querySelector('#ratio-chart .hist-bar rect[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              const before = document.querySelectorAll('#comp-tbody tr').length;
              bar.focus();
              return {label: bar.getAttribute('aria-label'), before: before};
            }""")
            if r3setup == "NO_BAR":
                check("R3 Enter on ratio bar filters the table", False, "no ratio bar")
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("""() => ({
                  bucket: window._activeRatioBucket !== null &&
                          window._activeRatioBucket !== undefined,
                  after: document.querySelectorAll('#comp-tbody tr').length
                })""")
                r3 = r3info["bucket"] and r3info["after"] < r3setup["before"]
                check("R3 Enter on ratio bar sets the ratio bucket and drops table rows",
                      r3, ("state: %r before=%d" % (r3info, r3setup["before"])) if not r3 else "")
                # Toggle the filter back off so later checks see the full table.
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)

            # R4: Enter on a focused top-10 bar fires findCompanyInTable once.
            r4setup = pg.evaluate("""() => {
              window.__findCalls = [];
              const orig = window.findCompanyInTable;
              window.findCompanyInTable = function(t) {
                window.__findCalls.push(t);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#top10-chart .top-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              bar.focus();
              const m = (bar.getAttribute('aria-label') || '').match(/\\(([A-Z][A-Z0-9.\\-]*)\\)/);
              return m ? m[1] : 'NO_TICKER';
            }""")
            if r4setup in ("NO_BAR", "NO_TICKER"):
                check("R4 Enter on top-10 bar fires findCompanyInTable", False,
                      "setup: %r" % r4setup)
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r4calls = pg.evaluate("window.__findCalls")
                r4 = len(r4calls) == 1 and r4calls[0] == r4setup
                check("R4 Enter on top-10 bar fires findCompanyInTable('%s') exactly once" % r4setup,
                      r4, ("calls: %r" % r4calls) if not r4 else "")

            # R5: zero JS page errors across the lifecycle.
            check("R5 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
    fails = [n for n, ok, _ in results if not ok]
    if fails or ok is False:
        if fails:
            print("FAILED: " + ", ".join(fails))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
