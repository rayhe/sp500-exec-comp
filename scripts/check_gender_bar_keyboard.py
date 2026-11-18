#!/usr/bin/env python3
"""Regression guard: gender-pay-chart female bars are keyboard-operable.

The 2026-10-10 11:30 PT 5-critic panel found the last actionable bar surface
in drawGenderPayChart without a keyboard path: the female bars carry a click
action (window.filterByGender('F'), filtering the main table to female CEOs)
plus a data-bearing hover tooltip (median pay, CEO count, premium, highest
paid woman), but had no tabindex/role/keydown -- the same failure-mode class
the 07:30 PT histogram-bar pilot and the 10:06 PT anomaly pilot closed on
other charts.

The gender-bar pilot extends _enableDotKeyboard (the scatter-dot roving
pilot) to #gender-pay-chart .gender-bar:

  - roving tabindex, role="button"
  - data-bearing aria-label (FY, female median pay, female CEO count, premium
    over the all-CEO median, highest paid woman + comp, "Press Enter to
    filter the table to female CEOs")
  - focus fires the exact hover-tooltip path via a synthetic event, blur hides
    it, Enter/Space replays the click path (hideChartTooltip + filterByGender)
  - css/style.css carries the --accent :focus-visible ring for .gender-bar
    (site convention)
  - the info-only overall bars keep no click path and stay out of tab order

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the gender-bar pilot call is present with the right container/selector.
     S2 the pilot passes label + activate; the label mentions female median
        data and the keyboard affordance.
     S3 css/style.css has the :focus-visible --accent ring for .gender-bar.
     S4 the pilot block is attribute-bound (no innerHTML).
     S5 the mouse click path (filterByGender('F')) is preserved.
     S6 node --check js/charts.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every .gender-bar is role=button with a data-bearing aria-label
        mentioning "Press Enter"; roving tabindex (exactly one tabindex="0").
     R2 focusing a gender bar shows the chart tooltip (.chart-tooltip.visible)
        -- the keyboard equivalent of the hover data.
     R3 pressing Enter on a focused gender bar calls window.filterByGender
        exactly once with 'F' and sets window._activeGenderFilter to 'F'
        (keyboard/click parity).
     R4 zero JS page errors.

Usage:
  scripts/check_gender_bar_keyboard.py              # static + render
  scripts/check_gender_bar_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

510th review (2026-11-18): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of exiting 0 with an
all-pass line). Pre-fix defects, both 429th-review classes in one
guard: a missing d3 shim made render_checks() return False, which
main() ignored entirely -- it exited 0 with "ALL 6 CHECKS PASSED"
while the render half never ran (430th class: the silent-pass
variant, worse than the exit-1 drift class); a transient render
exception raised before any R-check was uncaught (no retry wrapper)
-- proved in-process before the fix (~/workspace/sp500-510/
pre510_proof.py: Test A rc=0, "ALL 6 CHECKS PASSED", 0 R-checks;
Test A2 rc=0 skip-on-statics; Test B UNCATCHED RuntimeError on a
simulated transient Chromium launch stall), and corroborated live
by this guard itself FAILing the 2026-11-18T14:34Z shard-4 canary
with exit 1 and 0 R-checks (135.6s, per the 509th entry), then
PASSing standalone minutes later -- the transient-stall class, no
retry wrapper to absorb it. The proof monkeypatches get_d3_bytes
to None and stubs sys.modules['playwright.sync_api'] to None
(ImportError) rather than moving the d3 cache aside (the
monkeypatch touches no shared state). There is no Test A3: the
pre-fix guard has no INFRA sentinel at all, so no truthy-sentinel
form applies (unlike the 505th guard's latent S4 form). The
playwright-missing branch keeps its skip shape (rc=0 on passing
statics) and the docstring's exit-2 promise for that branch is
unchanged from the pre-fix guard, per the 486th/487th precedent.
render_checks() already returns an explicit bool on success
(458th note (27) checked). Slowest unadopted render guard by this
run's fresh in-canary times -- 19.7s vs keyboard_treemap_pilot
18.1s and conc_filter_label 19.1s in the 2026-11-18T17:07Z shard-4
run (canary_20261118_1707_shard4of4.log) -- and by the median over
the last three shard-4 runs (19.7s vs treemap 18.1s, conc 19.1s,
header_subtitle_fy 17.2s; the median is robust to the 14:34Z
artifact outlier, which sits at the max, not the middle, for
gender/conc/header); the standalone re-profile this run is a
near-tie (treemap 10.21s vs gender 10.19s, conc 9.49s, header
4.82s), so the pick rests on the freshest in-canary time plus the
median, per the 469th note (68) rule that the evidence base is the
multi-run history plus the re-profile, not one state reading. Shard
verified with drift_canary._guard_shard (432nd note):
gender_bar_keyboard in shard 4 (with the full check_ name and the
shard count; see note (157) for the bare-name trap and note (161)
for the .py-suffix trap).
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

CHART_ID = "#gender-pay-chart"
BAR_SEL = ".gender-bar"


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def pilot_block(charts):
    m = re.search(
        r"_enableDotKeyboard\(d3\.select\('" + re.escape(CHART_ID) +
        r"'\), '([^']*)', \{([\s\S]*?)\n    \}\);",
        charts)
    return m.group(0) if m else None, (m.group(1) if m else None)


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    blk, got_sel = pilot_block(charts)
    s1 = blk is not None and got_sel == BAR_SEL
    check("S1 gender-bar pilot present with the right container/selector",
          s1, ("" if s1 else "block missing or selector=%r" % (got_sel,)))

    s2 = (blk is not None
          and "label:" in blk and "activate:" in blk
          and "female_median_pay" in blk
          and "num_female_ceos" in blk
          and "Press Enter to filter the table to female CEOs" in blk
          and "filterByGender('F')" in blk)
    check("S2 pilot passes label + activate; label carries the female-pay data and the keyboard affordance",
          s2, "" if s2 else "label/activate incomplete in the pilot block")

    s3 = (re.search(r"#gender-pay-chart \.gender-bar:focus-visible\s*\{",
                    css) is not None
          and "outline: 2px solid var(--accent)" in css)
    check("S3 css :focus-visible --accent ring covers .gender-bar",
          s3, "" if s3 else "focus rule missing or off-convention")

    s4 = blk is not None and "innerHTML" not in blk
    check("S4 pilot block is attribute-bound (no innerHTML)",
          s4, "" if s4 else "innerHTML in the pilot block")

    s5 = re.search(
        r"function drawGenderPayChart\([\s\S]*?\.on\('click'", charts) is not None
    check("S5 mouse .on('click') handler preserved in drawGenderPayChart",
          s5, "" if s5 else "the click handler is gone")

    r = subprocess.run(["node", "--check", CHARTS_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/charts.js is green",
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
                "window.d3 && document.querySelectorAll('#gender-pay-chart .gender-bar').length >= 2",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every female bar is an upgraded button with roving tabindex.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#gender-pay-chart .gender-bar')];
              const badRole = bars.filter(b => b.getAttribute('role') !== 'button');
              const badLabel = bars.filter(b => {
                const l = b.getAttribute('aria-label') || '';
                return !l.length || l.indexOf('Press Enter') < 0
                    || l.indexOf('Female CEOs') < 0 || l.indexOf('median pay') < 0;
              });
              const holders = bars.filter(b => b.getAttribute('tabindex') === '0').length;
              return {n: bars.length, badRole: badRole.length,
                      badLabel: badLabel.length, holders: holders};
            }""")
            r1 = (r1info["n"] >= 2 and r1info["badRole"] == 0
                  and r1info["badLabel"] == 0 and r1info["holders"] == 1)
            check("R1 gender bars are role=button with data-bearing aria-labels, one roving tabindex=0",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # R2: focusing a gender bar shows the chart tooltip.
            r2ok = pg.evaluate("""() => {
              const bar = document.querySelector('#gender-pay-chart .gender-bar[tabindex="0"]');
              if (!bar) return false;
              bar.focus();
              return new Promise(res => setTimeout(() => res(
                document.querySelector('.chart-tooltip.visible') !== null), 400));
            }""")
            check("R2 focus on a gender bar shows the chart tooltip", bool(r2ok),
                  "" if r2ok else "no .chart-tooltip.visible after focus")

            # R3: Enter on a focused gender bar fires filterByGender('F') once.
            r3setup = pg.evaluate("""() => {
              window.__fgCalls = [];
              const orig = window.filterByGender;
              window.filterByGender = function(g) {
                window.__fgCalls.push(g);
                return orig.apply(this, arguments);
              };
              const bar = document.querySelector('#gender-pay-chart .gender-bar[tabindex="0"]');
              if (!bar) return 'NO_BAR';
              bar.focus();
              return 'OK';
            }""")
            if r3setup != "OK":
                check("R3 Enter on gender bar fires filterByGender('F')", False,
                      "setup: %r" % r3setup)
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(800)
                r3info = pg.evaluate("""() => ({
                  calls: window.__fgCalls,
                  active: window._activeGenderFilter
                })""")
                r3 = (r3info["calls"] == ["F"] and r3info["active"] == "F")
                check("R3 Enter fires filterByGender('F') exactly once and sets the filter",
                      r3, ("" if r3 else "state: %r" % (r3info,)))

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    ok = True
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
        ok = run_render_with_retry(render_checks, results, check)
        if ok is INFRA:
            return 2
        if ok is None:
            print("SKIP: render checks unavailable; static checks decide")
    fails = [n for n, ok, _ in results if not ok]
    if fails or ok is False:
        if fails:
            print("\n%d check(s) FAILED: %s" % (len(fails), ", ".join(fails)))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("\nALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
