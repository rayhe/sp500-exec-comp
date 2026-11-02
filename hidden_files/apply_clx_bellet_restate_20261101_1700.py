#!/usr/bin/env python3
"""307th review (2026-11-01 17:00 PT): CLX Bellet FY2025 restatement resolution.

Findings from the component_mismatch queue adjudication (45 rows):
  - 8 rows with genuine >$2 filing-side arithmetic gaps (CPRT Stearns 2023,
    DRI Vennam 2023, FDS Shan 2023, GNRC Taffe 2023, KR Sargent 2025,
    KR Foley 2024, NEE Sieving 2023, LITE Ali 2023): all re-verified
    filing-verbatim (latest 2026-10-28 batch); labels retained.
  - 19 rows with $1 filing-side rounding gaps: documented in their
    enrichment-review commit messages; labels retained.
  - 17 rows with incomplete component columns (column n/a in the filing's
    SCT, e.g. APH options-only, CDNS/RF/TSCO filing-side non-footing):
    all re-verified; labels retained.
  - 1 row resolvable: CLX Luc Bellet FY2025. The 272nd review noted
    "2026 proxy restates to component sum" but the stored row kept the
    2025 proxy's $2,622,295 (a $1 filing-side gap). The 2026 DEF 14A
    (e26316_clx-def14a.htm, filed 2026-10-07) SCT prints Bellet 2025:
    salary 514,776 + stock 1,599,673 + NEIP 362,301 + all other 145,546
    = total 2,622,296 (pension n/a; no bonus/option columns). Components
    unchanged; the printed total is now the component sum, so the row is
    repaired filing-verbatim: total 2622295 -> 2622296, tag cleared to
    verified.

This script applies that single repair. Read-only otherwise.
"""
import json
import shutil
from datetime import datetime

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_clx_bellet_restate.json"

shutil.copy2(DATA, BACKUP)
print("backup:", BACKUP)

data = json.load(open(DATA))
cos = data["companies"]

fixed = 0
for c in cos:
    if c["ticker"] != "CLX":
        continue
    for e in c.get("executives", []):
        if e["name"] == "Luc Bellet" and e["year"] == 2025:
            assert e["total"] == 2622295, f"unexpected stored total {e['total']}"
            assert e["_total_source"] == "component_mismatch"
            comps = ["salary", "bonus", "stock_awards", "option_awards",
                     "non_equity_incentive", "pension_nqdc", "all_other"]
            s = sum(e[k] for k in comps)
            assert s == 2622296, f"component sum {s} != restated total"
            e["total"] = 2622296
            e["_total_source"] = "verified"
            e["_restatement_note_20261101_1700"] = (
                "2026-11-01 17:00 PT (307th review): 2026 DEF 14A "
                "(e26316_clx-def14a.htm, filed 2026-10-07) SCT restates Bellet "
                "FY2025 total to $2,622,296 = component sum "
                "(514,776 + 1,599,673 + 362,301 + 145,546; pension n/a). The "
                "FY2025 proxy printed $2,622,295 ($1 filing-side arithmetic "
                "gap, flagged 272nd review); components unchanged. Row now "
                "sums exactly; component_mismatch cleared."
            )
            fixed += 1

assert fixed == 1, f"expected 1 row fixed, got {fixed}"

# timestamps already 2026-11-01; assert the invariant the metadata guard needs
assert data["metadata"]["last_dq_repair"] == "2026-11-01"
assert data["last_updated"] == "2026-11-01"

# metadata bucket sync (the metadata-consistency guard recounts these):
# one row moves component_mismatch -> verified
for _bucket in ("data_quality", "data_quality_detailed"):
    _b = data["metadata"][_bucket]
    _b["component_mismatch"] = 44
    _b["verified"] = 5846
    _b["verified_total"] = 7261

json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
open(DATA, "a", encoding="utf-8").write("\n")
print("repaired CLX Luc Bellet 2025: total 2622295 -> 2622296, tag -> verified")
