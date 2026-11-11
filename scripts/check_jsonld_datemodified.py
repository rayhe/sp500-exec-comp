#!/usr/bin/env python3
"""Regression guard: the Dataset JSON-LD block's dateModified must track
the live dataset freshness from data/compensation.json's metadata, not a
hard-coded date.

Background (2026-11-10, 419th review): the JSON-LD block hard-coded
"dateModified": "2026-11-02" while DQ batches had bumped
metadata.last_updated to 2026-11-06 - the live crawl still showed
"Updated: 2026-11-02", the date search engines and dataset consumers use.
Same stale-copy class as the footer vintage (2026-09-17), the header
subtitle FY label, and the sector-comp desc count (2026-10-07). The fix
renders dateModified live from metadata.last_updated via
renderJsonLdDateModified(), with the static value in index.html keeping
today's date as the no-JS fallback.

This guard has two halves:
  A. Static: the JSON-LD block parses, carries @type Dataset with a valid
     YYYY-MM-DD dateModified that never over-claims freshness (static date
     <= metadata.last_updated); renderJsonLdDateModified() exists, reads
     metadata.last_updated, rewrites only the dateModified value, and is
     called at load next to renderFooterVintage.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     the parsed JSON-LD dateModified equals metadata.last_updated on
     initial load; zero page errors.

Usage:
  scripts/check_jsonld_datemodified.py              # static + render
  scripts/check_jsonld_datemodified.py --static-only

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


def live_last_updated():
    data = json.load(open(DATA_JSON, encoding="utf-8"))
    md = data.get("metadata") or {}
    return md.get("last_updated") or data.get("last_updated")


def extract_jsonld(html):
    m = re.search(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL)
    if not m:
        return None, "no application/ld+json script block in index.html"
    try:
        return json.loads(m.group(1)), ""
    except json.JSONDecodeError as e:
        return None, "JSON-LD block does not parse: %s" % e


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    ymd = live_last_updated()

    # S1: JSON-LD parses, is a Dataset, dateModified is a valid YYYY-MM-DD.
    data, err = extract_jsonld(html)
    s1 = (data is not None and data.get("@type") == "Dataset"
          and isinstance(data.get("dateModified"), str)
          and re.match(r"^\d{4}-\d{2}-\d{2}$", data["dateModified"]) is not None)
    check("S1 JSON-LD parses as a Dataset with a valid YYYY-MM-DD dateModified",
          s1, err if not s1 else "")

    # S2: static dateModified never over-claims freshness vs the metadata.
    # (It may lag after a DQ batch bumps last_updated; the live sync in
    # renderJsonLdDateModified corrects it for JS consumers. Over-claiming
    # - a static date NEWER than the data - is the direction that lies.)
    static_date = data.get("dateModified") if isinstance(data, dict) else None
    s2 = (isinstance(static_date, str) and isinstance(ymd, str)
          and static_date <= ymd)
    check("S2 static dateModified (%s) is not newer than metadata last_updated (%s)"
          % (static_date, ymd),
          s2, "" if s2 else "static date over-claims dataset freshness")

    # S3: helper exists and derives its date from metadata.last_updated.
    s3 = ("function renderJsonLdDateModified(comp)" in src
          and re.search(r"function renderJsonLdDateModified\(comp\)\s*\{.*?last_updated",
                        src, re.DOTALL) is not None)
    check("S3 renderJsonLdDateModified() derives its date from metadata.last_updated",
          s3, "" if s3 else "helper missing or does not read last_updated")

    # S4: helper rewrites only the dateModified value (regex on the raw
    # text), never re-serializes the whole block or writes raw HTML.
    fn = src.split("function renderJsonLdDateModified(comp)", 1)
    body = fn[1].split("\n}\n", 1)[0] if len(fn) > 1 else ""
    s4 = ('"dateModified"' in body and "innerHTML" not in body
          and "JSON.stringify" not in body)
    check("S4 renderJsonLdDateModified() rewrites only dateModified (no innerHTML, no full re-serialize)",
          s4, "" if s4 else "helper rewrites more than dateModified")

    # S5: called at load next to the other live vintage renders.
    s5 = ("renderFooterVintage(comp);" in src
          and "renderJsonLdDateModified(comp);" in src)
    check("S5 renderJsonLdDateModified(comp) is called at load with renderFooterVintage",
          s5, "" if s5 else "load call site missing")

    # S6: the script tag carries the id the helper looks up.
    s6 = 'id="dataset-jsonld"' in html
    check("S6 JSON-LD script tag carries id=\"dataset-jsonld\"",
          s6, "" if s6 else "helper lookup id missing from index.html")


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

    ymd = live_last_updated()
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
            # loadData calls renderFooterVintage then renderJsonLdDateModified
            # in the same synchronous sequence, so a populated footer vintage
            # proves the JSON-LD sync has run.
            pg.wait_for_function(
                "window.d3 && document.getElementById('footer-data-vintage')"
                " && document.getElementById('footer-data-vintage').textContent.length > 0",
                timeout=90000)

            # R1: parsed JSON-LD dateModified tracks metadata last_updated.
            raw = pg.evaluate(
                "document.getElementById('dataset-jsonld').textContent")
            parsed = json.loads(raw)
            r1 = parsed.get("dateModified") == ymd
            check("R1 initial-load JSON-LD dateModified == metadata last_updated (%s)" % ymd,
                  r1, "got %r" % parsed.get("dateModified") if not r1 else "")

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
