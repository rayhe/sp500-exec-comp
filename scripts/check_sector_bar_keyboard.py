#!/usr/bin/env python3
"""Regression guard: sector chart bars are keyboard-operable.

The sector chart's median bars are click-to-filter controls
(window.filterBySector), but SVG rects are not keyboard-focusable by
default, so keyboard users had no path to the sector filter (2026-10-08
5-critic panel, Interactivity dimension). drawSectorChart() now exposes
each .bar as tabindex="0" role="button" with an aria-label and an
Enter/Space keydown that fires the same filterBySector path as click;
css/style.css carries a --accent :focus-visible ring matching the site
convention (e.g. .metric-card:focus-visible). The dist-box/whisker
overlays remain visual-only (drawn beneath the bars, no handlers).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the .bar join in drawSectorChart() sets tabindex="0",
        role="button", an aria-label mentioning the sector, and a
        keydown handler for Enter/Space that calls window.filterBySector.
     S2 the mouse click path is preserved (click -> filterBySector).
     S3 css/style.css has the #sector-chart rect.bar:focus-visible rule
        with the --accent outline convention.
     S4 the keyboard additions use .attr() (setAttribute-bound), not
        innerHTML — data never reaches HTML parsing.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered .bar carries tabindex="0", role="button" and a
        non-empty aria-label naming its sector.
     R2 focusing the first bar and pressing Enter filters the table
        (row count drops; sector filter chip appears).
     R3 zero JS page errors.

Usage:
  scripts/check_sector_bar_keyboard.py              # static + render
  scripts/check_sector_bar_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

503rd review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of exiting 0 with no
R-checks at all), and gains the "%d/%d checks passed" summary line
this guard never printed. static_checks() gains the
OSError-to-return-2 path (488th template). Pre-fix defects, both
429th-review classes in one guard: a missing d3 shim made
render_checks() return False, which main() ignored entirely, so it
exited 0 (the silent-pass variant, 430th shape, although the
docstring promises exit 2 for a missing shim) -- and printed no
summary line at all while the render half never ran; a missing
playwright install exited 0 the same way (the silent-pass variant,
although the docstring promises exit 2 for playwright missing);
and a transient render exception raised before any R-check was
uncaught (no retry wrapper) -- proved in-process before the fix
(~/workspace/sp500-503/pre503_proof.py: Test A-live rc=0,
0 R-checks; Test A2 rc=0, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (the monkeypatch touches no shared
state). The playwright-missing branch keeps its skip shape (rc=0
on passing statics) and the docstring's exit-2 promise for that
branch is unchanged from the pre-fix guard, per the 486th/487th
precedent. render_checks() already returns an explicit bool on
success (458th note (27) checked). Slowest unadopted shard-3
render guard by the multi-run history plus a clean standalone
re-profile before the canary (501st note (152) rule): sector_bar
median 13.9s / mean 15.2s / max 29.3s over 10 shard-3 runs
(Nov 15-17), freshest 11.9s, 9.38s standalone this run vs
correlation_keyboard median 13.6s / freshest 9.3s / 11.42s
standalone and summary_bar_keyboard median 13.1s / freshest 11.4s
/ 9.49s standalone -- the pick stands on the median lead plus the
freshest-state lead, per the 469th note (68) rule; correlation
leads only the standalone re-profile, within noise. Shard verified
with drift_canary._guard_shard (432nd note): sector_bar in shard 3
(61 guards).
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def bar_join_block():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    # The sector-chart .bar join: from ".attr('class', 'bar')" to the
    # closing of its chained handlers (the click+keydown tail).
    m = re.search(r"\.attr\('class', 'bar'\)([\s\S]{0,6000}?)\.on\('keydown', function\(event, d\) \{[\s\S]{0,400}?\}\);",
                  charts)
    return m.group(0) if m else None


def static_checks():
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
        css = open(CSS, encoding="utf-8").read()
        block = bar_join_block()
    except OSError as exc:
        print("INFRA: cannot read guard inputs: %s" % exc)
        return 2

    s1 = (block is not None
          and ".attr('tabindex', '0')" in block
          and ".attr('role', 'button')" in block
          and ".attr('aria-label', function(d)" in block
          and "d._compSector" in block
          and "event.key === 'Enter' || event.key === ' '" in block
          and "window.filterBySector" in block)
    check("S1 .bar join sets tabindex/role/aria-label and Enter/Space keydown -> filterBySector",
          s1, "" if s1 else "keyboard additions missing from the .bar join")

    s2 = (block is not None
          and ".on('click', function(event, d)" in block
          and "window.filterBySector(d._compSector)" in block)
    check("S2 mouse click path preserved (click -> filterBySector)",
          s2, "" if s2 else "click handler altered or lost")

    m = re.search(r"#sector-chart rect\.bar:focus-visible \{([^}]*)\}", css)
    s3 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S3 :focus-visible ring on #sector-chart rect.bar uses --accent convention",
          s3, "" if s3 else "focus ring missing or off-convention")

    # S4: the keyboard block must not introduce innerHTML near the new attrs.
    s4 = block is not None and "innerHTML" not in block
    check("S4 keyboard additions are setAttribute-bound (no innerHTML)",
          s4, "" if s4 else "innerHTML found in the .bar join block")


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
                "window.d3 && document.querySelectorAll('#sector-chart rect.bar').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every bar is a labelled button in the a11y tree.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#sector-chart rect.bar')];
              const bad = bars.filter(b =>
                b.getAttribute('tabindex') !== '0' ||
                b.getAttribute('role') !== 'button' ||
                !(b.getAttribute('aria-label') || '').includes('sector'));
              return {n: bars.length, bad: bad.length,
                      sample: bars[0] ? bars[0].getAttribute('aria-label') : null};
            }""")
            r1 = r1info["n"] > 0 and r1info["bad"] == 0
            check("R1 all %d bars are tabindex=0 role=button with sector aria-label" % r1info["n"],
                  r1, ("sample: %r" % r1info["sample"]) if not r1 else "")

            # R2: keyboard Enter on a focused bar filters the table.
            before = pg.evaluate(
                "document.querySelectorAll('#comp-table tbody tr').length")
            pg.evaluate("""() => {
              const bar = document.querySelector('#sector-chart rect.bar');
              bar.scrollIntoView({block: 'center'});
              bar.focus();
            }""")
            pg.wait_for_timeout(400)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(1000)
            after = pg.evaluate(
                "document.querySelectorAll('#comp-table tbody tr').length")
            chip = pg.evaluate(
                "document.body.textContent.includes('Clear') && "
                "document.querySelectorAll('#comp-table tbody tr').length < 50")
            r2 = after < before
            check("R2 Enter on focused bar filters table (%d -> %d rows)" % (before, after),
                  r2, "table did not filter" if not r2 else "")

            # R3: zero JS page errors across the lifecycle.
            check("R3 zero JS page errors", len(errors) == 0,
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
