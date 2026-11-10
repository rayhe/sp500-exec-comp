#!/usr/bin/env python3
"""Guard: quartile filter must survive the hash round trip.

Background (411th review, 2026-11-10): closes the 410th run's candidate
(2). The quartile filter was the last ticker-list filter with no hash
carrier: serializeState wrote nothing for it, so a shared link into a
quartile-filtered view dropped the filter on load (table unfiltered,
no chip, no badge) while the URL described nothing, and a back/forward
navigation could not drop it either (it was session-local by design).
The fix mirrors the position carrier: qtk (comma-joined tickers) +
qlbl (label) + qcid (Louvain id) + qlo + qhi (the composite toggle
key -- communityId + _lo + _hi -- is what the zone-click toggle
compares, so a restored filter without it would re-set instead of
clearing on a second click of the same zone). applyHashState restores
the filter + chip + zone marking; the hashchange handler nulls it
like every other serialized dim; the zone build marks the active
quartile at build time (the metrics panel re-renders on community-
mode toggle and column sort, which rebuilds the zone HTML from
scratch -- without build-time marking a restored filter would keep
filtering with no zone marked clicked after a re-render). The gate
is the label, not the ticker list: an empty zone filter (no company
total in range) has zero tickers and must still restore its chip +
empty table. No scatter redraw: the scatter never reads the quartile
filter.

Checks (static - file reads, <2s):
  C1  HARD FAIL: serializeState does not emit qtk for the quartile
      filter (no ticker carrier -- the round trip has no filter).
  C2  HARD FAIL: serializeState does not emit qlbl for the quartile
      filter (the chip/badge/announce render from the label).
  C3  HARD FAIL: serializeState does not emit qcid when the filter
      carries a communityId (the toggle compares it).
  C4  HARD FAIL: serializeState does not emit qlo when the filter
      carries _lo (the toggle compares communityId + _lo + _hi).
  C5  HARD FAIL: serializeState does not emit qhi when the filter
      carries _hi.
  C6  HARD FAIL: applyHashState does not restore _activeQuartileFilter
      from qtk/qlbl, gated on the label (an empty filter must
      restore -- gating on the ticker list would drop it).
  C7  HARD FAIL: the restore does not parse qcid into communityId.
  C8  HARD FAIL: the restore does not parse qlo/qhi into _lo/_hi
      (parseFloat -- the toggle compares doubles).
  C9  HARD FAIL: the restore does not call the quartile indicator
      updater (guarded) -- a deep link would filter the table with
      no dismiss chip.
  C10 HARD FAIL: the restore does not re-mark the zone for the
      restored quartile (guarded query by data-bp-cid + numeric
      lo/hi match, adds cm-bp-zone-clicked).
  C11 HARD FAIL: the hashchange handler does not null
      _activeQuartileFilter (also pinned by
      check_hashchange_reset_completeness C2, which derives the
      serialized set from serializeState).
  C12 HARD FAIL: the hashchange handler does not remove the
      quartile-filter-chip (also pinned by the reset-completeness
      guard's C3) or does not clear .cm-bp-zone-clicked on a dropped
      filter.
  C13 HARD FAIL: the community-metrics zone build does not mark the
      active quartile's zone at build time (a re-render after
      restore would drop the marking).

Render (headless Chromium, d3 shimmed from the local cache):
  R1  Set a quartile filter + Information Technology sector on the
      live page (state + updater, the same code path as the zone
      click), using a REAL zone's cid/lo/hi read from the DOM after
      enabling community mode. Read the hash, reload with it: chip
      reads 'Information Technology x Test Quartile (3)', badge
      carries the label, footer 3, announce names the quartile, and
      the restored filter keeps communityId/_lo/_hi; enabling
      community mode after the reload marks the zone clicked
      (build-time marking). Pre-fix: the hash carried no qtk, so
      the reload unfiltered with no chip. (load() reloads -- goto()
      to the identical hash URL is a same-document no-op in
      Chromium, so a plain goto would pass the reload checks
      vacuously on the pre-reload state.)
  R2  Same round trip for an EMPTY quartile filter (no company total
      in range): chip + badge carry the label with ' (0)', footer 0,
      and the reload restores the empty filter (tickers []).
      Pre-fix: the empty filter was session-local too.
  R3  Clear the hash on the reloaded page (hashchange): chip gone,
      badge gone, footer back to 518, _activeQuartileFilter null,
      and no zone stays marked clicked after community mode is
      re-enabled. Pre-fix: the filter was session-local, so
      clearing the hash left it filtering with no URL behind it.
  R4  zero page errors across the render half.

Usage:
  scripts/check_quartile_hash_roundtrip.py
  scripts/check_quartile_hash_roundtrip.py --static-only

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
        check("C1 serializeState emits qtk", False, "serializeState not found")
        return 1
    check("C1 serializeState emits qtk for the quartile filter",
          "'qtk='" in ser and "_activeQuartileFilter" in ser,
          "no qtk push in serializeState")
    check("C2 serializeState emits qlbl for the quartile filter",
          "'qlbl='" in ser,
          "no qlbl push in serializeState")
    check("C3 serializeState emits qcid when the filter carries a communityId",
          "'qcid='" in ser and ".communityId != null" in ser,
          "no guarded qcid push in serializeState")
    check("C4 serializeState emits qlo when the filter carries _lo",
          "'qlo='" in ser and "._lo != null" in ser,
          "no guarded qlo push in serializeState")
    check("C5 serializeState emits qhi when the filter carries _hi",
          "'qhi='" in ser and "._hi != null" in ser,
          "no guarded qhi push in serializeState")

    apply = extract_function_body(app, "function applyHashState(companies)")
    if apply is None:
        check("C6 applyHashState restores the quartile filter", False,
              "applyHashState not found")
        return 1
    q_block = block_between(apply, "// Quartile filter", "// Role filter")
    if q_block is None:
        check("C6 applyHashState restores the quartile filter", False,
              "quartile restore block not found in applyHashState")
        return 1
    check("C6 applyHashState restores _activeQuartileFilter from qtk/qlbl, gated on the label",
          ("state.qlbl" in q_block
           and "_activeQuartileFilter = { tickers: qTickers" in q_block
           and "if (state.qlbl)" in q_block),
          "restore block does not build the filter from qtk/qlbl gated on the label")
    check("C7 restore parses qcid into communityId",
          ("parseInt(state.qcid, 10)" in q_block
           and "communityId: isNaN(qCid) ? null : qCid" in q_block),
          "no parseInt(qcid) communityId assignment in the restore block")
    check("C8 restore parses qlo/qhi into _lo/_hi",
          ("parseFloat(state.qlo)" in q_block
           and "parseFloat(state.qhi)" in q_block
           and "_lo: isNaN(qLo) ? null : qLo" in q_block
           and "_hi: isNaN(qHi) ? null : qHi" in q_block),
          "no parseFloat(qlo/qhi) _lo/_hi assignment in the restore block")
    check("C9 restore calls the quartile indicator updater (guarded)",
          ("window._updateQuartileFilterIndicator) "
           "window._updateQuartileFilterIndicator();" in q_block),
          "no guarded indicator call in the restore block")
    check("C10 restore re-marks the zone for the restored quartile",
          (".cm-bp-zone[data-bp-cid=\"" in q_block
           and "parseFloat(z.dataset.bpLo) === qLo" in q_block
           and "parseFloat(z.dataset.bpHi) === qHi" in q_block
           and "cm-bp-zone-clicked" in q_block),
          "no guarded zone re-mark in the restore block")

    # C11-C12: the hashchange reset block (marker through the
    # applyHashState call inside it).
    marker = "// Listen for browser back/forward"
    start = app.find(marker)
    apply_idx = app.find("applyHashState(companies);", start) if start >= 0 else -1
    hblock = app[start:apply_idx] if start >= 0 and apply_idx > 0 else None
    if hblock is None:
        check("C11 hashchange handler nulls the quartile filter", False,
              "hashchange reset block not found")
        return 1
    check("C11 hashchange handler nulls the quartile filter",
          "window._activeQuartileFilter = null" in hblock,
          "quartile filter not nulled in the reset block")
    check("C12 hashchange handler removes the chip + clears clicked zones",
          ("quartile-filter-chip" in hblock
           and "cm-bp-zone-clicked" in hblock),
          "chip removal or clicked-zone clear missing from the reset block")

    # C13: the zone build marks the active quartile at build time.
    check("C13 zone build marks the active quartile at build time",
          ("_isActiveQ" in net
           and "window._activeQuartileFilter.communityId === r.id" in net
           and "window._activeQuartileFilter._lo === z.lo" in net
           and "window._activeQuartileFilter._hi === z.hi" in net
           and "cm-bp-zone' + (_isActiveQ ? ' cm-bp-zone-clicked' : '')" in net),
          "no active-quartile marking in the zone build")
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
                # (R2's zero-row reload has no rows at all).
                pg.wait_for_function(
                    "() => !document.querySelector("
                    "'#comp-tbody .skeleton-table-row-tr')",
                    timeout=30000)
                pg.wait_for_timeout(800)

            def chip_text():
                return pg.evaluate("""() => {
                    const c = document.getElementById('quartile-filter-chip');
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
                    "() => window._activeQuartileFilter || null")

            def enable_community_mode():
                pg.evaluate(
                    "() => document.getElementById('community-toggle').click()")
                pg.wait_for_selector(".cm-bp-zone", timeout=30000)
                pg.wait_for_timeout(500)

            def zone_is_clicked(zone):
                return pg.evaluate("""(z) => {
                    const zones = document.querySelectorAll(
                        '.cm-bp-zone[data-bp-cid="' + z.cid + '"]');
                    for (const el of zones) {
                        if (parseFloat(el.dataset.bpLo) === z.lo &&
                            parseFloat(el.dataset.bpHi) === z.hi) {
                            return el.classList.contains('cm-bp-zone-clicked');
                        }
                    }
                    return null;
                }""", zone)

            def clicked_zone_count():
                return pg.evaluate(
                    "() => document.querySelectorAll("
                    "'.cm-bp-zone-clicked').length")

            # R1: quartile filter + Information Technology sector.
            # AAPL/MSFT/NVDA are all Information Technology, so the
            # table keeps 3 rows. State + updater is the same code
            # path as the zone click (409th review's R1 precedent);
            # filterBySector re-runs the updaters and renderTable's
            # pushState carries the new hash keys. The toggle key
            # comes from a REAL zone read from the DOM, so the zone
            # re-mark after reload is verifiable.
            load()
            enable_community_mode()
            zone = pg.evaluate("""() => {
                const z = document.querySelector('.cm-bp-zone');
                return {cid: parseInt(z.dataset.bpCid),
                        lo: parseFloat(z.dataset.bpLo),
                        hi: parseFloat(z.dataset.bpHi)};
            }""")
            pg.evaluate("""(z) => {
                window._activeQuartileFilter = {
                    tickers: ['AAPL', 'MSFT', 'NVDA'],
                    label: 'Test Quartile (3)',
                    communityId: z.cid, _lo: z.lo, _hi: z.hi
                };
            }""", zone)
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateQuartileFilterIndicator()")
            pg.wait_for_timeout(1200)
            h1 = pg.evaluate("() => window.location.hash")
            chip1 = chip_text()
            badge1 = badge_text()
            n1 = footer_count()
            # Hash keys parsed by boundary, not substring: 'tqlbl='
            # (tenure) contains 'qlbl=' as a substring, so a bare
            # 'qlbl=' in h1 would false-pass.
            h1_keys = set(p.split('=')[0] for p in h1.lstrip('#').split('&') if p)
            r1_pre = (("qtk" in h1_keys and "qlbl" in h1_keys
                       and "qcid" in h1_keys and "qlo" in h1_keys
                       and "qhi" in h1_keys
                       and ("qcid=%d" % zone["cid"]) in h1
                       and ("qlo=%s" % zone["lo"]) in h1
                       and ("qhi=%s" % zone["hi"]) in h1)
                      and chip1 is not None
                      and "Information Technology \u00d7 Test Quartile (3)" in chip1
                      and badge1 is not None and "Test Quartile (3)" in badge1
                      and n1 == 3)
            check("R1 live set: hash carries qtk/qlbl/qcid/qlo/qhi, combined chip + badge, footer 3 "
                  "(hash=%r chip=%r badge=%r footer=%s zone=%r)" % (h1, chip1, badge1, n1, zone),
                  r1_pre,
                  "want qtk/qlbl/qcid/qlo/qhi in the hash, combined chip, badge, footer 3")

            # Reload with the captured hash: the deep link must
            # restore the filter, chip, badge, footer and announce,
            # and keep the composite toggle key; enabling community
            # mode must mark the zone clicked (build-time marking).
            url1 = pg.url
            load(url1)
            chip2 = chip_text()
            badge2 = badge_text()
            n2 = footer_count()
            a2 = last_announce()
            f2 = filter_state()
            enable_community_mode()
            z2 = zone_is_clicked(zone)
            r1_ok = (r1_pre
                     and chip2 is not None
                     and "Information Technology \u00d7 Test Quartile (3)" in chip2
                     and badge2 is not None and "Test Quartile (3)" in badge2
                     and n2 == 3
                     and f2 is not None and f2.get("communityId") == zone["cid"]
                     and f2.get("_lo") == zone["lo"] and f2.get("_hi") == zone["hi"]
                     and "quartile: Test Quartile (3)" in a2
                     and z2 is True)
            check("R1 reload with the hash restores chip + badge + footer 3 + toggle key + announce + zone clicked "
                  "(chip=%r badge=%r footer=%s filter=%r announce=%r zone_clicked=%r)" % (chip2, badge2, n2, f2, a2, z2),
                  r1_ok,
                  "want combined chip, badge, footer 3, communityId/_lo/_hi, 'quartile: ...' in the announce, zone clicked")

            # R2: an EMPTY quartile filter (no company total in range)
            # round-trips too: the chip + badge carry the label with
            # ' (0)', the footer is 0, and the reload restores the
            # empty ticker list.
            load()
            pg.evaluate("""(z) => {
                window._activeQuartileFilter = {
                    tickers: [],
                    label: 'Test Quartile (0)',
                    communityId: z.cid, _lo: z.lo, _hi: z.hi
                };
            }""", zone)
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateQuartileFilterIndicator()")
            pg.wait_for_timeout(1200)
            h2 = pg.evaluate("() => window.location.hash")
            chip_e = chip_text()
            badge_e = badge_text()
            n_e = footer_count()
            h2_keys = set(p.split('=')[0] for p in h2.lstrip('#').split('&') if p)
            r2_pre = (("qtk" in h2_keys and "qlbl" in h2_keys)
                      and chip_e is not None
                      and "Test Quartile (0)" in chip_e
                      and badge_e is not None
                      and "Test Quartile (0)" in badge_e
                      and n_e == 0)
            check("R2 live empty set: hash carries qtk=/qlbl, chip + badge carry ' (0)', footer 0 "
                  "(hash=%r chip=%r badge=%r footer=%s)" % (h2, chip_e, badge_e, n_e),
                  r2_pre,
                  "want qtk=/qlbl in the hash, ' (0)' chip + badge, footer 0")
            url2 = pg.url
            load(url2)
            chip_e2 = chip_text()
            badge_e2 = badge_text()
            n_e2 = footer_count()
            f_e2 = filter_state()
            r2_ok = (r2_pre
                     and chip_e2 is not None
                     and "Test Quartile (0)" in chip_e2
                     and badge_e2 is not None
                     and "Test Quartile (0)" in badge_e2
                     and n_e2 == 0
                     and f_e2 is not None and f_e2.get("tickers") == [])
            check("R2 reload with the hash restores the empty filter (chip + badge + footer 0 + tickers []) "
                  "(chip=%r badge=%r footer=%s filter=%r)" % (chip_e2, badge_e2, n_e2, f_e2),
                  r2_ok,
                  "want ' (0)' chip + badge, footer 0, tickers []")

            # R3: clear the hash (hashchange): the filter must drop
            # cleanly -- chip + badge gone, footer back to 518, and
            # no zone stays marked clicked after community mode is
            # re-enabled.
            pg.evaluate("() => { window.location.hash = ''; }")
            pg.wait_for_timeout(1200)
            chip3 = chip_text()
            badge3 = badge_text()
            n3 = footer_count()
            f3 = filter_state()
            enable_community_mode()
            z3 = clicked_zone_count()
            r3_ok = (chip3 is None and badge3 is None and n3 == 518
                     and f3 is None and z3 == 0)
            check("R3 hash cleared: chip + badge gone, footer 518, filter null, 0 zones clicked "
                  "(chip=%r badge=%r footer=%s filter=%r clicked=%s)" % (chip3, badge3, n3, f3, z3),
                  r3_ok,
                  "want no chip, no badge, footer 518, filter null, 0 clicked zones")

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
