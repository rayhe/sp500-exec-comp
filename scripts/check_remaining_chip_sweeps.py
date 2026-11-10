#!/usr/bin/env python3
"""Guard: the remaining document-wide '.chip' sweeps are scoped to sector chips.

Background (389th review, 2026-11-08): the 388th review scoped the six
sector-change paths to updateSectorChipStates, but nine document-wide
sweeps remained in js/app.js, and every one of them strips 'active'
from live indicator chips whose state the path deliberately keeps:

  sortTableByKey            keeps gov/vol/vol-tenure/yoy/board (its own
                            comment says so) -- a plain column sort made
                            a live vol/board chip look inactive.
  insightResetAndSort       keeps board (its _clearAfSelects comment
                            says so) -- every insight-card reset did it.
  Sector Tenure / SoP       insight actions: insightResetAndSort + a
  insight actions           sector sweep, so a live board chip lost
                            'active' on every insight click.
  Correlation Anomalies     insight action: performs NO reset at all,
  insight action            so the sweep stripped EVERY live indicator
                            chip while all of them kept filtering.
  applyHashState sector     vol/board/community/quartile/position were
  branch                    session-local (not hash-serialized) and
                            survived a hash change -- the sweep stripped
                            their chips on every back/forward navigation.
                            (Vol/vol-tenure/board joined the serialized
                            set in the 412th review, so the restore
                            below re-creates their chips; the sweep
                            must stay scoped for the sector chip
                            itself and for any dim without a restore.)
  sector-analytics row      calls twelve indicator updaters (which
  click                     re-render their chips WITH 'active') and
                            then swept the class right back off them.
  hashchange handler        same dims as above (vol/vol-tenure/board
                            hash-serialized since the 412th, so the
                            reset nulls them and removes their chips
                            by id; the sweep stays scoped to sector
                            chips all the same).
  Escape handler            keeps tenure/gov/vol/vol-tenure/board/
                            community/quartile/position/PvP-covered
                            (its own keptEsc list says so).

The fix: all nine sites call updateSectorChipStates (the 388th
helper, scoped to '#sector-chips .chip:not(.combined-filter-chip)')
with the sector the path sets (or null when it clears the sector).
The two full-reset paths keep their document-wide sweep on purpose:
resetAllFilters and findCompanyInTable null every filter state and
remove every indicator chip by id, so the sweep there is consistent.

Checks:
  C1  HARD FAIL: the updateSectorChipStates helper is missing, or its
      sweep is not scoped to '#sector-chips .chip:not(.combined-filter-chip)'.
  C2-C10 HARD FAIL: each of the nine sites above still carries the
      bare document-wide '.chip' sweep, or does not call the helper
      with the right active name (sortTableByKey / insightResetAndSort /
      hashchange / Escape: null; Sector Tenure: longestSec.name;
      Sector SoP: lowestSec.name; Correlation Anomalies: topSector;
      applyHashState: state.sector; SA row click: activeSector).
  C11 HARD FAIL: the file does not contain exactly two remaining
      bare sweeps, one inside resetAllFilters and one inside
      findCompanyInTable (the consistent full-reset paths).
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1 sort keeps the vol chip: vol 0-5pct active, then sortTableByKey
     runs -- the chip keeps 'active' and the footer count is unchanged.
     Pre-fix: the chip lost 'active' while still filtering.
  R2 Escape keeps the board chip: gender F + board low active, then
     Escape -- the gender chip is removed, the board chip keeps
     'active', and the footer still counts the board filter.
     Pre-fix: the board chip lost 'active' while still filtering.
  R3 sector-analytics row click keeps the vol chip: vol 0-5pct active,
     then a sector-analytics row is clicked -- the vol chip keeps
     'active' and the clicked sector chip is active. Pre-fix: the
     sweep stripped the vol chip (and every updater re-render).
  R4 (412th review) hash change drops the vol filter: vol 0-5pct
     active, then the hash gains sector=Information Technology --
     the vol chip is gone, state is null, the footer is the
     sector-only count and the IT sector chip is active. Pre-412th
     vol was session-local and the chip survived the navigation;
     now that it is hash-serialized, a hash that drops vmin must
     drop the filter (341st stuck-filter class).
  R5 Sector SoP insight card keeps the board chip: board low
     active, then the card is clicked -- the board chip keeps
     'active' and the lowest-SoP sector chip is active. Pre-fix: the
     board chip lost 'active' while still filtering. (The Sector
     Tenure card would test the same path, but its push-time action
     is dead: the insights[13].action index assignment at app.js
     ~3594 overwrites it with a sort+scroll action meant for another
     card -- a pre-existing index-fragility bug, queued for the next
     run, not this one.)
  R6 zero page errors across the render half.

Usage:
  scripts/check_remaining_chip_sweeps.py
  scripts/check_remaining_chip_sweeps.py --static-only

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

BARE_SWEEP = "document.querySelectorAll('.chip')"
SCOPED_SWEEP = ("document.querySelectorAll('#sector-chips "
                ".chip:not(.combined-filter-chip)')")

# (check name, body marker, expected helper call); marker may be a
# (label, action) pair for insight-card actions.
SITES = [
    ("C2 sortTableByKey calls helper with null",
     "function sortTableByKey(key, dir) {",
     "updateSectorChipStates(null);"),
    ("C3 insightResetAndSort calls helper with null",
     "function insightResetAndSort(sortKey, sortDir) {",
     "updateSectorChipStates(null);"),
    ("C4 Sector Tenure action calls helper with longestSec.name",
     ("Sector Tenure", "action: function() {"),
     "updateSectorChipStates(longestSec.name);"),
    ("C5 Sector SoP action calls helper with lowestSec.name",
     ("Sector SoP", "action: function() {"),
     "updateSectorChipStates(lowestSec.name);"),
    ("C6 Correlation Anomalies action calls helper with topSector",
     ("Correlation Anomalies", "action: function() {"),
     "updateSectorChipStates(topSector);"),
    ("C7 applyHashState sector branch calls helper with state.sector",
     "if (state.sector) {",
     "updateSectorChipStates(state.sector);"),
    ("C8 sector-analytics row click calls helper with activeSector",
     "tbody.addEventListener('click', function(ev) {",
     "updateSectorChipStates(activeSector);"),
    ("C9 hashchange handler calls helper with null",
     "window.addEventListener('hashchange', function() {",
     "updateSectorChipStates(null);"),
    ("C10 Escape handler calls helper with null",
     "if (activeSector || searchTerm || window._activeRatioBucket || window._activeDistFilter || window._activeConcTier",
     "updateSectorChipStates(null);"),
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


def action_body(app, label):
    """Brace-matched body of the insight-card action for a card label."""
    li = app.find("label: '" + label + "',")
    if li < 0:
        return None
    ai = app.find("action: function() {", li)
    if ai < 0:
        return None
    return fn_body(app[ai:], "action: function() {")


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
        if isinstance(marker, tuple):
            b = action_body(app, marker[0])
        else:
            b = fn_body(app, marker)
        if b is None:
            check(name, False, "site marker not found: %s" % str(marker)[:60])
            continue
        ok_call = call in b
        ok_nobare = BARE_SWEEP not in b
        check(name, ok_call and ok_nobare,
              "" if (ok_call and ok_nobare)
              else ("helper call missing" if not ok_call
                    else "bare document-wide .chip sweep still present"))

    # C11: exactly two bare sweeps remain, both in consistent full-reset
    # paths (resetAllFilters nulls every state and removes every chip
    # by id; findCompanyInTable does the same per the 376th review).
    count = app.count(BARE_SWEEP)
    reset_body = fn_body(app, "window.resetAllFilters = function() {")
    find_body = fn_body(app, "window.findCompanyInTable = function(ticker) {")
    in_reset = reset_body is not None and BARE_SWEEP in reset_body
    in_find = find_body is not None and BARE_SWEEP in find_body
    check("C11 exactly two bare sweeps remain, in resetAllFilters and findCompanyInTable",
          count == 2 and in_reset and in_find,
          "bare-sweep count=%d (want 2), in resetAllFilters=%s, in "
          "findCompanyInTable=%s" % (count, in_reset, in_find))

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

            def load():
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

            def set_vol():
                pg.evaluate("""() => {
                    window._activeVolatilityBucket = { min: 0, max: 5, label: '0-5%' };
                    window._updateVolatilityFilterIndicator();
                    if (window.compData) renderTable(compData.companies);
                }""")
                pg.wait_for_timeout(300)

            def set_board():
                pg.evaluate("""() => {
                    window._activeBoardFilter = { mode: 'low' };
                    window._updateBoardFilterIndicator();
                    if (window.compData) renderTable(compData.companies);
                }""")
                pg.wait_for_timeout(300)

            # R1: a plain column sort must not strip a live vol chip.
            # sortTableByKey deliberately keeps vol state (its own
            # comment), so pre-fix the chip lost 'active' while the
            # table stayed vol-filtered.
            load()
            set_vol()
            v_before = chip_state(chip_id="volatility-filter-chip")
            n_before = footer_count()
            pg.evaluate("() => sortTableByKey('total_compensation', 'asc')")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            v_after = chip_state(chip_id="volatility-filter-chip")
            r1_ok = (v_before is not None and v_before["active"]
                     and v_after is not None and v_after["active"]
                     and "Volatility" in v_after["text"]
                     and n_before >= 1 and n1 == n_before)
            check("R1 vol chip keeps 'active' across a column sort (footer unchanged)",
                  r1_ok,
                  "before=%r after=%r footer before=%s after=%s (want vol "
                  "active before+after, footer unchanged)" % (v_before, v_after, n_before, n1))

            # R2: Escape clears gender but must keep the board chip
            # (board is on Escape's own keptEsc list).
            load()
            pg.evaluate("""() => {
                window._activeGenderFilter = 'F';
                window._updateGenderFilterIndicator();
                window._activeBoardFilter = { mode: 'low' };
                window._updateBoardFilterIndicator();
            }""")
            pg.wait_for_timeout(300)
            g_before = chip_state(chip_id="gender-filter-chip")
            b_before = chip_state(chip_id="board-filter-chip")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(1200)
            n2 = footer_count()
            g_after = chip_state(chip_id="gender-filter-chip")
            b_after = chip_state(chip_id="board-filter-chip")
            r2_ok = (g_before is not None and g_before["active"]
                     and b_before is not None and b_before["active"]
                     and g_after is None
                     and b_after is not None and b_after["active"]
                     and "Board" in b_after["text"]
                     and n2 >= 1)
            check("R2 board chip keeps 'active' across Escape (gender chip removed)",
                  r2_ok,
                  "gender before=%r after=%r board before=%r after=%r "
                  "footer=%s (want gender removed, board active, >= 1 row)"
                  % (g_before, g_after, b_before, b_after, n2))

            # R3: a sector-analytics row click must not strip a live
            # vol chip -- the handler calls twelve indicator updaters
            # (re-rendering their chips WITH 'active') before the
            # sweep, so pre-fix the sweep undid them all.
            load()
            set_vol()
            v_before = chip_state(chip_id="volatility-filter-chip")
            pg.locator(".sector-analytics-row").first.click()
            pg.wait_for_timeout(1200)
            n3 = footer_count()
            v_after = chip_state(chip_id="volatility-filter-chip")
            any_sector_active = pg.evaluate("""() => {
                return [...document.querySelectorAll('#sector-chips .chip')]
                    .some(el => el.classList.contains('active')
                         && el.textContent.trim() !== 'All');
            }""")
            r3_ok = (v_before is not None and v_before["active"]
                     and v_after is not None and v_after["active"]
                     and any_sector_active and n3 >= 1)
            check("R3 vol chip keeps 'active' across a sector-analytics row click",
                  r3_ok,
                  "before=%r after=%r sector_active=%s footer=%s (want vol "
                  "active before+after, a sector chip active, >= 1 row)"
                  % (v_before, v_after, any_sector_active, n3))

            # R4 (412th review): vol joined the serialized set, so a
            # hash change to a sector-only link must DROP the vol
            # filter -- chip gone, state null, footer the sector-only
            # count -- the 341st stuck-filter class: a filter the URL
            # no longer describes must not survive the navigation.
            # Pre-412th vol was session-local and the chip survived.
            load()
            set_vol()
            v_before = chip_state(chip_id="volatility-filter-chip")
            n_vol = footer_count()
            pg.evaluate("() => { location.hash = '#sector=Information%20Technology'; }")
            pg.wait_for_timeout(1500)
            n4 = footer_count()
            v_after = chip_state(chip_id="volatility-filter-chip")
            f4 = pg.evaluate("() => window._activeVolatilityBucket || null")
            it_chip = chip_state(text="Information Technology")
            # IT-only count from a fresh load of the same sector link.
            pg.goto("http://127.0.0.1:%d/index.html#sector=Information%%20Technology" % port,
                    timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)
            n_it = footer_count()
            r4_ok = (v_before is not None and v_before["active"]
                     and v_after is None and f4 is None
                     and it_chip is not None and it_chip["active"]
                     and n4 == n_it and n4 >= 1 and n4 != n_vol)
            check("R4 hash change to a sector link drops the vol filter (chip gone, state null, footer = sector-only count)",
                  r4_ok,
                  "before=%r after=%r state=%r it=%r footer=%s it_only=%s vol_only=%s (want vol active before, chip + state gone after, IT active, footer == IT-only count)"
                  % (v_before, v_after, f4, it_chip, n4, n_it, n_vol))

            # R5: the Sector SoP insight card must not strip a live
            # board chip (insightResetAndSort keeps board state).
            # Sector Tenure would test the same path, but its action
            # is clobbered by the insights[13] index overwrite
            # (pre-existing bug -- see the docstring), so SoP is the
            # working sector-filtering insight card on this path.
            load()
            set_board()
            b_before = chip_state(chip_id="board-filter-chip")
            pg.locator(".insight-card.insight-clickable",
                       has_text="Sector SoP").first.click()
            pg.wait_for_timeout(1500)
            n5 = footer_count()
            b_after = chip_state(chip_id="board-filter-chip")
            any_sector_active = pg.evaluate("""() => {
                return [...document.querySelectorAll('#sector-chips .chip')]
                    .some(el => el.classList.contains('active')
                         && el.textContent.trim() !== 'All');
            }""")
            r5_ok = (b_before is not None and b_before["active"]
                     and b_after is not None and b_after["active"]
                     and "Board" in b_after["text"]
                     and any_sector_active and n5 >= 1)
            check("R5 board chip keeps 'active' across the Sector SoP insight card",
                  r5_ok,
                  "before=%r after=%r sector_active=%s footer=%s (want "
                  "board active before+after, a sector chip active, >= 1 row)"
                  % (b_before, b_after, any_sector_active, n5))

            r6_ok = len(errors) == 0
            check("R6 zero page errors across the render half",
                  r6_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok and r3_ok and r4_ok and r5_ok and r6_ok
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
