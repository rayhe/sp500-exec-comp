#!/usr/bin/env python3
"""Guard: the table announcement names all seven network/volatility
filter dims, and the chart-origin volatility state label is bare.

Background (386th review, 2026-11-08): the combined-filter badge
(renderSummaryBar filterParts, js/app.js) names 26 filter dims, but
the screen-reader announcement (announceMsg in renderTable) named
only 19 of them. The seven missing dims -- volatility bucket,
volatility x tenure bracket, peer distribution, community, quartile,
position, crosstab -- are all genuine row-hiding dims in renderTable's
data path, so a screen-reader user hearing the announcement was told
the table was filtered to the sector only while the badge showed eight
dims. Same class as the 382nd review (SoP) and the 385th (board),
now closed for the remaining seven.

The fix: one announceMsg line per dim in renderTable, in badge order,
after the governance line and before the role line. The vol-tenure
part uses the chip's wording ('volatility x tenure') so it cannot
collide with the tenure quartile's ', tenure: ' part.

408th review: the position line now uses the shared
positionFilterLabel helper instead of the bare stored label, so the
empty position filter's ' (0)' count survives into the announcement
(the chip and the badge use the same helper). The pinned line above
tracks that form; non-empty labels are unchanged.

Companion fix: the chart-origin volatility state label was
'Volatility ' + b.label, which doubled the prefix in both sites that
prepend their own ('Volatility: ' + label in the badge, ', volatility: '
+ label in the new announcement) -- the live badge read 'Volatility:
Volatility 0-5%'. Both chart-origin assignments in js/charts.js
(click + keyboard activate) now store the bare bucket label ('0-5%'),
matching the AF-origin shape ('Stable <10%'); the chip's prefix logic
already adds 'Volatility ' when absent, so the chip text is unchanged.

Checks:
  C1 HARD FAIL: any of the seven announceMsg lines is missing from
     js/app.js.
  C2 HARD FAIL: the seven lines are not in the announce block between
     the governance line and the role line, in badge order.
  C3 HARD FAIL: js/charts.js still assigns a 'Volatility ' + b.label
     state label, or either volatility assignment is not the bare
     bucket label.
Render (headless Chromium, d3 shim from the goal hidden_files cache --
the summary bar, AF panel and hash paths are pure app.js, the
volatility bars need real d3):
  R1 all seven states + Information Technology sector filters to 1
     company (AAPL) and the combined badge names all eight dims while
     the announcement names all seven plus the sector.
  R2 a real volatility-bar click sets the bare bucket label: the badge
     reads 'Volatility: 0-5%' (no doubling), the chip reads
     'Volatility 0-5%', and the announcement reads 'volatility: 0-5%'.
  R3 zero page errors across the render half.

Usage:
  scripts/check_announce_seven_dims.py
  scripts/check_announce_seven_dims.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

442nd review (2026-11-12): adopted render_guard_common (slowest
remaining render guard, ~32.7s in the 2026-11-13T02:31:11Z shard-4
run; re-profiled from the freshest drift_canary_state.json entries this
run, per the 432nd note). Pre-fix defect was the 429th-review class,
not the silent-pass variant: main() checked render_checks()'s return
value, but a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the docstring promises exit
2 (infra) -- proved in-process before the fix
(~/workspace/pre442_proof.py: rc=1, "3/3 checks passed" printed, 0
R-checks recorded; the 3 static checks pass, the 3 render checks never
run). 71 local copies remain.
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")
CHARTS_JS = os.path.join(REPO, "js", "charts.js")

ANNOUNCE_LINES = [
    ("volatility",
     "if (window._activeVolatilityBucket) announceMsg += ', volatility: ' "
     "+ window._activeVolatilityBucket.label;"),
    ("vol-tenure",
     "if (window._activeVolTenureBracket) announceMsg += ', volatility \u00d7 "
     "tenure: ' + window._activeVolTenureBracket.label;"),
    ("peer-dist",
     "if (window._activePeerDistFilter) announceMsg += ', peers: ' "
     "+ window._activePeerDistFilter.label;"),
    ("community",
     "if (window._activeCommunityFilter) announceMsg += ', community: ' "
     "+ window._activeCommunityFilter.label;"),
    ("quartile",
     "if (window._activeQuartileFilter) announceMsg += ', quartile: ' "
     "+ window._activeQuartileFilter.label;"),
    ("position",
     "if (window._activePositionFilter) announceMsg += ', position: ' "
     "+ positionFilterLabel(window._activePositionFilter);"),
    ("crosstab",
     "if (window._activeCrosstabFilter) announceMsg += ', crosstab: ' "
     "+ window._activeCrosstabFilter.label;"),
]

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
    try:
        charts = open(CHARTS_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/charts.js: %s" % exc)
        return 2

    # C1: all seven announceMsg lines present.
    missing = [name for name, line in ANNOUNCE_LINES if line not in app]
    check("C1 announcement names all seven network/volatility dims",
          not missing,
          "" if not missing else "missing announce lines: " + ", ".join(missing))

    # C2: the seven lines sit in the announce block between the
    # governance line and the role line, in badge order. Search for the
    # full announceMsg lines (the fix comment prose cannot match them).
    gov_idx = app.find(
        "if (window._activeGovGrade) announceMsg += ', governance: Grade '")
    role_idx = app.find(
        "if (activeRole && activeRole !== 'CEO') announceMsg += ', viewing '")
    idxs = [app.find(line) for _, line in ANNOUNCE_LINES]
    c2_ok = (gov_idx >= 0 and role_idx >= 0 and all(i >= 0 for i in idxs)
             and all(gov_idx < i < role_idx for i in idxs)
             and idxs == sorted(idxs))
    check("C2 seven announce lines are ordered in the announce block",
          c2_ok,
          "" if c2_ok else "lines outside gov-to-role block or out of "
          "badge order (gov=%d role=%d idxs=%s)"
          % (gov_idx, role_idx, idxs))

    # C3: no chart-origin volatility assignment prefixes the label, and
    # both assignments store the bare bucket label.
    c3_ok = ("label: 'Volatility ' + b.label" not in charts
             and charts.count("label: b.label") >= 2)
    check("C3 chart-origin volatility label is the bare bucket label",
          c3_ok,
          "" if c3_ok else "a 'Volatility ' + b.label assignment remains "
          "or fewer than 2 bare-label assignments")

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
    d3 = get_d3_bytes()
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

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

            def last_announce():
                return pg.evaluate(
                    "() => (typeof window._lastTableAnnounce === 'string' "
                    "&& window._lastTableAnnounce) || ''")

            # R1: all seven states (labels as the real setters produce
            # them post-fix: volatility bare) + Information Technology
            # sector -> 1 company; badge and announcement name all dims.
            # Pre-fix: badge names all seven, announcement names only
            # the sector.
            pg.evaluate("""() => {
                window._activeVolatilityBucket = { min: 0, max: Infinity, label: '0-100%' };
                window._activeVolTenureBracket = { min: 0, max: Infinity, label: '0-99 yrs' };
                window._activePeerDistFilter = { tickers: ['AAPL','MSFT'], label: 'Peers $10-20M', source: 'probe' };
                window._activeCommunityFilter = { tickers: ['AAPL','MSFT'], label: 'Cluster 3', id: 3 };
                window._activeQuartileFilter = { tickers: ['AAPL'], label: 'Cluster 3 Upper Quartile (1)', communityId: 3, _lo: 0, _hi: 1e9 };
                window._activePositionFilter = { tickers: ['AAPL'], label: 'Cluster 3 CEO Pay above #2 (1)', communityId: 3, metric: 'pay', rank: 2, direction: 'above' };
                window._activeCrosstabFilter = { tickers: ['AAPL'], label: 'Tenure 0-5 x Gov A (1)', cellKey: 'probe' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            b1 = badge_text()
            a1 = last_announce()
            r1_ok = (n1 == 1 and b1 is not None and a1 is not None
                     and "Volatility: 0-100%" in b1
                     # 387th review: the vol-tenure badge part is now
                     # 'Volatility x Tenure: 0-99 yrs'; the bare
                     # 'Tenure: 0-99 yrs' substring would pass vacuously
                     # on the new text, so assert the full part.
                     and "Volatility \u00d7 Tenure: 0-99 yrs" in b1
                     and "Peers: Peers $10-20M" in b1
                     and "Community: Cluster 3" in b1
                     and "Cluster 3 Upper Quartile (1)" in b1
                     and "CEO Pay above #2 (1)" in b1
                     and "Crosstab: Tenure 0-5 x Gov A (1)" in b1
                     and "volatility: 0-100%" in a1
                     and "volatility \u00d7 tenure: 0-99 yrs" in a1
                     and "peers: Peers $10-20M" in a1
                     and "community: Cluster 3" in a1
                     and "quartile: Cluster 3 Upper Quartile (1)" in a1
                     and "position: Cluster 3 CEO Pay above #2 (1)" in a1
                     and "crosstab: Tenure 0-5 x Gov A (1)" in a1)
            check("R1 badge and announcement name all seven dims",
                  r1_ok,
                  "footer=%s badge=%r announce=%r (want 1, all seven dims "
                  "in both)" % (n1, b1, a1))

            # R2: a real volatility-bar click sets the bare bucket label.
            # The first bucket is 0-5 pct ('Very Low'). Reload first: R1
            # leaves all seven states set, and their AND with the new
            # 0-5 pct range filters to zero rows, whose early return in
            # renderSummaryBar renders no badge at all. Click, then add
            # the sector so the combined badge renders (single dim shows
            # no badge). Pre-fix: badge read 'Volatility: Volatility
            # 0-5 pct' and the announcement never named volatility.
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)
            pg.wait_for_function(
                "document.querySelectorAll('#volatility-dist-chart .vol-bar').length > 3",
                timeout=90000)
            pg.locator("#volatility-dist-chart .vol-bar").first.click()
            pg.wait_for_timeout(1000)
            chip2 = pg.evaluate(
                "() => { const c = document.getElementById('volatility-filter-chip');"
                " return c ? c.textContent : null; }")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            b2 = badge_text()
            a2 = last_announce()
            r2_ok = (b2 is not None
                     and "Volatility: 0\u20135%" in b2
                     and "Volatility: Volatility" not in b2
                     and chip2 is not None and "Volatility 0\u20135%" in chip2
                     and a2 is not None and "volatility: 0\u20135%" in a2
                     and "volatility: Volatility" not in a2)
            check("R2 chart-click volatility label is bare in badge/chip/announce",
                  r2_ok,
                  "badge=%r chip=%r announce=%r (want Volatility 0-5 pct, "
                  "no doubling)" % (b2, chip2, a2))

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
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
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
