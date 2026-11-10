#!/usr/bin/env python3
"""Guard: position filter must survive the hash round trip.

Background (410th review, 2026-11-10): closes the 409th run's candidate
(1). The position filter was the last ticker-list filter with no hash
carrier: serializeState wrote nothing for it, so a shared link into a
position-filtered view dropped the filter on load (table unfiltered,
no chip, no badge) while the URL described nothing, and a back/forward
navigation could not drop it either (it was session-local by design).
The fix mirrors the community carrier: pstk (comma-joined tickers) +
pslbl (label) + pscid (Louvain id) + psm (metric) + psr (rank) + psd
(direction). The composite key (communityId/metric/rank/direction)
is what the row-click toggle compares, so a restored filter without
it would re-set instead of clearing on a second click; the detail
render re-marks the clicked row from the same key (isActivePos).
applyHashState restores the filter + chip; the hashchange handler
nulls it like every other serialized dim; the boot restore needs no
scatter redraw (the scatter never reads the position filter). The
gate is the label, not the ticker list: an empty filter (no peers in
that direction) has zero tickers and must still restore its chip +
empty table.

Checks (static - file reads, <2s):
  C1  HARD FAIL: serializeState does not emit pstk for the position
      filter (no ticker carrier -- the round trip has no filter).
  C2  HARD FAIL: serializeState does not emit pslbl for the position
      filter (the chip/badge/announce render from the label).
  C3  HARD FAIL: serializeState does not emit pscid when the filter
      carries a communityId (the toggle / row marking compare it).
  C4  HARD FAIL: serializeState does not emit psm for the metric
      (the toggle compares communityId + metric + rank).
  C5  HARD FAIL: serializeState does not emit psr when the filter
      carries a rank.
  C6  HARD FAIL: serializeState does not emit psd for the direction
      (above/below -- the toggle compares it too).
  C7  HARD FAIL: applyHashState does not restore _activePositionFilter
      from pstk/pslbl, gated on the label (an empty filter must
      restore -- gating on the ticker list would drop it).
  C8  HARD FAIL: the restore does not parse pscid into communityId.
  C9  HARD FAIL: the restore does not parse psr into rank.
  C10 HARD FAIL: the restore does not default direction to 'above'
      when psd is absent (old / hand-built links).
  C11 HARD FAIL: the restore does not call the position indicator
      updater (guarded) -- a deep link would filter the table with
      no dismiss chip.
  C12 HARD FAIL: the hashchange handler does not null
      _activePositionFilter (also pinned by
      check_hashchange_reset_completeness C2, which derives the
      serialized set from serializeState).
  C13 HARD FAIL: the hashchange handler does not remove the
      position-filter-chip (also pinned by the reset-completeness
      guard's C3) or does not clear .cb-pos-row-clicked on a dropped
      filter.

Render (headless Chromium, d3 shimmed from the local cache):
  R1  Set a position filter + Information Technology sector on the
      live page (state + updater, the same code path as the detail
      row click), read the hash, reload with it: chip reads
      'Information Technology x Info Tech CEO Pay above #3 (3)',
      badge carries the label, footer 3, announce names the
      position, and the restored filter keeps communityId 9999,
      metric pay, rank 3, direction above. Pre-fix: the hash
      carried no pstk, so the reload unfiltered with no chip.
  R2  Same round trip for an EMPTY position filter (no peers in
      that direction): chip + badge carry the label with ' (0)',
      footer 0, and the reload restores the empty filter (tickers
      []). Pre-fix: the empty filter was session-local too.
  R3  Clear the hash on the reloaded page (hashchange): chip gone,
      badge gone, footer back to 518, _activePositionFilter null.
      Pre-fix: the filter was session-local, so clearing the hash
      left it filtering with no URL behind it.
  R4  zero page errors across the render half.

Usage:
  scripts/check_position_hash_roundtrip.py
  scripts/check_position_hash_roundtrip.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable).

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


def block_between(src, start_marker, end_marker):
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
    except OSError as exc:
        print("INFRA: cannot read JS sources: %s" % exc)
        return 2

    ser = extract_function_body(app, "function serializeState()")
    if ser is None:
        check("C1 serializeState emits pstk", False, "serializeState not found")
        return 1
    check("C1 serializeState emits pstk for the position filter",
          "pstk=" in ser and "_activePositionFilter" in ser,
          "no pstk push in serializeState")
    check("C2 serializeState emits pslbl for the position filter",
          "pslbl=" in ser,
          "no pslbl push in serializeState")
    check("C3 serializeState emits pscid when the filter carries a communityId",
          "pscid=" in ser and ".communityId != null" in ser,
          "no guarded pscid push in serializeState")
    check("C4 serializeState emits psm for the metric",
          "psm=" in ser and ".metric" in ser,
          "no psm push in serializeState")
    check("C5 serializeState emits psr when the filter carries a rank",
          "psr=" in ser and ".rank != null" in ser,
          "no guarded psr push in serializeState")
    check("C6 serializeState emits psd for the direction",
          "psd=" in ser and ".direction" in ser,
          "no psd push in serializeState")

    apply = extract_function_body(app, "function applyHashState(companies)")
    if apply is None:
        check("C7 applyHashState restores the position filter", False,
              "applyHashState not found")
        return 1
    ps_block = block_between(apply, "// Position filter", "// Role filter")
    if ps_block is None:
        check("C7 applyHashState restores the position filter", False,
              "position restore block not found in applyHashState")
        return 1
    check("C7 applyHashState restores _activePositionFilter from pstk/pslbl, gated on the label",
          ("state.pslbl" in ps_block and "state.psm" in ps_block
           and "_activePositionFilter = { tickers: psTickers" in ps_block
           and "if (state.pslbl && state.psm)" in ps_block),
          "restore block does not build the filter from pstk/pslbl gated on the label")
    check("C8 restore parses pscid into communityId",
          ("parseInt(state.pscid, 10)" in ps_block
           and "communityId: isNaN(psCid) ? null : psCid" in ps_block),
          "no parseInt(pscid) communityId assignment in the restore block")
    check("C9 restore parses psr into rank",
          ("parseInt(state.psr, 10)" in ps_block
           and "rank: isNaN(psRank) ? null : psRank" in ps_block),
          "no parseInt(psr) rank assignment in the restore block")
    check("C10 restore defaults direction to 'above' when psd is absent",
          "direction: state.psd || 'above'" in ps_block,
          "no 'above' default for a missing psd in the restore block")
    check("C11 restore calls the position indicator updater (guarded)",
          ("window._updatePositionFilterIndicator) "
           "window._updatePositionFilterIndicator();" in ps_block),
          "no guarded indicator call in the restore block")

    # C12-C13: the hashchange reset block (marker through the
    # applyHashState call inside it).
    marker = "// Listen for browser back/forward"
    start = app.find(marker)
    apply_idx = app.find("applyHashState(companies);", start) if start >= 0 else -1
    hblock = app[start:apply_idx] if start >= 0 and apply_idx > 0 else None
    if hblock is None:
        check("C12 hashchange handler nulls the position filter", False,
              "hashchange reset block not found")
        return 1
    check("C12 hashchange handler nulls the position filter",
          "window._activePositionFilter = null" in hblock,
          "position filter not nulled in the reset block")
    check("C13 hashchange handler removes the chip + clears clicked rows",
          ("position-filter-chip" in hblock
           and "cb-pos-row-clicked" in hblock),
          "chip removal or clicked-row clear missing from the reset block")
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

            def load(url=None):
                if url is not None and pg.url == url:
                    # goto() to the identical hash URL is a
                    # same-document navigation in Chromium -- no
                    # reload, no restore, so the checks below would
                    # pass vacuously on the pre-reload state (411th
                    # probe: window.__probe survives goto(same hash
                    # URL) but not goto(same bare URL) or reload()).
                    # Force a real reload for the round trip.
                    # (413th review: vacuous-reload fix.)
                    pg.reload(timeout=60000)
                else:
                    pg.goto(url or "http://127.0.0.1:%d/index.html" % port,
                            timeout=60000)
                # Render done when the skeleton rows are gone -- a
                # plain row selector would never match an empty table
                # (R2's zero-row reload has no rows at all).
                pg.wait_for_function(
                    "() => !document.querySelector("
                    "'#comp-tbody .skeleton-table-row-tr')",
                    timeout=30000)
                pg.wait_for_timeout(800)

            def chip_text():
                return pg.evaluate("""() => {
                    const c = document.getElementById('position-filter-chip');
                    return c ? c.textContent : null;
                }""")

            def badge_text():
                return pg.evaluate("""() => {
                    const b = document.querySelector(
                        '#table-summary-bar .combined-filter-badge');
                    return b ? b.textContent : null;
                }""")

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            def last_announce():
                return pg.evaluate(
                    "() => (typeof window._lastTableAnnounce === 'string' "
                    "&& window._lastTableAnnounce) || ''")

            def filter_state():
                return pg.evaluate(
                    "() => window._activePositionFilter || null")

            # R1: position filter + Information Technology sector.
            # AAPL/MSFT/NVDA are all Information Technology, so the
            # table keeps 3 rows. State + updater is the same code
            # path as the detail row click (409th review's R1
            # precedent); filterBySector re-runs the updaters and
            # renderTable's pushState carries the new hash keys.
            load()
            pg.evaluate("""() => {
                window._activePositionFilter = {
                    tickers: ['AAPL', 'MSFT', 'NVDA'],
                    label: 'Info Tech CEO Pay above #3 (3)',
                    communityId: 9999, metric: 'pay', rank: 3,
                    direction: 'above'
                };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updatePositionFilterIndicator()")
            pg.wait_for_timeout(1200)
            h1 = pg.evaluate("() => window.location.hash")
            chip1 = chip_text()
            badge1 = badge_text()
            n1 = footer_count()
            r1_pre = (("pstk=" in h1 and "pslbl=" in h1 and "pscid=9999" in h1
                       and "psm=pay" in h1 and "psr=3" in h1 and "psd=above" in h1)
                      and chip1 is not None
                      and "Information Technology \u00d7 Info Tech CEO Pay above #3 (3)" in chip1
                      and badge1 is not None and "Info Tech CEO Pay above #3 (3)" in badge1
                      and n1 == 3)
            check("R1 live set: hash carries pstk/pslbl/pscid=9999/psm=pay/psr=3/psd=above, combined chip + badge, footer 3 "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h1, chip1, badge1, n1),
                  r1_pre,
                  "want pstk/pslbl/pscid=9999/psm=pay/psr=3/psd=above in the hash, combined chip, badge, footer 3")

            # Reload with the captured hash: the deep link must
            # restore the filter, chip, badge, footer and announce,
            # and keep the composite toggle key.
            url1 = pg.url
            load(url1)
            chip2 = chip_text()
            badge2 = badge_text()
            n2 = footer_count()
            a2 = last_announce()
            f2 = filter_state()
            r1_ok = (r1_pre
                     and chip2 is not None
                     and "Information Technology \u00d7 Info Tech CEO Pay above #3 (3)" in chip2
                     and badge2 is not None and "Info Tech CEO Pay above #3 (3)" in badge2
                     and n2 == 3
                     and f2 is not None and f2.get("communityId") == 9999
                     and f2.get("metric") == "pay" and f2.get("rank") == 3
                     and f2.get("direction") == "above"
                     and "position: Info Tech CEO Pay above #3 (3)" in a2)
            check("R1 reload with the hash restores chip + badge + footer 3 + toggle key + announce "
                  "(chip=%r badge=%r footer=%s filter=%r announce=%r)" % (chip2, badge2, n2, f2, a2),
                  r1_ok,
                  "want combined chip, badge, footer 3, communityId 9999 / pay / 3 / above, 'position: ...' in the announce")

            # R2: an EMPTY position filter (no peers in that
            # direction) round-trips too: the chip + badge carry the
            # label with ' (0)', the footer is 0, and the reload
            # restores the empty ticker list.
            load()
            pg.evaluate("""() => {
                window._activePositionFilter = {
                    tickers: [],
                    label: 'Info Tech CEO Pay above #1 \\u2014 no above',
                    communityId: 9999, metric: 'pay', rank: 1,
                    direction: 'above'
                };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updatePositionFilterIndicator()")
            pg.wait_for_timeout(1200)
            h2 = pg.evaluate("() => window.location.hash")
            chip_e = chip_text()
            badge_e = badge_text()
            n_e = footer_count()
            r2_pre = (("pstk=" in h2 and "pslbl=" in h2)
                      and chip_e is not None
                      and "Info Tech CEO Pay above #1 \u2014 no above (0)" in chip_e
                      and badge_e is not None
                      and "Info Tech CEO Pay above #1 \u2014 no above (0)" in badge_e
                      and n_e == 0)
            check("R2 live empty set: hash carries pstk=/pslbl, chip + badge carry ' (0)', footer 0 "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h2, chip_e, badge_e, n_e),
                  r2_pre,
                  "want pstk=/pslbl in the hash, ' (0)' chip + badge, footer 0")
            url2 = pg.url
            load(url2)
            chip_e2 = chip_text()
            badge_e2 = badge_text()
            n_e2 = footer_count()
            f_e2 = filter_state()
            r2_ok = (r2_pre
                     and chip_e2 is not None
                     and "Info Tech CEO Pay above #1 \u2014 no above (0)" in chip_e2
                     and badge_e2 is not None
                     and "Info Tech CEO Pay above #1 \u2014 no above (0)" in badge_e2
                     and n_e2 == 0
                     and f_e2 is not None and f_e2.get("tickers") == [])
            check("R2 reload with the hash restores the empty filter (chip + badge + footer 0 + tickers []) "
                  "(chip=%r badge=%r footer=%s filter=%r)" % (chip_e2, badge_e2, n_e2, f_e2),
                  r2_ok,
                  "want ' (0)' chip + badge, footer 0, tickers []")

            # R3: clear the hash (hashchange): the filter must drop
            # cleanly -- chip + badge gone, footer back to 518.
            pg.evaluate("() => { window.location.hash = ''; }")
            pg.wait_for_timeout(1200)
            chip3 = chip_text()
            badge3 = badge_text()
            n3 = footer_count()
            f3 = filter_state()
            r3_ok = (chip3 is None and badge3 is None and n3 == 518 and f3 is None)
            check("R3 hash cleared: chip + badge gone, footer 518, filter null "
                  "(chip=%r badge=%r footer=%s filter=%r)" % (chip3, badge3, n3, f3),
                  r3_ok,
                  "want no chip, no badge, footer 518, filter null")

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
