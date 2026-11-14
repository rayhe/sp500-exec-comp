#!/usr/bin/env python3
"""Guard: community filter must survive the hash round trip.

Background (409th review, 2026-11-10): closes the 408th run's candidate
(2). The community filter was the last ticker-list filter with no hash
carrier: serializeState wrote nothing for it, so a shared link into a
community-filtered view dropped the filter on load (table unfiltered,
no chip, no badge) while the URL described nothing, and a back/forward
navigation could not drop it either (it was session-local by design).
The fix mirrors the peer-dist / crosstab carrier: cmtk (comma-joined
tickers) + cmlbl (label) + cmid (Louvain id, so the legend and
metrics-row toggles match the restored filter). applyHashState
restores the filter + scatter tickers + chip + legend/metrics-row
marking; the hashchange handler nulls it like every other serialized
dim; the boot restore block and the hashchange highlight section
redraw the scatter (drawScatterChart reads _activeCommunityScatter-
Tickers at draw time, and the charts draw before applyHashState).

Checks (static - file reads, <2s):
  C1  HARD FAIL: serializeState does not emit cmtk for the community
      filter (no ticker carrier -- the round trip has no filter).
  C2  HARD FAIL: serializeState does not emit cmlbl for the community
      filter (the chip/badge/announce render from the label).
  C3  HARD FAIL: serializeState does not emit cmid when the filter
      carries an id (the legend/metrics-row toggles compare
      filter.id to the community id -- without it a restored filter
      re-sets instead of clearing on a second click).
  C4  HARD FAIL: applyHashState does not restore _activeCommunityFilter
      from cmtk/cmlbl (tickers split, non-empty gate).
  C5  HARD FAIL: the restore does not parse cmid into the filter id
      (a restored filter with no id breaks the toggle match above).
  C6  HARD FAIL: the restore does not set _activeCommunityScatterTickers
      from the restored tickers (the scatter highlight reads them at
      draw time).
  C7  HARD FAIL: the restore does not call the community indicator
      updater (guarded) -- a deep link would filter the table with
      no dismiss chip.
  C8  HARD FAIL: the restore does not re-mark the legend item /
      metrics row for the restored community id (guarded queries).
  C9  HARD FAIL: the hashchange handler does not null
      _activeCommunityFilter (also pinned by
      check_hashchange_reset_completeness C2, which derives the
      serialized set from serializeState) or does not null
      _activeCommunityScatterTickers alongside it.
  C10 HARD FAIL: the hashchange handler does not remove the
      community-filter-chip (also pinned by the reset-completeness
      guard's C3) or does not clear .community-legend-active /
      .cm-data.cm-active on a dropped filter.
  C11 HARD FAIL: the boot restore block does not redraw the scatter
      when a community filter was restored from the hash (the
      draw-before-restore gap: charts draw before applyHashState).
  C12 HARD FAIL: the hashchange highlight section does not redraw
      the scatter when the community state changed across the
      navigation (hadCommScatter / restored filter).
  C13 HARD FAIL: the legend build does not mark the active community's
      item at build time (a re-population after restore would drop
      the marking).
  C14 HARD FAIL: the community-metrics row build does not mark the
      active community's row at build time (same re-render gap).

Render (headless Chromium, d3 shimmed from the local cache):
  R1  Set a community filter + Information Technology sector on the
      live page (state + updater, the same code path as the legend
      click), read the hash, reload with it: chip reads
      'Information Technology x Community: Info Tech', badge carries
      'Community: Info Tech', footer 3, announce names the community,
      and the restored filter keeps id 9999. Pre-fix: the hash
      carried no cmtk, so the reload unfiltered with no chip.
  R2  Clear the hash on the reloaded page (hashchange): chip gone,
      badge gone, footer back to 518, _activeCommunityFilter null.
      Pre-fix: the filter was session-local, so clearing the hash
      left it filtering with no URL behind it.
  R3  zero page errors across the render half.

Usage:
  scripts/check_community_hash_roundtrip.py
  scripts/check_community_hash_roundtrip.py --static-only

457th review (2026-11-14): adopted scripts/render_guard_common.py
(slowest unadopted render guard in shard 4, 21.3s fresh shard-4
verdict; re-profiled with the canary's exact shard function, per the
455th note (17) -- the ranking held exactly). Pre-fix defects were
BOTH 429th-review classes: (#1, no retry wrapper) a transient render
exception raised before any R-check was uncaught -- traceback, exit 1,
0 R-checks, no FAIL verdict; (#2, missing-d3 exit-code mismatch)
render_checks() returned False on a missing d3 shim, which main()
folded into exit 1 (drift) although the docstring promises exit 2
(infra) -- both proved in-process before the fix
(~/workspace/sp500-457/pre457_proof.py: Test A rc=1 with "14/14
checks passed" printed and 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The adoption still
converts main() to return its exit code (not sys.exit) so the
contract guard's S4 harness can observe the INFRA mapping. 64
unadopted guards remain.

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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")
NET_JS = os.path.join(REPO, "js", "network.js")

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
        net = open(NET_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read JS sources: %s" % exc)
        return 2

    ser = extract_function_body(app, "function serializeState()")
    if ser is None:
        check("C1 serializeState emits cmtk", False, "serializeState not found")
        return 1
    check("C1 serializeState emits cmtk for the community filter",
          "cmtk=" in ser and "_activeCommunityFilter" in ser,
          "no cmtk push in serializeState")
    check("C2 serializeState emits cmlbl for the community filter",
          "cmlbl=" in ser,
          "no cmlbl push in serializeState")
    check("C3 serializeState emits cmid when the filter carries an id",
          "cmid=" in ser and ".id != null" in ser,
          "no guarded cmid push in serializeState")

    apply = extract_function_body(app, "function applyHashState(companies)")
    if apply is None:
        check("C4 applyHashState restores the community filter", False,
              "applyHashState not found")
        return 1
    cm_block = block_between(apply, "// Community filter", "// Role filter")
    if cm_block is None:
        check("C4 applyHashState restores the community filter", False,
              "community restore block not found in applyHashState")
        return 1
    check("C4 applyHashState restores _activeCommunityFilter from cmtk/cmlbl",
          ("state.cmtk" in cm_block and "state.cmlbl" in cm_block
           and "_activeCommunityFilter = { tickers: cmTickers" in cm_block
           and "cmTickers.length > 0" in cm_block),
          "restore block does not build the filter from cmtk/cmlbl")
    check("C5 restore parses cmid into the filter id",
          ("parseInt(state.cmid, 10)" in cm_block
           and "id: isNaN(cmId) ? null : cmId" in cm_block),
          "no parseInt(cmid) id assignment in the restore block")
    check("C6 restore sets _activeCommunityScatterTickers from the tickers",
          "_activeCommunityScatterTickers = new Set(cmTickers)" in cm_block,
          "no scatter-tickers assignment in the restore block")
    check("C7 restore calls the community indicator updater (guarded)",
          ("window._updateCommunityFilterIndicator) "
           "window._updateCommunityFilterIndicator();" in cm_block),
          "no guarded indicator call in the restore block")
    check("C8 restore re-marks the legend item / metrics row",
          ("community-legend-item[data-community=\"' + cmId + '\"]" in cm_block
           and "community-legend-active" in cm_block
           and ".cm-data[data-cm-community=\"' + cmId + '\"]" in cm_block
           and "cm-active" in cm_block),
          "no guarded legend/metrics-row marking in the restore block")

    # C9-C10: the hashchange reset block (marker through the
    # applyHashState call inside it).
    marker = "// Listen for browser back/forward"
    start = app.find(marker)
    apply_idx = app.find("applyHashState(companies);", start) if start >= 0 else -1
    hblock = app[start:apply_idx] if start >= 0 and apply_idx > 0 else None
    if hblock is None:
        check("C9 hashchange handler nulls the community filter", False,
              "hashchange reset block not found")
        return 1
    check("C9 hashchange handler nulls the community filter + scatter tickers",
          ("window._activeCommunityFilter = null" in hblock
           and "window._activeCommunityScatterTickers = null" in hblock),
          "community filter/scatter tickers not nulled in the reset block")
    check("C10 hashchange handler removes the chip + clears legend/metrics highlights",
          ("community-filter-chip" in hblock
           and "community-legend-active" in hblock
           and ".cm-data.cm-active" in hblock),
          "chip removal or legend/metrics clear missing from the reset block")

    # C11: the boot restore block redraws the scatter on a restored
    # community filter (the block after the crosstab highlight call).
    boot = block_between(app, "window.highlightCrosstabCell(window._activeCrosstabFilter.cellKey);",
                         "// Apply YoY filter chip if restored from hash")
    check("C11 boot restore block redraws the scatter on a restored community filter",
          (boot is not None
           and "window._activeCommunityFilter" in boot
           and "drawScatterChart(window._chartData.companies)" in boot),
          "no scatter redraw for a restored community filter at boot")
    # C12: the hashchange highlight section redraws the scatter when
    # the community state changed (hadCommScatter / restored filter).
    hsec = block_between(app, "hadCommScatter || window._activeCommunityFilter",
                         "// Restore CEO transition filter chip if present in hash state")
    check("C12 hashchange highlight section redraws the scatter on community change",
          (hsec is not None
           and "drawScatterChart(window._chartData.companies)" in hsec),
          "no scatter redraw on community-state change in the hashchange handler")

    # C13-C14: network.js build-time marking.
    check("C13 legend build marks the active community at build time",
          ("isActiveComm" in net
           and "window._activeCommunityFilter && window._activeCommunityFilter.id === cs.id" in net
           and "community-legend-active" in net),
          "no active-community marking in _populateCommunityLegend")
    check("C14 metrics-row build marks the active community at build time",
          ("isActiveCmRow" in net
           and "window._activeCommunityFilter && window._activeCommunityFilter.id === r.id" in net
           and "' cm-active'" in net),
          "no active-community marking in the metrics-row build")
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
    d3 = get_d3_bytes()
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

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
                pg.wait_for_selector(
                    "#comp-tbody > tr:not(.skeleton-table-row-tr)",
                    timeout=30000)
                pg.wait_for_timeout(800)

            def chip_text():
                return pg.evaluate("""() => {
                    const c = document.getElementById('community-filter-chip');
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

            # R1: community filter + Information Technology sector.
            # AAPL/MSFT/NVDA are all Information Technology, so the
            # table keeps 3 rows. State + updater is the same code
            # path as the legend click (407th review's R1 precedent);
            # filterBySector re-runs the updaters and renderTable's
            # pushState carries the new hash keys.
            load()
            pg.evaluate("""() => {
                window._activeCommunityFilter = {
                    tickers: ['AAPL', 'MSFT', 'NVDA'],
                    label: 'Info Tech', id: 9999
                };
                window._activeCommunityScatterTickers =
                    new Set(['AAPL', 'MSFT', 'NVDA']);
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateCommunityFilterIndicator()")
            pg.wait_for_timeout(1200)
            h1 = pg.evaluate("() => window.location.hash")
            chip1 = chip_text()
            badge1 = badge_text()
            n1 = footer_count()
            r1_pre = (("cmtk=" in h1 and "cmlbl=" in h1 and "cmid=9999" in h1)
                      and chip1 is not None
                      and "Information Technology \u00d7 Community: Info Tech" in chip1
                      and badge1 is not None and "Community: Info Tech" in badge1
                      and n1 == 3)
            check("R1 live set: hash carries cmtk/cmlbl/cmid=9999, combined chip + badge, footer 3 "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h1, chip1, badge1, n1),
                  r1_pre,
                  "want cmtk/cmlbl/cmid=9999 in the hash, combined chip, badge, footer 3")

            # Reload with the captured hash: the deep link must
            # restore the filter, chip, badge, footer and announce,
            # and keep the Louvain id.
            url1 = pg.url
            load(url1)
            chip2 = chip_text()
            badge2 = badge_text()
            n2 = footer_count()
            a2 = last_announce()
            id2 = pg.evaluate("() => window._activeCommunityFilter ? window._activeCommunityFilter.id : null")
            r1_ok = (r1_pre
                     and chip2 is not None
                     and "Information Technology \u00d7 Community: Info Tech" in chip2
                     and badge2 is not None and "Community: Info Tech" in badge2
                     and n2 == 3 and id2 == 9999
                     and "community: Info Tech" in a2)
            check("R1 reload with the hash restores chip + badge + footer 3 + id 9999 + announce "
                  "(chip=%r badge=%r footer=%s id=%r announce=%r)" % (chip2, badge2, n2, id2, a2),
                  r1_ok,
                  "want combined chip, badge, footer 3, id 9999, 'community: Info Tech' in the announce")

            # R2: clear the hash (hashchange): the filter must drop
            # cleanly -- chip + badge gone, footer back to 518.
            pg.evaluate("() => { window.location.hash = ''; }")
            pg.wait_for_timeout(1200)
            chip3 = chip_text()
            badge3 = badge_text()
            n3 = footer_count()
            f3 = pg.evaluate("() => window._activeCommunityFilter")
            r2_ok = (chip3 is None and badge3 is None and n3 == 518 and f3 is None)
            check("R2 hash cleared: chip + badge gone, footer 518, filter null "
                  "(chip=%r badge=%r footer=%s filter=%r)" % (chip3, badge3, n3, f3),
                  r2_ok,
                  "want no chip, no badge, footer 518, filter null")

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
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        print("render checks infra (d3 shim unavailable)")
        return 2
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
