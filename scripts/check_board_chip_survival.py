#!/usr/bin/env python3
"""Guard: the AF board-independence chip survives re-renders, and the
board filter itself survives a sort (it now filters in renderTable's
data path, not as a DOM post-process).

Background (384th review, 2026-11-08): queued candidate from the
382nd/383rd chip-wipe class -- handleBoard was the last AF handler
still appending its own span chip to #table-summary-bar, and
renderSummaryBar rebuilds that bar via innerHTML on every renderTable.
Worse than pay-band/SoP: the board filter itself was applied ONLY as a
DOM post-process in the AF _refreshTable wrapper, never in renderTable's
data path, so a sort, page change or search called renderTable directly
and the rows came back unfiltered while state, select and badge still
claimed the filter was live. sortTableByKey deliberately keeps board
state (330th review), so this was a live inconsistency, not intent.
Proved pre-fix: board high filtered to 39 visible rows on page 1 with
NO chip anywhere (the chip was wiped by the handler's own _refreshTable
-- it never survived its own selection) and the footer still read 518;
after a sort click all 50 rows on page 1 were visible while state,
af-board and badge still claimed "Board >=80%".

The fix has two parts: (1) renderTable applies the board filter in its
data path via the AF helper _applyBoardFilter, like every other AF dim,
so the footer count is truthful too (419 for high) and the _refreshTable
DOM post-process is removed (single source of truth); (2) the chip is
delegated to the new app.js indicator _updateBoardFilterIndicator (the
382nd/383rd pattern): a button chip in .table-controls, removed and
re-rendered by id, keyboard-focusable, with a dismiss that nulls state,
clears af-board and pushStates.

Checks:
  C1 HARD FAIL: handleBoard does not delegate its chip to
     _updateBoardFilterIndicator.
  C2 HARD FAIL: a summaryBar.appendChild site remains inside
     handleBoard (the pre-fix chip append).
  C3 HARD FAIL: renderTable does not apply the board filter in its
     data path (no _applyBoardFilter call inside renderTable).
  C4 HARD FAIL: the board-chip dismiss does not null state and clear
     af-board.
  C5 HARD FAIL: the board indicator does not render a button chip
     (the old span was click-only, not keyboard-focusable).
Render (headless Chromium, d3 requests aborted -- the AF panel, summary
bar and hash paths are pure app.js):
  R1 AF board high filters to 419 companies; the chip lives in
     .table-controls as a button and survives a sort-triggered
     renderTable (footer still 419, all 50 page-1 rows visible).
  R2 sector + board combined: dismissing the board chip restores the
     sector-only count (88 for Information Technology), keeps the
     sector chip active, clears af-board and nulls state.
  R3 a lone board high dismissed via its chip restores 518, removes
     the chip, nulls state and clears af-board.
  R4 zero page errors across the render half.

Usage:
  scripts/check_board_chip_survival.py
  scripts/check_board_chip_survival.py --static-only

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

    # C1/C2: handleBoard delegates its chip to the app.js indicator
    # and no longer appends a span to #table-summary-bar.
    board_body = extract_function_body(af, "function handleBoard")
    if board_body is None:
        check("C1 handleBoard exists in advanced-filters.js", False,
              "definition not found")
        check("C2 no summaryBar append inside handleBoard", False,
              "definition not found")
    else:
        # C1: the SET branch (after the state assignment) delegates the
        # chip to the indicator. The empty branch already calls the
        # indicator, so a whole-body substring check is vacuous on the
        # pre-fix tree -- scope to the set branch.
        set_branch = board_body.split("window._activeBoardFilter = {", 1)
        c1_ok = (len(set_branch) == 2
                 and "_updateBoardFilterIndicator()" in set_branch[1])
        check("C1 handleBoard delegates its chip to the board indicator",
              c1_ok,
              "" if c1_ok else "no _updateBoardFilterIndicator call in the "
              "handleBoard set branch")
        c2_ok = "summaryBar.appendChild" not in board_body
        check("C2 no summaryBar append inside handleBoard", c2_ok,
              "" if c2_ok else "summaryBar.appendChild still present in "
              "handleBoard")

    # C3: renderTable applies the board filter in its data path.
    render_body = extract_function_body(app, "function renderTable")
    if render_body is None:
        check("C3 renderTable applies the board filter in its data path",
              False, "definition not found")
    else:
        c3_ok = "_applyBoardFilter(filtered)" in render_body
        check("C3 renderTable applies the board filter in its data path",
              c3_ok,
              "" if c3_ok else "no _applyBoardFilter(filtered) call inside "
              "renderTable")

    # C4/C5: the board indicator's dismiss nulls state and clears
    # af-board, and the chip is a button (keyboard-focusable).
    ind_body = extract_function_body(app, "function updateBoardFilterIndicator")
    if ind_body is None:
        check("C4 board-chip dismiss nulls state and clears af-board",
              False, "definition not found")
        check("C5 board chip is a button", False, "definition not found")
    else:
        dismiss_body = extract_function_body(ind_body, "addEventListener('click'")
        c4_ok = (dismiss_body is not None
                 and "window._activeBoardFilter = null;" in dismiss_body
                 and "_clearAfSelects(['af-board'])" in dismiss_body)
        check("C4 board-chip dismiss nulls state and clears af-board",
              c4_ok,
              "" if c4_ok else "dismiss does not null state and clear "
              "af-board")
        c5_ok = "document.createElement('button')" in ind_body
        check("C5 board chip is a button", c5_ok,
              "" if c5_ok else "indicator does not create a button chip")

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

            def visible_rows():
                return pg.evaluate(
                    "() => [...document.querySelectorAll('#comp-tbody tr')]"
                    ".filter(tr => tr.style.display !== 'none' && "
                    "tr.offsetParent !== null).length")

            def board_chip():
                return pg.evaluate("""() => {
                    const c = document.getElementById('board-filter-chip');
                    if (!c) return null;
                    return {text: c.textContent.trim(),
                            parent: c.parentNode.className || c.parentNode.id,
                            tag: c.tagName};
                }""")

            def af_board_value():
                return pg.evaluate(
                    "() => document.getElementById('af-board').value")

            def sector_chip_active():
                return pg.evaluate("""() => [...document.querySelectorAll(
                    '.chip')].filter(c => c.textContent.trim()
                    === 'Information Technology').some(
                    c => c.classList.contains('active'))""")

            def dismiss_board_chip():
                pg.evaluate("""() => {
                    const c = document.getElementById('board-filter-chip');
                    if (c) c.click();
                }""")
                pg.wait_for_timeout(1000)

            # Open the AF panel once; the gov group holds the board
            # select.
            pg.click("#advanced-filters-toggle")
            pg.wait_for_timeout(400)
            pg.evaluate("""() => {
                const d = document.querySelector(
                    'details.af-cat[data-cat="gov"]');
                if (d) d.open = true;
            }""")

            # R1: AF board high -> 419 companies, button chip in
            # .table-controls, survives a sort-triggered renderTable
            # (pre-fix: 39 visible rows on page 1, no chip, footer 518;
            # after a sort all 50 rows came back while state stayed set).
            pg.select_option("#af-board", "high")
            pg.wait_for_timeout(800)
            n1a = footer_count()
            v1a = visible_rows()
            chip1a = board_chip()
            pg.click('th[data-sort="total_compensation"]')
            pg.wait_for_timeout(800)
            n1b = footer_count()
            v1b = visible_rows()
            chip1b = board_chip()
            r1_ok = (n1a == 419 and n1b == 419 and v1a == 50 and v1b == 50
                     and chip1a is not None and chip1b is not None
                     and "table-controls" in chip1a["parent"]
                     and "table-controls" in chip1b["parent"]
                     and chip1b["tag"] == "BUTTON"
                     and "Board" in chip1b["text"])
            check("R1 board chip survives a sort-triggered renderTable",
                  r1_ok,
                  "footer=%s/%s visible=%s/%s chip=%r/%r (want 419/419, "
                  "50/50, table-controls BUTTON)" % (n1a, n1b, v1a, v1b,
                                                      chip1a, chip1b))

            # R2: add the Information Technology sector (88 alone),
            # then dismiss the board chip: sector-only count returns,
            # sector chip stays active, af-board cleared, state null.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1000)
            n2a = footer_count()
            dismiss_board_chip()
            n2b = footer_count()
            sec2 = sector_chip_active()
            r2_ok = (0 < n2a < 88 and n2b == 88 and sec2
                     and af_board_value() == ""
                     and pg.evaluate("() => window._activeBoardFilter === null"))
            check("R2 board-chip dismiss keeps an independent sector filter",
                  r2_ok,
                  "combined=%s sector-only=%s sector-chip=%s af-board=%r "
                  "state-null=%s" % (n2a, n2b, sec2, af_board_value(),
                                     pg.evaluate("() => window._activeBoardFilter === null")))

            # R3: lone board high, dismissed via its chip, restores 518.
            pg.evaluate("() => window.filterBySector(null)")
            pg.wait_for_timeout(800)
            pg.select_option("#af-board", "high")
            pg.wait_for_timeout(800)
            n3a = footer_count()
            dismiss_board_chip()
            n3b = footer_count()
            chip3 = board_chip()
            r3_ok = (n3a == 419 and n3b == 518 and chip3 is None
                     and af_board_value() == ""
                     and pg.evaluate("() => window._activeBoardFilter === null"))
            check("R3 lone board chip dismiss restores the full table",
                  r3_ok,
                  "filtered=%s restored=%s chip=%r af-board=%r"
                  % (n3a, n3b, chip3, af_board_value()))

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
