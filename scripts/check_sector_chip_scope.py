#!/usr/bin/env python3
"""Guard: sector-chip state updates touch only sector chips.

Background (388th review, 2026-11-08): the six sector-change paths
(filterBySector, filterBySectorFromBar, filterByDistribution, the
buildSectorChips All/sector click handlers, and the dist-chip dismiss
hadSector branch) all reset chip state with a document-wide sweep:
document.querySelectorAll('.chip').forEach(... remove 'active').
That sweep also stripped 'active' from indicator chips -- the gender
chip and asp-delta chip live inside #sector-chips itself, the
vol-tenure / dist / ratio / ... chips live in .table-controls -- and
the indicator updaters for gender, vol-tenure, tenure, board, SoP and
stock-pct are NOT called on the sector path, so nothing restored the
class. The chip kept filtering (state, badge and count were right)
while looking inactive: a visible state lie. The 387th review's R1
had to re-render the vol-tenure chip by hand after filterBySector
for exactly this reason.

The fix: one helper, updateSectorChipStates(activeName), scopes the
sweep to '#sector-chips .chip:not(.combined-filter-chip)' -- sector
chips are plain 'chip', every indicator chip carries
combined-filter-chip -- and all six sector-change sites call it.
Full-reset paths (resetAllFilters, Escape, deep-link restore) keep
their document-wide sweep: they null all filter state and remove the
indicator chips by id, so the sweep there is consistent.

Checks:
  C1 HARD FAIL: the updateSectorChipStates helper is missing, or its
     sweep is not scoped to '#sector-chips .chip:not(.combined-filter-chip)'.
  C2-C7 HARD FAIL: each sector-change site still carries the bare
     document-wide '.chip' sweep, or does not call the helper with the
     right active name (All handler: null; sector handler: s;
     filterBySector: sectorName || null; filterByDistribution:
     _activeDistFilter ? sector : null; dist dismiss: null;
     filterBySectorFromBar: activeSector).
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1 gender F + Information Technology sector: the gender chip keeps
     its 'active' class after the sector click, the IT sector chip is
     active, 'All' is not, footer reads 6 (ACN, ADP, AMD, CDW, FIS,
     ORCL). Pre-fix: the gender chip lost 'active' while still
     filtering to 6.
  R2 vol-tenure 0-99 yrs + Information Technology sector: the
     vol-tenure chip keeps its 'active' class after the sector click
     and the footer still lists >= 1 company. Pre-fix: the chip lost
     'active' (387th review re-rendered it by hand to work around it).
  R3 zero page errors across the render half.

Usage:
  scripts/check_sector_chip_scope.py
  scripts/check_sector_chip_scope.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Render-half retry (429th review, 2026-11-11): this guard's render
half runs ~68.8s (second-slowest in the suite), so a load stall
that far in is expensive to lose -- an uncaught exception used to
read as drift (exit 1) with stdout ending at the last static check.
main() now runs the render half through the shared
run_render_with_retry() (scripts/render_guard_common.py): one retry
when the exception strikes before any R-check is recorded, then a
loud FAIL. The d3 fetcher is the shared get_d3_bytes() and a shim
that cannot be obtained returns the INFRA sentinel, mapped to exit
2 here -- the old code returned False (exit 1 drift) although this
docstring already promised exit 2 for infra.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")

BARE_SWEEP = "document.querySelectorAll('.chip')"
SCOPED_SWEEP = ("document.querySelectorAll('#sector-chips "
                ".chip:not(.combined-filter-chip)')")

# (check name, body marker, expected helper call)
SITES = [
    ("C2 All-chip handler calls helper with null",
     "allChip.addEventListener('click', function() {",
     "updateSectorChipStates(null);"),
    ("C3 sector-chip handler calls helper with s",
     "sectors.forEach(function(s) {",
     "updateSectorChipStates(s);"),
    ("C4 filterBySector calls helper with sectorName",
     "window.filterBySector = function(sectorName) {",
     "updateSectorChipStates(sectorName || null);"),
    ("C5 filterByDistribution calls helper with dist sector",
     "window.filterByDistribution = function(sector, minComp, maxComp, label) {",
     "updateSectorChipStates(window._activeDistFilter ? sector : null);"),
    ("C6 dist-chip dismiss calls helper with null",
     "function updateDistFilterIndicator() {",
     "updateSectorChipStates(null);"),
    ("C7 filterBySectorFromBar calls helper with activeSector",
     "window.filterBySectorFromBar = function(sectorName) {",
     "updateSectorChipStates(activeSector);"),
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def fn_body(app, marker):
    """Brace-matched body starting at the first '{' after marker."""
    i = app.find(marker)
    if i < 0:
        return None
    j = app.find("{", i)
    if j < 0:
        return None
    depth = 0
    k = j
    while k < len(app):
        if app[k] == "{":
            depth += 1
        elif app[k] == "}":
            depth -= 1
            if depth == 0:
                return app[j:k + 1]
        k += 1
    return None


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # C1: the helper exists and its sweep is scoped to sector chips.
    body = fn_body(app, "function updateSectorChipStates(activeSectorName) {")
    check("C1 updateSectorChipStates helper scopes its sweep to sector chips",
          body is not None and SCOPED_SWEEP in body,
          "" if (body is not None and SCOPED_SWEEP in body)
          else "helper missing or sweep not scoped")

    for name, marker, call in SITES:
        b = fn_body(app, marker)
        if b is None:
            check(name, False, "site marker not found: %s" % marker[:60])
            continue
        ok_call = call in b
        ok_nobare = BARE_SWEEP not in b
        check(name, ok_call and ok_nobare,
              "" if (ok_call and ok_nobare)
              else ("helper call missing" if not ok_call
                    else "bare document-wide .chip sweep still present"))

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

            def chip_state(chip_id=None, text=None):
                return pg.evaluate("""([chipId, text]) => {
                    let c = null;
                    if (chipId) c = document.getElementById(chipId);
                    else {
                        c = [...document.querySelectorAll('#sector-chips .chip')]
                            .find(el => el.textContent.trim() === text) || null;
                    }
                    if (!c) return null;
                    return { active: c.classList.contains('active'),
                             text: c.textContent.trim() };
                }""", [chip_id, text])

            # R1: gender F filter on, then a sector click. The gender
            # chip lives inside #sector-chips itself and its updater is
            # NOT called on the sector path, so pre-fix the sweep
            # stripped its 'active' class while it still filtered to 6.
            pg.evaluate("""() => {
                window._activeGenderFilter = 'F';
                window._updateGenderFilterIndicator();
            }""")
            pg.wait_for_timeout(300)
            g_before = chip_state(chip_id="gender-filter-chip")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            g_after = chip_state(chip_id="gender-filter-chip")
            it_chip = chip_state(text="Information Technology")
            all_chip = chip_state(text="All")
            r1_ok = (g_before is not None and g_before["active"]
                     and g_after is not None and g_after["active"]
                     and "Female CEOs" in g_after["text"]
                     and it_chip is not None and it_chip["active"]
                     and all_chip is not None and not all_chip["active"]
                     and n1 == 6)
            check("R1 gender chip keeps 'active' across a sector click (footer 6)",
                  r1_ok,
                  "before=%r after=%r it=%r all=%r footer=%s (want gender "
                  "active before+after, IT active, All inactive, 6 rows)"
                  % (g_before, g_after, it_chip, all_chip, n1))

            # R2: same for the vol-tenure chip, which lives in
            # .table-controls. Fresh page state: reload, set the
            # bracket, then the sector click.
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)
            pg.evaluate("""() => {
                window._activeVolTenureBracket = { min: 0, max: Infinity, label: '0-99 yrs' };
                window._updateVolTenureFilterIndicator();
            }""")
            pg.wait_for_timeout(300)
            v_before = chip_state(chip_id="vol-tenure-chip")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            n2 = footer_count()
            v_after = chip_state(chip_id="vol-tenure-chip")
            r2_ok = (v_before is not None and v_before["active"]
                     and v_after is not None and v_after["active"]
                     and "Volatility" in v_after["text"]
                     and n2 >= 1)
            check("R2 vol-tenure chip keeps 'active' across a sector click",
                  r2_ok,
                  "before=%r after=%r footer=%s (want vol-tenure active "
                  "before+after, >= 1 row)" % (v_before, v_after, n2))

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
        print("render checks infra (d3 shim unavailable)")
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
