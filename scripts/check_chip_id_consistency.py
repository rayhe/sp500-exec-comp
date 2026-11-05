#!/usr/bin/env python3
"""Guard: filter-chip ids removed by reset paths must match created chip ids.

Background (326th review, 2026-11-03): two reset paths cleared filter
state while leaving the corresponding dismissible chip on screen, so the
chip misrepresented an inactive filter as active:
  1. resetAllFilters' removal list named 'stock-pct-chip' and
     'ceo-transition-chip', neither of which any code creates; the real
     ids are 'stockpct-filter-chip' and 'transition-filter-chip'
     (creation sites in js/app.js). Reset All Filters therefore left
     both chips visible with their state cleared.
  2. sortTableByKey (metric-card click path) nulled 16 filters' state
     but removed only 5 chips (ratio/dist/conc/tenure/quartile),
     leaving the sop/transition/team/pctile/stockpct/gender/aspdelta/
     peer-dist/position/crosstab chips stale on screen.
The reference pairing is insightResetAndSort in js/app.js, which removes
exactly the chip for each filter whose state it clears, with the correct
ids throughout.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: resetAllFilters' removal list names an id that no code
     creates and that is not a documented defensive no-op. A plausible
     but uncreated id is the 326th-review bug class: the removal
     silently no-ops (getElementById returns null) while the real chip
     survives.
  C2 HARD FAIL: resetAllFilters' removal list omits a created chip id.
     (344th review: the old board-filter-chip exception is gone --
     resetAllFilters now nulls board state, so it must remove the
     board chip like every other created chip; the chip is
     Advanced-Filters owned but Reset All claims it too.)
  C3 HARD FAIL: sortTableByKey nulls a filter's state without removing
     that filter's chip. Only chips that are actually created somewhere
     are required (community/volatility/vol-tenure states have no chip
     rendered, so their absence from the removal set is not a bug).

Documented defensive no-ops in resetAllFilters' list (kept, not bugs):
  volatility-filter-chip, vol-tenure-chip, community-filter-chip -
  ids for states whose chip is never rendered; the removals no-op.

Usage:
  scripts/check_chip_id_consistency.py              # same checks
  scripts/check_chip_id_consistency.py --static-only # same checks

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import glob
import re
import sys

REPO = "/home/hatch/repos/sp500-exec-comp"
APP_JS = f"{REPO}/js/app.js"

if "--static-only" in sys.argv:
    pass  # static half is the whole check; flag accepted for the hook runner

# State variable -> dismissible chip id, per the insightResetAndSort pairing.
STATE_TO_CHIP = {
    "_activeRatioBucket": "ratio-filter-chip",
    "_activeDistFilter": "dist-filter-chip",
    "_activePeerDistFilter": "peer-dist-chip",
    "_activeConcTier": "conc-filter-chip",
    "_activeSopFilter": "sop-filter-chip",
    "_activeCeoTransitionFilter": "transition-filter-chip",
    "_activeTeamCompletenessFilter": "team-filter-chip",
    "_activeYoYBucket": "yoy-filter-chip",
    "_activePctileTier": "pctile-filter-chip",
    "_activeStockPctTier": "stockpct-filter-chip",
    "_activeGenderFilter": "gender-filter-chip",
    "_activeAspDeltaTier": "aspdelta-filter-chip",
    "_activeTenureQuartile": "tenure-filter-chip",
    "_activeGovGrade": "gov-filter-chip",
    "_activeVolatilityBucket": "volatility-filter-chip",
    "_activeVolTenureBracket": "vol-tenure-chip",
    "_activeCommunityFilter": "community-filter-chip",
    "_activeQuartileFilter": "quartile-filter-chip",
    "_activePositionFilter": "position-filter-chip",
    "_activeCrosstabFilter": "crosstab-filter-chip",
}

# No created-chip exception remains: since the 344th review
# resetAllFilters nulls board state and removes board-filter-chip,
# so the old AF-owned carve-out is deleted rather than kept stale.
# Defensive no-ops tolerated in resetAllFilters' list for C1.
C1_DEFENSIVE = {"volatility-filter-chip", "vol-tenure-chip",
                "community-filter-chip"}


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
        js_files = sorted(glob.glob(f"{REPO}/js/*.js"))
        sources = {f: open(f, encoding="utf-8").read() for f in js_files}
        app = sources[APP_JS]
    except OSError as exc:
        print(f"INFRA: cannot read JS sources: {exc}")
        return 2

    # Every chip id ever assigned: chip.id = '...-chip'.
    created = set()
    for src in sources.values():
        for m in re.finditer(r"\.id\s*=\s*'([^']+-chip)'", src):
            created.add(m.group(1))

    failures = []

    # --- resetAllFilters -------------------------------------------------
    reset_body = extract_function_body(app, "window.resetAllFilters = function")
    if reset_body is None:
        print("FAIL: resetAllFilters function not found in js/app.js")
        return 1
    m = re.search(r"Clear filter chips\s*\n\s*\[([\s\S]*?)\]", reset_body)
    if not m:
        print("FAIL: resetAllFilters chip-removal list not found")
        return 1
    reset_removed = set(re.findall(r"'([a-z0-9-]+-chip)'", m.group(1)))

    # C1: no phantom ids beyond the documented defensive no-ops.
    phantom = sorted(reset_removed - created - C1_DEFENSIVE)
    if phantom:
        failures.append(
            "C1 phantom resetAllFilters ids (created nowhere, removal "
            f"no-ops while the real chip survives): {phantom}")

    # C2: every created chip must be removed.
    missing = sorted(created - reset_removed)
    if missing:
        failures.append(
            "C2 resetAllFilters omits created chips (state cleared, chip "
            f"left stale): {missing}")

    # --- sortTableByKey --------------------------------------------------
    sort_body = extract_function_body(app, "function sortTableByKey")
    if sort_body is None:
        print("FAIL: sortTableByKey function not found in js/app.js")
        return 1
    # Removals may be getElementById calls or an array-literal loop
    # (sortTableByKey removes via a forEach over an id list).
    sort_removed = set(re.findall(
        r"getElementById\('([a-z0-9-]+-chip)'\)", sort_body))
    sort_removed |= set(re.findall(r"'([a-z0-9-]+-chip)'", sort_body))
    cleared_states = set(re.findall(
        r"window\.(_active\w+)\s*=\s*(?:null|false)", sort_body))
    # C3: each cleared state whose chip exists must have its chip removed.
    stale = sorted(
        STATE_TO_CHIP[s] for s in cleared_states
        if s in STATE_TO_CHIP and STATE_TO_CHIP[s] in created
        and STATE_TO_CHIP[s] not in sort_removed)
    if stale:
        failures.append(
            "C3 sortTableByKey clears state but leaves chips stale: "
            f"{stale}")

    # --- insightResetAndSort ---------------------------------------------
    # C4 HARD FAIL (327th review): same pairing rule as C3, applied to the
    # insight-card reset path. Before the 327th fix this path nulled
    # _activeVolatilityBucket / _activeVolTenureBracket without removing
    # their chips -- invisible while the chips did not exist, a live stale
    # chip once the 327th indicators created them. An indicator call counts
    # as removal (the indicator removes the chip when state is null).
    ins_body = extract_function_body(app, "function insightResetAndSort")
    if ins_body is None:
        print("FAIL: insightResetAndSort function not found in js/app.js")
        return 1
    ins_removed = set(re.findall(
        r"getElementById\('([a-z0-9-]+-chip)'\)", ins_body))
    ins_removed |= set(re.findall(r"'([a-z0-9-]+-chip)'", ins_body))
    ins_indicators = set(re.findall(
        r"(update\w+FilterIndicator)\(\)", ins_body))
    STATE_TO_INDICATOR = {
        "_activePeerDistFilter": "updatePeerDistFilterIndicator",
        "_activeVolatilityBucket": "updateVolatilityFilterIndicator",
        "_activeVolTenureBracket": "updateVolTenureFilterIndicator",
        "_activeCrosstabFilter": "updateCrosstabFilterIndicator",
    }
    ins_cleared = set(re.findall(
        r"window\.(_active\w+)\s*=\s*(?:null|false)", ins_body))
    ins_stale = sorted(
        STATE_TO_CHIP[s] for s in ins_cleared
        if s in STATE_TO_CHIP and STATE_TO_CHIP[s] in created
        and STATE_TO_CHIP[s] not in ins_removed
        and STATE_TO_INDICATOR.get(s) not in ins_indicators)
    if ins_stale:
        failures.append(
            "C4 insightResetAndSort clears state but leaves chips stale: "
            f"{ins_stale}")

    if failures:
        for f in failures:
            print("FAIL: chip-id-consistency: " + f)
        return 1
    print(f"PASS: chip-id-consistency: {len(created)} created chips; "
          f"resetAllFilters removes {len(reset_removed)}; "
          f"sortTableByKey removes {len(sort_removed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
