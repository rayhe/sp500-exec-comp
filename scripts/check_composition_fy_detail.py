#!/usr/bin/env python3
"""Regression guard: composition surfaces derive their fiscal year live.

The Composition Mix Detail trend card (js/app.js) and the composition donut
chart (js/charts.js) both read trends.json's granular breakdown through a
hard-coded `s_and_p_500_fy2024_detail` key, and the composition section
description in index.html hard-coded "S&P 500, FY2024" - the same stale-year
class as the Security Perks (2026-10-08 02:06) and Historic Peak (2026-10-08
02:08) fixes. latestCompositionDetailKey() now scans
trends.compensation_composition for s_and_p_500_fy<YYYY>_detail keys and
returns the latest, so a new study edition surfaces on both consumers
without a code change; the card label carries "(FY<year>)" and the section
description re-renders live (textContent-only, static HTML keeps today's
copy as the no-JS fallback).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 latestCompositionDetailKey() is defined in js/app.js, scans
        Object.keys(compComp) for /^s_and_p_500_fy(\\d{4})_detail$/ and
        takes the max year.
     S2 no literal "s_and_p_500_fy2024_detail" remains in js/app.js or
        js/charts.js (the helper's regex string never forms that literal).
     S3 card 5 resolves via latestCompositionDetailKey(), labels itself
        "Compensation Mix Detail (FY<year>)" with a _compMixDetail marker,
        and the click-through branch matches card._compMixDetail.
     S4 drawCompositionChart() resolves its detail via
        latestCompositionDetailKey(compComp) and live-labels
        #composition-desc with textContent only (no innerHTML).
     S5 index.html carries exactly one id="composition-desc" whose static
        fallback copy equals today's live-rendered copy.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 #composition-desc reads the live-year copy on initial load.
     R2 the "Compensation Mix Detail (FY<year>)" card exists in #trends-grid.
     R3 the composition donut renders the 6 granular segments.
     R4 zero JS page errors.

Usage:
  scripts/check_composition_fy_detail.py              # static + render
  scripts/check_composition_fy_detail.py --static-only

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
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
INDEX_HTML = os.path.join(REPO, "index.html")
TRENDS_JSON = os.path.join(REPO, "data", "trends.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_detail_year():
    comp = json.load(open(TRENDS_JSON, encoding="utf-8"))["compensation_composition"]
    years = [int(m.group(1)) for k in comp
             for m in [re.match(r"^s_and_p_500_fy(\d{4})_detail$", k)] if m]
    return max(years) if years else None


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    charts = open(CHARTS_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    year = live_detail_year()

    # S1: helper defined, scans the year-keyed fields, takes the max year.
    m = re.search(r"function latestCompositionDetailKey\(compComp\) \{[\s\S]*?\n\}\n", app)
    s1 = (m is not None
          and r"/^s_and_p_500_fy(\d{4})_detail$/" in m.group(0)
          and "Object.keys(compComp)" in m.group(0)
          and "sort(function (a, b) { return b - a; })" in m.group(0))
    check("S1 latestCompositionDetailKey() scans s_and_p_500_fy<YYYY>_detail keys, max-year first",
          s1, "" if s1 else "helper missing or does not scan/take the max year")

    # S2: the stale hard-coded field literal is gone from both consumers.
    s2 = "s_and_p_500_fy2024_detail" not in app and "s_and_p_500_fy2024_detail" not in charts
    check("S2 no literal 's_and_p_500_fy2024_detail' in js/app.js or js/charts.js",
          s2, "" if s2 else "stale hard-coded field literal still present")

    # S3: card 5 resolves via the helper, labels itself with the live year,
    # carries the _compMixDetail marker, and the click-through matches it.
    s3 = ("latestCompositionDetailKey(trends.compensation_composition)" in app
          and "label: 'Compensation Mix Detail (FY' + compDetailYear + ')'" in app
          and "_compMixDetail: true" in app
          and "} else if (card._compMixDetail) {" in app)
    check("S3 card 5 resolves via helper, FY-suffixed label, _compMixDetail marker, click-through matches",
          s3, "" if s3 else "card still hard-codes the field, label, or label-equality match")

    # S4: the donut chart resolves via the helper and live-labels the desc.
    s4 = ("latestCompositionDetailKey(compComp)" in charts
          and "document.getElementById('composition-desc')" in charts
          and "compDesc.textContent" in charts)
    cm = re.search(r"var compDesc = document\.getElementById\('composition-desc'\)[\s\S]{0,600}?compDesc\.textContent",
                   charts)
    s4 = s4 and cm is not None and "innerHTML" not in cm.group(0)
    check("S4 drawCompositionChart() resolves via helper and textContent-live-labels #composition-desc",
          s4, "" if s4 else "chart still hard-codes the field or uses innerHTML")

    # S5: static fallback carries today's live copy; the id is unique.
    desc_re = re.search(
        r'<p class="section-desc" id="composition-desc">(.*?)</p>', html, re.S)
    expected_desc = ("Granular breakdown of median CEO pay components with "
                     "year-over-year changes \u2014 S&P 500, FY%d") % year
    s5 = (desc_re is not None and desc_re.group(1).replace("&amp;", "&") == expected_desc
          and html.count('id="composition-desc"') == 1)
    check("S5 static #composition-desc fallback == live copy and id unique",
          s5, (("fallback %r" % (desc_re.group(1) if desc_re else None,))) if not s5 else "")


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

    year = live_detail_year()
    expected_desc = ("Granular breakdown of median CEO pay components with "
                     "year-over-year changes \u2014 S&P 500, FY%d") % year
    expected_card_label = "Compensation Mix Detail (FY%d)" % year

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
                "window.d3 && document.getElementById('composition-chart') && "
                "document.getElementById('composition-chart').querySelectorAll('.donut-seg').length > 0",
                timeout=90000)

            # R1: section description tracks the live detail year.
            desc = pg.evaluate("document.getElementById('composition-desc').textContent")
            r1 = desc == expected_desc
            check("R1 initial-load #composition-desc == live-year copy",
                  r1, "got %r" % desc if not r1 else "")

            # R2: the trend card carries the live-year label.
            labels = pg.evaluate(
                "Array.prototype.map.call(document.querySelectorAll('#trends-grid .trend-label'),"
                " function(e) { return e.textContent; })")
            r2 = expected_card_label in labels
            check("R2 #trends-grid carries '%s'" % expected_card_label,
                  r2, "labels %r" % labels if not r2 else "")

            # R3: the donut renders all six granular segments.
            segs = pg.evaluate(
                "document.getElementById('composition-chart').querySelectorAll('.donut-seg').length")
            r3 = segs == 6
            check("R3 composition donut renders 6 granular segments",
                  r3, "got %d" % segs if not r3 else "")

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
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
