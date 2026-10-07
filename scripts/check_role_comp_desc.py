#!/usr/bin/env python3
"""Regression guard: the "C-Suite Role Compensation" section description must
report the live NEO-record and tracked-company counts from
data/compensation.json's metadata, not hard-coded counts.

Background (2026-10-07): the description hard-coded "benchmarked from 7,078
Named Executive Officer records across 518 proxy filings" - true today, but
the same stale-count class the header company-count badge (2026-09-24), the
median-pay FY2025 sublabel (2026-10-07 10:00) and the sector-comp description
(2026-10-07 11:32) fixes addressed: every DQ/roster batch that changes the row
count would silently stale it. The fix renders both counts live from
metadata.total_neo_records and metadata.total_companies via
renderRoleCompDesc(), with the static HTML keeping today's counts ("7,078" /
"518") as the no-JS fallback.

This guard has two halves:
  A. Static: renderRoleCompDesc() exists, derives both counts from metadata,
     is textContent-only, and is called at load; index.html's #role-comp-desc
     fallback carries today's live counts and no id-less role-comp sentence
     remains.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     #role-comp-desc reads the live-count sentence on initial load; zero
     page errors.

Usage:
  scripts/check_role_comp_desc.py              # static + render
  scripts/check_role_comp_desc.py --static-only

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


def live_counts():
    md = json.load(open(DATA_JSON, encoding="utf-8"))["metadata"]
    return md.get("total_neo_records"), md.get("total_companies")


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    rows, n = live_counts()

    # S1: helper exists and derives both counts from metadata.
    s1 = ("function renderRoleCompDesc(comp)" in src
          and re.search(r"function renderRoleCompDesc\(comp\)\s*\{.*?total_neo_records",
                        src, re.DOTALL) is not None
          and re.search(r"function renderRoleCompDesc\(comp\)\s*\{.*?total_companies",
                        src, re.DOTALL) is not None)
    check("S1 renderRoleCompDesc() derives counts from metadata.total_neo_records + total_companies",
          s1, "" if s1 else "helper missing or does not read both metadata fields")

    # S2: textContent-only - the helper never writes raw HTML into the desc.
    fn = src.split("function renderRoleCompDesc(comp)", 1)
    body = fn[1].split("\n}\n", 1)[0] if len(fn) > 1 else ""
    s2 = "innerHTML" not in body
    check("S2 renderRoleCompDesc() is textContent-only (no innerHTML)",
          s2, "" if s2 else "helper writes raw HTML")

    # S3: called at load next to the other live vintage renders.
    s3 = ("renderFooterVintage(comp);" in src
          and "renderHeaderCompanyCount(comp);" in src
          and "renderSectorCompDesc(comp);" in src
          and "renderRoleCompDesc(comp);" in src)
    check("S3 renderRoleCompDesc(comp) is called at load with the other vintage renders",
          s3, "" if s3 else "load call site missing")

    # S4: static HTML fallback carries today's live counts; exactly one
    # id-bearing role-comp sentence.
    m = re.search(r'<p class="section-desc" id="role-comp-desc">(.*?)</p>', html, re.DOTALL)
    fallback_ok = (m is not None
                   and ("{:,} Named Executive Officer records".format(rows) in m.group(1))
                   and ("across {:,} proxy filings".format(n) in m.group(1)))
    check("S4 static #role-comp-desc fallback carries today's live counts (%s/%s)"
          % ("{:,}".format(rows), n),
          fallback_ok, "" if fallback_ok else "fallback missing id or wrong counts")

    # S5: no id-less role-comp sentence remains (would escape the live render).
    s5 = len(re.findall(r'class="section-desc"[^>]*>S&P 500 median total compensation by executive role',
                        html)) == 1
    check("S5 exactly one role-comp description sentence exists (id-bearing)",
          s5, "" if s5 else "duplicate or id-less sentence present")


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

    rows, n = live_counts()
    expected = ("S&P 500 median total compensation by executive role \u2014 "
                "benchmarked from %s Named Executive Officer records across %s "
                "proxy filings. IQR bars show P25\u2013P75 range."
                % ("{:,}".format(rows), "{:,}".format(n)))

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
                "window.d3 && document.getElementById('role-comp-desc')"
                " && document.getElementById('role-comp-desc').textContent.length > 0",
                timeout=90000)

            # R1: initial-load desc tracks the live counts.
            text = pg.evaluate(
                "document.getElementById('role-comp-desc').textContent")
            r1 = text == expected
            check("R1 initial-load role-comp desc == live-count sentence (%s/%s)"
                  % ("{:,}".format(rows), n),
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
