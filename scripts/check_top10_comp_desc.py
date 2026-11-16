#!/usr/bin/env python3
"""Regression guard: the Top-10 "Highest Paid" chart description must track
the live primary fiscal year from data/compensation.json's metadata, not a
hard-coded year.

Background (2026-10-07): the 2026-10-06 anchor promotion moved the primary
fiscal year from FY2024 to FY2025 (425 companies to FY2025, 22 non-calendar
filers to FY2026). TOP10_MODES.comp.desc stayed hard-coded at 'FY 2024 total
compensation from proxy statements' while the chart ranks the same
FY2025-anchored company list the median-pay metric card is computed from -
the value was FY2025-anchored while the label claimed FY2024. Same
stale-label class as the header company-count badge (2026-09-24), the
median-pay FY sublabel (2026-10-07 10:00 PT), the sector-comp desc
(2026-10-07 11:32 PT), the role-comp desc (2026-10-07 14:00 PT), the network
coverage clause (2026-10-07 15:38 PT), and the orphan-desc fallback
(2026-10-07 18:09 PT). The fix renders the year live from
_chartData.compData.metadata.primary_fiscal_year via _top10CompDesc().

This guard has two halves:
  A. Static: _top10CompDesc() exists and derives the year from
     _chartData.compData.metadata.primary_fiscal_year; drawTop10Chart uses it
     for the 'comp' mode (not cfg.desc raw); no hard-coded 'FY 2024 total
     compensation from proxy statements' string remains in js/charts.js; the
     comp mode has no hard-coded desc literal; the index.html #top10-desc
     fallback carries the live FY from the current metadata.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     #top10-desc reads 'FY<live> total compensation from proxy statements'
     on initial load; switching to the ratio mode then back to comp restores
     the live-year desc; zero page errors.

Usage:
  scripts/check_top10_comp_desc.py              # static + render
  scripts/check_top10_comp_desc.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

488th review (2026-11-16): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping. Pre-fix
defects: main() ignored render_checks()'s return value entirely,
so a missing d3 shim exited 0 with the 5 static PASS lines and
0 R-checks while the render half never ran (the silent-pass
variant; this guard prints no "N/N checks passed" summary line,
so the silence is the tell, although the docstring promises exit
2 for a missing shim); a missing playwright install exited 0 the
same way (the None branch returned 1-if-bad-else-0 on the statics
alone); and the INFRA sentinel itself is truthy, so a render half
returning INFRA would have exited 0 the same way (latent silent
pass, S4 form); and a transient render exception raised before
any R-check was uncaught (no retry wrapper) -- proved in-process
before the fix (~/workspace/sp500-488/pre488_proof.py: Test A-live
rc=0, 0 R-checks; Test A2 rc=0, 0 R-checks; Test A3 rc=0,
0 R-checks; Test B UNCATCHED RuntimeError on a simulated
transient Chromium launch stall). The proof monkeypatches
get_d3_bytes to None and stubs sys.modules['playwright.sync_api']
to None (ImportError) rather than moving the d3 cache aside (no
canary live concurrently this run; the monkeypatch touches no
shared state). main() already returned the exit code, so no
sys.exit() conversion was needed. The adopted main adds the
"----" + "%d/%d checks passed" summary the guard previously
lacked (the static-only and playwright-missing branches print it
too, matching the adopted siblings); the playwright-missing
branch keeps its skip shape (rc=0 on passing statics) and the
docstring's exit-2 promise for that branch is unchanged from the
pre-fix guard, per the 486th/487th precedent. render_checks()
already returns an explicit bool on success, so no
None-on-success fix was needed (458th note (27) checked).
Slowest unadopted shard-4 render guard by the multi-run history
plus the re-profile: freshest state 13.9s (2026-11-16T14:43Z
shard-4 run, tied with vol_tenure_keyboard) and multi-run median
11.7s vs vol_tenure_keyboard 13.9s fresh / 11.1s median and
zero_row_single_dim_badge 13.2s fresh / 11.2s median -- top10
leads the freshest state (tied) and the multi-run median; the
standalone re-profile this run flips the order (zero_row
11.61s vs top10 11.33s vs vol_tenure 10.63s), but the three
guards are within noise of each other, so the pick stands on the
freshest pre-run state plus the multi-run median, per the 486th
precedent; vol_tenure_keyboard stays queued next for shard 4.
"""
import json
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
INDEX_HTML = os.path.join(REPO, "index.html")
DATA_JSON = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_primary_fy():
    md = json.load(open(DATA_JSON, encoding="utf-8"))["metadata"]
    return md.get("primary_fiscal_year")


def static_checks():
    try:
        src = open(CHARTS_JS, encoding="utf-8").read()
        html = open(INDEX_HTML, encoding="utf-8").read()
        fy = live_primary_fy()
    except OSError as exc:
        print("INFRA: cannot read a source file: %s" % exc)
        return 2

    # S1: helper exists and derives the year from the live metadata path
    # (two-step deref: _chartData.compData.metadata, then .primary_fiscal_year).
    s1 = "function _top10CompDesc()" in src and re.search(
        r"function _top10CompDesc\(\)[\s\S]{0,600}compData\.metadata[\s\S]{0,200}primary_fiscal_year",
        src) is not None
    check("S1 _top10CompDesc() derives the year from _chartData.compData.metadata.primary_fiscal_year",
          s1, "" if s1 else "helper missing or does not read the live metadata path")

    # S2: drawTop10Chart uses the helper for the comp mode, not cfg.desc raw.
    s2 = re.search(
        r"var descText = \(mode === 'comp'\) \? _top10CompDesc\(\) : cfg\.desc;", src) is not None
    check("S2 drawTop10Chart renders the comp-mode desc via _top10CompDesc()",
          s2, "" if s2 else "drawTop10Chart does not use the helper for comp mode")

    # S3: no hard-coded 'FY 2024 total compensation from proxy statements'
    # string remains in charts.js.
    s3 = "FY 2024 total compensation from proxy statements" not in src
    check("S3 no hard-coded 'FY 2024 total compensation from proxy statements' in charts.js",
          s3, "" if s3 else "stale literal still present in charts.js")

    # S4: the comp mode block has no hard-coded desc property literal (the
    # year must come from _top10CompDesc at render time). The block may still
    # carry a // comment explaining the live render; match only a real
    # line-start 'desc:' property.
    comp_block = re.search(
        r"comp:\s*\{\s*title:[^}]*?filter:", src, re.DOTALL)
    s4 = (comp_block is not None
          and re.search(r"(?m)^\s*desc\s*:", comp_block.group(0)) is None)
    check("S4 TOP10_MODES.comp carries no hard-coded desc property",
          s4, "" if s4 else "comp mode still has a desc: property")

    # S5: the static HTML fallback carries the live FY from current metadata.
    m = re.search(r'<p class="section-desc" id="top10-desc">([^<]*)</p>', html)
    expected = "FY %d total compensation from proxy statements" % fy
    s5 = m is not None and m.group(1) == expected
    check("S5 index.html #top10-desc fallback == '%s'" % expected,
          s5, ("got %r" % (m.group(1) if m else None)) if not s5 else "")
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

    expected = "FY %d total compensation from proxy statements" % live_primary_fy()

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
                "window.d3 && document.getElementById('top10-desc')",
                timeout=90000)

            # R1: initial-load comp-mode desc tracks the live primary FY.
            desc = pg.evaluate(
                "document.getElementById('top10-desc').textContent")
            r1 = desc == expected
            check("R1 initial-load #top10-desc == '%s'" % expected,
                  r1, "got %r" % desc if not r1 else "")

            # R2: switch to the ratio mode then back to comp - the live-year
            # desc must be restored exactly.
            pg.click(".top10-mode-btn[data-mode='ratio']")
            pg.wait_for_timeout(800)
            ratio_desc = pg.evaluate(
                "document.getElementById('top10-desc').textContent")
            pg.click(".top10-mode-btn[data-mode='comp']")
            pg.wait_for_timeout(800)
            back_desc = pg.evaluate(
                "document.getElementById('top10-desc').textContent")
            r2 = ratio_desc != expected and back_desc == expected
            check("R2 mode switch round-trip restores the live-year comp desc",
                  r2, ("ratio=%r back=%r" % (ratio_desc, back_desc)) if not r2 else "")

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
        print("static-only: skipping render checks")
        failed = [n for (n, ok, d) in results if not ok]
        print("----")
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
        failed = [n for (n, ok, d) in results if not ok]
        print("----")
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    failed = [n for (n, ok, d) in results if not ok]
    if failed or not ok:
        print("----")
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("----")
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
