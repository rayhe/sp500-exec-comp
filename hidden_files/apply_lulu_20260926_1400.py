#!/usr/bin/env python3
"""LULU FY2025 backfill + DQ repairs (2026-09-26 14:00 PT run).

Source: LULU 2026 DEFC14A (contested definitive proxy, filed 2026-05-18,
accession 0001213900-26-058095). LULU filed no plain DEF 14A for 2026;
the DEFC14A carries the FY2025 Summary Compensation Table (SCT),
verified cell-by-cell from the primary filing
(goal hidden_files/lulu_defc14a_20260518.htm).

Changes:
1. ADD 8 FY2025 NEO rows (Frank, Maestrini, Neuburger, Dagnese,
   McDonald, Burgoyne) + Maestrini 2024/2023 (first appearance as NEO).
   All 15 parsed SCT rows foot exactly to their printed totals.
2. REPAIR Meghan Frank 2024 column shift: the stored row has
   bonus=2099878/stock=900031/option=592950/neip=0/all_other=0 while the
   filing prints bonus=-/stock=2099878/option=900031/neip=592950/all_other=-.
   The 2026-09-12 batch verified the total (4407239, correct) but missed
   the one-column-left shift (parser dropped the blank Bonus cell - the
   KR 2026-09-11 bug class). Components realigned; total untouched.
3. ADOPT restated McDonald 2024/2023 All Other Compensation from the 2026
   DEFC14A per the GEN Derse/Ko + TFC 2026-09-10 restatement-adoption
   precedent (supersedes the earlier same-day Y+1 note on the TFC row).
   Footnote (e) of the filing discloses the 2023/2024 "Other" amounts are
   security-related costs "previously not included ... presented here for
   completeness": 2024 all_other 37577->56060 (total 14551916->14570399);
   2023 all_other 33290->86401 (total 16494777->16547888). Originals
   preserved in the restate note.
4. Company anchor: FY2025 CEO = Calvin McDonald $24,023,294 (pay-ratio
   disclosure names him PEO as of 2026-01-30; ratio 918:1, median worker
   $26,179). Note: his FY2025 option awards include the incremental fair
   value of the separation-agreement option modification (footnote 9/10).
5. LULU/WSM Burgoyne collision (guard section 12, 2026-09-14) resolved as
   a legit transition: the 2026 DEFC14A confirms Burgoyne as LULU NEO
   through her 2025-12-31 resignation; she appears at WSM after.
"""
import json, shutil, sys
from datetime import date

REPO = "/home/hatch/repos/sp500-exec-comp"
PATH = REPO + "/data/compensation.json"
FILING_URL = ("https://www.sec.gov/Archives/edgar/data/1397187/"
              "000121390026058095/ea0281698-04.htm")
LABEL = "def14a_verified_20260926"
TODAY = "2026-09-26"

shutil.copy2(PATH, REPO + "/hidden_files/compensation_backup_20260926_1400_pre_lulu.json")

d = json.load(open(PATH))
cos = {c["ticker"]: c for c in d["companies"]}
c = cos["LULU"]

def row(name, title, year, salary, bonus, stock, option, neip, all_other, total, note=None):
    # filing components foot exactly (verified during parse); transposition
    # rule applied - values re-read digit-by-digit from the primary SCT
    assert salary + bonus + stock + option + neip + all_other == total, \
        (name, year, salary, bonus, stock, option, neip, all_other, total)
    r = {"name": name, "title": title, "year": year, "salary": salary,
         "bonus": bonus, "stock_awards": stock, "option_awards": option,
         "non_equity_incentive": neip, "all_other": all_other, "total": total,
         "_total_source": LABEL}
    if note:
        r["_note_20260926"] = note
    return r

NEW_ROWS = [
    row("Meghan Frank",
        "Interim Co-Chief Executive Officer and Chief Financial Officer",
        2025, 861195, 0, 5150017, 3348876, 307447, 0, 9667535,
        "FY2025 special awards: $2.0M RSUs + $2.0M options for dual interim co-CEO/CFO service (footnote 5)."),
    row("Andre Maestrini",
        "Interim Co-Chief Executive Officer, President, and Chief Commercial Officer",
        2025, 863008, 0, 5150017, 3348876, 308094, 61849, 9731844),
    row("Andre Maestrini",
        "Interim Co-Chief Executive Officer, President, and Chief Commercial Officer",
        2024, 800755, 0, 1925055, 825023, 583030, 57543, 4191406),
    row("Andre Maestrini",
        "Interim Co-Chief Executive Officer, President, and Chief Commercial Officer",
        2023, 762763, 0, 1749986, 750023, 1372974, 54951, 4690697),
    row("Nicole Neuburger", "Chief Brand & Product Activation Officer",
        2025, 797308, 0, 3349933, 2149304, 284639, 17055, 6598239),
    row("Edward Dagnese", "Chief Supply Chain Officer",
        2025, 670288, 0, 1800223, 1199686, 179470, 15771, 3865438),
    row("Calvin McDonald", "Former Chief Executive Officer",
        2025, 1393269, 0, 7800001, 13800030, 994794, 35200, 24023294,
        "Terminated 2026-01-31; separation treated as without-cause. Option awards include incremental fair value of separation-agreement option modification (footnote 9). PEO for FY2025 pay-ratio disclosure (918:1)."),
    row("Celeste Burgoyne",
        "Former President, Americas and Global Guest Innovation",
        2025, 825962, 0, 3150175, 1349991, 0, 0, 5326128,
        "Resigned 2025-12-31; no severance; unvested equity forfeited (footnote 11)."),
]

# index existing rows by (name, year)
idx = {(e["name"], e["year"]): e for e in c["executives"]}
for r in NEW_ROWS:
    key = (r["name"], r["year"])
    assert key not in idx, f"duplicate row would be created: {key}"
    c["executives"].append(r)

# 2. Repair Frank 2024 column shift (leading blank-Bonus cell dropped by parser)
frank24 = idx[("Meghan Frank", 2024)]
assert (frank24["bonus"], frank24["stock_awards"], frank24["option_awards"],
        frank24["non_equity_incentive"], frank24["all_other"]) == \
       (2099878, 900031, 592950, 0, 0), "Frank 2024 stored row changed since analysis"
frank24["bonus"] = 0
frank24["stock_awards"] = 2099878
frank24["option_awards"] = 900031
frank24["non_equity_incentive"] = 592950
frank24["all_other"] = 0
assert frank24["total"] == 4407239
frank24["_total_source"] = LABEL
frank24["_repair_note_20260926"] = (
    "Column-shift repair 2026-09-26 vs 2026 DEFC14A SCT " + FILING_URL +
    ": stored row had bonus=2099878/stock=900031/option=592950/neip=0/all_other=0; "
    "filing prints bonus=-/stock=2099878/option=900031/neip=592950/all_other=-. "
    "Parser dropped the blank Bonus cell (KR 2026-09-11 bug class); the 2026-09-12 "
    "batch verified the total but missed the shift. Total unchanged 4407239.")

# 3. Adopt restated McDonald 2024/2023 All Other (footnote (e) disclosure)
RESTATES = [
    ("Calvin McDonald", 2024, 37577, 56060, 14551916, 14570399),
    ("Calvin McDonald", 2023, 33290, 86401, 16494777, 16547888),
]
for name, year, old_ao, new_ao, old_tot, new_tot in RESTATES:
    e = idx[(name, year)]
    assert e["all_other"] == old_ao and e["total"] == old_tot, (name, year, e["all_other"], e["total"])
    e["all_other"] = new_ao
    e["total"] = new_tot
    e["_total_source"] = LABEL
    e["_restate_note_20260926"] = (
        f"Restatement adopted from 2026 DEFC14A SCT {FILING_URL}: {year} All Other "
        f"${old_ao:,} -> ${new_ao:,}, total ${old_tot:,} -> ${new_tot:,}. Filing footnote (e) "
        "discloses the 2023/2024 'Other' amounts are security-related costs 'previously not "
        "included ... presented here for completeness'. Adopted per GEN Derse/Ko + TFC "
        "2026-09-10 restatement-adoption precedent. Earlier contemporaneous-proxy values "
        f"({old_ao:,}/{old_tot:,}) preserved here.")

# 4. Company-level anchor update
c["ceo_name"] = "Calvin McDonald"
c["total_compensation"] = 24023294
c["fiscal_year"] = 2025
c["proxy_fiscal_year"] = 2025
c["source"] = "SEC DEFC14A 2026 \u2014 FY2025 CEO"
c["median_worker_pay"] = 26179
c["pay_ratio"] = 918
c["filing_date"] = "2026-05-18"
c["filing_url"] = FILING_URL
c["available_years"] = [2025, 2024, 2023, 2022]
c["neo_count"] = 6
c["total_neo_compensation"] = 59212478

# sanity: CEO anchor pairs with a real SCT row; NEO sum recounts
rows25 = [e for e in c["executives"] if e["year"] == 2025]
assert sum(e["total"] for e in rows25) == 59212478
assert any(e["name"] == "Calvin McDonald" and e["total"] == 24023294 for e in rows25)

# 5. Metadata buckets
m = d["metadata"]
dq = m["data_quality"]
dqd = m["data_quality_detailed"]
dq["def14a_verified_20260926"] = dq.get("def14a_verified_20260926", 0) + 11
dqd["def14a_verified_20260926"] = dqd.get("def14a_verified_20260926", 0) + 11
dq["def14a_verified_20260912"] -= 1
dqd["def14a_verified_20260912"] -= 1
dq["verified"] -= 2
dqd["verified"] -= 2
dq["verified_total"] = dq["verified_total"] + 8   # 8 new rows; 3 relabeled stay verified
dqd["verified_total"] = dqd["verified_total"] + 8
m["total_neo_records"] = m["total_neo_records"] + 8
m["total_neos"] = m.get("total_neos", 0) + 8
m["total_executives"] = m.get("total_executives", 0) + 8
m["last_updated"] = TODAY
d["last_updated"] = TODAY
m["last_dq_repair"] = TODAY

json.dump(d, open(PATH, "w"), ensure_ascii=False, indent=1)
print("OK: LULU now", len(c["executives"]), "rows;",
      "total_neo_records", m["total_neo_records"],
      "verified_total", dq["verified_total"])
