#!/usr/bin/env python3
"""Guard: the peer-dist filter keeps a persistent home above the table (374th review).

Background (374th review, 2026-11-07): closes the 373rd run's
candidate (4). The Peer Pay Distribution histogram lives inside a
company detail row, so closing that row (close button, Escape, or a
back/forward navigation that drops detail=) left the peer-dist chip
plus the filtered table with no visible source -- and the bucket
label is only a pay range, built from the source company's own peer
group, so the label alone cannot reconstruct the histogram. The fix
records the source ticker when a bucket is clicked, serializes it as
pdsrc= next to pdtk=/pdlbl=, restores it in applyHashState, and
renders a strip above the table that rebuilds the source company's
histogram (same peer list, same bucket math as the detail renderer)
with the active bucket ringed. The strip hides while the source
company's own detail panel is open (that panel already shows its
histogram) and degrades to nothing for old links without a source.
Strip columns switch the filter with the same toggle semantics, plus
Enter/Space. Every path that nulls the filter also empties the strip
(chip dismiss and insight reset via the indicator hook; Reset All,
hashchange-clear, and Escape filter-clear explicitly).

Checks (all static - small JS/CSS/HTML reads, <2s):
 C1 HARD FAIL: updatePeerDistStrip is not defined, or not exposed on window.
 C2 HARD FAIL: index.html has no peer-dist-strip container above the table.
 C3 HARD FAIL: the detail peer-dist click handler does not record the
    source ticker in the filter state.
 C4 HARD FAIL: serializeState does not emit pdsrc=, or applyHashState
    does not restore the source from state.pdsrc.
 C5 HARD FAIL: the peer-dist indicator does not refresh the strip, so a
    set/clear via chip or hash restore would leave the strip stale.
 C6 HARD FAIL: the strip does not hide while the source company's detail
    panel is open (it would duplicate that panel's histogram).
 C7 HARD FAIL: the strip does not rebuild from the source company's peer
    info with the detail renderer's bucket math.
 C8 HARD FAIL: strip columns are not clickable with the same toggle
    semantics, have no Enter/Space keyboard path, or leave empty
    (inert) columns in the tab order -- the detail panel's keyboard
    pilot excludes empty peer-dist columns.
 C9 HARD FAIL: resetAllFilters does not empty the strip container.
C10 HARD FAIL: the hashchange-clear path does not empty the strip container.
C11 HARD FAIL: the Escape filter-clear branch does not empty the strip container.
C12 HARD FAIL: the detail-open, detail-close-button, or Escape panel-close
    path does not refresh the strip (visibility would go stale).
C13 HARD FAIL: the strip CSS rule is missing.
C14 HARD FAIL: node --check fails on js/app.js.
C15 HARD FAIL: renderTable does not refresh the strip -- it wipes the
    tbody (killing the open detail panel) on every filter/sort/page
    change, so a bucket click would leave the filter with no visible
    histogram until some other path happened to refresh it.
C16 HARD FAIL: a filter-setting click handler does not null the expanded
    detail ticker (and diff key) before its renderTable -- the tbody
    wipe destroys the open panel, so the hash would keep detail= for a
    panel that no longer exists, and a reload would try to re-open it
    against a filtered table that excludes the source (the search trick
    then yields zero rows). Same pair-null invariant as the 371st Reset
    All and 372nd Escape-close fixes; covers the detail peer-dist click,
    the strip's own bucket click, and filterTableByTickers (crosstab).

Usage:
  scripts/check_peer_dist_strip.py
  scripts/check_peer_dist_strip.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import subprocess
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"
STYLE_CSS = f"{REPO}/css/style.css"
INDEX_HTML = f"{REPO}/index.html"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner


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


def main():
    try:
        app = open(APP_JS, encoding="utf-8").read()
        css = open(STYLE_CSS, encoding="utf-8").read()
        html = open(INDEX_HTML, encoding="utf-8").read()
    except OSError as exc:
        print(f"INFRA: cannot read JS/CSS/HTML sources: {exc}")
        return 2

    failures = []

    # --- C1: the strip function exists and is exposed ------------------
    strip_fn = extract_function_body(app, "function updatePeerDistStrip()")
    if strip_fn is None:
        failures.append("C1 updatePeerDistStrip is not defined in "
                        "js/app.js -- the peer-dist filter has no "
                        "persistent home outside the detail panel")
    if "window.updatePeerDistStrip = updatePeerDistStrip;" not in app:
        failures.append("C1 updatePeerDistStrip is not exposed on window "
                        "-- the detail open/close paths cannot refresh it")

    # --- C2: the container exists in the page --------------------------
    if '<div id="peer-dist-strip"></div>' not in html:
        failures.append("C2 index.html has no peer-dist-strip container -- "
                        "the strip has nowhere to render above the table")
    else:
        summary_pos = html.find('id="table-summary-bar"')
        strip_pos = html.find('id="peer-dist-strip"')
        wrapper_pos = html.find('id="table-wrapper"')
        if not (0 <= summary_pos < strip_pos < wrapper_pos):
            failures.append("C2 peer-dist-strip is not between the "
                            "table-summary-bar and the table-wrapper -- "
                            "it would render in the wrong place")

    # --- C3: the click handler records the source ----------------------
    # The detail click handler is the only place the filter is set from
    # a histogram; search the whole file for the state literal (the
    # handler lives inside setupDetailPanel, not a named function).
    if "label: label, source: ticker" not in app:
        failures.append("C3 the detail peer-dist click handler does not "
                        "record the source ticker in _activePeerDistFilter "
                        "-- the strip cannot rebuild the histogram")

    # --- C4: hash round trip for the source ----------------------------
    ser = extract_function_body(app, "function serializeState()")
    if ser is None:
        failures.append("C4 serializeState not found in js/app.js")
    elif "pdsrc=" not in ser:
        failures.append("C4 serializeState does not emit pdsrc= -- a "
                        "restored peer-dist filter shows no source histogram")
    ahs = extract_function_body(app, "function applyHashState(companies)")
    if ahs is None:
        failures.append("C4 applyHashState not found in js/app.js")
    elif "source: state.pdsrc" not in ahs:
        failures.append("C4 applyHashState does not restore the source "
                        "from state.pdsrc -- the hash round trip drops the "
                        "strip identity")

    # --- C5: the indicator refreshes the strip -------------------------
    ind = extract_function_body(
        app, "function updatePeerDistFilterIndicator()")
    if ind is None:
        failures.append("C5 updatePeerDistFilterIndicator not found in "
                        "js/app.js")
    elif "updatePeerDistStrip()" not in ind:
        failures.append("C5 the peer-dist indicator does not refresh the "
                        "strip -- a filter set or cleared via chip or hash "
                        "restore would leave the strip stale")

    # --- C6/C7/C8: strip body behavior ----------------------------------
    if strip_fn is not None:
        if "document.querySelector('#comp-tbody .detail-row')" not in strip_fn:
            failures.append("C6 the strip does not check the live DOM for "
                            "an open source panel -- the _expandedDetailTicker "
                            "variable stays set after renderTable wipes the "
                            "tbody, so a variable-only hide would keep the "
                            "strip hidden after the panel is already gone")
        if "getAttribute('data-ticker') === pf.source" not in strip_fn:
            failures.append("C6 the strip does not hide only for the source "
                            "company's open panel -- opening any other "
                            "company's panel would wrongly hide the filter's "
                            "provenance")
        if "getPeerInfo(pf.source)" not in strip_fn:
            failures.append("C7 the strip does not rebuild from the "
                            "source company's peer info -- it cannot show "
                            "the histogram the filter came from")
        if "compData.companies" not in strip_fn and "_chartData.companies" not in strip_fn:
            failures.append("C7 the strip does not resolve the company "
                            "list from compData/_chartData -- companies is "
                            "a parameter, not a global, so a bare reference "
                            "early-returns the strip to nothing")
        if "Math.min(8, Math.max(4, Math.ceil(" not in strip_fn:
            failures.append("C7 the strip does not use the detail "
                            "renderer's bucket-count math -- its buckets "
                            "would not match the source histogram")
        if "data-peer-label" not in strip_fn:
            failures.append("C8 strip columns carry no peer label -- "
                            "clicking one could not switch the filter")
        if "e.key === 'Enter'" not in strip_fn:
            failures.append("C8 strip columns have no Enter/Space "
                            "keyboard path -- the filter switch is "
                            "click-only")
        if "b.tickers.length > 0 ? ' tabindex=\"0\" role=\"button\"'" not in strip_fn:
            failures.append("C8 empty strip columns are not excluded from "
                            "the tab order -- the detail panel's keyboard "
                            "pilot excludes empty peer-dist columns, and a "
                            "focusable dead column would be a keyboard trap")
        if "source: pf.source" not in strip_fn:
            failures.append("C8 the strip's own column click does not "
                            "preserve the source -- switching buckets "
                            "would drop the strip identity")

    # --- C9: resetAllFilters empties the strip --------------------------
    reset_fn = extract_function_body(app, "window.resetAllFilters = function")
    if reset_fn is None:
        failures.append("C9 resetAllFilters not found in js/app.js")
    elif "peer-dist-strip" not in reset_fn or "innerHTML = ''" not in reset_fn:
        failures.append("C9 resetAllFilters does not empty the strip "
                        "container -- Reset All would null the filter "
                        "while the histogram stays on screen")

    # --- C10: hashchange-clear empties the strip ------------------------
    hash_fn = extract_function_body(
        app, "window.addEventListener('hashchange', function()")
    if hash_fn is None:
        failures.append("C10 hashchange handler not found in js/app.js")
    elif "peer-dist-strip" not in hash_fn or "innerHTML = ''" not in hash_fn:
        failures.append("C10 the hashchange-clear path does not empty the "
                        "strip container -- a navigation that drops the "
                        "filter would leave the histogram behind")

    # --- C11: Escape filter-clear empties the strip ----------------------
    esc_anchor = app.find("var pdcEsc = document.getElementById('peer-dist-chip');")
    if esc_anchor < 0:
        failures.append("C11 Escape peer-dist clear block not found in "
                        "js/app.js")
    elif "peer-dist-strip" not in app[esc_anchor:esc_anchor + 600]:
        failures.append("C11 the Escape filter-clear branch does not empty "
                        "the strip container -- Escape would null the "
                        "filter while the histogram stays on screen")

    # --- C12: open/close paths refresh the strip ------------------------
    open_anchor = app.find("// Track expanded detail for URL hash deep-linking")
    if open_anchor < 0:
        failures.append("C12 detail-open anchor not found in js/app.js")
    elif "updatePeerDistStrip()" not in app[open_anchor:open_anchor + 500]:
        failures.append("C12 the detail-open path does not refresh the "
                        "strip -- opening the source panel would leave "
                        "its histogram duplicated above the table")
    close_anchor = app.find("pushState();\n            // 374th review: the panel just closed")
    if close_anchor < 0:
        # Fall back to the Escape panel-close anchor (same refresh line).
        close_anchor = app.find("pushState();\n                // 374th review: same strip-reveal")
    if close_anchor < 0:
        failures.append("C12 detail-close refresh anchor not found in "
                        "js/app.js")
    elif "updatePeerDistStrip()" not in app[close_anchor:close_anchor + 500]:
        failures.append("C12 the detail-close path does not refresh the "
                        "strip -- closing the source panel would leave "
                        "the filter with no visible histogram")

    # --- C13: the CSS rule ----------------------------------------------
    if "#peer-dist-strip" not in css:
        failures.append("C13 peer-dist-strip rule missing from "
                        "css/style.css -- the strip has no visual "
                        "separation from the table")

    # --- C14: syntax -----------------------------------------------------
    try:
        chk = subprocess.run(["node", "--check", APP_JS],
                             capture_output=True, text=True, timeout=30)
        if chk.returncode != 0:
            failures.append("C14 node --check fails on js/app.js: "
                            + (chk.stderr or chk.stdout).strip()[:200])
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"INFRA: node --check unavailable: {exc}")
        return 2

    # --- C15: renderTable refreshes the strip ---------------------------
    rt_fn = extract_function_body(app, "function renderTable(companies, options)")
    if rt_fn is None:
        failures.append("C15 renderTable not found in js/app.js")
    elif "updatePeerDistStrip()" not in rt_fn:
        failures.append("C15 renderTable does not refresh the strip -- "
                        "its tbody wipe kills the open detail panel on "
                        "every filter/sort/page change, so a bucket click "
                        "would leave the filter with no visible histogram")

    # --- C16: filter-setting clicks null the dead panel ------------------
    # Detail peer-dist click handler: the state literal is unique.
    det_anchor = app.find("label: label, source: ticker };")
    if det_anchor < 0:
        failures.append("C16 detail peer-dist click handler not found in "
                        "js/app.js")
    elif "_expandedDetailTicker = null;" not in app[det_anchor:det_anchor + 1200]:
        failures.append("C16 the detail peer-dist click handler does not "
                        "null the expanded detail ticker before its "
                        "renderTable -- the tbody wipe destroys the panel "
                        "while the hash keeps detail= for it")
    # Strip's own bucket click: inside the strip function body.
    if strip_fn is not None and "_expandedDetailTicker = null;" not in strip_fn:
        failures.append("C16 the strip's bucket click does not null the "
                        "expanded detail ticker -- its renderTable wipes "
                        "any open detail panel while the hash keeps detail=")
    # Crosstab: same stale-detail class in filterTableByTickers.
    ftt = extract_function_body(app, "window.filterTableByTickers = function")
    if ftt is None:
        failures.append("C16 filterTableByTickers not found in js/app.js")
    elif "_expandedDetailTicker = null;" not in ftt:
        failures.append("C16 filterTableByTickers does not null the "
                        "expanded detail ticker -- its renderTable wipes "
                        "any open detail panel while the hash keeps detail=")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: peer-dist-strip: strip function defined and exposed, "
          "container above the table, click handler records the source, "
          "hash round-trips pdsrc, indicator refreshes the strip, strip "
          "hides while the source panel is open in the live DOM, rebuilds "
          "from the source peer group with matching buckets, columns switch "
          "the filter by click and keyboard (empty columns out of tab "
          "order), and Reset All / hashchange / Escape all empty it; "
          "open/close paths refresh it, renderTable refreshes it after "
          "every tbody wipe, and all three filter-setting click paths null "
          "the dead detail panel so the hash stays truthful")
    return 0


if __name__ == "__main__":
    sys.exit(main())
