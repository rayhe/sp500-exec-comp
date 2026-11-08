#!/usr/bin/env python3
"""Guard: the SoP filter is named in the combined-filter badge, the table
announcement, and the sort-summary histogram marks its active bucket.

Background (382nd review, 2026-11-08): the 381st review confirmed
behaviorally that _activeSopFilter is the only filter dim missing from
the filterParts/filterDims list in renderSummaryBar (js/app.js): SoP
90-101% + Female CEOs filtered to 24 companies, the SoP chip existed
separately, but the combined-filter badge was None -- the SoP dim was
unnamed in the summary bar even though every other dim (sector, ratio,
conc, CEO/CFO, YoY, pctile, equity, gender, asp, tenure, gov,
volatility, peers, community, quartile, position, crosstab, role)
contributes a part. The same omission held in renderTable's screen-
reader announcement (announceMsg names every other dim, never SoP).
And the SoP sort-summary histogram (renderSopSortSummary) was the only
dist histogram whose bar group carried neither the clickable-bar marker
nor the conditional active-bracket class -- the 381st spot-check had to
probe the inline outline for SoP because the class was absent.

The fix: one filterParts line for SoP ('SoP: ' + label, matching the
chip label), one announceMsg line ('say-on-pay: ' + label), and the
sop-dist-bar-group render site gains clickable-bar + the conditional
active-bracket, the same pattern every other dist histogram uses.

Checks:
  C1 HARD FAIL: renderSummaryBar does not name the SoP filter in the
     combined-filter badge (filterDims++ + filterParts.push('SoP: ')).
  C2 HARD FAIL: renderTable's announceMsg does not name the SoP filter.
  C3 HARD FAIL: the SoP sort-summary bar group does not carry
     clickable-bar + conditional active-bracket.
  C4 HARD FAIL: a bare sop-dist-bar-group render site remains (the
     pre-fix class string with no clickable-bar marker).
Render (headless Chromium, d3 requests aborted -- the summary bar, AF
panel and hash paths are pure app.js):
  R1 SoP 90-101 + Female CEOs filters to 24 companies and the combined
     badge names both dims ('SoP: 90-101%' and 'Female CEOs').
  R2 sorting by say-on-pay and clicking the 90-95 SoP bar filters the
     table and marks that bar with .active-bracket.
  R3 a lone SoP filter renders no combined badge (single dim) but the
     SoP chip is present.
  R4 zero page errors across the render half.

Usage:
  scripts/check_sop_combined_badge.py
  scripts/check_sop_combined_badge.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, server would not start).

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
import time

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def extract_function_body(src, start_marker):
    """Return the brace-matched body starting at start_marker, or None."""
    idx = src.find(start_marker)
    if idx < 0:
        return None
    brace = src.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[brace:i + 1]
    return None


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # C1: renderSummaryBar names SoP in the combined-filter badge.
    bar_body = extract_function_body(app, "function renderSummaryBar")
    if bar_body is None:
        check("C1 renderSummaryBar exists in app.js", False,
              "definition not found")
    else:
        c1_ok = ("filterParts.push('SoP: ' + window._activeSopFilter.label)"
                 in bar_body
                 and "if (window._activeSopFilter) { filterDims++;"
                 in bar_body)
        check("C1 combined-filter badge names the SoP filter", c1_ok,
              "" if c1_ok else "no 'SoP: ' filterParts push in "
              "renderSummaryBar")

    # C2: renderTable's screen-reader announcement names SoP.
    c2_ok = ("announceMsg += ', say-on-pay: ' + "
             "window._activeSopFilter.label;" in app)
    check("C2 table announcement names the SoP filter", c2_ok,
          "" if c2_ok else "no 'say-on-pay: ' announceMsg line")

    # C3: SoP sort-summary bar group carries clickable-bar + conditional
    # active-bracket, matching every other dist histogram.
    c3_ok = ("sop-dist-bar-group clickable-bar' + "
             "(isActive ? ' active-bracket' : '')" in app)
    check("C3 SoP bar group carries clickable-bar + active-bracket", c3_ok,
          "" if c3_ok else "sop-dist-bar-group render site lacks the "
          "clickable-bar / active-bracket pattern")

    # C4: no bare sop-dist-bar-group render site remains.
    c4_ok = '<div class="sop-dist-bar-group"' not in app
    check("C4 no bare sop-dist-bar-group render site remains", c4_ok,
          "" if c4_ok else "bare '<div class=\"sop-dist-bar-group\"' "
          "render site still present")

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

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            errors = []
            pg = browser.new_page(viewport={"width": 1280, "height": 800})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.route("**/d3*", lambda r: r.abort())
            pg.route("**/d3js.org/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            def badge_text():
                return pg.evaluate("""() => {
                    const b = document.querySelector(
                        '#table-summary-bar .combined-filter-badge');
                    return b ? b.textContent : null;
                }""")

            # R1: SoP 90-101 + Female CEOs -> 24 companies, badge names both.
            pg.click("#advanced-filters-toggle")
            pg.wait_for_timeout(400)
            pg.evaluate("""() => {
                ['gov', 'lead'].forEach(cat => {
                    const d = document.querySelector(
                        'details.af-cat[data-cat="' + cat + '"]');
                    if (d) d.open = true;
                });
            }""")
            pg.select_option("#af-sop-tier", "90-101")
            pg.wait_for_timeout(800)
            pg.select_option("#af-gender", "F")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            b1 = badge_text()
            check("R1 SoP+gender filters to 24 with badge naming both dims",
                  n1 == 24 and b1 is not None
                  and "SoP: 90-101%" in b1 and "Female" in b1,
                  "footer=%s badge=%r (want 24, SoP 90-101 pct + Female)"
                  % (n1, b1))

            # R3 (before clearing): lone SoP filter -> no combined badge,
            # SoP chip present. Clear gender only via its chip.
            pg.evaluate("""() => {
                const c = document.getElementById('gender-filter-chip');
                if (c) c.click();
            }""")
            pg.wait_for_timeout(1200)
            n3 = footer_count()
            b3 = badge_text()
            chip3 = pg.evaluate(
                "() => !!document.getElementById('sop-filter-chip')")
            check("R3 lone SoP filter has no combined badge but a SoP chip",
                  0 < n3 < 518 and b3 is None and chip3,
                  "footer=%s badge=%r chip=%s" % (n3, b3, chip3))

            # R2: sort by say-on-pay, click the 90-95 SoP bar.
            pg.evaluate("() => { location.hash = ''; }")
            pg.wait_for_timeout(800)
            pg.click('th[data-sort="_sopApproval"]')
            pg.wait_for_selector(
                "#table-summary-bar .sop-dist-bar-group", timeout=8000)
            pg.evaluate("""() => {
                const bars = [...document.querySelectorAll(
                    '#table-summary-bar .sop-dist-bar-group')];
                const t = bars.find(b => (b.getAttribute('onclick') || '')
                    .indexOf('highlightSopBucket(90,95)') >= 0);
                if (t) t.click();
            }""")
            pg.wait_for_timeout(1200)
            n2 = footer_count()
            active2 = pg.evaluate("""() => document.querySelectorAll(
                '#table-summary-bar .sop-dist-bar-group.active-bracket'
                ).length""")
            active_title2 = pg.evaluate("""() => {
                const a = document.querySelector(
                    '#table-summary-bar .sop-dist-bar-group.active-bracket');
                return a ? a.getAttribute('title') : null;
            }""")
            check("R2 SoP bar click filters and rings the 90-95 bucket",
                  0 < n2 < 518 and active2 >= 1
                  and active_title2 is not None
                  and "90-95" in active_title2,
                  "footer=%s active=%s title=%r"
                  % (n2, active2, active_title2))

            check("R4 zero page errors across the render half",
                  len(errors) == 0, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return (n1 == 24 and b1 is not None and "SoP: 90-101%" in b1
                    and "Female" in b1 and 0 < n3 < 518 and b3 is None
                    and chip3 and 0 < n2 < 518 and active2 >= 1
                    and active_title2 is not None
                    and "90-95" in active_title2 and len(errors) == 0)
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
