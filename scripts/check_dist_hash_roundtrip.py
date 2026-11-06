#!/usr/bin/env python3
"""Guard: non-sector dist filter must survive the hash round trip.

Background (365th review, 2026-11-06): a chart-bracket click
(filterByCompBracket) or an AF pay band sets _activeDistFilter with
sector:null, and serializeState writes dsec as an empty value. The
applyHashState restore gated on a truthy dsec, so a non-sector dist
filter was dropped on reload and on back/forward navigation: the table
unfiltered with no chip and no ring while the URL still carried
dmin/dmax. A sector-scoped dist filter (real sector name in dsec)
round-tripped fine, which is why the gap survived this long. The init
restore block and the hashchange handler already restore the dist chip
and the comp-dist highlight whenever _activeDistFilter is set, so the
restore gate was the only break.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the dist-restore gate in applyHashState does not test
     dsec by key presence (an empty dsec must pass the gate).
  C2 HARD FAIL: the dist-restore gate still tests dsec by truthiness
     (a bare dsec in the condition drops every non-sector filter).
  C3 HARD FAIL: the restored dist filter does not map an empty dsec
     to sector:null (an empty-string sector would break the
     sector-scoped branches that test !sector / === sector).
  C4 HARD FAIL: the restored label falls back to a sector-derived
     string even when dsec is empty (a bare sector suffix renders a
     leading-space "(filtered)" label on hand-made links with no dlbl).
  C5 HARD FAIL: serializeState no longer emits dsec for the dist
     filter (the round trip has no sector carrier at all).
  C6 HARD FAIL: the init restore block does not restore the dist chip
     and the comp-dist highlight when _activeDistFilter is set (the
     gate fix is useless without the chip/ring restore at load).
  C7 HARD FAIL: the hashchange handler does not restore the dist chip
     and highlight when the new hash carries the filter, or does not
     clear the highlight when the new hash drops it (stale-ring class).

Usage:
  scripts/check_dist_hash_roundtrip.py
  scripts/check_dist_hash_roundtrip.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import re
import sys

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = f"{REPO}/js/app.js"

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
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    failures = []

    # --- C1-C4: the dist-restore block inside applyHashState --------
    apply = extract_function_body(app, "function applyHashState(companies)")
    dist_block = ""
    if apply is None:
        failures.append("C1 applyHashState function not found in js/app.js")
    else:
        marker = "// Distribution filter"
        start = apply.find(marker)
        if start < 0:
            failures.append("C1 dist-restore block marker not found inside "
                            "applyHashState")
        else:
            end = apply.find("\n    }\n", start)
            if end < 0:
                failures.append("C1 dist-restore block end not found inside "
                                "applyHashState")
            else:
                dist_block = apply[start:end]
    if dist_block:
        # C1: gate tests dsec by key presence.
        if "state.dsec != null" not in dist_block:
            failures.append("C1 dist-restore gate does not test dsec by key "
                            "presence -- an empty dsec (non-sector bracket "
                            "or AF pay band) fails the gate and the filter "
                            "is dropped on reload / back-forward")
        # C2: no bare truthiness test on dsec in the gate.
        if re.search(r"&&\s*state\.dsec\s*[)\{]", dist_block):
            failures.append("C2 dist-restore gate still tests dsec by "
                            "truthiness -- an empty dsec is falsy, so every "
                            "non-sector dist filter is dropped on restore")
        # C3: empty dsec maps to sector:null.
        if "sector: state.dsec || null" not in dist_block:
            failures.append("C3 restored dist filter does not map an empty "
                            "dsec to sector:null -- an empty-string sector "
                            "breaks the branches that test !sector or "
                            "sector equality")
        # C4: label fallback must not derive from an empty dsec.
        if "state.dlbl || state.dsec + ' (filtered)'" in dist_block:
            failures.append("C4 restored label still falls back to a "
                            "sector-derived string -- with an empty dsec "
                            "and no dlbl that renders a leading-space "
                            "'(filtered)' label")

    # --- C5: serializeState still emits dsec ------------------------
    if ("dsec=' + encodeURIComponent(window._activeDistFilter.sector || '')"
            not in app):
        failures.append("C5 serializeState no longer emits dsec for the "
                        "dist filter -- the round trip has no sector "
                        "carrier, so a restored filter cannot tell "
                        "sector-scoped from non-sector")

    # --- C6: init restore block restores chip + highlight -----------
    init_start = app.find("applyHashState(companies);\n    _stateInitialized = true;")
    if init_start < 0:
        failures.append("C6 init restore anchor (applyHashState + "
                        "_stateInitialized) not found in js/app.js")
    else:
        init_end = app.find("// === CSV Export ===",
                            init_start)
        if init_end < 0:
            failures.append("C6 init restore end marker (CSV Export "
                            "section) not found in js/app.js")
        else:
            init_block = app[init_start:init_end]
            if "updateDistFilterIndicator();" not in init_block:
                failures.append("C6 init restore block does not render the "
                                "dist filter chip when _activeDistFilter is "
                                "set -- a restored filter has no dismiss "
                                "affordance at load")
            if ("highlightCompDistBucket(window._activeDistFilter.min, "
                    "window._activeDistFilter.max)") not in init_block:
                failures.append("C6 init restore block does not ring the "
                                "comp-dist bucket when _activeDistFilter is "
                                "set -- a deep-linked bracket filter leaves "
                                "the chart un-ringed at load")

    # --- C7: hashchange handler restores and clears ------------------
    handler = extract_function_body(
        app, "window.addEventListener('hashchange', function() {")
    if handler is None:
        failures.append("C7 hashchange handler not found in js/app.js")
    else:
        if "updateDistFilterIndicator();" not in handler:
            failures.append("C7 hashchange handler does not restore the "
                            "dist filter chip when the new hash carries the "
                            "filter -- back/forward into a bracket filter "
                            "leaves the chip missing")
        if ("highlightCompDistBucket(window._activeDistFilter.min, "
                "window._activeDistFilter.max)") not in handler:
            failures.append("C7 hashchange handler does not ring the "
                            "comp-dist bucket when the new hash carries the "
                            "filter -- back/forward into a bracket filter "
                            "leaves the chart un-ringed")
        if "window.highlightCompDistBucket(null);" not in handler:
            failures.append("C7 hashchange handler does not clear the "
                            "comp-dist highlight when the new hash drops "
                            "the filter -- the ring lingers with its chip "
                            "already removed")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: dist-hash-roundtrip: applyHashState restores a non-sector "
          "dist filter (empty dsec passes the presence gate and maps to "
          "sector:null, label fallback is dsec-safe); serializeState still "
          "emits dsec; init restore block and hashchange handler restore "
          "the dist chip and comp-dist highlight and clear the ring when "
          "the filter is dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
