#!/usr/bin/env python3
"""Guard: AF Clear and AF-origin tenure/gov setters must refresh the
app.js-owned filter chips.

Background (334th review, 2026-11-04): clearAdvancedFilters() in
js/advanced-filters.js nulls AF filter state but only removes chips
carrying dataset.af === '1'. The gender, tenure, gov and conc chips are
app.js-owned (created by update*FilterIndicator in js/app.js, no
dataset.af), so after AF Clear their state was nulled while the chip
stayed visible: a stale chip for a filter that no longer filters.
The 327th review fixed exactly this shape for volatility by calling
window._updateVolatilityFilterIndicator() after the removal loop; the
334th fix extends the same treatment to gender, tenure, gov and conc,
exposes the one indicator that was never on window (gov), and makes
the AF-origin tenure/gov setters refresh their chips so an AF value
replaces (not hides behind) a stale chart-origin tag.

Checks (all static - small reads, <2s):
  C1 HARD FAIL: clearAdvancedFilters() does not call one of
     _updateGenderFilterIndicator, _updateTenureFilterIndicator,
     _updateGovFilterIndicator, _updateConcFilterIndicator
     (volatility is covered by the 327th review's own guard path and
     asserted here too, so the full set stays in one place).
  C2 HARD FAIL: js/app.js does not expose
     window._updateGovFilterIndicator (the 334th fix's exposure line).
  C3 HARD FAIL: handleTenure() does not call _updateTenureFilterIndicator
     or handleGov() does not call _updateGovFilterIndicator.
  C4 HARD FAIL (335th review): handlePayBand() does not call
     _updateDistFilterIndicator, or handleConc() does not call
     _updateConcFilterIndicator, on their individual-clear paths.
     The 334th fix covered AF Clear only; the '' branches had the
     same hole (AF value set over a chart-origin chip leaves a chip
     with no dataset.af, skipped by the removal check, while state
     was just nulled).

Usage:
  scripts/check_af_clear_indicators.py
  scripts/check_af_clear_indicators.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (files unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDICATORS = [
    "_updateVolatilityFilterIndicator",
    "_updateGenderFilterIndicator",
    "_updateTenureFilterIndicator",
    "_updateGovFilterIndicator",
    "_updateConcFilterIndicator",
    # 335th review: dist and sop complete the set -- their AF handlers
    # reuse the app.js chip id and only overwrite its textContent
    # (never setting dataset.af), so AF Clear's removal loop skips a
    # chart-origin-collided chip while state is nulled.
    "_updateDistFilterIndicator",
    "_updateSopFilterIndicator",
]


def _function_body(src, name):
    """Return the source span of `function name(...) { ... }` (brace-matched)."""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\(", src)
    if not m:
        return None
    i = src.find("{", m.end())
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    return None


def main():
    failures = []
    try:
        af = open(os.path.join(ROOT, "js", "advanced-filters.js"),
                  encoding="utf-8").read()
        app = open(os.path.join(ROOT, "js", "app.js"),
                   encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read js sources: %s" % e)
        return 2

    clear_body = _function_body(af, "clearAdvancedFilters")
    if clear_body is None:
        failures.append("C1 clearAdvancedFilters() not found in "
                        "js/advanced-filters.js")
    else:
        for ind in INDICATORS:
            if ind not in clear_body:
                failures.append("C1 clearAdvancedFilters() never calls %s "
                                "(stale app.js-owned chip after AF Clear)"
                                % ind)

    if "window._updateGovFilterIndicator" not in app:
        failures.append("C2 js/app.js never exposes "
                        "window._updateGovFilterIndicator (AF panel cannot "
                        "refresh the gov chip)")

    tenure_body = _function_body(af, "handleTenure")
    if tenure_body is None:
        failures.append("C3 handleTenure() not found in "
                        "js/advanced-filters.js")
    elif "_updateTenureFilterIndicator" not in tenure_body:
        failures.append("C3 handleTenure() never calls "
                        "_updateTenureFilterIndicator (AF-origin tenure "
                        "value hides behind a stale chart-origin chip)")

    gov_body = _function_body(af, "handleGov")
    if gov_body is None:
        failures.append("C3 handleGov() not found in "
                        "js/advanced-filters.js")
    elif "_updateGovFilterIndicator" not in gov_body:
        failures.append("C3 handleGov() never calls "
                        "_updateGovFilterIndicator (AF-origin gov grade "
                        "hides behind a stale chart-origin chip)")

    pay_body = _function_body(af, "handlePayBand")
    if pay_body is None:
        failures.append("C4 handlePayBand() not found in "
                        "js/advanced-filters.js")
    elif "_updateDistFilterIndicator" not in pay_body:
        failures.append("C4 handlePayBand() never calls "
                        "_updateDistFilterIndicator (AF pay band cleared "
                        "over a chart-origin dist chip leaves a stale chip)")

    conc_body = _function_body(af, "handleConc")
    if conc_body is None:
        failures.append("C4 handleConc() not found in "
                        "js/advanced-filters.js")
    elif "_updateConcFilterIndicator" not in conc_body:
        failures.append("C4 handleConc() never calls "
                        "_updateConcFilterIndicator (AF conc cleared "
                        "individually leaves the app.js-owned chip stale)")

    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        return 1
    print("PASS: AF Clear refreshes all app.js-owned chips; "
          "tenure/gov setters refresh theirs; pay-band/conc "
          "individual clears refresh theirs; gov indicator exposed")
    return 0


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        pass  # static checks only; no browser/render half exists
    sys.exit(main())
