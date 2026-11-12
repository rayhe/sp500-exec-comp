#!/usr/bin/env python3
"""Guard: volatility bucket, vol-tenure bracket and board filter must
survive the hash round trip.

Background (412th review, 2026-11-10): closes the 411th run's candidate
(2). The volatility bucket, vol-tenure bracket and board filter were
the last three session-local filters with no hash carrier:
serializeState wrote nothing for them, so a shared link into a
volatility- or board-filtered view dropped the filter on load (table
unfiltered, no chip, no badge) while the URL described nothing, and a
back/forward navigation could not drop it either (it was session-local
by design). The fix mirrors the quartile carrier: min/max + label for
the two range filters (vmin/vmax/vlbl, vtmin/vtmax/vtlbl -- 'inf' for
the open-ended top bucket, like ratio/YoY), mode for board (board=high
| mid | low, validated against the three AF modes). applyHashState
restores each filter + its chip; the hashchange handler nulls all
three like every other serialized dim (341st stuck-filter class); the
init restore block and the hashchange highlight section re-apply the
vol chart ring (highlightVolatilityBucket overlaps AF bands against
chart buckets). The restored filters are hash-origin, not AF-origin
(337th-review gender precedent): no _isAf flag, no AF select sync --
the chip dismiss takes the non-AF branch. Vol-tenure / board have no
chart highlight function (like pctile / peer-dist), so a deep link
filters the table and raises the chip with the bars un-ringed.

Checks (static - file reads, <2s):
  C1  HARD FAIL: serializeState does not emit vmin/vmax/vlbl for the
      volatility bucket (no range carrier -- the round trip has no
      filter).
  C2  HARD FAIL: serializeState does not emit vtmin/vtmax/vtlbl for
      the vol-tenure bracket.
  C3  HARD FAIL: serializeState does not emit board= for the board
      filter.
  C4  HARD FAIL: applyHashState does not restore
      _activeVolatilityBucket from vmin/vmax/vlbl (parseFloat, 'inf'
      for the open-ended max).
  C5  HARD FAIL: the vol restore does not call the volatility
      indicator updater (guarded) -- a deep link would filter the
      table with no dismiss chip.
  C6  HARD FAIL: applyHashState does not restore
      _activeVolTenureBracket from vtmin/vtmax/vtlbl.
  C7  HARD FAIL: the vol-tenure restore does not call the vol-tenure
      indicator updater (guarded).
  C8  HARD FAIL: applyHashState does not restore _activeBoardFilter
      from board=, or does not validate the mode against
      high/mid/low (a hand-built link with anything else must
      restore nothing).
  C9  HARD FAIL: the board restore does not call the board indicator
      updater (guarded).
  C10 HARD FAIL: the hashchange handler does not null all three
      filters (also pinned by check_hashchange_reset_completeness
      C2, which derives the serialized set from serializeState).
  C11 HARD FAIL: the hashchange handler does not remove the three
      chips (also pinned by the reset-completeness guard's C3) or
      does not clear af-vol / af-board (also pinned by its C4).
  C12 HARD FAIL: the init restore block does not re-apply the vol
      chart highlight from the restored state (also pinned by
      check_hash_restore_highlights).
  C13 HARD FAIL: the hashchange handler does not restore the vol
      chart highlight when the new hash carries the filter, or does
      not clear it when the new hash drops the filter (also pinned
      by check_hash_restore_highlights).

Render (headless Chromium, d3 shimmed from the local cache):
  R1  Set a vol bucket (0-5%) + Information Technology sector on the
      live page (state + updater, the same code path as the histogram
      bar click). Read the hash, reload with it: chip reads
      'Information Technology x Volatility 0-5%', badge carries the
      label, footer matches, announce names the volatility, and the
      restored filter keeps min/max/label. Pre-fix: the hash carried
      no vmin, so the reload unfiltered with no chip.
  R2  Same round trip for a vol-tenure bracket (Veterans, 20+ yrs,
      max Infinity) + Information Technology sector: hash carries
      vtmin=20/vtmax=inf, reload restores the combined chip + badge
      + footer + state with max === Infinity. (The sector supplies
      the second dim the combined badge needs.) Pre-fix: the bracket
      was session-local too.
  R3  Same round trip for a board filter (low) + Information
      Technology sector: hash carries board=low, reload restores the
      combined 'Board <60%' chip + badge + footer + state. Pre-fix:
      the filter was session-local too.
  R4  Set all three filters on one page, then clear the hash
      (hashchange): all three chips gone, footer back to 518, all
      three states null. Pre-fix: the filters were session-local, so
      clearing the hash left them filtering with no URL behind it.
  R5  zero page errors across the render half.

Usage:
  scripts/check_vol_board_hash_roundtrip.py
  scripts/check_vol_board_hash_roundtrip.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

437th review (2026-11-12): adopted render_guard_common (slowest
remaining render guard, ~32.5s max in the 2026-11-12 shard runs;
re-profiled from the freshest drift_canary_state.json entries this
run, per the 432nd note). Pre-fix defect was the 429th-review class,
not the silent-pass variant: main() checked render_checks()'s return
value, but a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the docstring promises exit
2 (infra) -- proved in-process before the fix
(~/workspace/pre437_proof.py: rc=1, "13/13 checks passed" printed, 0
R-checks recorded). 73 local copies remain.
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
        check("C1 serializeState emits vmin/vmax/vlbl", False, "serializeState not found")
        return 1
    check("C1 serializeState emits vmin/vmax/vlbl for the volatility bucket",
          ("'vmin='" in ser and "'vmax='" in ser and "'vlbl='" in ser
           and "_activeVolatilityBucket" in ser),
          "no vmin/vmax/vlbl push in serializeState")
    check("C2 serializeState emits vtmin/vtmax/vtlbl for the vol-tenure bracket",
          ("'vtmin='" in ser and "'vtmax='" in ser and "'vtlbl='" in ser
           and "_activeVolTenureBracket" in ser),
          "no vtmin/vtmax/vtlbl push in serializeState")
    check("C3 serializeState emits board= for the board filter",
          ("'board='" in ser and "_activeBoardFilter" in ser),
          "no board push in serializeState")

    apply = extract_function_body(app, "function applyHashState(companies)")
    if apply is None:
        check("C4 applyHashState restores the volatility bucket", False,
              "applyHashState not found")
        return 1
    v_block = block_between(apply, "// Volatility bucket filter", "// Volatility x Tenure bracket filter")
    if v_block is None:
        check("C4 applyHashState restores the volatility bucket", False,
              "vol restore block not found in applyHashState")
        return 1
    check("C4 applyHashState restores _activeVolatilityBucket from vmin/vmax/vlbl",
          ("state.vmin" in v_block and "state.vmax" in v_block and "state.vlbl" in v_block
           and "parseFloat(state.vmin)" in v_block
           and "state.vmax === 'inf' ? Infinity : parseFloat(state.vmax)" in v_block
           and "_activeVolatilityBucket = { min: vMin, max: vMax, label: state.vlbl }" in v_block),
          "restore block does not build the filter from vmin/vmax/vlbl with parseFloat + 'inf'")
    check("C5 restore calls the volatility indicator updater (guarded)",
          ("window._updateVolatilityFilterIndicator) "
           "window._updateVolatilityFilterIndicator();" in v_block),
          "no guarded indicator call in the vol restore block")

    vt_block = block_between(apply, "// Volatility x Tenure bracket filter", "// Board independence filter")
    if vt_block is None:
        check("C6 applyHashState restores the vol-tenure bracket", False,
              "vol-tenure restore block not found in applyHashState")
        return 1
    check("C6 applyHashState restores _activeVolTenureBracket from vtmin/vtmax/vtlbl",
          ("state.vtmin" in vt_block and "state.vtmax" in vt_block and "state.vtlbl" in vt_block
           and "parseFloat(state.vtmin)" in vt_block
           and "state.vtmax === 'inf' ? Infinity : parseFloat(state.vtmax)" in vt_block
           and "_activeVolTenureBracket = { min: vtMin, max: vtMax, label: state.vtlbl }" in vt_block),
          "restore block does not build the filter from vtmin/vtmax/vtlbl with parseFloat + 'inf'")
    check("C7 restore calls the vol-tenure indicator updater (guarded)",
          ("window._updateVolTenureFilterIndicator) "
           "window._updateVolTenureFilterIndicator();" in vt_block),
          "no guarded indicator call in the vol-tenure restore block")

    bd_block = block_between(apply, "// Board independence filter", "// Role filter")
    if bd_block is None:
        check("C8 applyHashState restores the board filter", False,
              "board restore block not found in applyHashState")
        return 1
    check("C8 applyHashState restores _activeBoardFilter from board= with mode validation",
          ("state.board" in bd_block
           and "['high', 'mid', 'low']" in bd_block
           and "bdModes.indexOf(state.board) >= 0" in bd_block
           and "_activeBoardFilter = { mode: state.board }" in bd_block),
          "restore block does not build the filter from board= with high/mid/low validation")
    check("C9 restore calls the board indicator updater (guarded)",
          ("window._updateBoardFilterIndicator) "
           "window._updateBoardFilterIndicator();" in bd_block),
          "no guarded indicator call in the board restore block")

    # C10-C11: the hashchange reset block (marker through the
    # applyHashState call inside it).
    marker = "// Listen for browser back/forward"
    start = app.find(marker)
    apply_idx = app.find("applyHashState(companies);", start) if start >= 0 else -1
    hblock = app[start:apply_idx] if start >= 0 and apply_idx > 0 else None
    if hblock is None:
        check("C10 hashchange handler nulls the three filters", False,
              "hashchange reset block not found")
        return 1
    check("C10 hashchange handler nulls the volatility bucket, vol-tenure bracket and board filter",
          ("window._activeVolatilityBucket = null" in hblock
           and "window._activeVolTenureBracket = null" in hblock
           and "window._activeBoardFilter = null" in hblock),
          "one of the three filters is not nulled in the reset block")
    check("C11 hashchange handler removes the three chips + clears af-vol / af-board",
          ("volatility-filter-chip" in hblock
           and "vol-tenure-chip" in hblock
           and "board-filter-chip" in hblock
           and "af-vol" in hblock and "af-board" in hblock),
          "chip removal or AF-select clear missing from the reset block")

    # C12: the init restore block re-applies the vol chart highlight.
    init_start = app.find("applyHashState(companies);\n    _stateInitialized = true;")
    init_end = app.find("// === Table horizontal scroll indicator ===",
                        init_start) if init_start >= 0 else -1
    init_block = app[init_start:init_end] if init_start >= 0 and init_end > 0 else ""
    check("C12 init restore block re-applies the vol chart highlight from the restored state",
          ("window._activeVolatilityBucket && window.highlightVolatilityBucket" in init_block
           and "window.highlightVolatilityBucket(window._activeVolatilityBucket.min, window._activeVolatilityBucket.max)" in init_block),
          "no highlightVolatilityBucket restore in the init block")

    # C13: the hashchange highlight section restores + clears the vol ring.
    handler = extract_function_body(
        app, "window.addEventListener('hashchange', function() {")
    if handler is None:
        check("C13 hashchange handler restores + clears the vol chart highlight", False,
              "hashchange handler not found")
        return 1
    check("C13 hashchange handler restores + clears the vol chart highlight",
          ("highlightVolatilityBucket(window._activeVolatilityBucket.min, window._activeVolatilityBucket.max)" in handler
           and "highlightVolatilityBucket(null, null)" in handler),
          "no highlightVolatilityBucket restore/clear in the hashchange handler")
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
                    # pass vacuously on the pre-reload state (probe:
                    # window.__probe survives goto(same hash URL) but
                    # not goto(same bare URL) or reload()). Force a
                    # real reload for the round trip.
                    pg.reload(timeout=60000)
                else:
                    pg.goto(url or "http://127.0.0.1:%d/index.html" % port,
                            timeout=60000)
                # Render done when the skeleton rows are gone -- a
                # plain row selector would never match an empty table
                # (a zero-row reload has no rows at all).
                pg.wait_for_function(
                    "() => !document.querySelector("
                    "'#comp-tbody .skeleton-table-row-tr')",
                    timeout=30000)
                pg.wait_for_timeout(800)

            def chip_text(chip_id):
                return pg.evaluate("""(id) => {
                    const c = document.getElementById(id);
                    return c ? c.textContent : null;
                }""", chip_id)

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

            def hash_keys():
                h = pg.evaluate("() => window.location.hash")
                return (h, set(p.split('=')[0] for p in h.lstrip('#').split('&') if p))

            # R1: vol bucket (0-5%) + Information Technology sector.
            # State + updater is the same code path as the histogram
            # bar click (409th review's R1 precedent); filterBySector
            # re-runs the updaters and renderTable's pushState carries
            # the new hash keys.
            load()
            pg.evaluate("""() => {
                window._activeVolatilityBucket = { min: 0, max: 5, label: '0\u20135%' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateVolatilityFilterIndicator()")
            pg.wait_for_timeout(1200)
            h1, h1_keys = hash_keys()
            chip1 = chip_text("volatility-filter-chip")
            badge1 = badge_text()
            n1 = footer_count()
            r1_pre = (("vmin" in h1_keys and "vmax" in h1_keys and "vlbl" in h1_keys
                       and "vmin=0" in h1 and "vmax=5" in h1)
                      and chip1 is not None
                      and "Information Technology \u00d7 Volatility 0\u20135%" in chip1
                      and badge1 is not None and "Volatility: 0\u20135%" in badge1
                      and n1 >= 1)
            check("R1 live set: hash carries vmin/vmax/vlbl, combined chip + badge, footer >= 1 "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h1, chip1, badge1, n1),
                  r1_pre,
                  "want vmin=0/vmax=5/vlbl in the hash, combined chip, badge, footer >= 1")

            # Reload with the captured hash: the deep link must
            # restore the filter, chip, badge, footer and announce,
            # and keep min/max/label.
            url1 = pg.url
            load(url1)
            chip2 = chip_text("volatility-filter-chip")
            badge2 = badge_text()
            n2 = footer_count()
            a2 = last_announce()
            f2 = pg.evaluate("() => window._activeVolatilityBucket || null")
            r1_ok = (r1_pre
                     and chip2 is not None
                     and "Information Technology \u00d7 Volatility 0\u20135%" in chip2
                     and badge2 is not None and "Volatility: 0\u20135%" in badge2
                     and n2 == n1
                     and f2 is not None and f2.get("min") == 0
                     and f2.get("max") == 5 and f2.get("label") == "0\u20135%"
                     and "volatility: 0\u20135%" in a2)
            check("R1 reload with the hash restores chip + badge + footer + min/max/label + announce "
                  "(chip=%r badge=%r footer=%s filter=%r announce=%r)" % (chip2, badge2, n2, f2, a2),
                  r1_ok,
                  "want combined chip, badge, same footer, min 0 / max 5 / label, 'volatility: ...' in the announce")

            # R2: vol-tenure bracket (Veterans, 20+ yrs, max Infinity)
            # + Information Technology sector (the combined badge
            # only renders when filterDims >= 2, so a lone bracket
            # has no badge to check -- the sector supplies the
            # second dim, as in R1).
            load()
            pg.evaluate("""() => {
                window._activeVolTenureBracket = { min: 20, max: Infinity, label: 'Veterans (20+ yrs)' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateVolTenureFilterIndicator()")
            pg.wait_for_timeout(1200)
            h2, h2_keys = hash_keys()
            chip_v = chip_text("vol-tenure-chip")
            badge_v = badge_text()
            n_v = footer_count()
            r2_pre = (("vtmin" in h2_keys and "vtmax" in h2_keys and "vtlbl" in h2_keys
                       and "vtmin=20" in h2 and "vtmax=inf" in h2)
                      and chip_v is not None
                      and "Information Technology \u00d7 Volatility \u00d7 Tenure: Veterans (20+ yrs)" in chip_v
                      and badge_v is not None
                      and "Volatility \u00d7 Tenure: Veterans (20+ yrs)" in badge_v)
            check("R2 live set: hash carries vtmin=20/vtmax=inf/vtlbl, combined chip + badge "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h2, chip_v, badge_v, n_v),
                  r2_pre,
                  "want vtmin=20/vtmax=inf/vtlbl in the hash, combined chip, badge")
            url2 = pg.url
            load(url2)
            chip_v2 = chip_text("vol-tenure-chip")
            badge_v2 = badge_text()
            n_v2 = footer_count()
            f_v2 = pg.evaluate("() => window._activeVolTenureBracket || null")
            max_inf = pg.evaluate("() => window._activeVolTenureBracket && window._activeVolTenureBracket.max === Infinity")
            r2_ok = (r2_pre
                     and chip_v2 is not None
                     and "Information Technology \u00d7 Volatility \u00d7 Tenure: Veterans (20+ yrs)" in chip_v2
                     and badge_v2 is not None
                     and "Volatility \u00d7 Tenure: Veterans (20+ yrs)" in badge_v2
                     and n_v2 == n_v
                     and f_v2 is not None and f_v2.get("min") == 20
                     and f_v2.get("label") == "Veterans (20+ yrs)"
                     and max_inf is True)
            check("R2 reload with the hash restores chip + badge + footer + min/label + max Infinity "
                  "(chip=%r badge=%r footer=%s filter=%r max_inf=%r)" % (chip_v2, badge_v2, n_v2, f_v2, max_inf),
                  r2_ok,
                  "want chip, badge, same footer, min 20 / label, max === Infinity")

            # R3: board filter (low) + Information Technology sector
            # (the combined badge only renders when filterDims >= 2,
            # so a lone board filter has no badge to check -- the
            # sector supplies the second dim, as in R1/R2).
            load()
            pg.evaluate("""() => {
                window._activeBoardFilter = { mode: 'low' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateBoardFilterIndicator()")
            pg.wait_for_timeout(1200)
            h3, h3_keys = hash_keys()
            chip_b = chip_text("board-filter-chip")
            badge_b = badge_text()
            n_b = footer_count()
            r3_pre = (("board" in h3_keys and "board=low" in h3)
                      and chip_b is not None
                      and "Information Technology \u00d7 Board <60%" in chip_b
                      and badge_b is not None and "Board <60%" in badge_b)
            check("R3 live set: hash carries board=low, combined chip + badge "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h3, chip_b, badge_b, n_b),
                  r3_pre,
                  "want board=low in the hash, combined 'Board <60%' chip + badge")
            url3 = pg.url
            load(url3)
            chip_b2 = chip_text("board-filter-chip")
            badge_b2 = badge_text()
            n_b2 = footer_count()
            f_b2 = pg.evaluate("() => window._activeBoardFilter || null")
            r3_ok = (r3_pre
                     and chip_b2 is not None
                     and "Information Technology \u00d7 Board <60%" in chip_b2
                     and badge_b2 is not None and "Board <60%" in badge_b2
                     and n_b2 == n_b
                     and f_b2 is not None and f_b2.get("mode") == "low")
            check("R3 reload with the hash restores chip + badge + footer + mode "
                  "(chip=%r badge=%r footer=%s filter=%r)" % (chip_b2, badge_b2, n_b2, f_b2),
                  r3_ok,
                  "want 'Board <60%' chip + badge, same footer, mode low")

            # R4: all three filters set, then clear the hash
            # (hashchange): chips gone, footer back to 518, all
            # three states null.
            load()
            pg.evaluate("""() => {
                window._activeVolatilityBucket = { min: 0, max: 5, label: '0\u20135%' };
                window._activeVolTenureBracket = { min: 20, max: Infinity, label: 'Veterans (20+ yrs)' };
                window._activeBoardFilter = { mode: 'low' };
                window._updateVolatilityFilterIndicator();
                window._updateVolTenureFilterIndicator();
                window._updateBoardFilterIndicator();
                if (window.compData) renderTable(compData.companies);
            }""")
            pg.wait_for_timeout(1200)
            chips_before = [chip_text(c) for c in
                            ("volatility-filter-chip", "vol-tenure-chip", "board-filter-chip")]
            pg.evaluate("() => { window.location.hash = ''; }")
            pg.wait_for_timeout(1200)
            chips_after = [chip_text(c) for c in
                           ("volatility-filter-chip", "vol-tenure-chip", "board-filter-chip")]
            n4 = footer_count()
            f4 = pg.evaluate("""() => ({
                vol: window._activeVolatilityBucket || null,
                vt: window._activeVolTenureBracket || null,
                board: window._activeBoardFilter || null
            })""")
            r4_ok = (all(c is not None for c in chips_before)
                     and all(c is None for c in chips_after)
                     and n4 == 518
                     and f4.get("vol") is None and f4.get("vt") is None
                     and f4.get("board") is None)
            check("R4 hash cleared: all three chips gone, footer 518, all three states null "
                  "(before=%r after=%r footer=%s states=%r)" % (chips_before, chips_after, n4, f4),
                  r4_ok,
                  "want 3 chips before, none after, footer 518, all states null")

            r5_ok = len(errors) == 0
            check("R5 zero page errors across the render half",
                  r5_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok and r3_ok and r4_ok and r5_ok
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
