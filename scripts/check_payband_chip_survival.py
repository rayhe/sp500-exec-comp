#!/usr/bin/env python3
"""Guard: the AF pay-band chip survives re-renders and its dismiss keeps
an independent sector filter.

Background (383rd review, 2026-11-08): queued candidate from the 382nd
review -- handlePayBand appended its own span chip to
#table-summary-bar, and renderSummaryBar rebuilds that bar via innerHTML
on every renderTable, so the chip vanished on the next sort/render while
the pay-band filter persisted (footer kept the filtered count, no
dismiss affordance remained). Same class as the SoP chip wipe fixed in
the 382nd review. Proved pre-fix: AF pay band 15-25M filtered to 192
companies with chip "Pay: 15-25M" in #table-summary-bar; after a sort
click the chip was gone, footer still 192, state still set.

The fix delegates the chip to the app.js indicator
_updateDistFilterIndicator (the SoP pattern): a button chip in
.table-controls, removed and re-rendered by id, so re-selecting a band
re-renders correctly. The AF label is already chart-style ('$15M-$25M'),
matching the combined-filter badge, which pushes _activeDistFilter.label
raw. The indicator's dismiss previously cleared the sector
unconditionally, but the old AF chip only nulled the band -- so the
dismiss now clears the sector (and its chip state / bar ring) only when
the dist filter itself carries a sector (the chart-origin distribution
filter); an AF pay band or comp bracket carries sector null, and the
sector is an independent dim then.

Checks:
  C1 HARD FAIL: handlePayBand does not delegate its chip to
     _updateDistFilterIndicator.
  C2 HARD FAIL: a summaryBar.appendChild site remains inside
     handlePayBand (the pre-fix chip append).
  C3 HARD FAIL: the dist-chip dismiss does not gate setActiveSector on
     the filter's own sector.
  C4 HARD FAIL: the sector chip-state reset / sector bar ring-clear in
     the dist-chip dismiss is not gated the same way.
Render (headless Chromium, d3 requests aborted -- the AF panel, summary
bar and hash paths are pure app.js):
  R1 AF pay band 15-25M filters to 192 companies; the chip lives in
     .table-controls and survives a sort-triggered renderTable.
  R2 sector + pay band combined: dismissing the pay chip restores the
     sector-only count, keeps the sector chip active, clears af-pay-band
     and drops dmin from the hash.
  R3 a lone pay band dismissed via its chip restores 518, nulls state,
     clears af-pay-band and drops dmin from the hash.
  R4 zero page errors across the render half.

Usage:
  scripts/check_payband_chip_survival.py
  scripts/check_payband_chip_survival.py --static-only

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
AF_JS = os.path.join(REPO, "js", "advanced-filters.js")

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
        af = open(AF_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js files: %s" % exc)
        return 2

    # C1/C2: handlePayBand delegates its chip to the app.js indicator
    # and no longer appends a span to #table-summary-bar.
    pay_body = extract_function_body(af, "function handlePayBand")
    if pay_body is None:
        check("C1 handlePayBand exists in advanced-filters.js", False,
              "definition not found")
        check("C2 no summaryBar append inside handlePayBand", False,
              "definition not found")
    else:
        # C1: the SET branch (after the state assignment) delegates the
        # chip to the indicator. The empty branch already calls the
        # indicator (335th review), so a whole-body substring check is
        # vacuous on the pre-fix tree -- scope to the set branch.
        set_branch = pay_body.split("window._activeDistFilter = {", 1)
        c1_ok = (len(set_branch) == 2
                 and "_updateDistFilterIndicator()" in set_branch[1])
        check("C1 handlePayBand delegates its chip to the dist indicator",
              c1_ok,
              "" if c1_ok else "no _updateDistFilterIndicator call in the "
              "handlePayBand set branch")
        c2_ok = "summaryBar.appendChild" not in pay_body
        check("C2 no summaryBar append inside handlePayBand", c2_ok,
              "" if c2_ok else "summaryBar.appendChild still present in "
              "handlePayBand")

    # C3/C4: the dist-chip dismiss clears the sector only when the
    # dist filter itself carries one (chart-origin distribution filter).
    ind_body = extract_function_body(app, "function updateDistFilterIndicator")
    if ind_body is None:
        check("C3 dist-chip dismiss gates setActiveSector on own sector",
              False, "definition not found")
        check("C4 sector chip-state reset and bar ring gated the same way",
              False, "definition not found")
    else:
        c3_ok = "if (hadSector) setActiveSector(null);" in ind_body
        check("C3 dist-chip dismiss gates setActiveSector on own sector",
              c3_ok,
              "" if c3_ok else "no gated setActiveSector in "
              "updateDistFilterIndicator")
        # 388th review: the inline chip sweep moved into the
        # updateSectorChipStates helper; accept the helper call gated
        # on hadSector in either the old block form or the one-liner
        # form (the pre-388th tree used the inline sweep inside an
        # 'if (hadSector) {' block).
        gated_block = extract_function_body(ind_body, "if (hadSector) {")
        c4_ok = (("if (hadSector) updateSectorChipStates(null);" in ind_body
                 or (gated_block is not None
                     and ("querySelectorAll('.chip')" in gated_block
                          or "updateSectorChipStates(null)" in gated_block)))
                 and "if (hadSector && window.highlightSectorBar) "
                     "window.highlightSectorBar(null);" in ind_body)
        check("C4 sector chip-state reset and bar ring gated the same way",
              c4_ok,
              "" if c4_ok else "chip reset or sector-bar clear not gated "
              "on hadSector")

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

            def dist_chip():
                return pg.evaluate("""() => {
                    const c = document.getElementById('dist-filter-chip');
                    if (!c) return null;
                    return {text: c.textContent.trim(),
                            parent: c.parentNode.className || c.parentNode.id,
                            tag: c.tagName};
                }""")

            def badge_text():
                return pg.evaluate("""() => {
                    const b = document.querySelector(
                        '#table-summary-bar .combined-filter-badge');
                    return b ? b.textContent : null;
                }""")

            def hash_has_dmin():
                return pg.evaluate("() => location.hash.indexOf('dmin') >= 0")

            def af_pay_value():
                return pg.evaluate(
                    "() => document.getElementById('af-pay-band').value")

            def sector_chip_active():
                return pg.evaluate("""() => [...document.querySelectorAll(
                    '.chip')].filter(c => c.textContent.trim()
                    === 'Information Technology').some(
                    c => c.classList.contains('active'))""")

            def dismiss_dist_chip():
                pg.evaluate("""() => {
                    const c = document.getElementById('dist-filter-chip');
                    if (c) c.click();
                }""")
                pg.wait_for_timeout(1000)

            # Open the AF panel once; the comp details group holds the
            # pay-band select.
            pg.click("#advanced-filters-toggle")
            pg.wait_for_timeout(400)
            pg.evaluate("""() => {
                const d = document.querySelector(
                    'details.af-cat[data-cat="comp"]');
                if (d) d.open = true;
            }""")

            # R1: AF pay band 15-25M -> 192 companies, chip in
            # .table-controls, survives a sort-triggered renderTable.
            pg.select_option("#af-pay-band", "15000000-25000000")
            pg.wait_for_timeout(800)
            n1a = footer_count()
            chip1a = dist_chip()
            pg.click('th[data-sort="total_compensation"]')
            pg.wait_for_timeout(800)
            n1b = footer_count()
            chip1b = dist_chip()
            r1_ok = (n1a == 192 and n1b == 192 and chip1a is not None
                     and chip1b is not None
                     and "table-controls" in chip1a["parent"]
                     and "table-controls" in chip1b["parent"]
                     and "$15M" in chip1b["text"])
            check("R1 pay-band chip survives a sort-triggered renderTable",
                  r1_ok,
                  "footer=%s/%s chip=%r/%r (want 192/192, table-controls, "
                  "$15M)" % (n1a, n1b, chip1a, chip1b))

            # R2: add the Information Technology sector (88 alone),
            # then dismiss the pay chip: sector-only count returns,
            # sector chip stays active, af-pay-band cleared, dmin gone.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1000)
            n2a = footer_count()
            b2 = badge_text()
            dismiss_dist_chip()
            n2b = footer_count()
            sec2 = sector_chip_active()
            r2_ok = (0 < n2a < 88 and b2 is not None
                     and "Information Technology" in b2 and "$15M" in b2
                     and n2b == 88 and sec2
                     and af_pay_value() == "" and not hash_has_dmin()
                     and pg.evaluate("() => window._activeDistFilter === null"))
            check("R2 pay-chip dismiss keeps an independent sector filter",
                  r2_ok,
                  "combined=%s badge=%r sector-only=%s sector-chip=%s "
                  "af-pay=%r dmin=%s" % (n2a, b2, n2b, sec2,
                                         af_pay_value(), hash_has_dmin()))

            # R3: lone pay band, dismissed via its chip, restores 518.
            pg.evaluate("() => window.filterBySector(null)")
            pg.wait_for_timeout(800)
            pg.select_option("#af-pay-band", "15000000-25000000")
            pg.wait_for_timeout(800)
            n3a = footer_count()
            dismiss_dist_chip()
            n3b = footer_count()
            chip3 = dist_chip()
            r3_ok = (n3a == 192 and n3b == 518 and chip3 is None
                     and af_pay_value() == "" and not hash_has_dmin()
                     and pg.evaluate("() => window._activeDistFilter === null"))
            check("R3 lone pay-band chip dismiss restores the full table",
                  r3_ok,
                  "filtered=%s restored=%s chip=%r af-pay=%r dmin=%s"
                  % (n3a, n3b, chip3, af_pay_value(), hash_has_dmin()))

            r4_ok = len(errors) == 0
            check("R4 zero page errors across the render half",
                  r4_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok and r3_ok and r4_ok
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
