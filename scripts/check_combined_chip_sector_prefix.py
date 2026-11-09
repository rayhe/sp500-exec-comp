#!/usr/bin/env python3
"""Guard: every combined-filter chip shows the sector prefix when combined.

Background (393rd review, 2026-11-08): the 392nd review queued
indicator-chip label staleness -- chips whose updaters were not called
on the sector path kept their pre-sector (lone-filter) label while the
table was filtered to a sector + that dim. The audit found two halves:

  1. Five updaters never read activeSector at all, so even a re-run
     could not show the combined label: peer-dist, volatility,
     vol-tenure, gov, crosstab. (Board and ceo-cfo already had the
     isCombined label; gender, tenure, SoP, stock-pct and the rest did
     too.) All five now use the established purple treatment
     (rgba(167,139,250,...) + #a78bfa) with a 'Click to clear combined
     sector + ... filter' title, like the other fourteen updaters.
  2. Seven updaters were never re-run on the sector path at all:
     board, ceo-cfo, gov, peer-dist, crosstab, volatility, vol-tenure.
     The sector-change refresh existed at six sites -- the All chip,
     the sector chips, filterBySector (the canonical programmatic path
     every chart sector-bar click uses), filterBySectorFromBar, the
     sector-analytics row click, and the Correlation Anomalies scatter
     action -- and filterBySector's list was the stalest (9 calls: it
     also lacked sop, stock-pct, gender and tenure). All six sites now
     call all twenty-two indicator updaters (21 chips + the PvP toggle).
     The insight-card sector actions need no call: insightResetAndSort
     nulls every filter and removes every chip before setActiveSector,
     so there is no live chip to go stale.

Out of scope (next-run candidates, not pinned here): the quartile and
position chips are inline-built in network.js / the detail panel with
no updater to re-run, so a later sector change leaves their labels
lone; applyHashState restores ceo-cfo / sop / stock-pct state without
calling their updaters, so a deep link into those filters may show no
chip at all (a missing-chip gap, not a stale-label one).

Update (394th review, 2026-11-09): the quartile/position half is now
closed -- updateQuartileFilterIndicator (network.js) and
updatePositionFilterIndicator (app.js) exist and are called from all
six sector paths, pinned by scripts/check_quartile_position_sector_prefix.py
(this guard still pins only the nineteen app.js updaters; together
the two guards pin all twenty-one chips). The applyHashState half
was verified closed by the 394th run's audit: both restore sites
(init and hashchange) render the ceo-cfo chip, and the sop /
stock-pct chips were fixed at both sites in the 324th review.

Update (395th review, 2026-11-09): the "all twenty at six sites"
count in this docstring was stale twice over -- the 394th review
added quartile + position as the 20th and 21st chips (twenty-two
updaters with the toggle), and the Correlation Anomalies scatter
action never called the toggle (twenty-one, not twenty-two). The
395th review adds the toggle call to the scatter action (its render
is sector-independent -- the count comes from the full companies
list, so the call is uniformity-only) and corrects the count here
and in the two "All twenty" comments in js/app.js to twenty-two.
scripts/check_position_chip_lone_text.py pins the scatter-action
toggle call and the corrected count claims.

Checks (static - file reads, <1s):
  C1  HARD FAIL: all 19 update*FilterIndicator bodies contain an
      isCombined assignment reading activeSector AND a combined label
      built as activeSector + '...'. The dist updater's form is
      `activeSector && !df.sector` (sector-scoped dist), the rest are
      `!!activeSector`; the check accepts either.
  C2a HARD FAIL: the All-chip click handler re-runs all 19 updaters.
  C2b HARD FAIL: the sector-chip click handler re-runs all 19 updaters.
  C2c HARD FAIL: filterBySector re-runs all 19 updaters (bare calls).
  C2d HARD FAIL: filterBySectorFromBar re-runs all 19 updaters.
  C2e HARD FAIL: the sector-analytics row click re-runs all 19 updaters.
  C2f HARD FAIL: the Correlation Anomalies scatter action re-runs all
      19 updaters after setActiveSector(topSector).
Render (headless Chromium, d3 aborted -- no chart click is needed):
  R1  Board high (real AF select) + real Information Technology
      sector-chip click: board chip reads
      'Information Technology x Board >=80%' in purple.
      Pre-fix: lone 'Board >=80%' in blue.
  R2  Gov B (filterByGovGrade, the gov badge onclick target) +
      filterBySector('Information Technology'): gov chip reads
      'Information Technology x Gov: Grade B' in purple, footer 5.
      Grade B, not A: only 4 companies in the whole index are grade A
      and none is in Information Technology, so A+IT is a genuine
      zero-row combination. Pre-fix: lone 'Gov: Grade B'
      (filterBySector never re-ran it).
  R3  Vol-tenure bracket (evaluate setup -- the chart that sets it
      lives in a sort-contextual summary, same direct-handler
      precedent as the 392nd R3) + real sector-analytics row click:
      vol-tenure chip reads
      'Information Technology x Volatility x Tenure: ...' in purple.
      Pre-fix: lone 'Volatility x Tenure: ...'.
  R4  All-chip click after R1: board chip reverts to lone
      'Board >=80%' in blue (the sector context is removed, not
      stuck).
  R5  zero page errors across the render half.

Usage:
  scripts/check_combined_chip_sector_prefix.py
  scripts/check_combined_chip_sector_prefix.py --static-only

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

# The 19 chip updaters (the PvP toggle is a 20th refresh call but not a
# chip updater -- it has no label to combine, so C1 does not cover it).
UPDATERS = ["Dist", "Ratio", "Sop", "Board", "Conc", "CeoCfo", "YoY",
            "Pctile", "StockPct", "CeoTransition", "TeamCompleteness",
            "Gender", "AspDelta", "Tenure", "Gov", "Crosstab",
            "PeerDist", "Volatility", "VolTenure"]

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


def window_after(app, start_marker, end_marker):
    """Text between the first start_marker and the next end_marker."""
    i = app.find(start_marker)
    if i < 0:
        return None
    j = app.find(end_marker, i + len(start_marker))
    if j < 0:
        return None
    return app[i:j]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # C1: every updater body reads activeSector into isCombined and
    # builds a combined label from it. The check looks for the code
    # pattern, not the bare word -- the 393rd comments say "combined
    # label" but never assign isCombined, so prose cannot false-pass.
    missing = []
    for name in UPDATERS:
        body = fn_body(app, "function update%sFilterIndicator(" % name)
        ok = (body is not None
              and re.search(r"var isCombined\s*=.*activeSector", body)
              and "activeSector + '" in body)
        if not ok:
            missing.append(name)
    check("C1 all 19 indicator updaters build a combined sector label",
          len(missing) == 0,
          "updater(s) without isCombined label: %s" % (missing,)
          if missing else "")

    def site_calls(site_window, guarded):
        """Updater names whose refresh call is missing from a window."""
        if site_window is None:
            return list(UPDATERS)
        gone = []
        for name in UPDATERS:
            if guarded:
                call = ("window._update%sFilterIndicator) "
                        "window._update%sFilterIndicator();" % (name, name))
            else:
                call = "update%sFilterIndicator();" % name
            if call not in site_window:
                gone.append(name)
        return gone

    # C2a: All-chip click handler (window-guarded calls).
    w = window_after(app, "allChip.addEventListener('click', function() {",
                     "highlightSectorBar(null)")
    gone = site_calls(w, guarded=True)
    check("C2a All-chip click re-runs all 19 indicator updaters",
          len(gone) == 0,
          "missing: %s" % (gone,) if gone else "")

    # C2b: sector-chip click handler -- setActiveSector(s) is unique to
    # buildSectorChips' per-sector handler.
    w = window_after(app, "setActiveSector(s);", "highlightSectorBar(s)")
    gone = site_calls(w, guarded=True)
    check("C2b sector-chip click re-runs all 19 indicator updaters",
          len(gone) == 0,
          "missing: %s" % (gone,) if gone else "")

    # C2c: filterBySector (bare calls, same scope as the updaters).
    w = window_after(app, "window.filterBySector = function(sectorName) {",
                     "renderTable(companies);")
    gone = site_calls(w, guarded=False)
    check("C2c filterBySector re-runs all 19 indicator updaters",
          len(gone) == 0,
          "missing: %s" % (gone,) if gone else "")

    # C2d: filterBySectorFromBar (bare calls).
    w = window_after(app,
                     "window.filterBySectorFromBar = function(sectorName) {",
                     "renderTable(companies);")
    gone = site_calls(w, guarded=False)
    check("C2d filterBySectorFromBar re-runs all 19 indicator updaters",
          len(gone) == 0,
          "missing: %s" % (gone,) if gone else "")

    # C2e: sector-analytics row click -- the refresh comment is unique.
    w = window_after(
        app,
        "// Refresh combined filter chips to include/exclude sector context",
        "renderTable(companies);")
    gone = site_calls(w, guarded=True)
    check("C2e sector-analytics row click re-runs all 19 updaters",
          len(gone) == 0,
          "missing: %s" % (gone,) if gone else "")

    # C2f: Correlation Anomalies scatter action -- the only
    # setActiveSector(topSector) in the file; the refresh block sits
    # between it and the scatter redraw.
    w = window_after(app, "setActiveSector(topSector);", "drawScatterChart")
    gone = site_calls(w, guarded=True)
    check("C2f scatter action re-runs all 19 indicator updaters",
          len(gone) == 0,
          "missing: %s" % (gone,) if gone else "")

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
            browser = pw.chromium.launch(args=["--no-proxy-server"])
            errors = []
            pg = browser.new_page(viewport={"width": 1280, "height": 800})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.route("**/d3*", lambda r: r.abort())
            pg.route("**/d3js.org/**", lambda r: r.abort())
            pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())

            def load(url=None):
                pg.goto(url or "http://127.0.0.1:%d/index.html" % port,
                        timeout=60000)
                pg.wait_for_selector(
                    "#comp-tbody > tr:not(.skeleton-table-row-tr)",
                    timeout=30000)
                pg.wait_for_timeout(800)

            def chip_text(chip_id):
                return pg.evaluate("""(id) => {
                    const c = document.getElementById(id);
                    if (!c) return null;
                    const cs = getComputedStyle(c);
                    return { text: c.textContent, color: cs.color };
                }""", chip_id)

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            def click_sector_chip(name):
                pg.locator("#sector-chips .chip",
                           has_text=name).first.click()
                pg.wait_for_timeout(1000)

            # R1: board high via the real AF select, then a real
            # sector-chip click (site C2b). Pre-fix the chip kept its
            # lone label because updateBoardFilterIndicator never
            # re-ran on the sector path.
            load()
            pg.click("#advanced-filters-toggle")
            pg.wait_for_timeout(400)
            pg.evaluate("""() => {
                const d = document.querySelector(
                    'details.af-cat[data-cat="gov"]');
                if (d) d.open = true;
            }""")
            pg.select_option("#af-board", "high")
            pg.wait_for_timeout(800)
            pre1 = chip_text("board-filter-chip")
            click_sector_chip("Information Technology")
            c1 = chip_text("board-filter-chip")
            n1 = footer_count()
            r1_ok = (pre1 is not None and "Information Technology" not in pre1["text"]
                     and c1 is not None
                     and c1["text"].startswith(
                         "Information Technology \u00d7 Board \u226580%")
                     and c1["color"] == "rgb(167, 139, 250)"
                     and n1 == 70)
            check("R1 board+sector chip: board chip gains sector prefix "
                  "(chip=%r footer=%s)" % (c1, n1),
                  r1_ok,
                  "want 'Information Technology x Board >=80%%' in purple, "
                  "footer 70 (pre-click chip=%r)" % (pre1,))

            # R4: the All chip (site C2a) strips the sector context
            # back off -- same page state as R1, no reload.
            pg.locator("#sector-chips .chip", has_text="All").first.click()
            pg.wait_for_timeout(1000)
            c4 = chip_text("board-filter-chip")
            r4_ok = (c4 is not None
                     and c4["text"].startswith("Board \u226580%")
                     and "Information Technology" not in c4["text"]
                     and c4["color"] == "rgb(17, 138, 178)")
            check("R4 All chip: board chip reverts to lone label "
                  "(chip=%r)" % (c4,),
                  r4_ok,
                  "want lone 'Board >=80%' back in blue")

            # R2: gov B via filterByGovGrade (the gov badge onclick
            # target), then filterBySector (site C2c -- the chart
            # sector-bar path). Pre-fix filterBySector never re-ran
            # the gov updater, so the chip stayed lone. Grade B, not
            # A: only 4 companies in the whole index are grade A and
            # none is in Information Technology (probed 393rd review),
            # so A+IT is a genuine zero-row combination; B+IT is 5.
            load()
            pg.evaluate("() => filterByGovGrade('B', 65, 80)")
            pg.wait_for_timeout(800)
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1000)
            c2 = chip_text("gov-filter-chip")
            n2 = footer_count()
            r2_ok = (c2 is not None
                     and c2["text"].startswith(
                         "Information Technology \u00d7 Gov: Grade B")
                     and c2["color"] == "rgb(167, 139, 250)"
                     and n2 == 5)
            check("R2 gov+sector via filterBySector: gov chip gains "
                  "sector prefix (chip=%r footer=%s)" % (c2, n2),
                  r2_ok,
                  "want 'Information Technology x Gov: Grade B' in purple, "
                  "footer 5")

            # R3: vol-tenure bracket + real sector-analytics row click
            # (site C2e). The bracket is set by evaluate: the chart
            # that sets it lives in a sort-contextual summary, so the
            # setup calls the updater directly -- the 392nd R3
            # precedent -- while the sector change itself is the real
            # row click under test.
            load()
            pg.evaluate("""() => {
                window._activeVolTenureBracket =
                    { min: 0, max: 5, label: '0-5 yrs' };
                window._updateVolTenureFilterIndicator();
            }""")
            pg.wait_for_timeout(800)
            pre3 = chip_text("vol-tenure-chip")
            pg.locator('.sector-analytics-row[data-sector="Information Technology"]').first.click()
            pg.wait_for_timeout(1000)
            c3 = chip_text("vol-tenure-chip")
            n3 = footer_count()
            r3_ok = (pre3 is not None and "Information Technology" not in pre3["text"]
                     and c3 is not None
                     and c3["text"].startswith(
                         "Information Technology \u00d7 Volatility "
                         "\u00d7 Tenure:")
                     and c3["color"] == "rgb(167, 139, 250)"
                     and 0 < n3 < 518)
            check("R3 vol-tenure+sector row: chip gains sector prefix "
                  "(chip=%r footer=%s)" % (c3, n3),
                  r3_ok,
                  "want 'Information Technology x Volatility x Tenure: ...' "
                  "in purple, footer 1-517 (pre-click chip=%r)" % (pre3,))

            r5_ok = len(errors) == 0
            check("R5 zero page errors across the render half",
                  r5_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return all([r1_ok, r4_ok, r2_ok, r3_ok, r5_ok])
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
