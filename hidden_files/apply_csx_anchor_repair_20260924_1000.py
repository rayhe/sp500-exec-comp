#!/usr/bin/env python3
"""2026-09-24 10:00 PT: CSX CEO-anchor adjudication + SCT row completion.

Backlog candidate #8 (panel 2026-09-24 07:30 PT). Two defects in the CSX
record, both verified verbatim against the 2026 DEF 14A (acc.
0001628280-26-021944, filed 2026-03-26; local copy goal hidden workspace
dq_20260917_1000/CSX.htm, values cross-checked against the filing's SCT
table cells, not the parser dump):

1. Stale CEO anchor. The company-aggregate anchor still reads FY2024 /
   Kevin S. Boone ($4,663,680) while the ingested DEF 14A data covers FY2025
   (proxy_fiscal_year=2025, available_years=[2025,2024,2023]). Per the 2026
   proxy, Stephen F. Angel was appointed President and CEO effective
   September 28, 2025; Boone is Executive Vice President and CFO in 2025.
   Least-false-statement principle (TMUS/MAA precedent): re-anchor the CEO
   aggregate to the named 2025 CEO's verified SCT row.
   ceo_name 'Kevin S. Boone' -> 'Stephen F. Angel'
   total_compensation 4,663,680 -> 11,711,612 (Angel FY2025 SCT total)
   fiscal_year 2024 -> 2025
   pay_ratio 124 -> 123, median_worker_pay 123,935 -> 122,362 (filed FY2025
   CEO Pay Ratio disclosure: median employee $122,362; CEO $14,938,149
   annualized; ratio 123:1)
   ceo_tenure -> {year: 2025, month: 9, confidence: high,
                  sources: ['def14a_2026_ceo_transition_20250928']}
   neo_count 3 -> 7, total_neo_compensation 13,326,258 -> 58,325,215
   (sum of all FY2025 SCT rows, convention confirmed on MSFT/AAPL/NVDA/META)

2. Missing SCT rows. The stored executives list kept only the 4 current
   NEOs' rows; the 2026-proxy SCT also covers 3 departed NEOs (the data model
   keeps departed execs: 318 'Former' / 7 'Retired' rows elsewhere). Added
   filing-verbatim:
   Diana B. Sorfleet 2025 (Retired EVP and CAO)          $3,526,301
   Joseph R. Hinrichs 2025/2024/2023 (Former Pres/CEO)   $23,696,453 / $15,350,652 / $14,074,235
   Sean R. Pelkey 2025/2024/2023 (Former EVP/CFO)        $4,263,336 / $3,803,265 / $3,960,324

All 7 rows foot exactly (0 rounding gap). Labeled def14a_verified_20260924.

Run from repo root.
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260924_1000_pre_csxanchor.json")
README_PATH = os.path.join(HERE, "..", "README.md")
INDEX_PATH = os.path.join(HERE, "..", "index.html")
APPJS_PATH = os.path.join(HERE, "..", "js", "app.js")

SRC = "def14a_verified_20260924"
NOTE = "2026-09-24 10:00 PT"
ACCESSION = "0001628280-26-021944"
FILING_URL = ("https://www.sec.gov/Archives/edgar/data/277948/"
              "000162828026021944/csx-20260326.htm")

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]


def foot(e):
    return sum((e.get(k) or 0) for k in COMP8)


def get(ticker, name, year):
    hits = [e for e in companies[ticker]["executives"]
            if e["name"] == name and e["year"] == year]
    assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
    return hits[0]


# ---------------- pre-write assertions ----------------
n0 = sum(len(c["executives"]) for c in data["companies"])
assert n0 == 6866, f"row count {n0} != 6866"

c = companies["CSX"]
assert (c["ceo_name"], c["total_compensation"], c["fiscal_year"],
        c["proxy_fiscal_year"], c["pay_ratio"], c["median_worker_pay"],
        c["neo_count"], c["total_neo_compensation"]) == \
    ("Kevin S. Boone", 4663680, 2024, 2025, 124, 123935, 3, 13326258), \
    "CSX anchor pre-change values drifted"
assert c["ceo_tenure"] == {"year": 2025, "month": None,
                           "confidence": "medium", "sources": ["table"]}, \
    "CSX ceo_tenure pre-change drifted"
assert c["filing_url"] == FILING_URL, "CSX filing_url drifted"

# the 9 retained CSX rows must match the filing dump values
STORED = [
    ("Stephen F. Angel", 2025, 386364, 5385342, 5248065, 513863, None,
     177978, 11711612),
    ("Kevin S. Boone", 2025, 747917, 2527360, 630000, 568417, 159396,
     54969, 4688058),
    ("Kevin S. Boone", 2024, 725000, 2520020, 630006, 594500, 146119,
     48035, 4663680),
    ("Kevin S. Boone", 2023, 725000, 2520013, 630001, 833750, 157053,
     68285, 4934102),
    ("Michael A. Cory", 2025, 757083, 2527360, 630000, 575383, None,
     2365655, 6855481),
    ("Michael A. Cory", 2024, 725000, 2520020, 630006, 594500, None,
     606698, 5076224),
    ("Stephen Fortune", 2025, 668333, 1865419, 465008, 507933, None,
     77281, 3583974),
    ("Stephen Fortune", 2024, 650000, 1860052, 465004, 533000, None,
     78298, 3586354),
    ("Stephen Fortune", 2023, 650000, 1860011, 465008, 747500, None,
     83469, 3805988),
]
for nm, yr, sal, stk, opt, neip, pen, ao, tot in STORED:
    e = get("CSX", nm, yr)
    got = (e["salary"], e["stock_awards"], e["option_awards"],
           e["non_equity_incentive"], e.get("pension_nqdc") or None,
           e["all_other"], e["total"])
    assert got == (sal, stk, opt, neip, pen, ao, tot), \
        f"CSX {nm} {yr} stored values drifted: {got}"
# the 7 rows to add must be absent
for nm, yr in [("Diana B. Sorfleet", 2025), ("Joseph R. Hinrichs", 2025),
               ("Joseph R. Hinrichs", 2024), ("Joseph R. Hinrichs", 2023),
               ("Sean R. Pelkey", 2025), ("Sean R. Pelkey", 2024),
               ("Sean R. Pelkey", 2023)]:
    assert not [e for e in c["executives"]
                if e["name"] == nm and e["year"] == yr], \
        f"CSX {nm} {yr} already present"
print("pre-write assertions OK")

# ---------------- add the 7 missing SCT rows ----------------
# name, year, salary, stock, option, neip, pension, all_other, total, title
NEW_ROWS = [
    ("Diana B. Sorfleet", 2025, 588333, 1865419, 465008, 402420, 160430,
     44691, 3526301, "Retired Executive Vice President and Chief Administrative Officer"),
    ("Joseph R. Hinrichs", 2025, 1113636, 10029002, 2500008, 1481137, None,
     8572670, 23696453, "Former President and Chief Executive Officer"),
    ("Joseph R. Hinrichs", 2024, 1487302, 9120036, 2280008, 2110361, None,
     352945, 15350652, "Former President and Chief Executive Officer"),
    ("Joseph R. Hinrichs", 2023, 1400000, 8000032, 2000003, 2415000, None,
     259200, 14074235, "Former President and Chief Executive Officer"),
    ("Sean R. Pelkey", 2025, 604257, 2206389, 550008, 459235, 139238,
     304209, 4263336, "Former Executive Vice President and Chief Financial Officer"),
    ("Sean R. Pelkey", 2024, 696667, 1860052, 465004, 571267, 151462,
     58813, 3803265, "Former Executive Vice President and Chief Financial Officer"),
    ("Sean R. Pelkey", 2023, 660000, 1860011, 465008, 759000, 156340,
     59965, 3960324, "Former Executive Vice President and Chief Financial Officer"),
]
NOTE_TXT = (f"{NOTE}: row restored from the 2026 DEF 14A SCT "
            f"(acc. {ACCESSION}); filing-verbatim components, total foots exactly. "
            f"{FILING_URL}")
added = 0
for nm, yr, sal, stk, opt, neip, pen, ao, tot, ti in NEW_ROWS:
    e = {"name": nm, "year": yr, "salary": sal, "stock_awards": stk,
         "option_awards": opt, "non_equity_incentive": neip}
    if pen is not None:
        e["pension_nqdc"] = pen
    e["all_other"] = ao
    e["total"] = tot
    e["title"] = ti
    e["_total_source"] = SRC
    e["_accession"] = ACCESSION
    e["_repair_note_20260924_1000"] = NOTE_TXT
    gap = abs(foot(e) - tot)
    assert gap == 0, f"CSX {nm} {yr}: components {foot(e):,} != total {tot:,}"
    c["executives"].append(e)
    added += 1
print(f"added {added} rows")

# ---------------- re-anchor the company aggregate ----------------
old = (c["ceo_name"], c["total_compensation"], c["fiscal_year"],
       c["pay_ratio"], c["median_worker_pay"], c["neo_count"],
       c["total_neo_compensation"])
c["ceo_name"] = "Stephen F. Angel"
c["total_compensation"] = 11711612
c["fiscal_year"] = 2025
c["pay_ratio"] = 123
c["median_worker_pay"] = 122362
c["neo_count"] = 7
c["total_neo_compensation"] = 58325215
c["ceo_tenure"] = {"year": 2025, "month": 9, "confidence": "high",
                   "sources": ["def14a_2026_ceo_transition_20250928"]}

# post-change pairing checks (DQ guard section 6/6b mirror)
ceo_rows = [e for e in c["executives"]
            if e["name"] == c["ceo_name"] and e["year"] == c["fiscal_year"]]
assert len(ceo_rows) == 1, f"CSX: {len(ceo_rows)} anchor-year CEO rows"
assert ceo_rows[0]["total"] == c["total_compensation"] == 11711612, \
    "CSX CEO name/total pairing failed"
assert "Chief Executive Officer" in ceo_rows[0]["title"], \
    "CSX CEO title-awareness failed"
fy_rows = [e for e in c["executives"] if e["year"] == c["fiscal_year"]]
assert len(fy_rows) == c["neo_count"] == 7, "CSX neo_count mismatch"
assert sum(e["total"] for e in fy_rows) == c["total_neo_compensation"] == 58325215, \
    "CSX total_neo_compensation mismatch"
print(f"CSX anchor: {old} -> ('Stephen F. Angel', 11711612, 2025, 123, 122362, 7, 58325215)")

# ---------------- metadata re-sync ----------------
shutil.copy(JSON_PATH, BACKUP)
print("backup:", BACKUP)

n = sum(len(co["executives"]) for co in data["companies"])
assert n == 6873, f"total {n} != 6873 (expected 6866 + 7)"
recount = {}
for co in data["companies"]:
    for e in co["executives"]:
        recount[e.get("_total_source", "?")] = \
            recount.get(e.get("_total_source", "?"), 0) + 1
assert recount.get(SRC) == 7, f"new bucket recount {recount.get(SRC)} != 7"
for block_name in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_name]
    for k, v in recount.items():
        if k in block or k.startswith("def14a_verified") or k in (
                "verified", "component_mismatch", "rounding", "recomputed"):
            block[k] = v
    block["verified_total"] = (recount.get("verified", 0)
                               + sum(v for k, v in recount.items()
                                     if k.startswith("def14a_verified")))
    block["last_audit"] = "2026-09-24"
assert sum(recount.values()) == n
dq = data["metadata"]["data_quality"]
vt, total = dq["verified_total"], n
assert (vt, total) == (6845, 6873), f"unexpected buckets {(vt, total)}"
pct = f"{vt / total * 100:.1f}%"
assert pct == "99.6%", f"unexpected headline {vt}/{total} {pct}"
data["metadata"]["last_updated"] = "2026-09-24"
data["metadata"]["last_dq_repair"] = "2026-09-24"
data["metadata"]["description"] = "500 companies, 6873 NEO records, 500 companies enriched"
# headline recount fields asserted by DQ guard sections 1-2
data["metadata"]["total_neo_records"] = 6873
data["metadata"]["total_executives"] = 6873
data["metadata"]["title_coverage"] = "6873/6873"
data["last_updated"] = "2026-09-24"
print(f"headline: {vt:,} of {total:,} ({pct}) | {SRC}: 7")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
    f.write("\n")

# ---------------- static-copy sync ----------------
# README line 11 (index 10): headline clause + audit-trail append
with open(README_PATH, encoding="utf-8") as f:
    lines = f.readlines()
head = lines[10]
assert "99.6% verified component-total consistency (6,838 of 6,866 records" in head
assert "last audit 2026-09-19" in head
assert "last partial re-verification 2026-09-19" in head
head = head.replace(
    "99.6% verified component-total consistency (6,838 of 6,866 records",
    "99.6% verified component-total consistency (6,845 of 6,873 records")
head = head.replace("last audit 2026-09-19", "last audit 2026-09-24")
head = head.replace("last partial re-verification 2026-09-19",
                    "last partial re-verification 2026-09-24")
audit = ("; 2026-09-24 10:00 PT batch: CSX CEO-anchor adjudication + SCT row "
         "completion (2026 DEF 14A, acc. 0001628280-26-021944): 7 missing SCT "
         "rows restored filing-verbatim (Sorfleet 2025 $3.53M; Hinrichs "
         "2025/2024/2023 $23.70M/$15.35M/$14.07M; Pelkey 2025/2024/2023 "
         "$4.26M/$3.80M/$3.96M - all foot exactly, 0 rounding gap), labeled "
         "def14a_verified_20260924; CEO anchor re-anchored to FY2025: Stephen "
         "F. Angel (appointed President and CEO 2025-09-28) $11,711,612, "
         "was Kevin S. Boone FY2024 $4,663,680; pay ratio 124->123, median "
         "worker pay $123,935->$122,362 (filed FY2025 disclosure: median "
         "$122,362, CEO $14,938,149 annualized, 123:1); neo_count 3->7, "
         "total_neo $13.33M->$58.33M; headline buckets 99.6% (6,845/6,873).")
assert head.rstrip("\n").endswith("."), "audit-trail anchor lost"
lines[10] = head.rstrip("\n") + audit + "\n"

# README line 80: taxonomy bucket header
assert "Buckets (as of 2026-09-19: 6,866 rows):" in lines[79]
lines[79] = lines[79].replace(
    "Buckets (as of 2026-09-19: 6,866 rows):",
    "Buckets (as of 2026-09-24: 6,873 rows):")
# README line 84: verified bucket cell
assert "| 6,838 (99.6%) |" in lines[83]
lines[83] = lines[83].replace("| 6,838 (99.6%) |", "| 6,845 (99.6%) |")
# README line 98: coverage checklist headline
assert "Component-total consistency verified: 99.6% verified (6,838 of 6,866 total NEO records)" in lines[97]
lines[97] = lines[97].replace(
    "Component-total consistency verified: 99.6% verified (6,838 of 6,866 total NEO records)",
    "Component-total consistency verified: 99.6% verified (6,845 of 6,873 total NEO records)")
with open(README_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README static copy synced")

# index.html: benchmark blurb row count
with open(INDEX_PATH, encoding="utf-8") as f:
    html = f.read()
assert "6,866 Named Executive Officer records" in html
html = html.replace("6,866 Named Executive Officer records",
                    "6,873 Named Executive Officer records")
with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print("index.html static copy synced")

# js/app.js: dataq modal fallback + coverage header + live default
with open(APPJS_PATH, encoding="utf-8") as f:
    js = f.read()
assert "6,838 of 6,866 NEO rows verified (99.6%)" in js
js = js.replace("6,838 of 6,866 NEO rows verified (99.6%)",
                "6,845 of 6,873 NEO rows verified (99.6%)")
assert "Coverage (last audit 2026-09-19)" in js
js = js.replace("Coverage (last audit 2026-09-19)",
                "Coverage (last audit 2026-09-24)")
assert "|| '2026-09-19'" in js
js = js.replace("|| '2026-09-19'", "|| '2026-09-24'")
with open(APPJS_PATH, "w", encoding="utf-8") as f:
    f.write(js)
print("js/app.js static copy synced")

print(f"done: added={added} total_records={n} vt={vt}")
