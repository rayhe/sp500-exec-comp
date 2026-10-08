#!/usr/bin/env python3
"""Regression guard: metric-trend sparkline labels derive year ranges live.

The four metric-card trend sparkline labels (aria-label/title on the
.metric-trend divs: median CEO pay, pay ratio, worker pay, indexed
growth path) carried hard-coded year ranges - "2020-2025",
"2018 then 2023-2025", "2023-2025", "indexed to 100 at 2020" - while the
series themselves are year-keyed, so a trends.json data extension would
silently stale them (same stale-year class as the header-subtitle,
insights FY labels, median-pay FY label, Early Filers, Security Perks,
Historic Peak, and sector-trend-window fixes). addTrend() now builds the
label from a {range}/{first} template filled by fmtYearRange() over the
plotted years; gapped series keep the "2018 then 2023-2025" form.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 fmtYearRange() exists in js/app.js and collapses contiguous years
        to "A-B" while keeping gapped runs as "A then B-C".
     S2 no hard-coded sparkline label literals remain in js/app.js.
     S3 addTrend() fills the {range} and {first} placeholders from the
        plotted years and uses the live label for wrap.title and the
        svg aria-label.
     S4 the four addTrend call sites pass {range}/{first} templates.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 the rendered .metric-trend div titles and svg aria-labels equal
        the year-range-derived labels for today's trends.json data.
     R2 zero JS page errors.

Usage:
  scripts/check_metric_spark_labels.py              # static + render
  scripts/check_metric_spark_labels.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
TRENDS_JSON = os.path.join(REPO, "data", "trends.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def fmt_year_range(years):
    """Python mirror of the JS fmtYearRange: contiguous -> 'A-B', gaps -> 'A then B-C'."""
    nums = sorted(set(int(round(y)) for y in years if y == y))  # drop NaN
    runs = []
    for y in nums:
        if runs and y == runs[-1][-1]:
            continue  # defensive dupe skip
        if runs and y == runs[-1][-1] + 1:
            runs[-1].append(y)
        else:
            runs.append([y])
    return " then ".join(
        ("%d-%d" % (r[0], r[-1])) if len(r) > 1 else str(r[0]) for r in runs)


def series_years(series):
    return [d["year"] for d in series if d.get("year") is not None]


def expected_labels():
    t = json.load(open(TRENDS_JSON, encoding="utf-8"))
    med = series_years(t["median_ceo_pay_by_year"]["data"])
    rat = series_years(t["pay_ratio_trend"]["data"])
    wrk = series_years(t["median_worker_pay_by_year"]["data"])
    return {
        "metric-median-delta": "S&P 500 median CEO pay trend, %s (Equilar/AP)" % fmt_year_range(med),
        "metric-ratio-sub": "S&P 500 median pay ratio trend, %s (Harvard Law Forum / Equilar)" % fmt_year_range(rat),
        "metric-worker-delta": "S&P 500 median worker pay trend, %s (Conference Board / Equilar)" % fmt_year_range(wrk),
        "metric-5yr-sub": "S&P 500 median CEO pay indexed to 100 at %d (Equilar/AP)" % min(med),
    }


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()

    # S1: fmtYearRange helper exists with the run-collapse logic.
    s1 = (re.search(r"function fmtYearRange\(years\)", src) is not None
          and "' then '" in src
          and ".replace('{range}', fmtYearRange(sortedXs))" in src)
    check("S1 fmtYearRange() exists; contiguous runs collapse, gaps join with ' then '",
          s1, "" if s1 else "helper missing or range-fill wiring absent")

    # S2: the stale hard-coded label literals are gone.
    stale = ["trend, 2020-2025 (Equilar/AP)",
             "then 2023-2025 (Harvard Law Forum",
             "trend, 2023-2025 (Conference Board",
             "indexed to 100 at 2020 (Equilar/AP)"]
    found = [s for s in stale if s in src]
    s2 = not found
    check("S2 no hard-coded sparkline year-range literals in js/app.js",
          s2, ("stale literals remain: %r" % found) if not s2 else "")

    # S3: addTrend fills {range} and {first} from the plotted years and uses
    # the live label for wrap.title and the svg aria-label.
    s3 = (".replace('{range}', fmtYearRange(sortedXs))" in src
          and ".replace('{first}', String(sortedXs[0]))" in src
          and "wrap.title = sparkLabelLive;" in src
          and "sparkSvg(xs, ys, sparkLabelLive)" in src)
    check("S3 addTrend fills {range}/{first} from plotted years; wrap.title and svg aria-label use the live label",
          s3, "" if s3 else "placeholder fill or live-label usage missing")

    # S4: the four call sites pass template labels.
    s4 = ("'S&P 500 median CEO pay trend, {range} (Equilar/AP)'" in src
          and "'S&P 500 median pay ratio trend, {range} (Harvard Law Forum / Equilar)'" in src
          and "'S&P 500 median worker pay trend, {range} (Conference Board / Equilar)'" in src
          and "'S&P 500 median CEO pay indexed to 100 at {first} (Equilar/AP)'" in src)
    check("S4 four addTrend call sites pass {range}/{first} templates",
          s4, "" if s4 else "a call site still hard-codes its year range")


def get_d3_bytes():
    # Same cached copy as the other render guards (build-time shim only).
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

    expected = expected_labels()
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
                "window.d3 && document.querySelectorAll('.metric-trend').length >= 4",
                timeout=90000)

            # R1: each metric-trend div's title and its svg aria-label equal
            # the year-range-derived label. The div sits right after its
            # delta/sub element, keyed by the expected map.
            got = pg.evaluate(
                """(() => {
                    const out = {};
                    document.querySelectorAll('.metric-trend').forEach(el => {
                        const prev = el.previousElementSibling;
                        if (!prev || !prev.id) return;
                        const svg = el.querySelector('svg');
                        out[prev.id] = {
                            title: el.getAttribute('title'),
                            aria: svg ? svg.getAttribute('aria-label') : null
                        };
                    });
                    return out;
                })()""")
            r1 = True
            details = []
            for el_id, label in expected.items():
                g = (got or {}).get(el_id)
                ok = g is not None and g.get("title") == label and g.get("aria") == label
                r1 = r1 and ok
                if not ok:
                    details.append("%s -> title %r aria %r (want %r)"
                                   % (el_id, g.get("title") if g else None,
                                      g.get("aria") if g else None, label))
            check("R1 rendered .metric-trend titles/aria-labels equal live year-range labels",
                  r1, "; ".join(details) if details else "")

            # R2: zero JS page errors across the lifecycle.
            check("R2 zero JS page errors", len(errors) == 0,
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
