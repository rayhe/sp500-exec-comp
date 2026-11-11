#!/usr/bin/env python3
"""Guard: the zero-row summary bar names a lone active filter dim.

Background (423rd review, 2026-11-11): the 410th review hoisted the
combined-filter badge into the zero-row path of renderSummaryBar, but
kept the normal path's filterDims >= 2 gate there. A LONE dim that
yields zero rows -- a search term with no matches, a single empty
position filter -- therefore still showed only 'No companies match
current filters' in the bar, with no dim named. The dismiss chips in
table-controls named it and the ARIA announcement named it, but the
bar itself did not. The fix: the zero-row branch gates the badge on
filterDims >= 1. The normal path keeps >= 2 (a lone dim's stats line
already names it via the sector/count text), but the zero-row state
has no stats at all, so any active dim gets the badge there.

Checks:
  S1 HARD FAIL: the zero-row branch (filtered.length === 0) gates
     the combined badge on filterDims >= 1, not >= 2.
  S2 HARD FAIL: the normal path still gates the badge on
     filterDims >= 2 (the 423rd fix is zero-row-only).
  S3 HARD FAIL: the zero-row branch still renders the 'No companies
     match current filters' message.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  A search term with no matches ('zzzzqq'): the bar shows the
      combined badge naming the term ('"zzzzqq"') alongside the
      zero-row message, and the announcement names the search.
  R2  Two-dim zero-row (same search + Information Technology
      sector): the badge names both dims (410th regression cover).
  R3  zero page errors across the render half.

Usage:
  scripts/check_zero_row_single_dim_badge.py
  scripts/check_zero_row_single_dim_badge.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # Isolate the zero-row branch: from the filtered.length === 0
    # guard to its early return.
    zr = app[app.find("if (filtered.length === 0) {"):]
    zr = zr[:zr.find("return;\n    }\n\n    // 361st review")]

    # S1: the zero-row branch gates the badge on filterDims >= 1.
    s1 = ("if (filterDims >= 1) emptyHtml += combinedFilterBadgeHtml(filterParts);"
          in zr)
    check("S1 zero-row branch gates badge on filterDims >= 1",
          s1, "" if s1 else "zero-row gate is not >= 1")

    # S2: the normal path still gates on filterDims >= 2.
    s2 = "if (filterDims >= 2) {\n        html += combinedFilterBadgeHtml(filterParts);" in app
    check("S2 normal path still gates badge on filterDims >= 2",
          s2, "" if s2 else "normal-path gate changed (423rd fix is zero-row-only)")

    # S3: the zero-row message still renders in that branch.
    s3 = "No companies match current filters" in zr
    check("S3 zero-row branch still renders the no-match message",
          s3, "" if s3 else "zero-row message missing from the branch")

    return 0


def get_d3_bytes():
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

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-proxy-server"])
            errors = []
            pg = browser.new_page(viewport={"width": 1280, "height": 800})
            pg.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript",
                              body=d3)

            pg.route("**/npm/d3@7*", d3_route)
            pg.route("**/unpkg.com/d3@7*", d3_route)
            pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)

            def bar_text():
                return pg.evaluate(
                    "() => { const b = document.getElementById('table-summary-bar');"
                    " return b ? b.textContent : null; }")

            def badge_text():
                return pg.evaluate("""() => {
                    const b = document.querySelector(
                        '#table-summary-bar .combined-filter-badge');
                    return b ? b.textContent : null;
                }""")

            def last_announce():
                return pg.evaluate(
                    "() => (typeof window._lastTableAnnounce === 'string' "
                    "&& window._lastTableAnnounce) || ''")

            # R1: lone search dim with no matches. Pre-fix the bar
            # showed only the no-match message; post-fix the badge
            # names the term.
            pg.fill("#table-search", "zzzzqq")
            pg.wait_for_timeout(1200)
            b1 = badge_text()
            bar1 = bar_text()
            a1 = last_announce()
            r1_ok = (b1 is not None and '"zzzzqq"' in b1
                     and bar1 is not None and "No companies match" in bar1
                     and "search: zzzzqq" in a1)
            check("R1 lone no-match search shows badge naming the term + zero-row message",
                  r1_ok,
                  "badge=%r bar=%r announce=%r" % (b1, bar1, a1))

            # R2: two-dim zero-row (same search + sector) still
            # badges both dims (410th regression cover).
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            b2 = badge_text()
            bar2 = bar_text()
            r2_ok = (b2 is not None and '"zzzzqq"' in b2
                     and "Information Technology" in b2
                     and bar2 is not None and "No companies match" in bar2)
            check("R2 two-dim zero-row badges both dims",
                  r2_ok,
                  "badge=%r bar=%r" % (b2, bar2))

            r3_ok = len(errors) == 0
            check("R3 zero page errors across the render half",
                  r3_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok and r3_ok
    finally:
        server.terminate()


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = render_checks()
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
