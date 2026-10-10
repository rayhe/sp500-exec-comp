#!/usr/bin/env python3
"""Regression guard: click-only surfaces outside insight cards are
keyboard-operable (roving-tabindex groups).

The 2026-10-09 19:30 PT run closed the queued candidate from the 18:00 PT
run: the click-only control classes that live OUTSIDE insight cards were
entirely mouse-only while every earlier keyboard pilot had targeted card
chart surfaces, card interiors, or inline onclick prose controls. The
remaining surfaces:

  .hm-sector-label / .hm-cell (sector comp heatmap, addEventListener wiring)
  .rs-sector-label / .rs-cell (role ranking table, inline onclick wiring)
  .eq-tbl-badge-clickable / .new-ceo-badge-clickable / .conc-badge-clickable
  / .asp-tbl-badge-clickable / .gov-badge-clickable (main-table per-row
  filter badges, inline onclick wiring)
  .detail-trajectory-clickable (detail panel pay-anomaly sparkline,
  addEventListener wiring)
  .tc-missing-link (detail panel team-completeness missing-roles link,
  inline onclick wiring)

js/app.js gains a FILE-SCOPE helper _kbdUpgradeRoving(container, selector)
(file scope, because the heatmap/role-table/main-table/detail call sites all
sit outside the block that holds _upgradeInlineOnclickControls). It upgrades
every matching element that is not already keyboard-operable:

  - skipped: native controls (a/button/input/select/textarea), elements
    carrying their own tabindex or onkeydown, elements already role=button,
    and already-upgraded nodes (data-kbd-upgraded)
  - upgraded: roving tabindex (first element "0", rest "-1"),
    role="button", data-bearing aria-label (the element's own title with
    "click to" -> "Press Enter to"; visible text when there is no title),
    data-kbd-upgraded="1", Enter/Space keydown that preventDefault()s,
    stopPropagation()s (keyboard-pilot contract; the tbody keydown handler
    would otherwise ALSO toggle the detail panel on Enter), and fires
    el.click() so the keyboard path reproduces the exact mouse behavior
    (inline onclick and/or listeners). Arrow keys move the roving holder
    linearly (treemap-roving convention), preventDefault()ed and
    stopPropagation()ed so the global ArrowLeft/Right table-page shortcut
    cannot double-fire.

Call sites (each right after the surface's HTML/click wiring is in place):
  renderSectorCompHeatmap -> '.hm-sector-label, .hm-cell:not(.hm-zero)'
  renderRoleCompAnalysis   -> '.rs-sector-label, .rs-cell:not(.rs-cell-empty)'
  renderTable              -> the five badge classes (one group per render)
  detail panel render      -> '.detail-trajectory-clickable, .tc-missing-link'
Zero/empty cells carry no click action and are excluded (click/no-op parity,
same as the anomaly-row precedent). The main-table group is roving (not
tabindex=0 on every badge) so a page of ~25 rows keeps a single badge tab
stop instead of hundreds.

CSS adds a general [data-kbd-upgraded]:focus-visible --accent ring; the
scoped .insight-card rule from the 18:00 PT run is kept intact.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _kbdUpgradeRoving is file-scope and implements the skip set, roving
        tabindex, role=button, aria-label derivation, data-kbd-upgraded,
        Enter/Space -> preventDefault/stopPropagation/click(), arrow-key
        linear move -> preventDefault/stopPropagation/focus.
     S2 the four call sites exist with the exact selectors above.
     S3 css/style.css has the general [data-kbd-upgraded]:focus-visible
        rule with the --accent outline convention.
     S4 the scoped .insight-card [data-kbd-upgraded]:focus-visible rule is
        still present (protects the 18:00 PT guard's S4).
     S5 no innerHTML in the new helper (attribute-bound additions only).
     S6 node --check js/app.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 heatmap group: exactly one tabindex="0" holder; all are
        role=button with data-bearing aria-labels; Enter on the holder
        fires window.filterBySector with the holder's sector; ArrowRight
        moves the holder.
     R2 main-table badge group: exactly one tabindex="0" holder across all
        five badge classes; Enter on the holder fires exactly one of the
        five window.filterBy* functions (keyboard/click parity).
     R3 detail panel: open AMGN via window.openCompanyDetailWithDiff (AMGN
        carries both _ceoTrend >= 2 and _teamMissingExpected); trajectory
        wrap + missing-roles link are one roving group (one holder, both
        role=button with data-bearing aria-labels); Enter on the trajectory
        wrap fires window.navigateToPayAnomaly(sector, 'AMGN'); ArrowRight
        moves the holder to the missing-roles link.
     R4 zero JS page errors.

Usage:
  scripts/check_roving_keyboard.py              # static + render
  scripts/check_roving_keyboard.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

BADGE_CLASSES = [
    ".eq-tbl-badge-clickable",
    ".new-ceo-badge-clickable",
    ".conc-badge-clickable",
    ".asp-tbl-badge-clickable",
    ".gov-badge-clickable",
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def helper_block(app):
    m = re.search(
        r"^function _kbdUpgradeRoving\(container, selector\) \{([\s\S]*?)\n\}$",
        app, re.M)
    return m.group(0) if m else None


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    hb = helper_block(app)

    s1 = (hb is not None
          and "hasAttribute('tabindex')" in hb
          and "hasAttribute('onkeydown')" in hb
          and "hasAttribute('data-kbd-upgraded')" in hb
          and "getAttribute('role') === 'button'" in hb
          and "tag === 'A'" in hb and "tag === 'BUTTON'" in hb
          and "setAttribute('tabindex', idx === 0 ? '0' : '-1')" in hb
          and "setAttribute('role', 'button')" in hb
          and "setAttribute('aria-label', label)" in hb
          and "setAttribute('data-kbd-upgraded', '1')" in hb
          and "addEventListener('keydown'" in hb
          and "e.key === 'Enter'" in hb
          and "e.key === ' '" in hb
          and "e.preventDefault()" in hb
          and "e.stopPropagation()" in hb
          and "e.currentTarget.click()" in hb
          and "e.key === 'ArrowRight'" in hb
          and "els[next].setAttribute('tabindex', '0')" in hb
          and "els[next].focus()" in hb)
    check("S1 _kbdUpgradeRoving: skip set, roving tabindex, role=button, aria-label, Enter/Space -> preventDefault/stopPropagation/click(), arrows -> linear move + focus",
          s1, "" if s1 else "helper wiring missing or diverged")

    s2 = ("_kbdUpgradeRoving(container, '.hm-sector-label, .hm-cell:not(.hm-zero)')" in app
          and "_kbdUpgradeRoving(container, '.rs-sector-label, .rs-cell:not(.rs-cell-empty)')" in app
          and "_kbdUpgradeRoving(tbody, '.eq-tbl-badge-clickable, .new-ceo-badge-clickable, .conc-badge-clickable, .asp-tbl-badge-clickable, .gov-badge-clickable')" in app
          and "_kbdUpgradeRoving(detailRow, '.detail-trajectory-clickable, .tc-missing-link')" in app)
    check("S2 four call sites present (heatmap, role table, main-table badges, detail panel)",
          s2, "" if s2 else "a call site is missing or the selector diverged")

    m = re.search(
        r"(?<!\.insight-card )\[data-kbd-upgraded\]:focus-visible\s*\{([\s\S]*?)\}",
        css)
    s3 = (m is not None and "outline: 2px solid var(--accent)" in m.group(1))
    check("S3 general [data-kbd-upgraded]:focus-visible --accent ring",
          s3, "" if s3 else "general focus rule missing or off-convention")

    m2 = re.search(
        r"\.insight-card \[data-kbd-upgraded\]:focus-visible\s*\{([\s\S]*?)\}",
        css)
    s4 = (m2 is not None and "outline: 2px solid var(--accent)" in m2.group(1))
    check("S4 scoped .insight-card rule kept intact (18:00 PT guard compatibility)",
          s4, "" if s4 else "scoped rule removed or changed")

    s5 = (hb is not None and "innerHTML" not in hb)
    check("S5 keyboard additions are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML found in the helper")

    r = subprocess.run(["node", "--check", APP_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/app.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")


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

    badge_sel = ", ".join(BADGE_CLASSES)
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
                "window.d3 && document.querySelectorAll('.insight-card').length > 10",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('.hm-cell').length > 20",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: heatmap roving group.
            r1info = pg.evaluate("""() => {
              const els = [...document.querySelectorAll(
                '.hm-sector-label, .hm-cell:not(.hm-zero)')];
              const holders = els.filter(el => el.getAttribute('tabindex') === '0');
              const neg = els.filter(el => el.getAttribute('tabindex') === '-1');
              const bad = els.filter(el =>
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').length ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              const zeroUp = [...document.querySelectorAll('.hm-cell.hm-zero')]
                .filter(el => el.hasAttribute('data-kbd-upgraded')).length;
              return {n: els.length, holders: holders.length, neg: neg.length,
                      bad: bad.length, zeroUp: zeroUp,
                      label: holders[0] ? holders[0].getAttribute('aria-label') : null,
                      sector: holders[0] ? (holders[0].dataset.sector || null) : null};
            }""")
            r1shape = (r1info["n"] > 30 and r1info["holders"] == 1
                       and r1info["neg"] == r1info["n"] - 1
                       and r1info["bad"] == 0 and r1info["zeroUp"] == 0)
            r1 = False
            r1detail = "shape: %r" % (r1info,)
            if r1shape:
                pg.evaluate("""() => {
                  window.__sectorCalls = [];
                  window.__origFilterBySector = window.filterBySector;
                  window.filterBySector = function(s) {
                    window.__sectorCalls.push(s);
                  };
                  const h = document.querySelector(
                    '.hm-sector-label[tabindex="0"], .hm-cell:not(.hm-zero)[tabindex="0"]');
                  h.focus();
                }""")
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(600)
                calls = pg.evaluate("window.__sectorCalls")
                # ArrowRight moves the roving holder to the next element.
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(300)
                moved = pg.evaluate("""() => {
                  const els = [...document.querySelectorAll(
                    '.hm-sector-label, .hm-cell:not(.hm-zero)')];
                  return els.filter(el => el.getAttribute('tabindex') === '0').length === 1
                    && document.activeElement !== document.body
                    && /hm-/.test(document.activeElement.className || '');
                }""")
                r1 = (len(calls) == 1 and calls[0] == r1info["sector"] and moved)
                r1detail = ("calls=%r expected=%r moved=%r"
                            % (calls, r1info["sector"], moved))
                pg.evaluate("window.filterBySector = window.__origFilterBySector")
            check("R1 heatmap is a roving group; Enter fires filterBySector(sector); ArrowRight moves holder",
                  r1, "" if r1 else r1detail)

            # R2: main-table badge roving group.
            r2info = pg.evaluate("""() => {
              const els = [...document.querySelectorAll('#comp-tbody %s')];
              const holders = els.filter(el => el.getAttribute('tabindex') === '0');
              const bad = els.filter(el =>
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').length ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              return {n: els.length, holders: holders.length, bad: bad.length};
            }""" % badge_sel)
            r2 = False
            r2detail = "badge state: %r" % (r2info,)
            if r2info["n"] > 0 and r2info["holders"] == 1 and r2info["bad"] == 0:
                pg.evaluate("""() => {
                  window.__badgeCalls = [];
                  window.__origBadgeFns = {};
                  ['filterByStockPctTier', 'filterByCeoTransition',
                   'filterByConcTier', 'filterByAspDeltaTier',
                   'filterByGovGrade'].forEach(function(fn) {
                    window.__origBadgeFns[fn] = window[fn];
                    window[fn] = function() {
                      window.__badgeCalls.push(fn);
                    };
                  });
                  const b = document.querySelector(
                    '#comp-tbody .eq-tbl-badge-clickable[tabindex="0"], ' +
                    '#comp-tbody .new-ceo-badge-clickable[tabindex="0"], ' +
                    '#comp-tbody .conc-badge-clickable[tabindex="0"], ' +
                    '#comp-tbody .asp-tbl-badge-clickable[tabindex="0"], ' +
                    '#comp-tbody .gov-badge-clickable[tabindex="0"]');
                  if (b) b.focus();
                }""")
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(600)
                bcalls = pg.evaluate("window.__badgeCalls")
                r2 = (len(bcalls) == 1)
                r2detail = "calls=%r" % (bcalls,)
                pg.evaluate("""() => {
                  Object.keys(window.__origBadgeFns || {}).forEach(function(fn) {
                    window[fn] = window.__origBadgeFns[fn];
                  });
                }""")
            check("R2 table badges are a roving group (one holder); Enter fires exactly one filter",
                  r2, "" if r2 else r2detail)

            # R3: detail panel trajectory wrap + missing-roles link (AMGN carries
            # both: _ceoTrend >= 2 and _teamMissingExpected non-empty).
            pg.evaluate("window.openCompanyDetailWithDiff('AMGN', '')")
            try:
                pg.wait_for_selector('.detail-row[data-ticker="AMGN"] .detail-trajectory-clickable',
                                     timeout=20000)
            except Exception:
                pass
            r3info = pg.evaluate("""() => {
              const row = document.querySelector('.detail-row[data-ticker="AMGN"]');
              if (!row) return null;
              const els = [...row.querySelectorAll(
                '.detail-trajectory-clickable, .tc-missing-link')];
              const holders = els.filter(el => el.getAttribute('tabindex') === '0');
              const bad = els.filter(el =>
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').length ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              const traj = row.querySelector('.detail-trajectory-clickable');
              return {n: els.length, holders: holders.length, bad: bad.length,
                      trajLabel: traj ? traj.getAttribute('aria-label') : null};
            }""")
            r3 = False
            r3detail = "detail state: %r" % (r3info,)
            if (r3info and r3info["n"] == 2 and r3info["holders"] == 1
                    and r3info["bad"] == 0
                    and (r3info["trajLabel"] or "")):
                pg.evaluate("""() => {
                  window.__anomalyCalls = [];
                  const orig = window.navigateToPayAnomaly;
                  window.navigateToPayAnomaly = function() {
                    window.__anomalyCalls.push([].slice.call(arguments));
                  };
                  const w = document.querySelector(
                    '.detail-row[data-ticker="AMGN"] .detail-trajectory-clickable');
                  w.focus();
                }""")
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(600)
                acalls = pg.evaluate("window.__anomalyCalls")
                # ArrowRight moves the holder from the trajectory wrap to the
                # missing-roles link (roving group of 2).
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(300)
                moved = pg.evaluate("""() => {
                  const link = document.querySelector(
                    '.detail-row[data-ticker="AMGN"] .tc-missing-link');
                  return link && link.getAttribute('tabindex') === '0'
                    && document.activeElement === link;
                }""")
                r3 = (len(acalls) == 1 and acalls[0][1] == "AMGN" and moved)
                r3detail = "calls=%r moved=%r" % (acalls, moved)
            check("R3 AMGN detail: trajectory + missing-link are one roving group; Enter fires navigateToPayAnomaly(sector, 'AMGN'); ArrowRight moves holder",
                  r3, "" if r3 else r3detail)

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
        rc = render_checks()
        if rc is None:
            print("SKIP: render checks unavailable; static checks decide")
    fails = [n for n, ok, _ in results if not ok]
    if fails:
        print("\n%d check(s) FAILED: %s" % (len(fails), ", ".join(fails)))
        return 1
    print("\nALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
