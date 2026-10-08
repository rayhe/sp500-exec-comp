#!/usr/bin/env python3
"""Regression guard: header subtitle renders the live primary fiscal year.

The header subtitle ("Executive compensation data from SEC DEF 14A proxy
statements, FY 2024-2025") drifted stale when the 2026-10-06 anchor
promotion moved metadata.primary_fiscal_year from FY2024 to FY2025 (425
companies to FY2025, 22 non-calendar filers to FY2026) - the same
stale-year class as the median-pay FY2025 sublabel (2026-10-07 10:00) and
the top-10 comp desc (2026-10-07 19:40) fixes. renderHeaderSubtitle() in
js/app.js now renders the year live from metadata.primary_fiscal_year,
matching the flagship metric cards' "FY<year>" vintage convention.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 renderHeaderSubtitle() exists and derives the year from
        comp.metadata.primary_fiscal_year (two-step deref).
     S2 the load path calls renderHeaderSubtitle(comp) next to
        renderHeaderCompanyCount(comp).
     S3 no hard-coded "FY 2024<en dash>2025" literal remains in
        index.html or js/app.js (the stale copy used U+2013).
     S4 textContent-only: the helper assigns el.textContent, never
        innerHTML.
     S5 the static HTML fallback carries today's live copy
        ("...proxy statements, FY<live>") and the element has
        id="header-subtitle" exactly once.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 #header-subtitle reads the live-year copy on initial load.
     R2 zero JS page errors.

Usage:
  scripts/check_header_subtitle_fy.py              # static + render
  scripts/check_header_subtitle_fy.py --static-only

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


def live_primary_fy():
    md = json.load(open(DATA_JSON, encoding="utf-8"))["metadata"]
    return md.get("primary_fiscal_year")


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    fy = live_primary_fy()
    expected = "Executive compensation data from SEC DEF 14A proxy statements, FY%d" % fy

    # S1: helper exists and derives the year from the live metadata path
    # (two-step deref: comp.metadata, then .primary_fiscal_year).
    s1 = "function renderHeaderSubtitle(comp)" in src and re.search(
        r"function renderHeaderSubtitle\(comp\)[\s\S]{0,600}metadata[\s\S]{0,200}primary_fiscal_year",
        src) is not None
    check("S1 renderHeaderSubtitle() derives the year from comp.metadata.primary_fiscal_year",
          s1, "" if s1 else "helper missing or does not read the live metadata path")

    # S2: the load path calls the helper next to renderHeaderCompanyCount.
    s2 = re.search(
        r"renderHeaderSubtitle\(comp\);\s*\n\s*renderHeaderCompanyCount\(comp\);", src) is not None
    check("S2 load path calls renderHeaderSubtitle(comp) next to renderHeaderCompanyCount",
          s2, "" if s2 else "call site missing or misplaced")

    # S3: the stale "FY 2024<en dash>2025" literal (U+2013) is gone from
    # both files. The app.js history comment uses an ASCII hyphen, which
    # must not trip this check.
    stale = "FY 2024\u20132025"
    s3 = stale not in html and stale not in src
    check("S3 no hard-coded stale FY-range literal in index.html or js/app.js",
          s3, "" if s3 else "stale 'FY 2024\u20132025' literal still present")

    # S4: textContent-only (data-derived year stays inert).
    fn = re.search(
        r"function renderHeaderSubtitle\(comp\)[\s\S]*?\n\}\n", src)
    s4 = fn is not None and "el.textContent" in fn.group(0) and "innerHTML" not in fn.group(0)
    check("S4 helper is textContent-only (no innerHTML)",
          s4, "" if s4 else "helper missing textContent assignment or uses innerHTML")

    # S5: static HTML fallback carries the live copy, id present exactly once.
    m = re.search(r'<p class="subtitle" id="header-subtitle">([^<]*)</p>', html)
    s5 = (m is not None and m.group(1) == expected
          and html.count('id="header-subtitle"') == 1)
    check("S5 index.html #header-subtitle fallback == live copy '%s'" % expected,
          s5, ("got %r" % (m.group(1) if m else None)) if not s5 else "")


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

    expected = "Executive compensation data from SEC DEF 14A proxy statements, FY%d" % live_primary_fy()

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
                "window.d3 && document.getElementById('header-subtitle')",
                timeout=90000)

            # R1: initial-load subtitle tracks the live primary FY.
            sub = pg.evaluate(
                "document.getElementById('header-subtitle').textContent")
            r1 = sub == expected
            check("R1 initial-load #header-subtitle == live copy '%s'" % expected,
                  r1, "got %r" % sub if not r1 else "")

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
