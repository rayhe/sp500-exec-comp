#!/usr/bin/env python3
"""Regression guard: the Median CEO Pay metric-card sublabel must track the
live primary fiscal year from data/compensation.json's metadata, not a
hard-coded year.

Background (2026-10-07): the 2026-10-06 anchor promotion moved the primary
fiscal year from FY2024 to FY2025 (425 companies to FY2025, 22 non-calendar
filers to FY2026) and recomputed aggregate_stats.median_ceo_pay ($17,188,658)
on the new anchors, but js/app.js still stamped the card sublabel as
'S&P 500, FY2024' in both populateMetrics() and _restoreDefaultMetrics()
(the sector-filter restore path). The value shown was FY2025-anchored while
the label claimed FY2024 - the same stale-label class the header
company-count fix (2026-09-24) addressed. The fix renders the sublabel live
from metadata.primary_fiscal_year via _medianPayFYLabel().

This guard has two halves:
  A. Static: _medianPayFYLabel() exists and derives 'S&P 500, FY<year>' from
     its argument; populateMetrics() passes comp.metadata.primary_fiscal_year;
     _restoreDefaultMetrics() passes _sp500Metrics.primaryFY; no hard-coded
     'S&P 500, FY2024' assignment to metric-median-delta remains;
     setupReactiveMetrics() captures primaryFY from metadata.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     #metric-median-delta reads 'S&P 500, FY<live primary_fiscal_year>' on
     initial load; applying then clearing a sector filter
     (window._updateMetricsStrip) restores the same live label; zero page
     errors.

Usage:
  scripts/check_median_pay_fy_label.py              # static + render
  scripts/check_median_pay_fy_label.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

486th review (2026-11-16): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping. Pre-fix
defects were BOTH 429th-review classes: main() ignored
render_checks()'s return value, so a missing d3 shim exited 0 with
"5/5 checks passed" while the render half never ran (the silent-pass
variant, 430th-review shape); and the INFRA sentinel itself is
truthy, so a render half returning INFRA would have exited 0 the
same way (latent silent pass, S4 form); and a transient render
exception raised before any R-check was uncaught (no retry wrapper)
-- proved in-process before the fix
(~/workspace/sp500-486/pre486_proof.py: Test A-live rc=0, "5/5
checks passed", 0 R-checks; Test A2 rc=0, "5/5 checks passed", 0
R-checks; Test B UNCATCHED RuntimeError on a simulated transient
Chromium launch stall). The proof monkeypatches get_d3_bytes to
None rather than moving the d3 cache aside (no canary live
concurrently this run; the monkeypatch touches no shared state).
main() previously called sys.exit() directly, so the restructure
also converts it to return the exit code. The static-only and
playwright-missing branches keep the guard's existing "%d/%d checks
passed" summary format. render_checks() already returns an explicit
bool on success, so no None-on-success fix was needed (458th note
(27) checked). Slowest unadopted shard-2 render guard by the
multi-run history plus the re-profile: freshest state 9.0s
(2026-11-16T10:32Z shard-2 run) and multi-run median 9.1s vs
sector_trend_fy_label 7.2s fresh / 7.9s median and
composition_fy_detail 6.6s fresh / 7.4s median -- median_pay leads
the freshest state and the multi-run median; the standalone
re-profile this run flips the order (composition 10.72s vs
median_pay 10.01s vs sector_trend 7.93s), but the three guards are
within noise of each other (all-readings medians 9.1s / 7.9s /
7.4s), so the pick stands on the freshest pre-run state plus the
multi-run median, and composition_fy_detail stays queued next for
shard 2.
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
APP_JS = os.path.join(REPO, "js", "app.js")
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
        src = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # S1: helper exists and derives the label from its fiscal-year argument.
    s1 = ("function _medianPayFYLabel(fy)" in src
          and re.search(r"function _medianPayFYLabel\(fy\)\s*\{[^}]*FY['\"]?\s*\+\s*fy", src) is not None)
    check("S1 _medianPayFYLabel() derives 'S&P 500, FY<year>' from its argument",
          s1, "" if s1 else "helper missing or does not interpolate the year")

    # S2: populateMetrics passes metadata.primary_fiscal_year (not a literal).
    s2 = "_medianPayFYLabel(comp.metadata && comp.metadata.primary_fiscal_year)" in src
    check("S2 populateMetrics labels the median card from metadata.primary_fiscal_year",
          s2, "" if s2 else "populateMetrics does not pass the live fiscal year")

    # S3: the sector-filter restore path uses the stored live fiscal year.
    s3 = "_medianPayFYLabel(_sp500Metrics.primaryFY)" in src
    check("S3 _restoreDefaultMetrics labels the median card from _sp500Metrics.primaryFY",
          s3, "" if s3 else "restore path does not use the live fiscal year")

    # S4: no hard-coded 'S&P 500, FY2024' assignment to the median delta remains.
    hard = re.findall(r"metric-median-delta['\"]\)\.(?:textContent|innerHTML)\s*=\s*'S&P 500, FY2024'", src)
    s4 = len(hard) == 0
    check("S4 no hard-coded 'S&P 500, FY2024' assignment to #metric-median-delta remains",
          s4, ("found %d hard-coded assignment(s)" % len(hard)) if not s4 else "")

    # S5: setupReactiveMetrics captures primaryFY from metadata.
    s5 = "primaryFY: (comp.metadata && comp.metadata.primary_fiscal_year) || null" in src
    check("S5 setupReactiveMetrics captures primaryFY from comp.metadata",
          s5, "" if s5 else "primaryFY not captured in _sp500Metrics")

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
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

    expected = "S&P 500, FY%d" % live_primary_fy()

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
                "window.d3 && document.getElementById('metric-median-delta')"
                " && document.getElementById('metric-median-delta').textContent.length > 0",
                timeout=90000)

            # R1: initial-load label tracks the live primary fiscal year.
            label = pg.evaluate(
                "document.getElementById('metric-median-delta').textContent")
            r1 = label == expected
            check("R1 initial-load median-card sublabel == '%s'" % expected,
                  r1, "got %r" % label if not r1 else "")

            # R2: sector filter then clear restores the same live label.
            pg.evaluate("window._updateMetricsStrip('Technology')")
            pg.wait_for_timeout(600)
            filtered = pg.evaluate(
                "document.getElementById('metric-median-delta').textContent")
            pg.evaluate("window._updateMetricsStrip(null)")
            pg.wait_for_timeout(800)
            restored = pg.evaluate(
                "document.getElementById('metric-median-delta').textContent")
            r2 = restored == expected
            check("R2 sector filter then clear restores '%s'" % expected,
                  r2, "filtered=%r restored=%r" % (filtered, restored) if not r2 else "")

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
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
        failed = [r for r in results if not r[1]]
        return 1 if failed else 0
    failed = [r for r in results if not r[1]]
    if failed or not ok:
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
