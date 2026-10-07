#!/usr/bin/env python3
"""Regression guard: the "Compensation Structure by Sector" section
description must report the live tracked-company count from
data/compensation.json's metadata, not a hard-coded count.

Background (2026-10-07): the description hard-coded "computed from 500 DEF
14A proxy filings" while the tracked universe had grown to 518 companies -
the same stale-count class the header company-count badge (2026-09-24) and
the median-pay FY2025 sublabel (2026-10-07) fixes addressed. The fix renders
the count live from metadata.total_companies via renderSectorCompDesc(),
with the static HTML keeping today's count ("518") as the no-JS fallback.

This guard has two halves:
  A. Static: renderSectorCompDesc() exists, derives its count from
     metadata.total_companies, is textContent-only, and is called at load;
     index.html's #sector-comp-desc fallback carries today's live count and
     no hard-coded "500 DEF 14A" remains.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     #sector-comp-desc reads the live-count sentence on initial load; zero
     page errors.

Usage:
  scripts/check_sector_comp_desc.py              # static + render
  scripts/check_sector_comp_desc.py --static-only

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


def live_company_count():
    md = json.load(open(DATA_JSON, encoding="utf-8"))["metadata"]
    return md.get("total_companies")


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    n = live_company_count()

    # S1: helper exists and derives the count from metadata.total_companies.
    s1 = ("function renderSectorCompDesc(comp)" in src
          and re.search(r"function renderSectorCompDesc\(comp\)\s*\{.*?total_companies",
                        src, re.DOTALL) is not None)
    check("S1 renderSectorCompDesc() derives the count from metadata.total_companies",
          s1, "" if s1 else "helper missing or does not read total_companies")

    # S2: textContent-only - the helper never writes raw HTML into the desc.
    fn = src.split("function renderSectorCompDesc(comp)", 1)
    body = fn[1].split("\n}\n", 1)[0] if len(fn) > 1 else ""
    s2 = "innerHTML" not in body
    check("S2 renderSectorCompDesc() is textContent-only (no innerHTML)",
          s2, "" if s2 else "helper writes raw HTML")

    # S3: called at load next to the other live vintage renders.
    s3 = ("renderFooterVintage(comp);" in src
          and "renderHeaderCompanyCount(comp);" in src
          and "renderSectorCompDesc(comp);" in src)
    check("S3 renderSectorCompDesc(comp) is called at load with the other vintage renders",
          s3, "" if s3 else "load call site missing")

    # S4: static HTML fallback carries today's live count; no stale "500" remains.
    m = re.search(r'<p class="section-desc" id="sector-comp-desc">(.*?)</p>', html, re.DOTALL)
    fallback_ok = m is not None and ("%d DEF 14A proxy filings" % n) in m.group(1)
    check("S4 static #sector-comp-desc fallback carries today's live count (%d)" % n,
          fallback_ok, "" if fallback_ok else "fallback missing id or wrong count")
    s5 = "computed from 500 DEF 14A proxy filings" not in html
    check("S5 no stale 'computed from 500 DEF 14A proxy filings' remains in index.html",
          s5, "" if s5 else "stale 500-count copy still present")


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

    n = live_company_count()
    expected = ("Median CEO pay component mix across all 11 GICS sectors \u2014 "
                "computed from %s DEF 14A proxy filings. Cell intensity shows "
                "component weight; click any cell to filter the table."
                % "{:,}".format(n))

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
                "window.d3 && document.getElementById('sector-comp-desc')"
                " && document.getElementById('sector-comp-desc').textContent.length > 0",
                timeout=90000)

            # R1: initial-load desc tracks the live company count.
            text = pg.evaluate(
                "document.getElementById('sector-comp-desc').textContent")
            r1 = text == expected
            check("R1 initial-load sector-comp desc == live-count sentence (%d)" % n,
                  r1, "got %r" % text if not r1 else "")

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
    if not static_only:
        rc = render_checks()
        if rc is None:
            print("render checks skipped")
    fails = [n for n, ok, _ in results if not ok]
    print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
    if fails:
        print("FAILED: " + ", ".join(fails))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
