#!/usr/bin/env python3
"""STX/KLAC-style None-vs-0 schema normalization (303rd review, 2026-11-01).

Within-company consistency pass: for the three SCT component fields where a
filing dash unambiguously means $0 (bonus, option_awards, pension_nqdc), any
executive row in a company that already represents the dash as an explicit 0
in sibling rows gets its missing-key or explicit-None normalized to 0.

Scope guardrails:
- Only companies where the field has BOTH an explicit 0 and a None/missing
  value across rows (133 company-field pairs) - pure-legacy companies are a
  separate pass.
- Only the three dash-means-zero fields. stock_awards / non_equity_incentive /
  all_other / salary are EXCLUDED: a missing stock_awards cell can be an
  extraction miss (APH Lampo 2023 foots -$63k), all_other is almost never a
  genuine $0, and a $0 salary for a serving NEO is a miss, not a dash.
- Never creates pension_nqdc+pension_change both-keys rows (checked: 0 cases).
- Totals, row counts, verified flags, metadata: asserted unchanged.

Display-neutral: every JS path treats None/missing/0 identically
(`|| 0`, `|| ''`, truthy checks, `yrHasBonus` > 0 test). Guard-neutral:
check_metadata_consistency uses _int_or_zero (None/missing/0 -> 0) and
_eff_pension (pn==0 & pc>0 -> pc), so recounts and footing are byte-identical.
"""

import json
import shutil
from collections import defaultdict

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
FIELDS = ["bonus", "option_awards", "pension_nqdc"]
BACKUP = f"{REPO}/data/compensation_backup_20261101_0900_pre_nonezero_norm.json"


def main():
    with open(DATA) as f:
        d = json.load(f)
    shutil.copy2(DATA, BACKUP)

    before_rows = sum(len(c.get("executives", [])) for c in d["companies"])
    before_totals = {
        (c["ticker"], e.get("name"), e.get("year")): e.get("total")
        for c in d["companies"] for e in c.get("executives", [])
    }
    before_meta = json.dumps(d["metadata"], sort_keys=True)

    changed = defaultdict(int)
    pairs = []
    for c in d["companies"]:
        t = c["ticker"]
        for f in FIELDS:
            vals = [e.get(f) for e in c.get("executives", [])]
            if any(v == 0 for v in vals) and any(v is None for v in vals):
                n = 0
                for e in c["executives"]:
                    if e.get(f) is None:
                        if f == "pension_nqdc" and e.get("pension_change"):
                            continue  # never create both-keys rows
                        e[f] = 0
                        n += 1
                if n:
                    changed[f] += n
                    pairs.append((t, f, n))

    # Invariants
    after_rows = sum(len(c.get("executives", [])) for c in d["companies"])
    assert after_rows == before_rows, f"row count changed {before_rows}->{after_rows}"
    for c in d["companies"]:
        for e in c.get("executives", []):
            key = (c["ticker"], e.get("name"), e.get("year"))
            assert e.get("total") == before_totals[key], f"total changed for {key}"
    assert json.dumps(d["metadata"], sort_keys=True) == before_meta, "metadata changed"
    # real both-keys check: pension_nqdc set AND pension_change set
    both = sum(
        1 for c in d["companies"] for e in c.get("executives", [])
        if ("pension_nqdc" in e and e["pension_nqdc"] not in (None, 0)
            and "pension_change" in e and e["pension_change"] not in (None, 0))
    )
    assert both == 0, f"both-keys pension rows: {both}"

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")

    total = sum(changed.values())
    print(f"normalized rows: {total} across {len(pairs)} company-field pairs")
    for f in FIELDS:
        print(f"  {f}: {changed[f]}")
    for t, f, n in sorted(pairs):
        print(f"  {t} {f}: {n}")


if __name__ == "__main__":
    main()
