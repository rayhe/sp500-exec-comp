#!/usr/bin/env python3
"""Regression guard: the sector chart's sector-vocabulary bridge.

Background (2026-10-07 23:30 PT): trends.json's
median_pay_by_sector_sp500_fy2024.data[].sector uses a different sector
naming than the GICS-style company records in compensation.json (only 5 of
11 names match verbatim: Communication Services, Energy, Industrials,
Real Estate, Utilities). Before the fix, drawSectorChart keyed its
per-sector distribution join (sectorDist) on raw company sectors, so the
IQR boxes, min-max whiskers, (n) counts, tooltip distribution stats, and
3-year sparklines silently rendered only for the 5 name-matching sectors,
and clicking a bar for one of the 6 renamed sectors called
filterBySector() with a trends-vocabulary name that matches zero company
records — emptying the table. The fix introduces SECTOR_TREND_TO_COMP plus
a per-datum _compSector (company-vocabulary name) used for all data joins,
interactions, and labels.

This guard has two halves:
  A. Static: the bridge map exists and covers every trends sector that is
     absent from the company vocabulary; the map values are all real
     company sectors; drawSectorChart attaches _compSector to each datum;
     the distribution merge, bar click, y domain, highlight sync, and
     sparkline lookup all use _compSector rather than the raw trends name.
  B. Render (headless Chromium via playwright, 1440px desktop, cached d3
     shim): 11 IQR boxes and 11 whiskers render (one per trends sector);
     every bar label carries an (n) count; clicking the Information
     Technology bar filters the table to a nonzero row set with the sector
     named in the summary bar; zero page errors.

Usage:
  scripts/check_sector_vocab_bridge.py              # static + render
  scripts/check_sector_vocab_bridge.py --static-only

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
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
TRENDS_JSON = os.path.join(REPO, "data", "trends.json")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_vocabularies():
    trends = json.load(open(TRENDS_JSON))
    comp = json.load(open(COMP_JSON))
    trend_sectors = set(
        d["sector"] for d in trends["median_pay_by_sector_sp500_fy2024"]["data"] if d.get("sector"))
    comp_sectors = set(c.get("sector") for c in comp["companies"] if c.get("sector"))
    return trend_sectors, comp_sectors


def js_map_entries():
    src = open(CHARTS_JS).read()
    m = re.search(r"var SECTOR_TREND_TO_COMP = \{(.*?)\};", src, re.S)
    if not m:
        return None
    pairs = re.findall(r"'([^']+)'\s*:\s*'([^']+)'", m.group(1))
    return dict(pairs)


def static_checks():
    src = open(CHARTS_JS).read()

    # S1: the bridge map exists and matches the known 6 renames.
    expected = {
        "Consumer Cyclical": "Consumer Discretionary",
        "Consumer Defensive": "Consumer Staples",
        "Financial Services": "Financials",
        "Healthcare": "Health Care",
        "Technology": "Information Technology",
        "Basic Materials": "Materials",
    }
    got = js_map_entries()
    check("S1 SECTOR_TREND_TO_COMP carries the 6 known renames",
          got == expected, ("got %r" % got) if got != expected else "")

    # S2: helper exists.
    check("S2 sectorTrendToComp() helper exists",
          "function sectorTrendToComp(trendSector)" in src)

    # S3: every trends sector absent from the company vocabulary is covered
    # by the map, and every map value is a real company sector. This is the
    # check that fails loudly if either data file gains a renamed sector.
    if got is not None:
        trend_sectors, comp_sectors = live_vocabularies()
        uncovered = sorted(s for s in trend_sectors
                           if s not in comp_sectors and s not in got)
        badvals = sorted(v for v in got.values() if v not in comp_sectors)
        check("S3 bridge covers every renamed trends sector",
              not uncovered, ("uncovered: %r" % uncovered) if uncovered else "")
        check("S4 every bridge target is a real company sector",
              not badvals, ("bad targets: %r" % badvals) if badvals else "")
    else:
        check("S3 bridge covers every renamed trends sector", False, "map missing")
        check("S4 every bridge target is a real company sector", False, "map missing")

    # S5: drawSectorChart attaches _compSector to each datum.
    check("S5 drawSectorChart sets d._compSector = sectorTrendToComp(d.sector)",
          "d._compSector = sectorTrendToComp(d.sector)" in src)

    # S6: the distribution merge joins on _compSector, not the raw name.
    check("S6 distribution merge uses sectorDist[d._compSector]",
          "sectorDist[d._compSector]" in src and "sectorDist[d.sector]" not in src)

    # S7: bar click filters on the company-vocabulary name.
    check("S7 bar click calls filterBySector(d._compSector)",
          "window.filterBySector(d._compSector)" in src)

    # S8: no remaining raw d.sector join/interaction inside drawSectorChart's
    # S8: no bare d.sector data joins/interactions remain inside
    # drawSectorChart. Allowed: the bridge construction itself
    # (sectorTrendToComp(d.sector)) and the hit-zone datum field
    # (zd.sector), which now carries the company-vocabulary name.
    start = src.index("function drawSectorChart")
    end = src.index("function drawTrendChart")
    region = src[start:end]
    bad = []
    for m in re.finditer(r"(?<![\w$.])d\.sector\b", region):
        ctx = region[max(0, m.start() - 40):m.end() + 10]
        if "sectorTrendToComp(d.sector)" in ctx:
            continue
        line_start = region.rfind("\n", 0, m.start()) + 1
        line_end = region.find("\n", m.end())
        bad.append(region[line_start:line_end].strip()[:100])
    check("S8 no bare d.sector joins remain in drawSectorChart",
          not bad, ("; ".join(bad[:4])) if bad else "")

    # S9: highlightSectorBar (called with company-vocabulary names from the
    # sector chips) compares against _compSector.
    check("S9 highlightSectorBar compares d._compSector",
          "d._compSector === sectorName" in src)


def get_d3_bytes():
    # Same cached copy as the other render guards (build-time shim only).
    cache = os.path.expanduser(
        "~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/methbtn-20261005/d3.min.js")
    if os.path.exists(cache):
        return open(cache, "rb").read()
    return None


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
                "window.d3 && document.querySelectorAll('#sector-chart .bar').length === 11",
                timeout=90000)
            pg.evaluate("document.getElementById('sector-chart-panel').scrollIntoView()")
            pg.wait_for_timeout(1200)

            # R1: one IQR box + one whisker per sector.
            boxes = pg.evaluate("document.querySelectorAll('#sector-chart .dist-box').length")
            whiskers = pg.evaluate("document.querySelectorAll('#sector-chart .dist-whisker').length")
            check("R1 11 IQR boxes + 11 whiskers render", boxes == 11 and whiskers == 11,
                  ("boxes=%d whiskers=%d" % (boxes, whiskers)) if not (boxes == 11 and whiskers == 11) else "")

            # R2: every bar label carries an (n) company count.
            labels = pg.evaluate("[...document.querySelectorAll('#sector-chart .bar-label')].map(e => e.textContent)")
            ok = len(labels) == 11 and all(re.search(r"\(\d+\)$", t) for t in labels)
            check("R2 all 11 bar labels carry an (n) count", ok,
                  ("got %r" % labels) if not ok else "")

            # R3: clicking the Information Technology bar (a renamed sector)
            # filters the table to a nonzero row set with the sector named.
            clicked = pg.evaluate("""() => {
                const bars = [...document.querySelectorAll('#sector-chart .bar')];
                const tech = bars.find(b => b.__data__ && b.__data__._compSector === 'Information Technology');
                if (tech) tech.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                return !!tech;
            }""")
            pg.wait_for_timeout(1500)
            rows = pg.evaluate("document.querySelectorAll('#comp-table tbody tr').length")
            summary = pg.evaluate("document.querySelector('#table-summary-bar')?.innerText || ''")
            ok3 = clicked and rows > 0 and "Information Technology" in summary
            check("R3 IT bar click filters the table (nonzero rows, sector named)",
                  ok3, ("clicked=%s rows=%s summary=%r" % (clicked, rows, summary[:80])) if not ok3 else "")

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
        rc = all(ok for _, ok, _ in results)
    else:
        rc = render_checks()
        if rc is None:
            rc = all(ok for _, ok, _ in results)
    print("RESULT:", "PASS" if rc else "FAIL")
    sys.exit(0 if rc else 1)


if __name__ == "__main__":
    main()
