#!/usr/bin/env python3
"""Guard: quartile and position chips show the sector prefix when combined.

Background (394th review, 2026-11-09): the 393rd review closed the
stale-label class for the nineteen app.js indicator updaters but left
the quartile and position chips out of scope -- both were inline-built
(the quartile chip in the network.js box-plot zone click handler, the
position chip in setupDetailPanel's handlePosFilter) with no updater
to re-run, so a later sector change left their labels lone while the
table was filtered to a sector + that dim. This review extracts
updateQuartileFilterIndicator (network.js) and
updatePositionFilterIndicator (app.js, top-level, next to
updatePeerDistFilterIndicator) and calls both from all six sector
paths, plus at set time, so the chips are born combined when a sector
is already active. The lone styling is preserved exactly (quartile:
the combined purple already; position: its own violet
rgba(139,92,246,...) with the accent-cyan inherited text color -- a
pre-existing quirk, noted as a next-run candidate, not changed here);
the combined state uses the established purple treatment
(rgba(167,139,250,...) + #a78bfa) with a 'Click to clear combined
sector + ... filter' title. The position chip's dismiss glyph moves
from a leading 'x ' (textContent) to the trailing x span every other
chip uses; no guard pinned the old prefix. The badge and announcement
already name both dims with the sector as a separate part, so they
need no change; the table already ANDs both filters with the sector.

Checks (static - file reads, <1s):
  C1  HARD FAIL: updateQuartileFilterIndicator (network.js) reads
      activeSector into isCombined and builds a combined label from
      it (window._activeSector -- network.js is a separate script).
  C2  HARD FAIL: updatePositionFilterIndicator (app.js) reads
      activeSector into isCombined and builds a combined label.
  C3  HARD FAIL: the box-plot zone click handler calls
      updateQuartileFilterIndicator at set time (the // Build label
      branch -- the clear branch must not satisfy this).
  C4  HARD FAIL: handlePosFilter calls updatePositionFilterIndicator
      in both branches (empty + non-empty), exactly twice.
  C5a HARD FAIL: the All-chip click handler re-runs both updaters
      (guarded window._ calls).
  C5b HARD FAIL: the sector-chip click handler re-runs both.
  C5c HARD FAIL: filterBySector re-runs both (position bare, same
      file; quartile guarded -- it lives in network.js, and a bare
      call would throw if that script failed to load).
  C5d HARD FAIL: filterBySectorFromBar re-runs both (same split).
  C5e HARD FAIL: the sector-analytics row click re-runs both.
  C5f HARD FAIL: the Correlation Anomalies scatter action re-runs
      both after setActiveSector(topSector).
  C6  HARD FAIL: the stock-% hash restore defaults a missing sptag
      to 'Equity' (394th follow-up: a tag-less link restored tag:''
      and the lone chip read ' (0-50%)' -- the lone label is
      tag + ' (' + label + ')'; the combined label and badge already
      use 'Equity: ', so the fallback matches them).
Render (headless Chromium, real d3 shim -- the community panel needs
the network graph; keyboard activation per the residual-keyboard
guard, since a mouse click on a narrow zone is swallowed by the
sticky header):
  R1  Real zone activation (keyboard Enter) + real Information
      Technology sector-chip click: quartile chip gains the
      'Information Technology x ...' prefix in purple; footer equals
      the live-computed IT intersection of the quartile's tickers.
      Pre-fix: the chip kept its lone label.
  R2  Position filter via evaluate + updater (deterministic AAPL /
      MSFT tickers) + real IT sector-chip click: position chip gains
      the prefix in purple; footer 2. Pre-fix: the updater does not
      exist, so the setup itself fails loudly.
  R3  With IT still active, a second real zone activation: the
      quartile chip is born combined ('Information Technology x ...').
      Pre-fix: born lone.
  R4  zero page errors across the render half.

Usage:
  scripts/check_quartile_position_sector_prefix.py
  scripts/check_quartile_position_sector_prefix.py --static-only

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
NET_JS = os.path.join(REPO, "js", "network.js")
D3_CACHE = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/"
    "hidden_files/methbtn-20261005/d3.min.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def fn_body(src, marker):
    """Brace-matched body starting at the first '{' after marker."""
    i = src.find(marker)
    if i < 0:
        return None
    j = src.find("{", i)
    if j < 0:
        return None
    depth = 0
    k = j
    while k < len(src):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[j:k + 1]
        k += 1
    return None


def window_after(src, start_marker, end_marker):
    """Text between the first start_marker and the next end_marker."""
    i = src.find(start_marker)
    if i < 0:
        return None
    j = src.find(end_marker, i + len(start_marker))
    if j < 0:
        return None
    return src[i:j]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
        net = open(NET_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js files: %s" % exc)
        return 2

    # C1: quartile updater (network.js) reads activeSector into
    # isCombined and builds a combined label from it.
    body = fn_body(net, "function updateQuartileFilterIndicator(")
    ok = (body is not None
          and re.search(r"var isCombined\s*=.*activeSector", body)
          and "activeSector + '" in body)
    check("C1 quartile updater builds a combined sector label",
          ok, "updater missing or without isCombined label" if not ok else "")

    # C2: position updater (app.js) reads activeSector into
    # isCombined and builds a combined label from it.
    body = fn_body(app, "function updatePositionFilterIndicator(")
    ok = (body is not None
          and re.search(r"var isCombined\s*=.*activeSector", body)
          and "activeSector + '" in body)
    check("C2 position updater builds a combined sector label",
          ok, "updater missing or without isCombined label" if not ok else "")

    # C3: the zone click handler's set branch calls the updater.
    # The window starts at the set branch's own comment so the
    # clear (toggle-off) branch above it cannot satisfy the check.
    w = window_after(net, "// Build label",
                     "announce('Filtered to '")
    ok = w is not None and "updateQuartileFilterIndicator();" in w
    check("C3 zone click set path calls updateQuartileFilterIndicator",
          ok, "updater call missing from the set branch" if not ok else "")

    # C4: handlePosFilter calls the updater in both branches.
    body = fn_body(app, "function handlePosFilter(e)")
    n = body.count("updatePositionFilterIndicator();") if body else 0
    check("C4 handlePosFilter calls updatePositionFilterIndicator twice",
          n == 2, "calls found: %d" % n)

    def site_has(window_text, guarded_quartile, bare_position):
        """(quartile-ok, position-ok) for one sector-change site."""
        if window_text is None:
            return (False, False)
        q_ok = ("if (window._updateQuartileFilterIndicator) "
                "window._updateQuartileFilterIndicator();" in window_text)
        if bare_position:
            p_ok = re.search(
                r"(?m)^\s*updatePositionFilterIndicator\(\);",
                window_text) is not None
        else:
            p_ok = ("if (window._updatePositionFilterIndicator) "
                    "window._updatePositionFilterIndicator();" in window_text)
        return (q_ok, p_ok)

    def site_check(name, window_text, guarded_quartile, bare_position):
        q_ok, p_ok = site_has(window_text, guarded_quartile, bare_position)
        check(name, q_ok and p_ok,
              ("quartile missing; " if not q_ok else "")
              + ("position missing" if not p_ok else ""))

    # C5a: All-chip click handler (window-guarded calls).
    site_check("C5a All-chip click re-runs quartile + position",
               window_after(app, "allChip.addEventListener('click', function() {",
                            "highlightSectorBar(null)"),
               True, False)
    # C5b: sector-chip click handler.
    site_check("C5b sector-chip click re-runs quartile + position",
               window_after(app, "setActiveSector(s);", "highlightSectorBar(s)"),
               True, False)
    # C5c: filterBySector (position bare, quartile guarded).
    site_check("C5c filterBySector re-runs quartile + position",
               window_after(app, "window.filterBySector = function(sectorName) {",
                            "renderTable(companies);"),
               True, True)
    # C5d: filterBySectorFromBar (position bare, quartile guarded).
    site_check("C5d filterBySectorFromBar re-runs quartile + position",
               window_after(app,
                            "window.filterBySectorFromBar = function(sectorName) {",
                            "renderTable(companies);"),
               True, True)
    # C5e: sector-analytics row click.
    site_check("C5e sector-analytics row click re-runs quartile + position",
               window_after(
                   app,
                   "// Refresh combined filter chips to include/exclude sector context",
                   "renderTable(companies);"),
               True, False)
    # C5f: Correlation Anomalies scatter action.
    site_check("C5f scatter action re-runs quartile + position",
               window_after(app, "setActiveSector(topSector);",
                            "drawScatterChart"),
               True, False)

    # C6: tag-less stock-% restore falls back to 'Equity' (the lone
    # chip label is tag + ' (' + label + ')', so a missing sptag left
    # a blank prefix -- ' (0-50%)'). The restore block is the single
    # site (applyHashState serves both the init and hashchange paths).
    w = window_after(
        app,
        "if (state.spmin != null && state.spmax != null && state.splbl) {",
        "// Say-on-pay filter")
    ok = (w is not None
          and "tag: state.sptag ? state.sptag : 'Equity'" in w)
    check("C6 tag-less stock-% restore defaults tag to 'Equity'",
          ok, "fallback missing from the spmin restore" if not ok else "")

    return 0


def get_d3_bytes():
    if os.path.exists(D3_CACHE):
        return open(D3_CACHE, "rb").read()
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
            pg = browser.new_page(viewport={"width": 1440, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript",
                              body=d3)

            pg.route("**/npm/d3@7*", d3_route)
            pg.route("**/unpkg.com/d3@7*", d3_route)
            pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, wait_until="load")
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
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

            def it_count():
                return pg.evaluate("""() => {
                    const byTicker = {};
                    window._chartData.companies.forEach(c => {
                        byTicker[c.ticker] = c;
                    });
                    return window._chartData.companies.filter(
                        c => c.sector === 'Information Technology').length;
                }""")

            def it_count_of_active_quartile():
                return pg.evaluate("""() => {
                    const f = window._activeQuartileFilter;
                    if (!f) return -1;
                    const byTicker = {};
                    window._chartData.companies.forEach(c => {
                        byTicker[c.ticker] = c;
                    });
                    return f.tickers.filter(t =>
                        byTicker[t] && byTicker[t].sector ===
                        'Information Technology').length;
                }""")

            def click_sector_chip(name):
                pg.locator("#sector-chips .chip",
                           has_text=name).first.click()
                pg.wait_for_timeout(1000)

            def activate_zone(idx):
                ok = pg.evaluate("""(i) => {
                    const z = document.querySelectorAll(
                        '.cm-bp-zone[data-bp-cid]')[i];
                    if (!z) return false;
                    z.scrollIntoView({block: 'center'});
                    z.focus();
                    return document.activeElement === z;
                }""", idx)
                if not ok:
                    return False
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1000)
                return True

            # Navigate to the network section and enable community mode.
            pg.click('a[data-section="peer-network-section"]')
            pg.wait_for_selector("#network-graph canvas", timeout=90000)
            pg.click("#network-overflow-toggle")
            pg.click("#community-toggle")
            pg.wait_for_function(
                "document.querySelectorAll('.cm-bp-zone[data-bp-cid]').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: real zone activation, then a real IT sector-chip
            # click. Try zones until one holds IT members (a zero-IT
            # quartile would leave a zero-row table, which cannot
            # prove the combined label). Pre-fix the chip stays lone.
            r1_ok = False
            r1_detail = "no zone with IT members found"
            base_label = None
            for idx in range(5):
                if not activate_zone(idx):
                    r1_detail = "zone %d did not take focus" % idx
                    break
                c = chip_text("quartile-filter-chip")
                if c is None:
                    r1_detail = "zone %d set no chip" % idx
                    break
                if it_count_of_active_quartile() <= 0:
                    pg.locator("#quartile-filter-chip").click()
                    pg.wait_for_timeout(800)
                    continue
                base_label = c["text"]
                click_sector_chip("Information Technology")
                c2 = chip_text("quartile-filter-chip")
                n2 = footer_count()
                want = it_count_of_active_quartile()
                r1_ok = (c2 is not None
                         and c2["text"].startswith(
                             "Information Technology \u00d7 " + base_label)
                         and c2["color"] == "rgb(167, 139, 250)"
                         and n2 == want and want > 0)
                r1_detail = ("chip=%r footer=%s want=%s pre=%r"
                             % (c2, n2, want, c))
                break
            check("R1 quartile+sector chip: quartile chip gains sector "
                  "prefix (chip/footer %s)" % r1_detail,
                  r1_ok,
                  "want 'Information Technology x <lone label>' in purple")

            # R1b: dismissing the quartile chip leaves the IT filter.
            if r1_ok:
                pg.locator("#quartile-filter-chip").click()
                pg.wait_for_timeout(800)
                c1b = chip_text("quartile-filter-chip")
                n1b = footer_count()
                r1b_ok = c1b is None and n1b == it_count()
                check("R1b quartile chip dismiss: chip gone, IT table "
                      "remains (footer=%s)" % n1b,
                      r1b_ok, "chip=%r footer=%s want=%s"
                      % (c1b, n1b, it_count()))
            else:
                check("R1b quartile chip dismiss: chip gone, IT table remains",
                      False, "skipped: R1 failed")

            # R2: position filter via evaluate + updater (deterministic
            # tickers), then a real IT sector-chip click. Pre-fix the
            # updater does not exist, so the setup fails loudly here.
            pg.locator("#sector-chips .chip", has_text="All").first.click()
            pg.wait_for_timeout(800)
            has_updater = pg.evaluate(
                "typeof window._updatePositionFilterIndicator === 'function'")
            if not has_updater:
                check("R2 position+sector chip: position chip gains "
                      "sector prefix", False,
                      "window._updatePositionFilterIndicator is not a function")
                r2_ok = False
            else:
                pg.evaluate("""() => {
                    window._activePositionFilter = {
                        tickers: ['AAPL', 'MSFT'],
                        label: 'Cluster 1 CEO Pay above #1 (2)',
                        communityId: 1, metric: 'pay', rank: 1,
                        direction: 'above'
                    };
                    window._updatePositionFilterIndicator();
                    renderTable(window._chartData.companies);
                }""")
                pg.wait_for_timeout(800)
                pre2 = chip_text("position-filter-chip")
                n2a = footer_count()
                click_sector_chip("Information Technology")
                c2 = chip_text("position-filter-chip")
                n2 = footer_count()
                r2_ok = (pre2 is not None
                         and pre2["text"].startswith(
                             "Cluster 1 CEO Pay above #1 (2)")
                         and "Information Technology" not in pre2["text"]
                         and c2 is not None
                         and c2["text"].startswith(
                             "Information Technology \u00d7 Cluster 1 CEO "
                             "Pay above #1 (2)")
                         and c2["color"] == "rgb(167, 139, 250)"
                         and n2a == 2 and n2 == 2)
                check("R2 position+sector chip: position chip gains "
                      "sector prefix (chip=%r footer=%s/%s)" % (c2, n2a, n2),
                      r2_ok,
                      "want 'Information Technology x Cluster 1 CEO Pay "
                      "above #1 (2)' in purple, footer 2 (pre=%r)" % (pre2,))
                if r2_ok:
                    pg.locator("#position-filter-chip").click()
                    pg.wait_for_timeout(800)

            # R3: with IT still active, a real zone activation is born
            # combined. Pre-fix the chip is born lone.
            r3_ok = False
            if activate_zone(1):
                c3 = chip_text("quartile-filter-chip")
                r3_ok = (c3 is not None
                         and c3["text"].startswith(
                             "Information Technology \u00d7")
                         and c3["color"] == "rgb(167, 139, 250)")
                check("R3 quartile set while sector active: chip born "
                      "combined (chip=%r)" % (c3,),
                      r3_ok,
                      "want 'Information Technology x ...' in purple")
                if r3_ok:
                    pg.locator("#quartile-filter-chip").click()
                    pg.wait_for_timeout(800)
            else:
                check("R3 quartile set while sector active: chip born combined",
                      False, "zone 1 did not take focus")

            r4_ok = len(errors) == 0
            check("R4 zero page errors across the render half",
                  r4_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return all([r1_ok, r2_ok, r3_ok, r4_ok])
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
