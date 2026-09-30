#!/usr/bin/env python3
"""PvP ticker normalization (2026-09-30 03:30 PT iteration).

Findings from the 5-critic panel review:
- pay_vs_performance.json shipped BOTH the stale and current tickers for two
  companies whose tickers changed: BK/BNY (BNY Mellon, CIK 0001390777) and
  MMC/MRSH (Marsh McLennan, CIK 0000062709). The year records are byte-equal
  (same CIK, same filing date, identical 2021-2025 402(v) values); only the
  wave-authored annotation strings differ. The stale duplicates rendered as
  extra rows in the Pay-vs-Performance comparison table whose click-through
  (findCompanyInTable('BK'/'MMC')) resolves to nothing, since the roster
  carries BNY/MRSH.
- Two more records were keyed ONLY under stale tickers: FI (Fiserv, roster
  ticker FISV since the Aug-2025 ticker change, CIK 0000798354) and BF-B
  (Brown-Forman, roster ticker BF-A, CIK 0000014693). FISV/BNY/MRSH/BF-A
  detail panels rendered an empty PvP section even though the data existed.

Fix: drop the stale duplicate keys BK/MMC; rename FI->FISV and BF-B->BF-A so
every shipped key is a current roster ticker (CIK-verified 1:1). Metadata
companies 497->495, company_years 2464->2454; methodology's guard-checked
"all N company-years passed" sentence updated in step.
"""
import json
import shutil
from collections import OrderedDict

REPO = "/home/hatch/repos/sp500-exec-comp"
PVP = REPO + "/data/pay_vs_performance.json"
BACKUP = REPO + "/hidden_files/pay_vs_performance_backup_20260930_0330_pre_ticker_normalize.json"

shutil.copy2(PVP, BACKUP)

with open(PVP, encoding="utf-8") as f:
    pvp = json.load(f, object_pairs_hook=OrderedDict)

cos = pvp["companies"]
assert set(cos) >= {"BK", "BNY", "MMC", "MRSH", "FI", "BF-B"}, "expected stale keys missing"

# 1. Drop stale duplicates (byte-identical year data to the current-ticker key).
for stale, keep in (("BK", "BNY"), ("MMC", "MRSH")):
    s, k = cos[stale], cos[keep]
    assert s["cik"] == k["cik"], f"CIK mismatch {stale}/{keep}"
    ya = {y["year"]: y for y in s["years"]}
    yb = {y["year"]: y for y in k["years"]}
    assert ya == yb, f"year data differs {stale}/{keep} - NOT a pure duplicate, abort"
    del cos[stale]

# 2. Rename stale-only keys to the current roster ticker (CIK-verified).
for old, new in (("FI", "FISV"), ("BF-B", "BF-A")):
    rec = cos.pop(old)
    assert "ticker" in rec
    rec["ticker"] = new
    cos[new] = rec

# 3. Metadata recount.
md = pvp["metadata"]
n_comp = len(cos)
n_years = sum(len(c.get("years", [])) for c in cos.values())
assert n_comp == 495, n_comp
assert n_years == 2454, n_years
md["companies"] = n_comp
md["company_years"] = n_years
old_phrase = "all 2464 company-years passed"
assert old_phrase in md["methodology"], "guard-checked methodology phrase not found"
md["methodology"] = md["methodology"].replace(old_phrase, "all 2454 company-years passed")
md["coverage_note"] = (md.get("coverage_note", "") +
    " 2026-09-30 ticker normalization: dropped stale duplicate keys BK/MMC "
    "(byte-identical 2021-2025 402(v) year data to BNY/MRSH, same CIK/filing; "
    "earlier waves had shipped both the old and new tickers); renamed FI->FISV "
    "and BF-B->BF-A to the current roster tickers (same CIK). All 495 shipped "
    "keys are now current roster tickers.")

with open(PVP, "w", encoding="utf-8") as f:
    json.dump(pvp, f, indent=1, ensure_ascii=False)
    f.write("\n")

print(f"OK: {n_comp} companies, {n_years} company-years; backup at {BACKUP}")
print("stale keys remaining:", [t for t in ("BK", "MMC", "FI", "BF-B") if t in cos])
