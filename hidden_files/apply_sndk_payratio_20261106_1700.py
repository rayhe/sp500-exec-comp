#!/usr/bin/env python3
"""SNDK FY2026 pay-ratio + median-worker fill (2026-11-06 17:00 PT run).

Source: Sandisk 2026 DEF 14A, accession 0001308179-26-000423, filed
2026-10-06. CEO Pay Ratio section (proxy p.62): median employee annual
total compensation $56,823; CEO annual total compensation $15,181,160;
ratio 267 to 1. CEO figure cross-checks the stored FY2026 SCT total
exactly. SCT rows were already stored from this filing; this batch adds
the missing pay-ratio/median fields plus per-row provenance, and re-checks
FDXF (still 0 DEF 14A).

Also documents a filing-side quirk for the next pay-vs-performance wave:
the proxy PvP reconciliation table reports the PEO SCT total as
$10,456,161, which omits the $4,725,000 non-equity incentive (salary +
stock + all-other only). The SCT total is $15,181,160; do not ingest
$10,456,161 as the SCT total.
"""
import json, shutil, statistics, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(REPO, "data",
                      "compensation_backup_20261106_1700_pre_sndk_payratio.json")
DOC_URL = ("https://www.sec.gov/Archives/edgar/data/2023554/"
           "000130817926000423/sndk-20261005.htm")
ACCESSION = "0001308179-26-000423"

shutil.copy(DATA, BACKUP)
print("backup:", BACKUP)

d = json.load(open(DATA, encoding="utf-8"))
comps = {c["ticker"]: c for c in d["companies"]}

# --- SNDK pay ratio / median ---
sndk = comps["SNDK"]
assert "pay_ratio" not in sndk and "median_worker_pay" not in sndk
sndk["median_worker_pay"] = 56823
sndk["pay_ratio"] = 267
sndk["_index_note"] = (
    "Pay ratio and median worker pay from the 2026 DEF 14A (acc. "
    "0001308179-26-000423, filed 2026-10-06), CEO Pay Ratio section p.62: "
    "median employee annual total compensation $56,823, CEO $15,181,160, "
    "ratio 267 to 1. CEO figure cross-checks the stored FY2026 SCT total "
    "exactly. Filing-side quirk for the next pay-vs-performance wave: the "
    "proxy PvP reconciliation table reports the PEO SCT total as "
    "$10,456,161, which omits the $4,725,000 non-equity incentive (salary "
    "plus stock plus all-other only); the SCT total is $15,181,160, do not "
    "ingest $10,456,161 as the SCT total."
)

row_notes = {
    "David V. Goeckeler": (
        "SCT (proxy p.56), FY2026 (ended July 3, 2026). Filing-side $1 "
        "footing difference: components sum to $15,181,161 vs filed total "
        "$15,181,160 (rounded underlying values); total kept verbatim as "
        "filed. Salary reflects 27 payroll periods. No Option/Pension "
        "columns in this SCT (keys 0). CEO total cross-checked by the CEO "
        "Pay Ratio disclosure (median $56,823, 267 to 1)."
    ),
    "Luis F. Visoso": "SCT (proxy p.56), FY2026. Components foot exactly to filed total.",
    "Alper Ilkbahar": "SCT (proxy p.56), FY2026. Components foot exactly to filed total.",
    "Bernard Shek": (
        "SCT (proxy p.56), FY2026. Filing-side $1 footing difference: "
        "components sum to $2,630,463 vs filed total $2,630,464 (rounded "
        "underlying values); total kept verbatim as filed."
    ),
}
for e in sndk["executives"]:
    if e["year"] != 2026:
        continue
    assert e["name"] in row_notes, e["name"]
    e["_accession"] = ACCESSION
    e["_filing_url"] = DOC_URL
    e["_note"] = row_notes[e["name"]]
    # verify components against the filing SCT (verbatim totals kept)
    s = (e["salary"] + e["bonus"] + e["stock_awards"] + e["option_awards"]
         + e["non_equity_incentive"] + e["pension_nqdc"] + e["all_other"])
    print(f"  SNDK 2026 {e['name'].split()[-1]}: components {s} vs filed {e['total']} "
          f"diff {e['total'] - s} flag {e['_total_source']}")

# --- FDXF re-check note ---
fdxf = comps["FDXF"]
fdxf["_index_note"] = (fdxf.get("_index_note", "") +
    " Re-checked 2026-11-06: CIK 0002082247 submissions still show 0 DEF 14A "
    "(recent filings 10-Q/8-K Oct 29 only).")

# --- metadata: recompute aggregates with guard semantics ---
companies = d["companies"]
ceo_pays = [c["total_compensation"] for c in companies if c.get("total_compensation", 0) > 0]
worker_pays = [c["median_worker_pay"] for c in companies
               if c.get("median_worker_pay") and c["median_worker_pay"] > 0]
ratios = [c["pay_ratio"] for c in companies
          if c.get("pay_ratio") is not None and c["pay_ratio"] > 0]
agg = {
    "total_companies": len(companies),
    "companies_with_pay_ratio": len(ratios),
    "median_ceo_pay": int(statistics.median(ceo_pays)),
    "mean_ceo_pay": int(statistics.mean(ceo_pays)),
    "max_ceo_pay": max(ceo_pays),
    "min_ceo_pay": min(ceo_pays),
    "median_worker_pay": int(statistics.median(worker_pays)) if worker_pays else 0,
    "median_pay_ratio": int(statistics.median(ratios)) if ratios else 0,
}
print("aggregate_stats:", agg)
d["metadata"]["aggregate_stats"] = agg
# sync the stale top-level keys to the same live recounts
d["metadata"]["companies_with_pay_ratio"] = len(ratios)
d["metadata"]["median_pay_ratio"] = agg["median_pay_ratio"]
d["metadata"]["median_worker_pay"] = agg["median_worker_pay"]
d["last_updated"] = "2026-11-06"
d["metadata"]["last_updated"] = "2026-11-06"
d["metadata"]["last_dq_repair"] = "2026-11-06"
d["metadata"]["notes"].append(
    "SNDK (Sandisk): FY2026 median worker pay $56,823 and pay ratio 267 to 1 "
    "added 2026-11-06 from the 2026 DEF 14A CEO Pay Ratio disclosure (acc. "
    "0001308179-26-000423); CEO $15,181,160 cross-checks the stored SCT total "
    "exactly. The filing PvP reconciliation table understates the PEO SCT "
    "total ($10,456,161) by omitting the $4,725,000 non-equity incentive; "
    "SCT total $15,181,160 stands. FDXF re-checked 2026-11-06: still 0 DEF "
    "14A. VMRK re-checked 2026-11-06: still no post-merger DEF 14A."
)

with open(DATA, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("wrote", DATA)

# Postscript (same run, after the guard's first pass): the guard flagged
# sector_medians[Information Technology] documented_anchors 0 -> 1 and
# undocumented_anchors 3 -> 2, because the new _note on SNDK's anchor row
# (Goeckeler 2026, component_mismatch, now documented) moves it from the
# undocumented bucket to the documented bucket per section-17 semantics.
# Synced in place; guard re-run green.
