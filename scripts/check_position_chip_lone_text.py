#!/usr/bin/env python3
"""Guard: lone position chip uses its own violet text; the scatter action
re-runs the PvP toggle like the other five sector paths.

Background (395th review, 2026-11-09): the 394th review extracted
updatePositionFilterIndicator with the dim's own violet background /
border (rgba(139,92,246,...)) but left the text color '' -- so the
lone chip inherited accent-cyan from .chip.active and read
cyan-on-violet, while every other lone chip uses its dim color (the
position chip was the only updater that left the lone color blank).
This review sets the lone text to #8b5cf6 (the same violet, matching
the background/border); the combined state keeps #a78bfa.

The same review closes the 394th review's candidate (4): the
Correlation Anomalies scatter action's refresh list called all 21
chip updaters but not the PvP toggle, while the other five sector
paths call all twenty-two (21 chips + the toggle). The toggle's
render is sector-independent -- the count comes from the full
companies list and the label carries no sector part -- so the call
is uniformity-only, not a behavior fix. This review adds the call
and corrects the count claims ("all twenty at six sites" in the
393rd guard docstring and the two "All twenty" comments in
js/app.js) to twenty-two.

Update (407th review, 2026-11-10): the community filter gains a chip
as the 22nd chip, so the six sector paths now call all twenty-three
indicator updaters (22 chips + the PvP toggle). The count claims are
corrected to twenty-three here, in the 393rd guard's docstring, and
in the four present-tense "twenty-two updaters" comments in
js/app.js; C5 below pins the corrected phrase.

Checks (static - file reads, <1s):
  C1  HARD FAIL: updatePositionFilterIndicator sets the lone color to
      '#8b5cf6' (the combined branch keeps '#a78bfa').
  C2  HARD FAIL: no indicator updater leaves a blank lone color --
      zero occurrences of the ': '''' color assignment across
      js/app.js and js/network.js (the position chip was the only one).
  C3  HARD FAIL: the Correlation Anomalies scatter action calls
      _updatePvpOnlyToggle after setActiveSector(topSector).
  C4  HARD FAIL: all six sector-change sites call _updatePvpOnlyToggle
      (guarded window._ calls at the All chip, sector chips,
      sector-analytics row click and scatter action; bare calls in
      filterBySector / filterBySectorFromBar, same file as the
      updater). The bare form is matched with a ^\\s*-anchored regex:
      the guarded form's text contains the bare call as a substring,
      so a plain substring check would pass vacuously (394th review).
  C5  HARD FAIL: the count claims are corrected -- the 393rd guard's
      docstring says "twenty-three indicator updaters (22 chips + the
      PvP toggle)" and js/app.js carries no "All twenty indicator
      updaters" (the stale phrase). (407th review: community is the
      22nd chip, so the count moved from twenty-two to twenty-three.)
Render (headless Chromium, real d3 shim -- the scatter action redraws
the scatter chart):
  R1  Position filter via evaluate + updater (deterministic AAPL /
      MSFT tickers), no sector active: the lone chip's computed color
      is rgb(139, 92, 246) and the footer is 2. Pre-fix the chip is
      rgb(0, 180, 216) (accent-cyan from .chip.active).
  R2  The same chip after a real Information Technology sector-chip
      click: combined color rgb(167, 139, 250), footer 2.
  R3  With the PvP toggle on, clicking the Correlation Anomalies card
      (label area, per the 389th review) leaves the toggle's text
      identical and the toggle still active, while the sector changes
      to the card's target (proving the action ran and the toggle
      refresh is a no-op in effect). Aborts with a setup detail if the
      card's target sector is 'S&P 500' (the action sets no sector
      then).
  R4  zero page errors across the render half.

Usage:
  scripts/check_position_chip_lone_text.py
  scripts/check_position_chip_lone_text.py --static-only

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
GUARD_393 = os.path.join(
    REPO, "scripts", "check_combined_chip_sector_prefix.py")
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
        guard393 = open(GUARD_393, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/guard files: %s" % exc)
        return 2

    # C1: the position updater's lone branch is its own violet.
    body = fn_body(app, "function updatePositionFilterIndicator(")
    ok = (body is not None
          and "chip.style.color = isCombined ? '#a78bfa' : '#8b5cf6';" in body)
    check("C1 position updater lone color is #8b5cf6 (combined #a78bfa)",
          ok, "color line missing or still blank" if not ok else "")

    # C2: no updater leaves a blank lone color (the position chip was
    # the only ': '''' assignment; every other updater names a color).
    blank = len(re.findall(
        r"chip\.style\.color\s*=\s*isCombined\s*\?\s*'#a78bfa'\s*:\s*'';",
        app + "\n" + net))
    check("C2 no indicator updater leaves a blank lone color",
          blank == 0,
          "blank lone-color assignments: %d" % blank if blank else "")

    # C3: the scatter action refreshes the PvP toggle after setting
    # the sector (guarded window._ call, same as the other chips).
    w = window_after(app, "setActiveSector(topSector);", "drawScatterChart")
    ok = (w is not None
          and "if (window._updatePvpOnlyToggle) "
              "window._updatePvpOnlyToggle();" in w)
    check("C3 scatter action re-runs _updatePvpOnlyToggle",
          ok, "toggle call missing from the scatter action" if not ok else "")

    # C4: all six sector-change sites call the toggle. Bare form in
    # filterBySector / filterBySectorFromBar (same file as the updater),
    # guarded window._ calls at the other four sites.
    def site_toggle(name, window_text, bare):
        if window_text is None:
            check(name, False, "site window not found")
            return
        if bare:
            ok = re.search(r"(?m)^\s*updatePvpOnlyToggle\(\);",
                           window_text) is not None
        else:
            ok = ("if (window._updatePvpOnlyToggle) "
                  "window._updatePvpOnlyToggle();" in window_text)
        check(name, ok, "toggle call missing" if not ok else "")

    site_toggle("C4a All-chip click re-runs _updatePvpOnlyToggle",
                window_after(app, "allChip.addEventListener('click', function() {",
                             "highlightSectorBar(null)"),
                False)
    site_toggle("C4b sector-chip click re-runs _updatePvpOnlyToggle",
                window_after(app, "setActiveSector(s);", "highlightSectorBar(s)"),
                False)
    site_toggle("C4c filterBySector re-runs updatePvpOnlyToggle (bare)",
                window_after(app, "window.filterBySector = function(sectorName) {",
                             "renderTable(companies);"),
                True)
    site_toggle("C4d filterBySectorFromBar re-runs updatePvpOnlyToggle (bare)",
                window_after(app,
                             "window.filterBySectorFromBar = function(sectorName) {",
                             "renderTable(companies);"),
                True)
    site_toggle("C4e sector-analytics row click re-runs _updatePvpOnlyToggle",
                window_after(
                    app,
                    "// Refresh combined filter chips to include/exclude sector context",
                    "renderTable(companies);"),
                False)
    site_toggle("C4f scatter action re-runs _updatePvpOnlyToggle",
                window_after(app, "setActiveSector(topSector);",
                             "drawScatterChart"),
                False)

    # C5: the count claims are corrected (the 393rd "all twenty at
    # six sites" is now twenty-three everywhere it is asserted --
    # 407th review: community is the 22nd chip).
    ok_doc = ("twenty-three indicator updaters (22 chips + the PvP toggle)"
              in guard393)
    ok_app = "All twenty indicator updaters" not in app
    check("C5 count claims corrected to twenty-three (22 chips + toggle)",
          ok_doc and ok_app,
          ("393rd guard docstring still says twenty-two; " if not ok_doc else "")
          + ("stale 'All twenty' comment in app.js" if not ok_app else ""))

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

            def chip_state(chip_id):
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

            def set_position_filter():
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

            # R1: lone position chip is its own violet, footer 2.
            # Pre-fix the color is rgb(0, 180, 216) (accent-cyan from
            # .chip.active).
            set_position_filter()
            pre = chip_state("position-filter-chip")
            n1 = footer_count()
            r1_ok = (pre is not None
                     and pre["color"] == "rgb(139, 92, 246)"
                     and pre["text"].startswith("Cluster 1 CEO Pay above #1 (2)")
                     and "Information Technology" not in pre["text"]
                     and n1 == 2)
            check("R1 lone position chip is violet #8b5cf6 (chip=%r footer=%s)"
                  % (pre, n1),
                  r1_ok, "want rgb(139, 92, 246), footer 2")

            # R2: the same chip combined with a real IT sector click.
            click_sector_chip("Information Technology")
            c2 = chip_state("position-filter-chip")
            n2 = footer_count()
            r2_ok = (c2 is not None
                     and c2["color"] == "rgb(167, 139, 250)"
                     and c2["text"].startswith(
                         "Information Technology \u00d7 Cluster 1 CEO "
                         "Pay above #1 (2)")
                     and n2 == 2)
            check("R2 combined position chip is purple #a78bfa (chip=%r footer=%s)"
                  % (c2, n2),
                  r2_ok, "want 'Information Technology x Cluster 1 CEO "
                         "Pay above #1 (2)' in purple, footer 2")
            if r2_ok:
                pg.locator("#position-filter-chip").click()
                pg.wait_for_timeout(800)
            pg.locator("#sector-chips .chip", has_text="All").first.click()
            pg.wait_for_timeout(800)

            # R3: the PvP toggle survives the Correlation Anomalies
            # scatter action unchanged (its render is sector-
            # independent), while the sector changes to the card's
            # target -- proving the action ran and the toggle refresh
            # is a no-op in effect.
            pg.click("#pvp-only-toggle")
            pg.wait_for_timeout(800)
            tog_before = pg.evaluate("""() => {
                const b = document.getElementById('pvp-only-toggle');
                return b ? { text: b.textContent.trim(),
                             active: b.classList.contains('active') } : null;
            }""")
            target = pg.evaluate("""() => {
                const el = [...document.querySelectorAll('.insight-card')]
                    .find(c => (c.querySelector('.insight-label') || {})
                        .textContent.trim() === 'Correlation Anomalies');
                if (!el) return null;
                const m = (el.getAttribute('aria-label') || '')
                    .match(/View (.+) in scatter plot/);
                return m ? m[1] : null;
            }""")
            if tog_before is None or not tog_before["active"]:
                check("R3 PvP toggle survives scatter action unchanged",
                      False, "toggle did not activate (toggle=%r)" % (tog_before,))
                r3_ok = False
            elif target is None or target == "S&P 500":
                check("R3 PvP toggle survives scatter action unchanged",
                      False, "setup: card target sector is %r (no sector set)"
                      % (target,))
                r3_ok = False
            else:
                pg.evaluate("""() => {
                    const el = [...document.querySelectorAll('.insight-card')]
                        .find(c => (c.querySelector('.insight-label') || {})
                            .textContent.trim() === 'Correlation Anomalies');
                    const label = el.querySelector('.insight-label');
                    (label || el).click();
                }""")
                pg.wait_for_timeout(1500)
                tog_after = pg.evaluate("""() => {
                    const b = document.getElementById('pvp-only-toggle');
                    return b ? { text: b.textContent.trim(),
                                 active: b.classList.contains('active') } : null;
                }""")
                sector = pg.evaluate("""() => {
                    const c = [...document.querySelectorAll('#sector-chips .chip')]
                        .find(el => el.classList.contains('active'));
                    return c ? c.textContent.trim() : null;
                }""")
                r3_ok = (tog_after is not None
                         and tog_after["text"] == tog_before["text"]
                         and tog_after["active"]
                         and sector == target)
                check("R3 PvP toggle survives scatter action unchanged "
                      "(before=%r after=%r sector=%r target=%r)"
                      % (tog_before, tog_after, sector, target),
                      r3_ok,
                      "want identical toggle text, still active, sector "
                      "changed to the card target")

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
