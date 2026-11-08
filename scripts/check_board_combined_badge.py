#!/usr/bin/env python3
"""Guard: the board-independence filter is named in the combined-filter
badge and the table announcement, and all three board labels come from
one shared helper.

Background (385th review, 2026-11-08): queued candidate from the 384th
review -- board was the only filter dim missing from BOTH the
combined-filter badge (renderSummaryBar filterParts, js/app.js) and the
screen-reader announcement (announceMsg in renderTable). Board plus any
second filter showed a badge/announcement that never named the board
part, the exact 382nd-review class (SoP was added to both there). The
board chip already carried the label ('Board >=80%' / 'Board 60-80%' /
'Board <60%'), built from a local labelMap inside
updateBoardFilterIndicator.

The fix: one filterParts line for board (boardFilterLabel(mode),
matching the chip label), one announceMsg line ('board independence: '
+ boardFilterLabel(mode)), and the chip's local labelMap replaced by
the new file-scope boardFilterLabel helper so all three sites name the
dim identically from a single source of truth.

Checks:
  C1 HARD FAIL: renderSummaryBar does not name the board filter in the
     combined-filter badge (filterDims++ + filterParts.push(
     boardFilterLabel(...))).
  C2 HARD FAIL: renderTable's announceMsg does not name the board filter.
  C3 HARD FAIL: the boardFilterLabel helper is missing or does not map
     all three modes (high/mid/low).
  C4 HARD FAIL: updateBoardFilterIndicator still carries its own local
     labelMap instead of using the shared helper.
Render (headless Chromium, d3 requests aborted -- the summary bar, AF
panel and hash paths are pure app.js):
  R1 board high + Information Technology sector filters to 70 companies
     and the combined badge names both dims ('Board >=80%' and
     'Information Technology'), and the announcement names the board
     dim ('board independence: Board >=80%').
  R2 a lone board filter renders no combined badge (single dim) but the
     board chip is present and the announcement still names board.
  R3 zero page errors across the render half.

Usage:
  scripts/check_board_combined_badge.py
  scripts/check_board_combined_badge.py --static-only

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

    # C1: renderSummaryBar names board in the combined-filter badge.
    bar_body = extract_function_body(app, "function renderSummaryBar")
    if bar_body is None:
        check("C1 renderSummaryBar exists in app.js", False,
              "definition not found")
    else:
        c1_ok = ("filterParts.push(boardFilterLabel("
                 "window._activeBoardFilter.mode))" in bar_body
                 and "if (window._activeBoardFilter) { filterDims++;"
                 in bar_body)
        check("C1 combined-filter badge names the board filter", c1_ok,
              "" if c1_ok else "no boardFilterLabel filterParts push in "
              "renderSummaryBar")

    # C2: renderTable's screen-reader announcement names board.
    c2_ok = ("announceMsg += ', board independence: ' + "
             "boardFilterLabel(window._activeBoardFilter.mode);" in app)
    check("C2 table announcement names the board filter", c2_ok,
          "" if c2_ok else "no 'board independence: ' announceMsg line")

    # C3: the shared boardFilterLabel helper maps all three modes.
    helper_body = extract_function_body(app, "function boardFilterLabel")
    if helper_body is None:
        check("C3 boardFilterLabel helper maps all three modes", False,
              "definition not found")
    else:
        c3_ok = ("high: 'Board" in helper_body
                 and "mid: 'Board" in helper_body
                 and "low: 'Board" in helper_body)
        check("C3 boardFilterLabel helper maps all three modes", c3_ok,
              "" if c3_ok else "helper does not map high/mid/low")

    # C4: the board indicator uses the shared helper; no local labelMap
    # duplicate remains anywhere in app.js.
    ind_body = extract_function_body(app, "function updateBoardFilterIndicator")
    if ind_body is None:
        check("C4 board chip uses the shared boardFilterLabel helper",
              False, "definition not found")
    else:
        c4_ok = ("boardFilterLabel(bf.mode)" in ind_body
                 and "var labelMap" not in app)
        check("C4 board chip uses the shared boardFilterLabel helper",
              c4_ok,
              "" if c4_ok else "indicator does not use boardFilterLabel "
              "or a local labelMap remains")

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

            def last_announce():
                return pg.evaluate(
                    "() => (typeof window._lastTableAnnounce === 'string' "
                    "&& window._lastTableAnnounce) || "
                    "document.getElementById('sr-announce').textContent")

            def board_chip_present():
                return pg.evaluate(
                    "() => !!document.getElementById('board-filter-chip')")

            # Open the AF panel once; the gov group holds the board
            # select.
            pg.click("#advanced-filters-toggle")
            pg.wait_for_timeout(400)
            pg.evaluate("""() => {
                const d = document.querySelector(
                    'details.af-cat[data-cat="gov"]');
                if (d) d.open = true;
            }""")

            # R1: board high + Information Technology sector -> 70
            # companies; the combined badge names both dims and the
            # announcement names the board dim (pre-fix: badge showed
            # the sector only, announcement never mentioned board).
            pg.select_option("#af-board", "high")
            pg.wait_for_timeout(800)
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1000)
            n1 = footer_count()
            b1 = badge_text()
            a1 = last_announce()
            r1_ok = (n1 == 70 and b1 is not None
                     and "Board" in b1 and "80%" in b1
                     and "Information Technology" in b1
                     and a1 is not None
                     and "board independence: Board" in a1
                     and "80%" in a1)
            check("R1 board+sector badge and announcement name the board dim",
                  r1_ok,
                  "footer=%s badge=%r announce=%r (want 70, Board 80 pct "
                  "+ IT)" % (n1, b1, a1))

            # R2: lone board filter (sector cleared) -> no combined
            # badge (single dim) but the board chip is present and the
            # announcement still names board.
            pg.evaluate("() => window.filterBySector(null)")
            pg.wait_for_timeout(1000)
            n2 = footer_count()
            b2 = badge_text()
            a2 = last_announce()
            chip2 = board_chip_present()
            r2_ok = (n2 == 419 and b2 is None and chip2
                     and a2 is not None
                     and "board independence: Board" in a2)
            check("R2 lone board filter has no badge but announces board",
                  r2_ok,
                  "footer=%s badge=%r announce=%r chip=%s (want 419, no "
                  "badge)" % (n2, b2, a2, chip2))

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
