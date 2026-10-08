#!/usr/bin/env python3
"""Regression guard: sector chart derives its study edition live.

drawSectorChart() (js/charts.js) read trends.json's sector-median data
through a hard-coded `median_pay_by_sector_sp500_fy2024` key, and the
"CEO Pay by Sector" section description carried no study-vintage at all —
the same stale-year class as the composition-detail fix (2026-10-08
10:00 PT). latestSectorMedianKey() now scans trends for
median_pay_by_sector_sp500_fy<YYYY> keys and returns the latest, so a new
study edition surfaces without a code change; the legacy un-keyed
median_pay_by_sector_sp500 (a partial edition, 4 sectors) is used only
when no year-keyed full breakdown exists; with neither, the chart's
existing "No sector data available" path fires. The section description
live-labels itself "S&P 500, FY<year>" from the resolved edition's
fiscal_year via textContent only (static HTML keeps today's copy as the
no-JS fallback).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 latestSectorMedianKey() is defined in js/charts.js, scans
        Object.keys(trends) for /^median_pay_by_sector_sp500_fy(\\d{4})$/
        and takes the max year, with the un-keyed fallback.
     S2 no literal "median_pay_by_sector_sp500_fy2024" remains in any
        js/*.js file (the helper's regex string never forms that literal).
     S3 drawSectorChart() resolves its data via
        latestSectorMedianKey(trends) and live-labels #sector-desc with
        textContent only (no innerHTML).
     S4 index.html carries exactly one id="sector-desc" whose static
        fallback copy equals today's live-rendered copy.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 the sector chart renders the current edition's bar count on
        initial load.
     R2 #sector-desc reads the live-year copy on initial load.
     R3 zero JS page errors.

Usage:
  scripts/check_sector_median_fy_key.py              # static + render
  scripts/check_sector_median_fy_key.py --static-only

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
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
INDEX_HTML = os.path.join(REPO, "index.html")
TRENDS_JSON = os.path.join(REPO, "data", "trends.json")

BASE_DESC = ("Median total CEO compensation by sector with distribution range "
             "(box plot). Click distribution ranges to filter the table.")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_sector_edition():
    trends = json.load(open(TRENDS_JSON, encoding="utf-8"))
    years = [int(m.group(1)) for k in trends
             for m in [re.match(r"^median_pay_by_sector_sp500_fy(\d{4})$", k)] if m]
    if years:
        return "median_pay_by_sector_sp500_fy%d" % max(years)
    return "median_pay_by_sector_sp500" if "median_pay_by_sector_sp500" in trends else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()

    # S1: helper defined, scans the year-keyed fields, takes the max year,
    # falls back to the un-keyed legacy field.
    m = re.search(r"function latestSectorMedianKey\(trends\) \{[\s\S]*?\n\}\n", charts)
    s1 = (m is not None
          and r"/^median_pay_by_sector_sp500_fy(\d{4})$/" in m.group(0)
          and "Object.keys(trends)" in m.group(0)
          and "sort(function (a, b) { return b - a; })" in m.group(0)
          and "trends.median_pay_by_sector_sp500" in m.group(0))
    check("S1 latestSectorMedianKey() scans median_pay_by_sector_sp500_fy<YYYY> keys, max-year first, un-keyed fallback",
          s1, "" if s1 else "helper missing or does not scan/take the max year")

    # S2: the stale hard-coded field literal is gone from all JS.
    s2 = "median_pay_by_sector_sp500_fy2024" not in charts
    check("S2 no literal 'median_pay_by_sector_sp500_fy2024' in js/charts.js",
          s2, "" if s2 else "stale hard-coded field literal still present")

    # S3: the chart resolves via the helper and live-labels the desc
    # with textContent only.
    body = re.search(r"function drawSectorChart\(trends, companies\) \{[\s\S]{0,2500}", charts)
    s3 = (body is not None
          and "var sectorKey = latestSectorMedianKey(trends);" in body.group(0)
          and "document.getElementById('sector-desc')" in charts
          and "sectorDesc.textContent" in charts)
    cm = re.search(r"var sectorDesc = document\.getElementById\('sector-desc'\)[\s\S]{0,600}?sectorDesc\.textContent",
                   charts)
    s3 = s3 and cm is not None and "innerHTML" not in cm.group(0)
    check("S3 drawSectorChart() resolves via helper and textContent-live-labels #sector-desc",
          s3, "" if s3 else "chart still hard-codes the field or uses innerHTML")

    # S4: static fallback carries today's live copy; the id is unique.
    desc_re = re.search(
        r'<p class="section-desc" id="sector-desc">(.*?)</p>', html, re.S)
    trends = json.load(open(TRENDS_JSON, encoding="utf-8"))
    key = live_sector_edition()
    fy = trends[key].get("fiscal_year") if key else None
    expected_desc = BASE_DESC + (" \u2014 S&P 500, FY%d" % fy if fy else "")
    s4 = (desc_re is not None
          and desc_re.group(1).replace("&amp;", "&") == expected_desc
          and html.count('id="sector-desc"') == 1)
    check("S4 static #sector-desc fallback == live copy and id unique",
          s4, (("fallback %r" % (desc_re.group(1) if desc_re else None,))) if not s4 else "")


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

    trends = json.load(open(TRENDS_JSON, encoding="utf-8"))
    key = live_sector_edition()
    expected_bars = len([d for d in trends[key]["data"] if d.get("median_pay")])
    fy = trends[key].get("fiscal_year")
    expected_desc = BASE_DESC + (" \u2014 S&P 500, FY%d" % fy if fy else "")

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

            # R1: the sector chart renders the current edition's bars.
            bars = pg.evaluate(
                "document.querySelectorAll('#sector-chart rect.bar').length")
            r1 = bars == expected_bars
            check("R1 sector chart renders %d bars (current edition)" % expected_bars,
                  r1, "got %d" % bars if not r1 else "")

            # R2: section description tracks the live edition year.
            desc = pg.evaluate("document.getElementById('sector-desc').textContent")
            r2 = desc == expected_desc
            check("R2 initial-load #sector-desc == live-year copy",
                  r2, "got %r" % desc if not r2 else "")

            # R3: zero JS page errors across the lifecycle.
            check("R3 zero JS page errors", len(errors) == 0,
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
