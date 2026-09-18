#!/usr/bin/env python3
"""2026-09-18 06:00 PT primary-source DQ batch: missing-NEO-row restoration + column-shift repair.

Classes repaired (all re-extracted verbatim from the 2026 DEF 14A SCTs, 4 filings re-fetched from EDGAR this run):

1. MAA (Mid-America Apartment): COLUMN SHIFT on all 8 existing rows. The MAA SCT has
   NO Option Awards column (Salary|Bonus|Stock Awards|Non-Equity Incentive|All Other|Total),
   but the parser mapped SCT col (4) Non-Equity Incentive -> option_awards and col (5)
   All Other -> non_equity_incentive. Repaired: option_awards=0,
   non_equity_incentive=<old option_awards>, all_other=<old non_equity_incentive>.
   Filing components now foot exactly to filing totals.
2. Missing NEO-year rows restored (28 total):
   - CTVA x7: Eathington 2025/2024/2023, King 2024/2023, Fuerer 2025/2024
     (Johnson 2023 / O'Connor 2024-2023 do not exist in the SCT - not NEOs those years)
   - GL x10: Darden 2024/2023, Kalmbach 2024, Majors 2024, Mitchell 2025/2024/2023,
     Hensley 2025/2024/2023
   - MAA x7: Bolton 2025, Hill 2024/2023, DelPriore 2024/2023, Argo 2024/2023
   - GPN x4: Loy 2025, Green 2025/2024/2023
     (Cortopassi 2023 is an all-dash SCT row - not an NEO that year)
   CTVA Eathington 2025 / King 2024+2023 / Eathington 2023 / Fuerer 2024 carry the
   filing's own $1 arithmetic gaps (kept verbatim).
3. GPN title repairs to SCT-verbatim: Bready "Chair of the Board" -> "Chief Executive Officer"
   (x3 rows; also clears the 6b no-CEO-token guard warning), Whipple "Executive Vice President"
   -> "Chief Financial Officer" (x3 rows).
4. Company aggregates recomputed (total_neo_compensation = sum of latest-year NEO totals,
   neo_count = latest-year NEO count) for CTVA/GL/MAA/GPN. Note: 430/500 companies still
   carry aggregates from the pre-2025-proxy cycle (systematic staleness, flagged for a
   dedicated bulk run - NOT touched here).

Net: 6791 -> 6819 records (+28). All 28 new rows carry _total_source def14a_verified_20260918.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260918_0600_pre_missingrows.json")

SRC = "def14a_verified_20260918"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
shutil.copy2(JSON_PATH, BACKUP)
print("backup:", BACKUP)

companies = {c["ticker"]: c for c in data["companies"]}
added = 0
repaired = 0

def find(ticker, name, year):
    c = companies[ticker]
    hits = [e for e in c["executives"] if e.get("name") == name and e.get("year") == year]
    assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
    return hits[0]

def add(ticker, row):
    global added
    c = companies[ticker]
    assert not [e for e in c["executives"] if e["name"] == row["name"] and e["year"] == row["year"]], \
        f"duplicate {ticker} {row['name']} {row['year']}"
    row["_total_source"] = SRC
    c["executives"].append(row)
    added += 1

def rep(ticker, name, year, note, **fields):
    global repaired
    e = find(ticker, name, year)
    for k, v in fields.items():
        e[k] = v
    e["_repair_note_20260918_0600"] = note
    repaired += 1

# ---------------- MAA: column-shift repair (8 existing rows) ----------------
for (name, year) in [
    ("A Clay Holder", 2025), ("A Clay Holder", 2024),
    ("A. Bradley Hill", 2025),
    ("Amber Fairbanks", 2025),
    ("H. Eric Bolton Jr.", 2024), ("H. Eric Bolton Jr.", 2023),
    ("Robert J. DelPriore", 2025),
    ("Timothy Argo", 2025),
]:
    e = find("MAA", name, year)
    old_opt, old_neip = e["option_awards"], e["non_equity_incentive"]
    rep("MAA", name, year,
        "2026-09-18 06:00 PT: column-shift repair - MAA SCT has no Option Awards column; "
        f"option_awards {old_opt} -> non_equity_incentive, non_equity_incentive {old_neip} -> all_other, "
        "option_awards=0; filing components now foot exactly to filing total",
        option_awards=0, non_equity_incentive=old_opt, all_other=old_neip)

# ---------------- MAA: 7 missing rows ----------------
MAA_ACC = "0001140361-26-013212"
maa_new = [
    ("H. Eric Bolton Jr.", "Former CEO, Executive Chairman", 2025, 884988, 0, 3826747, 942007, 221247, 5874989),
    ("A. Bradley Hill", "CEO and President", 2024, 596162, 500, 1680031, 860206, 60647, 3197546),
    ("A. Bradley Hill", "CEO and President", 2023, 496743, 500, 1173086, 729960, 77904, 2478193),
    ("Robert J. DelPriore", "EVP and CAO", 2024, 582259, 500, 1496421, 729498, 118326, 2927004),
    ("Robert J. DelPriore", "EVP and CAO", 2023, 562469, 500, 1453743, 849706, 127785, 2994203),
    ("Timothy Argo", "EVP and CSAO", 2024, 383910, 500, 430770, 328593, 45401, 1189174),
    ("Timothy Argo", "EVP and CSAO", 2023, 375692, 500, 412506, 368815, 40813, 1198326),
]
for name, title, yr, sal, bon, stk, neip, allo, tot in maa_new:
    assert sal + bon + stk + neip + allo == tot, (name, yr)
    add("MAA", {"name": name, "title": title, "year": yr, "salary": sal, "bonus": bon,
                "stock_awards": stk, "option_awards": 0, "non_equity_incentive": neip,
                "pension_nqdc": 0, "all_other": allo, "total": tot, "_accession": MAA_ACC})

# ---------------- CTVA: 7 missing rows ----------------
CTVA_ACC = "0001193125-26-116069"
ctva_new = [
    ("Samuel R. Eathington", "EVP, Chief Technology & Digital Officer", 2025, 694365, 0, 1320076, 330007, 1320500, 0, 107992, 3772941),
    ("Samuel R. Eathington", "EVP, Chief Technology & Digital Officer", 2024, 675962, 0, 1200051, 300001, 537300, 0, 141404, 2854718),
    ("Samuel R. Eathington", "EVP, Chief Technology & Digital Officer", 2023, 645962, 0, 1120099, 280002, 472550, 0, 171551, 2690163),
    ("Robert D. King", "EVP, Crop Protection Business Unit", 2024, 675962, 0, 1280069, 320015, 396900, 0, 109876, 2782821),
    ("Robert D. King", "EVP, Crop Protection Business Unit", 2023, 641923, 0, 1200079, 300009, 283400, 0, 118627, 2544037),
    ("Cornel B. Fuerer", "Former SVP, Chief Legal & Public Affairs Officer & Secretary", 2025, 680192, 0, 1320076, 330007, 1106275, 0, 122736, 3559286),
    ("Cornel B. Fuerer", "Former SVP, Chief Legal & Public Affairs Officer & Secretary", 2024, 642385, 0, 1200051, 300001, 433024, 0, 127166, 2702626),
]
for name, title, yr, sal, bon, stk, opt, neip, pen, allo, tot in ctva_new:
    s = sal + bon + stk + opt + neip + pen + allo
    assert abs(s - tot) <= 1, (name, yr, s, tot)  # $1 gaps are the filing's own arithmetic, kept verbatim
    add("CTVA", {"name": name, "title": title, "year": yr, "salary": sal, "bonus": bon,
                 "stock_awards": stk, "option_awards": opt, "non_equity_incentive": neip,
                 "pension_nqdc": pen, "all_other": allo, "total": tot, "_accession": CTVA_ACC})

# ---------------- GL: 10 missing rows ----------------
GL_ACC = "0000320335-26-000135"
gl_new = [
    ("J. Matthew Darden", "Co-Chairman and Chief Executive Officer", 2024, 900000, 2978880, 2432880, 1967580, 138054, 41772, 8459166),
    ("J. Matthew Darden", "Co-Chairman and Chief Executive Officer", 2023, 850000, 2008568, 2015625, 1535000, 399676, 52027, 6860896),
    ("Thomas P. Kalmbach", "Executive Vice President and Chief Financial Officer", 2024, 572000, 1168440, 780549, 560000, 315588, 38744, 3435321),
    ("Michael C. Majors", "Executive Vice President and Chief Strategy Officer", 2024, 515000, 832032, 834613, 470000, 615160, 17111, 3283916),
    ("R. Brian Mitchell", "Executive Vice President, General Counsel and Chief Risk Officer", 2025, 557669, 1186373, 487024, 425000, 958590, 39847, 3654503),
    ("R. Brian Mitchell", "Executive Vice President, General Counsel and Chief Risk Officer", 2024, 515000, 796080, 794065, 445000, 413028, 34303, 2997476),
    ("R. Brian Mitchell", "Executive Vice President, General Counsel and Chief Risk Officer", 2023, 495000, 773546, 774000, 300000, 585923, 30917, 2959386),
    ("Robert E. Hensley", "Executive Vice President and Chief Investment Officer", 2025, 554654, 1196568, 495008, 435000, 254110, 24859, 2960199),
    ("Robert E. Hensley", "Executive Vice President and Chief Investment Officer", 2024, 510000, 955296, 635252, 470000, 250686, 10325, 2831559),
    ("Robert E. Hensley", "Executive Vice President and Chief Investment Officer", 2023, 485000, 837406, 561150, 360000, 195386, 13496, 2452438),
]
for name, title, yr, sal, stk, opt, neip, pen, allo, tot in gl_new:
    assert sal + stk + opt + neip + pen + allo == tot, (name, yr)
    add("GL", {"name": name, "title": title, "year": yr, "salary": sal,
               "stock_awards": stk, "option_awards": opt, "non_equity_incentive": neip,
               "pension_nqdc": pen, "all_other": allo, "total": tot, "_accession": GL_ACC})

# ---------------- GPN: 4 missing rows ----------------
GPN_ACC = "0001104659-26-029453"
gpn_new = [
    ("Ryan J. Loy", "Chief Technology Officer", 2025, 416667, 500000, 4006820, 875027, 576102, 78026, 6452642),
    ("David L. Green", "Chief Administrative Officer", 2025, 695000, 0, 3070536, 1012516, 1153125, 102472, 6033649),
    ("David L. Green", "Chief Administrative Officer", 2024, 685000, 0, 2545616, 825007, 798162, 114064, 4967849),
    ("David L. Green", "Chief Administrative Officer", 2023, 675000, 0, 2457004, 775029, 684045, 119183, 4710261),
]
for name, title, yr, sal, bon, stk, opt, neip, allo, tot in gpn_new:
    assert sal + bon + stk + opt + neip + allo == tot, (name, yr)
    row = {"name": name, "title": title, "year": yr, "salary": sal,
           "stock_awards": stk, "option_awards": opt, "non_equity_incentive": neip,
           "all_other": allo, "total": tot, "_accession": GPN_ACC}
    if bon:
        row["bonus"] = bon
    add("GPN", row)

# ---------------- GPN: title repairs (SCT-verbatim) ----------------
for yr in (2025, 2024, 2023):
    rep("GPN", "Cameron M. Bready", yr,
        "2026-09-18 06:00 PT: title -> SCT-verbatim 'Chief Executive Officer' (was 'Chair of the Board')",
        title="Chief Executive Officer")
    rep("GPN", "Joshua J. Whipple", yr,
        "2026-09-18 06:00 PT: title -> SCT-verbatim 'Chief Financial Officer' (was 'Executive Vice President')",
        title="Chief Financial Officer")

# ---------------- aggregates: CTVA / GL / MAA / GPN ----------------
for ticker in ("CTVA", "GL", "MAA", "GPN"):
    c = companies[ticker]
    ly = max(c["available_years"])
    rows = [e for e in c["executives"] if e["year"] == ly]
    old_agg, old_n = c["total_neo_compensation"], c["neo_count"]
    c["total_neo_compensation"] = sum(e["total"] for e in rows)
    c["neo_count"] = len(rows)
    print(f"{ticker}: agg {old_agg} -> {c['total_neo_compensation']}, neo_count {old_n} -> {c['neo_count']} ({ly}, {len(rows)} rows)")

# ---------------- metadata re-sync ----------------
n = sum(len(c["executives"]) for c in data["companies"])
dq = data["metadata"]["data_quality"]
dq["def14a_verified_20260918"] = dq.get("def14a_verified_20260918", 0) + added
data["metadata"]["total_neo_records"] = n
data["metadata"]["total_executives"] = n
data["metadata"]["description"] = f"500 companies, {n} NEO records, 500 companies enriched"
data["metadata"]["last_audit"] = "2026-09-18"
data["metadata"]["last_updated"] = "2026-09-18"

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))

print(f"added={added} repaired={repaired} total_records={n}")
