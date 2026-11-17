#!/usr/bin/env python3
"""Regression guard: scatter path-finder step badges are keyboard-operable.

The 2026-10-10 5-critic panel audit for NEW failure-mode classes flagged
_applyScatterPathOverlay (js/charts.js) as the next missed
click-without-keyboard surface (the 21:59 PT vol-tenure pilot, the 19:33 PT
vol-sector pilot, the 18:03 PT GER pilot, the 15:35 PT tenure-growth pilot,
the 14:05 PT sector-gov pilot, the 11:30 PT gender-bar pilot, and the
10:06 PT anomaly pilot closed the same class on other charts):

  - the path-finder step badges (transparent circles over the step number
    badges, pointer-events 'all', cursor:pointer, click = window
    .findCompanyInTable(d.pt.ticker)) plus a data-bearing hover tooltip
    (ticker, company, CEO, total pay, sector, comp breakdown, "Click for
    detail") had no tabindex/role/keydown and no class.

The scatter-path pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to the badge surface:

  - roving tabindex, role="button"
  - data-bearing aria-label (step N of M, ticker, company, CEO, total pay,
    sector, "Press Enter to view <ticker> in the table.")
  - badge focus fires the exact hover-tooltip path via a synthetic
    mouseover, blur hides it
  - Enter/Space replays the click path exactly (hideChartTooltip +
    window.findCompanyInTable(d.pt.ticker))
  - css/style.css carries the --accent :focus-visible ring for
    #scatter-chart .scatter-path-step (site convention)

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the scatter-path pilot call is present for .scatter-path-step.
     S2 the badge hover circle carries class scatter-path-step inside
        _applyScatterPathOverlay.
     S3 the pilot passes label + activate; the label carries the step
        data and the keyboard affordance, and activate replays the click
        path (hideChartTooltip + findCompanyInTable).
     S4 css/style.css has the :focus-visible --accent ring for
        #scatter-chart .scatter-path-step.
     S5 the pilot block is attribute-bound (no innerHTML).
     S6 the mouse .on('click') handler is preserved in
        _applyScatterPathOverlay.
     S7 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .scatter-path-step is role=button with a data-bearing
        aria-label mentioning "Press Enter" and "Step"; roving tabindex
        (exactly one tabindex="0").
     R2 focusing the tabindex="0" step badge shows the chart tooltip
        (.chart-tooltip.visible) -- the keyboard equivalent of the
        hover data.
     R3 pressing Enter on the focused step badge calls
        window.findCompanyInTable exactly once with the badge's ticker
        -- keyboard/click parity.
     R4 zero JS page errors.

Usage:
  scripts/check_scatter_path_keyboard.py              # static + render
  scripts/check_scatter_path_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

499th review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of printing no summary
and returning 0). static_checks() gains the OSError-to-return-2 path
(488th template). Pre-fix defects, both 429th-review classes in one
guard: main() ignored render_checks()'s return value, so a missing d3
shim exited 0 with "ALL 7 CHECKS PASSED" while the render half never
ran (the silent-pass variant, 430th-review shape, although the
docstring promises exit 2 for a missing shim); a missing playwright
install likewise exited 0 on the statics alone (the silent-pass
variant, although the docstring promises exit 2 for playwright
missing); and a transient render exception raised before any R-check
was uncaught (no retry wrapper) -- proved in-process before the fix
(~/workspace/sp500-499/pre499_proof.py: Test A-live rc=0,
0 R-checks; Test A2 rc=0, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (no canary live concurrently this
run at proof time; the monkeypatch touches no shared state). The
playwright-missing branch keeps its skip shape (rc=0 on passing
statics) and the docstring's exit-2 promise for that branch is
unchanged from the pre-fix guard, per the 486th/487th precedent.
render_checks() already returns an explicit bool on success (458th
note (27) checked). The adopted main prints the "N/N checks passed"
summary line in the 493rd shape (the pre-fix main printed
"ALL N CHECKS PASSED"). Slowest unadopted shard-3 render guard by the
multi-run history plus the re-profile: 18 shard-3 runs:
scatter_path median 11.2s / mean 14.33s / max 34.2s vs correlation
median 10.8s / mean 13.72s / max 31.7s vs sector_bar median 9.9s /
mean 12.44s / max 29.3s; freshest state reading vol_sector 48.5s vs
scatter_path 34.2s (2026-11-17T13:13Z shard-3 run, a globally slow
run: all nine shard-3 candidates 22-48s against medians of 6-11s);
clean standalone re-profile this run scatter_path 19.38s rc=0 11/11
vs sector_bar 21.19s vs vol_sector 18.73s vs correlation 16.80s, and
a second re-profile scatter_path 9.55s vs sector_bar 9.59s (a tie;
one tie-break attempt was killed mid-run by a service restart and
retried once) -- scatter_path leads the median, the mean, and the
max, and ties the re-profile (sector_bar leads only the first
re-profile run), so the pick stands on the multi-run history plus
the re-profile, per the 469th note (68) rule. Pick verified with the
canary's exact shard function (432nd note): _guard_shard(stem, 4).
That check also corrects the 498th note, which labeled
scatter_dots a shard-2 guard: it partitions to shard 4 (it runs in
shard4of4 logs; the 498th re-baseline itself was genuinely shard 2).
Shard 3 is the stalest shard (last run 2026-11-17T13:13Z vs shard 4
14:37Z, shard 1 17:06Z, shard 2 18:38Z), continuing the re-baseline
sequence 493rd shard 1, 494th shard 2, 495th shard 3, 496th shard 4,
497th shard 1, 498th shard 2. sector_trend_fy_label and
composition_fy_detail stay queued next for shard 2.
"""
import os
import re
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.path.dirname(HERE)
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []

CHART_ID = "#scatter-chart"
STEP_SEL = ".scatter-path-step"


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts):
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(CHART_ID) +
        r"'\), '" + re.escape(STEP_SEL) + r"', \{([\s\S]*?)\n    \}\);",
        charts)
    return m.group(0) if m else None


def overlay_fn(charts):
    m = re.search(
        r"function _applyScatterPathOverlay\(([\s\S]*?)\nwindow\._redrawScatterForPathOverlay = function",
        charts)
    return m.group(0) if m else None


def static_checks():
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
        css = open(CSS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/charts.js or css/style.css: %s" % exc)
        return 2

    blk = pilot_block(charts)
    check("S1 scatter-path pilot present for .scatter-path-step",
          blk is not None,
          "" if blk else "pilot block missing")

    fn = overlay_fn(charts)
    s2 = fn is not None and ".attr('class', 'scatter-path-step')" in fn
    check("S2 badge hover circle carries class scatter-path-step in "
          "_applyScatterPathOverlay",
          s2, "" if s2 else "class not found on the hover circle")

    s3 = (blk is not None
          and "label:" in blk and "activate:" in blk
          and "Press Enter to view" in blk
          and "'Step '" in blk
          and "total pay" in blk
          and "findCompanyInTable(d.pt.ticker)" in blk
          and "hideChartTooltip()" in blk)
    check("S3 pilot passes label + activate; label carries the step data "
          "and the keyboard affordance; activate replays the click path "
          "(hideChartTooltip + findCompanyInTable)",
          s3, "" if s3 else "label/activate incomplete in the pilot block")

    s4 = (re.search(r"#scatter-chart \.scatter-path-step:focus-visible", css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S4 css :focus-visible --accent ring covers "
          "#scatter-chart .scatter-path-step",
          s4, "" if s4 else "focus rule missing or off-convention")

    s5 = blk is not None and "innerHTML" not in blk
    check("S5 pilot block is attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML in the pilot block or block missing")

    s6 = (fn is not None
          and fn.count(".on('click'") >= 1
          and "window.findCompanyInTable(d.pt.ticker)" in fn)
    check("S6 mouse .on('click') handler preserved in "
          "_applyScatterPathOverlay",
          s6, "" if s6 else "the click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S7 node --check js/charts.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")


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
                "window.d3 && document.querySelectorAll('#scatter-chart .scatter-dot').length >= 100",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # Trigger the path-finder overlay on the scatter.
            pg.evaluate("""() => {
              window._activePathFinderNodes = ['AAPL', 'MSFT', 'NVDA'];
              window._redrawScatterForPathOverlay();
            }""")
            pg.wait_for_function(
                "document.querySelectorAll('#scatter-chart .scatter-path-step').length >= 2",
                timeout=30000)
            pg.wait_for_timeout(800)

            # R1: badges are upgraded buttons with roving tabindex.
            r1info = pg.evaluate("""() => {
              const steps = [...document.querySelectorAll('#scatter-chart .scatter-path-step')];
              const ok = steps.length >= 2 &&
                steps.every(e => e.getAttribute('role') === 'button' &&
                  (e.getAttribute('aria-label') || '').indexOf('Press Enter') >= 0 &&
                  (e.getAttribute('aria-label') || '').indexOf('Step') >= 0) &&
                steps.filter(e => e.getAttribute('tabindex') === '0').length === 1;
              return {n: steps.length, ok: ok,
                      labels: steps.map(e => e.getAttribute('aria-label')).slice(0, 2)};
            }""")
            r1 = r1info["ok"]
            check("R1 path step badges are role=button with data-bearing "
                  "aria-labels ('Press Enter', 'Step'), one roving tabindex=0",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing the tabindex=0 badge shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const step = document.querySelector(
                '#scatter-chart .scatter-path-step[tabindex="0"]');
              if (!step) return 'MISSING';
              step.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null
                  ? 'SHOWN' : 'HIDDEN'), 400));
            }""")
            r2 = (r2ok == "SHOWN")
            check("R2 focus on a path step badge shows the chart tooltip",
                  r2, ("" if r2 else "state: %r" % (r2ok,)))

            # R3: Enter on the focused badge calls findCompanyInTable once
            # with the badge's ticker -- keyboard/click parity.
            r3setup = pg.evaluate("""() => {
              window.__spCalls = [];
              const orig = window.findCompanyInTable;
              if (typeof orig !== 'function') return 'NO_FN';
              window.findCompanyInTable = function(t) {
                window.__spCalls.push(t);
                return orig.apply(this, arguments);
              };
              const step = document.querySelector(
                '#scatter-chart .scatter-path-step[tabindex="0"]');
              if (!step) return 'NO_STEP';
              const toks = (step.getAttribute('aria-label') || '').split(' ');
              step.focus();
              return 'OK|' + toks[4];
            }""")
            if not r3setup.startswith("OK|"):
                check("R3 Enter on step badge fires findCompanyInTable",
                      False, "setup: %r" % r3setup)
            else:
                expected = r3setup.split("|", 1)[1]
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1200)
                r3info = pg.evaluate(
                    "() => ({calls: window.__spCalls})")
                r3 = (r3info["calls"] == [expected])
                check("R3 Enter calls window.findCompanyInTable exactly once "
                      "with the badge's ticker (%s; keyboard/click parity)" % expected,
                      r3, ("" if r3 else "state: %r, expected [%r]" % (r3info, expected)))

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
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
    failed = [r for r in results if not r[1]]
    if failed or ok is False:
        if failed:
            print("FAILED: " + ", ".join(r[0] for r in failed))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
