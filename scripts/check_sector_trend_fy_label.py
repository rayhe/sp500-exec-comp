#!/usr/bin/env python3
"""Regression guard: sector-analytics trend window renders live from metadata.

The sector-analytics "Trend" column computed its 3-year median-CEO-pay
window from a hard-coded [2023, 2024, 2025] array, and the section
description, column header label, header title attr, and tooltip all
carried hard-coded "FY2023-2025" / "Trend FY23-25" copy - the same
stale-year class as the header-subtitle (2026-10-07 20:20) and
top-10-comp-desc (2026-10-07 19:40) fixes. renderSectorAnalytics() now
derives the window as [FY-2, FY-1, FY] from
metadata.primary_fiscal_year, and renderSectorAnalyticsLiveLabels()
renders the description, header label, and title attr live; the tooltip
in trendCellHtml() builds its year labels from the same window.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 saTrendYears is derived from compData.metadata.primary_fiscal_year
        as a [FY-2, FY-1, FY] window (saFy-2 / saFy-1 / saFy).
     S2 no hard-coded "var saTrendYears = [2023, 2024, 2025]" remains in
        js/app.js.
     S3 renderSectorAnalyticsLiveLabels() exists and is textContent/title
        only (no innerHTML); it is invoked inside the IIFE.
     S4 the static HTML fallback carries today's live copy
        (desc "(FY2023-2025)", header "Trend FY23-25", title attr
        "FY2023 to FY2025") and ids sector-analytics-desc / sa-trend-th
        occur exactly once.
     S5 trendCellHtml() builds yrTxt/tip from saTrendYears (no hard-coded
        '2023: ... FY2023-2025' tooltip literals).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 #sector-analytics-desc reads the live-window copy on initial load.
     R2 #sa-trend-th label and title attr track the live window.
     R3 zero JS page errors.

Usage:
  scripts/check_sector_trend_fy_label.py              # static + render
  scripts/check_sector_trend_fy_label.py --static-only

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
INDEX_HTML = os.path.join(REPO, "index.html")
DATA_JSON = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_trend_window():
    fy = json.load(open(DATA_JSON, encoding="utf-8"))["metadata"].get("primary_fiscal_year")
    return (fy - 2, fy - 1, fy)


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    y0, y1, y2 = live_trend_window()

    # S1: window derived from compData.metadata.primary_fiscal_year.
    s1 = re.search(
        r"primary_fiscal_year[^\n;]{0,120}\s*[:?][\s\S]{0,300}var saTrendYears\s*=\s*\[\s*saFy\s*-\s*2\s*,\s*saFy\s*-\s*1\s*,\s*saFy\s*\]",
        src) is not None
    check("S1 saTrendYears derived as [saFy-2, saFy-1, saFy] from compData.metadata.primary_fiscal_year",
          s1, "" if s1 else "derivation missing or window not anchored on the live FY")

    # S2: the stale hard-coded window is gone.
    s2 = "var saTrendYears = [2023, 2024, 2025]" not in src
    check("S2 no hard-coded 'var saTrendYears = [2023, 2024, 2025]' in js/app.js",
          s2, "" if s2 else "stale hard-coded window still present")

    # S3: live-label renderer exists, is textContent/title-only, and runs.
    # (Anchor the capture on the invocation line so the inner if-blocks'
    # closers can't truncate the function body.)
    m = re.search(
        r"function renderSectorAnalyticsLiveLabels\(\)[\s\S]*?\n        \}\n        renderSectorAnalyticsLiveLabels\(\);",
        src)
    s3 = (m is not None and "textContent" in m.group(0) and ".title" in m.group(0)
          and "innerHTML" not in m.group(0)
          and "renderSectorAnalyticsLiveLabels();" in src)
    check("S3 renderSectorAnalyticsLiveLabels() exists, textContent/title-only, and is invoked",
          s3, "" if s3 else "helper missing, uses innerHTML, or is never invoked")

    # S4: static HTML fallback carries today's live copy; ids unique.
    desc_re = re.search(
        r'<p class="section-desc" id="sector-analytics-desc">(.*?)</p>', html, re.S)
    expected_desc = ("Cross-sector comparison of CEO compensation metrics \u2014 median, mean, "
                     "equity mix, pay ratios, governance, erosion risk, top earner per sector, "
                     "and median pay trajectory (FY%d-%d). Click a row to filter the main table.") % (y0, y2)
    th_re = re.search(
        r'<th[^>]*id="sa-trend-th"[^>]*title="([^"]*)"[^>]*>([^<]*)</th>|'
        r'<th[^>]*title="([^"]*)"[^>]*id="sa-trend-th"[^>]*>([^<]*)</th>', html)
    expected_title = ("Sector median CEO total compensation, FY%d to FY%d, computed live from "
                      "DEF 14A exec rows. Anchor-year values use verified company totals; other "
                      "years match the CEO by SCT title (transition years take the higher-paid "
                      "CEO row). Sorts by %d to %d change.") % (y0, y2, y0, y2)
    expected_label = "Trend FY%s-%s" % (str(y0)[-2:], str(y2)[-2:])
    if th_re:
        got_title = th_re.group(1) if th_re.group(1) is not None else th_re.group(3)
        got_label = th_re.group(2) if th_re.group(2) is not None else th_re.group(4)
    else:
        got_title = got_label = None
    s4 = (desc_re is not None and desc_re.group(1) == expected_desc
          and html.count('id="sector-analytics-desc"') == 1
          and got_title == expected_title and got_label == expected_label
          and html.count('id="sa-trend-th"') == 1)
    check("S4 static fallback == live window copy (desc/header/title) and ids unique",
          s4, ("desc %r label %r title %r" % (desc_re.group(1) if desc_re else None,
              got_label, got_title)) if not s4 else "")

    # S5: tooltip builds its year labels from the live window.
    s5 = ("'2023: ' + fmt(meds[0])" not in src
          and "FY2023-2025' + (pct" not in src
          and "saTrendYears.map(function(y, i) { return y + ': ' + fmt(meds[i]); })" in src)
    check("S5 trendCellHtml tooltip year labels come from saTrendYears, no hard-coded '2023:' / 'FY2023-2025'",
          s5, "" if s5 else "stale hard-coded tooltip literals remain")


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

    y0, y1, y2 = live_trend_window()
    expected_desc = ("Cross-sector comparison of CEO compensation metrics \u2014 median, mean, "
                     "equity mix, pay ratios, governance, erosion risk, top earner per sector, "
                     "and median pay trajectory (FY%d\u2013%d). Click a row to filter the main table.") % (y0, y2)
    expected_label = "Trend FY%s-%s" % (str(y0)[-2:], str(y2)[-2:])
    expected_title = ("Sector median CEO total compensation, FY%d to FY%d, computed live from "
                      "DEF 14A exec rows. Anchor-year values use verified company totals; other "
                      "years match the CEO by SCT title (transition years take the higher-paid "
                      "CEO row). Sorts by %d to %d change.") % (y0, y2, y0, y2)

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
                "window.d3 && document.getElementById('sector-analytics-tbody') && "
                "document.getElementById('sector-analytics-tbody').children.length > 0",
                timeout=90000)

            # R1: section description tracks the live window.
            desc = pg.evaluate("document.getElementById('sector-analytics-desc').textContent")
            r1 = desc == expected_desc
            check("R1 initial-load #sector-analytics-desc == live-window copy",
                  r1, "got %r" % desc if not r1 else "")

            # R2: header label and title attr track the live window.
            th_label = pg.evaluate("document.getElementById('sa-trend-th').textContent")
            th_title = pg.evaluate("document.getElementById('sa-trend-th').title")
            r2 = th_label == expected_label and th_title == expected_title
            check("R2 #sa-trend-th label/title track the live window",
                  r2, "label %r title %r" % (th_label, th_title) if not r2 else "")

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
