#!/usr/bin/env python3
"""Guard: the hashchange handler must reset every hash-serialized filter.

Background (341st review, 2026-11-04): closes the 340th run's candidate
(2) -- the popstate/hashchange path audit. applyHashState is additive:
it only sets a filter when its hash key is present. The hashchange
handler therefore has to reset filter state to defaults BEFORE calling
applyHashState, or a back/forward navigation that drops a filter from
the URL leaves the old filter silently active. Before this fix the
handler nulled only sector/ratio/dist/transition/team/yoy: a dropped
conc filter kept filtering with its chip already removed (a stuck,
invisible filter), and dropped sop/gender/tenure/gov/pctile/stockpct/
aspdelta/peerdist/crosstab/pvponly/role filters kept filtering with
stale chips, toggles, or role chips while the URL no longer described
the view.

The serialized set is derived from serializeState itself, so adding a
new hash-serialized filter without a matching hashchange reset trips
this guard -- update the handler, do not silence the guard.

Deliberately NOT required here (and asserted absent from the AF-select
list, so a future edit cannot silently widen the reset):
  vol / board / community / quartile / position -- NOT hash-serialized,
  so a hash change cannot drop them; they stay session-local by design
  (same reasoning as resetAllFilters keeping _activeBoardFilter).
  _compareSet -- synced separately in the handler's restore block
  (compareSet.length = 0 + hash cmp refill), not nulled in reset.
  _expandedDetailTicker / _activeDiffKey -- already nulled pre-fix.

Checks (all static - small JS reads, <2s):
  C1 HARD FAIL: the hashchange listener block cannot be located
     (marker "// Listen for browser back/forward" through the
     applyHashState(companies) call inside it).
  C2 HARD FAIL: any window._active* state referenced by serializeState
     (minus the _compareSet allowlist) is not assigned null/false in
     the reset block, or activeRole / _isAfGender is not reset. The
     serialized set includes _activeSectionDeepLink (navigation state,
     not a filter, but hash-serialized all the same -- a dropped
     section= must not be re-serialized by the next pushState).
  C3 HARD FAIL: any filter-chip id for a C2 dimension does not appear
     in the reset block (chip removed individually or via the array
     literal). applyHashState's indicator updaters re-create chips
     for filters the new hash carries, so removal here is safe.
  C4 HARD FAIL: the reset block does not call window._clearAfSelects
     with exactly the 6 selects for the nulled AF-mapped dims
     (af-pay-band, af-sop-tier, af-tenure, af-gov, af-gender,
     af-conc) -- the 330th-review panel-sync rule for this path.
     af-vol and af-board must NOT appear (vol/board not nulled here).
  C5 HARD FAIL: the reset block does not re-render the PvP toggle
     off (_updatePvpOnlyToggle) or does not reset the role chips
     (.role-chip active classes + updateRoleColumnHeader).

Usage:
  scripts/check_hashchange_reset_completeness.py
  scripts/check_hashchange_reset_completeness.py --static-only

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

# Filter-chip id per hash-serialized dimension (chip ids as rendered by
# the indicator updaters; conc/ratio/dist/transition/team/yoy chips were
# already removed pre-fix and are included so a regression trips C3).
CHIP_IDS = [
    "ratio-filter-chip", "dist-filter-chip", "conc-filter-chip",
    "sop-filter-chip", "gender-filter-chip", "aspdelta-filter-chip",
    "tenure-filter-chip", "gov-filter-chip", "pctile-filter-chip",
    "stockpct-filter-chip", "peer-dist-chip", "crosstab-filter-chip",
    "transition-filter-chip", "team-filter-chip", "yoy-filter-chip",
]

# AF selects for exactly the AF-mapped dims nulled in the reset block.
EXPECTED_AF_SELECTS = {
    "af-pay-band", "af-sop-tier", "af-tenure", "af-gov",
    "af-gender", "af-conc",
}
FORBIDDEN_AF_SELECTS = {"af-vol", "af-board"}

# window._active* names serializeState references that need no reset.
SERIALIZE_ALLOWLIST = {"_compareSet"}


def fail(msg):
    print(f"FAIL: {msg}")
    return 1


def main():
    try:
        with open(APP_JS, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"INFRA: cannot read {APP_JS}: {e}")
        return 2

    # C1: locate the hashchange reset block.
    marker = "// Listen for browser back/forward"
    start = src.find(marker)
    if start < 0:
        return fail("C1: hashchange listener marker not found")
    apply_idx = src.find("applyHashState(companies);", start)
    if apply_idx < 0:
        return fail("C1: applyHashState call not found inside hashchange listener")
    block = src[start:apply_idx]

    # Serialized window._active* set, derived from serializeState.
    ser_start = src.find("function serializeState()")
    ser_end = src.find("function pushState()", ser_start)
    if ser_start < 0 or ser_end < 0:
        return fail("C1: serializeState body not found")
    serialized = set(re.findall(r"window\.(_active\w+)", src[ser_start:ser_end]))
    serialized -= SERIALIZE_ALLOWLIST

    # C2: every serialized state must be nulled/false in the reset block.
    for name in sorted(serialized):
        pat = re.compile(r"window\." + re.escape(name) + r"\s*=\s*(null|false)\b")
        if not pat.search(block):
            return fail(f"C2: hashchange reset never nulls {name} "
                        f"(serialized by serializeState)")
    if not re.search(r"\bactiveRole\s*=\s*null\b", block):
        return fail("C2: hashchange reset never nulls activeRole "
                    "(serialized via role=)")
    if not re.search(r"window\._isAfGender\s*=\s*false\b", block):
        return fail("C2: hashchange reset never clears window._isAfGender "
                    "(gender nulling must not leave a stale AF-origin flag)")

    # C3: every filter chip id must be removed in the reset block.
    for chip_id in CHIP_IDS:
        if chip_id not in block:
            return fail(f"C3: hashchange reset never removes {chip_id}")

    # C4: exactly the expected AF selects cleared, no forbidden ones.
    m = re.search(r"window\._clearAfSelects\(\s*\[([^\]]*)\]", block)
    if not m:
        return fail("C4: hashchange reset never calls window._clearAfSelects")
    selects = set(re.findall(r"'([^']+)'", m.group(1)))
    if selects != EXPECTED_AF_SELECTS:
        return fail(f"C4: _clearAfSelects selects {sorted(selects)} != "
                    f"expected {sorted(EXPECTED_AF_SELECTS)}")
    bad = selects & FORBIDDEN_AF_SELECTS
    if bad:
        return fail(f"C4: forbidden selects in hashchange clear: {sorted(bad)}")

    # C5: PvP toggle re-render + role-chip reset.
    if "_updatePvpOnlyToggle" not in block:
        return fail("C5: hashchange reset never re-renders the PvP toggle off")
    if "role-chip" not in block or "updateRoleColumnHeader()" not in block:
        return fail("C5: hashchange reset never resets role chips/header")

    print(f"OK: hashchange reset covers {len(serialized)} serialized "
          f"filter states, {len(CHIP_IDS)} chips, "
          f"{len(EXPECTED_AF_SELECTS)} AF selects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
