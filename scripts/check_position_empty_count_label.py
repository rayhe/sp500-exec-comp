#!/usr/bin/env python3
"""Guard: the empty position filter's ' (0)' count is the same in the
chip, the combined-filter badge, and the ARIA announcement.

Background (408th review, 2026-11-10): the position filter's stored
label carries no count for the empty filter (no peers in that
direction -- 'Cluster 3 pay #2 -- no above'), unlike the non-empty
form which embeds '(N)'. The dismiss chip appended ' (0)' inline,
so the chip read '... -- no above (0)' while the combined-filter
badge part and the ARIA announcement both used the bare stored
label -- the same chip-wording-must-match-badge class the 402nd /
403rd reviews closed for percentile and equity-mix.

The fix: one shared helper positionFilterLabel(pf) (js/app.js, next
to boardFilterLabel) returning pf.label + ' (0)' when tickers is
empty, used by the chip updater, the badge part (renderSummaryBar
filterParts) and the announcement. Non-empty filters are unchanged
(the stored label already carries '(N)').

Checks:
  C1 HARD FAIL: the positionFilterLabel helper exists and appends
     ' (0)' for an empty tickers list.
  C2 HARD FAIL: the badge part uses positionFilterLabel, not the
     bare stored label.
  C3 HARD FAIL: the announcement uses positionFilterLabel, not the
     bare stored label.
  C4 HARD FAIL: the chip updater uses positionFilterLabel (no inline
     ' (0)' suffix logic left in updatePositionFilterIndicator).
  C5 HARD FAIL: no bare 'filterParts.push(window._activePositionFilter.label)'
     or bare announce form remains anywhere in js/app.js.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Non-empty position filter + Information Technology sector:
      badge, chip and announce all carry the '(1)' count.
  R2  Empty position filter + the same sector: the chip and the
      announcement carry the helper's ' (0)'; the table is empty, so
      the summary bar shows the zero-row message and no badge renders
      (pre-existing zero-row early return -- the badge part is pinned
      statically by C2 and renders live in R1's form).
  R3  zero page errors across the render half.

Usage:
  scripts/check_position_empty_count_label.py
  scripts/check_position_empty_count_label.py --static-only

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

    # C1: the helper exists and appends ' (0)' for an empty tickers list.
    m = re.search(r"function positionFilterLabel\(pf\) \{([^}]*)\}", app)
    c1 = bool(m) and "' (0)'" in m.group(1) and "length === 0" in m.group(1)
    check("C1 positionFilterLabel helper appends ' (0)' for empty tickers",
          c1, "" if c1 else "helper missing or suffix logic absent")

    # C2: the badge part uses the helper.
    c2 = "filterParts.push(positionFilterLabel(window._activePositionFilter))" in app
    check("C2 badge position part uses positionFilterLabel",
          c2, "" if c2 else "badge still uses the bare stored label")

    # C3: the announcement uses the helper.
    c3 = "announceMsg += ', position: ' + positionFilterLabel(window._activePositionFilter)" in app
    check("C3 announcement position part uses positionFilterLabel",
          c3, "" if c3 else "announce still uses the bare stored label")

    # C4: the chip updater uses the helper (no inline suffix logic).
    upd = app[app.find("function updatePositionFilterIndicator"):]
    upd = upd[:upd.find("window._updatePositionFilterIndicator")]
    c4 = "positionFilterLabel(pf)" in upd and "var suffix" not in upd
    check("C4 position chip uses positionFilterLabel, no inline suffix",
          c4, "" if c4 else "updater still builds the suffix inline")

    # C5: no bare stored-label use remains in the badge or announce.
    c5a = "filterParts.push(window._activePositionFilter.label)" not in app
    c5b = "announceMsg += ', position: ' + window._activePositionFilter.label" not in app
    check("C5 no bare stored-label position wording remains",
          c5a and c5b,
          "" if (c5a and c5b) else "bare label use still present")

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
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)

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

            # R1: non-empty position filter + Information Technology
            # sector. AAPL is an Information Technology company, so the
            # table keeps 1 row and the badge renders; badge, chip and
            # announce all carry the '(1)' count the stored label embeds.
            pg.evaluate("""() => {
                window._activePositionFilter = { tickers: ['AAPL'],
                    label: 'Cluster 3 CEO Pay above #2 (1)',
                    communityId: 3, metric: 'pay', rank: 2,
                    direction: 'above' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updatePositionFilterIndicator()")
            pg.wait_for_timeout(1200)
            b1 = badge_text()
            a1 = last_announce()
            chip1 = pg.evaluate(
                "() => { const c = document.getElementById('position-filter-chip');"
                " return c ? c.textContent : null; }")
            want1 = "Cluster 3 CEO Pay above #2 (1)"
            r1_ok = (b1 is not None and a1 is not None and chip1 is not None
                     and want1 in b1 and want1 in chip1
                     and ("position: " + want1) in a1)
            check("R1 non-empty position filter keeps '(1)' in chip, badge, announce",
                  r1_ok,
                  "badge=%r chip=%r announce=%r (want %r in all three)"
                  % (b1, chip1, a1, want1))

            # R2: empty position filter (no peers in that direction).
            # The chip and the announcement carry the helper's ' (0)';
            # the table is empty, so the summary bar shows the zero-row
            # message and no badge renders at all (pre-existing zero-row
            # early return in renderSummaryBar -- the badge part is
            # pinned statically by C2 and renders live in R1's form).
            pg.evaluate("""() => {
                window._activePositionFilter = { tickers: [],
                    label: 'Cluster 3 pay #2 \\u2014 no above',
                    communityId: 3, metric: 'pay', rank: 2,
                    direction: 'above' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updatePositionFilterIndicator()")
            pg.wait_for_timeout(1200)
            b2 = badge_text()
            a2 = last_announce()
            chip2 = pg.evaluate(
                "() => { const c = document.getElementById('position-filter-chip');"
                " return c ? c.textContent : null; }")
            bar2 = pg.evaluate(
                "() => { const b = document.getElementById('table-summary-bar');"
                " return b ? b.textContent : null; }")
            want2 = "Cluster 3 pay #2 \u2014 no above (0)"
            r2_ok = (b2 is None and chip2 is not None and a2 is not None
                     and want2 in chip2 and ("position: " + want2) in a2
                     and bar2 is not None and "No companies match" in bar2)
            check("R2 empty position filter keeps ' (0)' in chip and announce (zero-row bar, no badge)",
                  r2_ok,
                  "badge=%r chip=%r announce=%r bar=%r (want %r in chip and announce)"
                  % (b2, chip2, a2, bar2, want2))

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
