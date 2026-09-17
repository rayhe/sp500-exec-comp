"""IN-BATCH CORRECTION (2026-09-17 ~02:40 PT): the 21 pension_nqdc assignments
below were REVERTED before commit. The pension-aware 8-component recheck (per the
2026-09-14 22:00 pension-queue retirement) showed all 21 rows already footed
exactly with pension in pension_change; the assignments would have double-counted.
Net pension changes from this batch: zero. The committed data also reflects
follow-up fixes NOT in this script: PPL titles corrected to SCT-verbatim
abbreviated forms, PM Kennedy 2025/2024 titles -> 'CEO PMI U.S.', company
aggregates recomputed (AME/TFC/PPL), metadata buckets re-synced. This script is
kept as an audit artifact of the initial pass, not a reproducer of final state.
"""
#!/usr/bin/env python3
"""2026-09-17 02:00 PT primary-source DQ batch: dropped-pension-column repair.

Bug class: the original EDGAR parse dropped the SCT "Change in Pension Value /
NQDC Earnings" column (stored 0/None) for 21 NEO rows across 5 companies
(SO x13, PM x1, PPL x1, TFC x3, AME x3). Detected by a global
sum(components)-vs-total scan (41 mismatch rows; the other 20 are the known
filing-side component_mismatch bucket, untouched). All 21 repaired rows were
re-extracted verbatim from the 2026 DEF 14A SCTs (5 filings re-fetched from
EDGAR this run) and now foot exactly.

Same pass also repaired, from the same filings:
- TFC Lesher 2024: all_other 149,511 -> 207,396, total 14,573,637 -> 14,631,522
  (parser misread the All Other cell).
- AME Hardin 2024: total 2,415,254 -> 2,415,255 (stored total off by $1 vs
  filing; components foot to the filing's printed total).
- AME Hardin 2023: name "Electronic Instruments" -> "John W. Hardin"
  (title-fragment bleed into the name field).
- Title-shift repairs (each NEO had been assigned the previous NEO's title):
  PPL Sorgi/Bergstein/Stark/Del Vecchio/Bonenberger, TFC Maguire/Lesher/
  Wilson/Bender/Cummins, AME Zapico/Puri/Hard/Hermance, SO Tucker, PM Kennedy
  ("CEO PMI U" truncation).
- 6 missing NEO rows restored from the SCTs: TFC Wilson 2025/2024, PPL Stark
  2024, AME Oscher 2025/2024/2023. (TFC Wilson 2025 carries the filing's own
  $1 arithmetic inconsistency: components sum 6,287,511 vs printed total
  6,287,512; kept verbatim.)

Net: 6781 -> 6787 records (+6). All 52 touched rows (46 existing + 6 new)
carry _total_source def14a_verified_20260917.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260917_0200_pre_pensiondrop.json")

SRC = "def14a_verified_20260917"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
shutil.copy2(JSON_PATH, BACKUP)

companies = {c["ticker"]: c for c in data["companies"]}
touched = 0

def rep(ticker, name, year, **fields):
    global touched
    c = companies[ticker]
    hits = [e for e in c["executives"]
            if e.get("name") == name and e.get("year") == year]
    assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
    e = hits[0]
    for k, v in fields.items():
        e[k] = v
    e["_total_source"] = SRC
    touched += 1

# ---------------------------------------------------------------- SO: 13 pension drops
SO_PENSION = {
    ("Christopher C. Womack", 2025): 8961516,
    ("Christopher C. Womack", 2024): 7142735,
    ("Christopher C. Womack", 2023): 9352563,
    ("David P. Poroch", 2025): 1217519,
    ("Stanley W. Connally, Jr", 2024): 332668,
    ("Stanley W. Connally, Jr", 2025): 1590775,
    ("Kimberly S. Greene", 2025): 1532018,
    ("Kimberly S. Greene", 2024): 716640,
    ("Kimberly S. Greene", 2023): 1076497,
    ("J. Jeffrey Peoples", 2025): 3804829,
    ("Daniel S. Tucker", 2025): 3403558,
    ("Daniel S. Tucker", 2024): 622033,
    ("Daniel S. Tucker", 2023): 1735519,
}
for (name, year), pen in SO_PENSION.items():
    rep("SO", name, year, pension_nqdc=pen)
# SO Tucker title: filing SCT reads "Former Executive Vice President and CFO"
for y in (2025, 2024, 2023):
    rep("SO", "Daniel S. Tucker", y,
        title="Former Executive Vice President and CFO, Southern Company")

# ---------------------------------------------------------------- PM
rep("PM", "Stacey Kennedy", 2023, pension_nqdc=1752402, title="CEO PMI U.S.")

# ---------------------------------------------------------------- PPL
rep("PPL", "Vincent Sorgi", 2024, pension_nqdc=1483614)
for y in (2025, 2024, 2023):
    rep("PPL", "Vincent Sorgi", y,
        title="President and Chief Executive Officer (CEO)")
for y in (2025, 2024, 2023):
    rep("PPL", "Joseph P. Bergstein, Jr.", y,
        title="Executive Vice President and Chief Financial Officer (CFO)")
for y in (2025, 2023):
    rep("PPL", "Wendy E. Stark", y,
        title="Executive Vice President - Utilities and Chief Legal Officer (CLO)")
for y in (2025, 2024):
    rep("PPL", "Dean A. Del Vecchio", y,
        title="Executive Vice President and Chief Technology & Innovation Officer (CTIO)")
rep("PPL", "David J. Bonenberger", 2025,
    title="Executive Vice President and Chief Operating Officer-Utilities")

# ---------------------------------------------------------------- TFC
rep("TFC", "William H. Rogers, Jr", 2023, pension_nqdc=1107866)
rep("TFC", "Hugh S. Cummins III", 2024, pension_nqdc=480156)
rep("TFC", "Hugh S. Cummins III", 2023, pension_nqdc=701917)
rep("TFC", "Kristin Lesher", 2024, all_other=207396, total=14631522)
for y in (2025, 2024, 2023):
    rep("TFC", "Michael B. Maguire", y,
        title="Senior Executive Vice President and Chief Financial Officer")
for y in (2025, 2024):
    rep("TFC", "Kristin Lesher", y,
        title="Senior Executive Vice President and Chief Wholesale Banking Officer")
rep("TFC", "Dontá L. Wilson", 2023,
    title="Senior Executive Vice President and Chief Consumer and Small Business Banking Officer")
rep("TFC", "Bradley D. Bender", 2025,
    title="Senior Executive Vice President and Chief Risk Officer")
for y in (2025, 2024, 2023):
    rep("TFC", "Hugh S. Cummins III", y,
        title="Former Vice Chair and Chief Operating Officer")

# ---------------------------------------------------------------- AME
rep("AME", "David A. Zapico", 2024, pension_nqdc=212725)
rep("AME", "David A. Zapico", 2023, pension_nqdc=335760)
rep("AME", "John W. Hardin", 2024, pension_nqdc=81548, total=2415255)
# Hardin 2023: name-bleed repair
c = companies["AME"]
hits = [e for e in c["executives"]
        if e.get("name") == "Electronic Instruments" and e.get("year") == 2023]
assert len(hits) == 1
hits[0]["name"] = "John W. Hardin"
hits[0]["_total_source"] = SRC
touched += 1
for y in (2025, 2024, 2023):
    rep("AME", "David A. Zapico", y,
        title="Chairman and Chief Executive Officer")
for y in (2025, 2024):
    rep("AME", "Dalip M. Puri", y,
        title="Executive Vice President\u2013Chief Financial Officer")
for y in (2025, 2024, 2023):
    rep("AME", "John W. Hardin", y,
        title="President\u2013Electronic Instruments")
rep("AME", "David F. Hermance", 2025,
    title="President\u2013Electromechanical Group")

# ---------------------------------------------------------------- new rows (filing-verbatim)
def add(ticker, name, title, year, salary, bonus, stock, options, non_eq,
        pension, all_other, total, filing_url):
    global touched
    c = companies[ticker]
    c["executives"].append({
        "name": name, "title": title, "year": year,
        "salary": salary, "bonus": bonus,
        "stock_awards": stock, "option_awards": options,
        "non_equity_incentive": non_eq, "pension_nqdc": pension,
        "all_other": all_other, "total": total,
        "_total_source": SRC,
    })
    touched += 1

TFC_URL = companies["TFC"]["filing_url"]
PPL_URL = companies["PPL"]["filing_url"]
AME_URL = companies["AME"]["filing_url"]
WT = "Senior Executive Vice President and Chief Consumer and Small Business Banking Officer"
add("TFC", "Dontá L. Wilson", WT, 2025,
    770833, 1334, 2526373, None, 1616263, 1245844, 126864, 6287512, TFC_URL)
add("TFC", "Dontá L. Wilson", WT, 2024,
    750000, None, 6412734, None, 2399440, 9160, 98332, 9669666, TFC_URL)
add("PPL", "Wendy E. Stark",
    "Executive Vice President - Utilities and Chief Legal Officer (CLO)", 2024,
    612907, None, 1213157, None, 604047, None, 110628, 2540739, PPL_URL)
add("AME", "Ronald J. Oscher", "Chief Administrative Officer", 2025,
    597958, 64587, 992427, 246274, 476904, None, 127042, 2505193, AME_URL)
add("AME", "Ronald J. Oscher", "Chief Administrative Officer", 2024,
    582663, 83204, 769882, 218898, 261907, None, 151839, 2068393, AME_URL)
add("AME", "Ronald J. Oscher", "Chief Administrative Officer", 2023,
    559715, 137522, 704237, 247334, 379527, None, 155566, 2183901, AME_URL)

# ---------------------------------------------------------------- verify + metadata
FIELDS = ["salary", "bonus", "stock_awards", "option_awards",
          "non_equity_incentive", "pension_nqdc", "all_other"]
n = 0
worst = []
for co in data["companies"]:
    for e in co.get("executives", []):
        n += 1
        s = sum((e.get(f) or 0) for f in FIELDS)
        tot = e.get("total")
        if tot is not None and abs(s - tot) > 2 and \
                e.get("_total_source") != "component_mismatch":
            worst.append((abs(s - tot), co["ticker"], e.get("name"), e.get("year")))
assert n == 6787, f"record count drift: {n}"
assert not worst, f"non-mismatch rows still off: {worst[:5]}"

meta = data["metadata"]
meta["total_neo_records"] = n
meta["total_executives"] = n
meta["title_coverage"] = f"{n}/{n}"
meta["description"] = meta["description"].replace("6781 NEO records", "6787 NEO records")
meta["last_updated"] = "2026-09-17"

from collections import Counter
cnt = Counter()
for co in data["companies"]:
    for e in co.get("executives", []):
        cnt[e.get("_total_source")] += 1
for block in ("data_quality", "data_quality_detailed"):
    dq = meta[block]
    for k, v in cnt.items():
        if k in dq:
            dq[k] = v
    dq[SRC] = cnt[SRC]
    dq["verified_total"] = sum(v for k, v in cnt.items() if k != "component_mismatch")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    # Repo format discipline (per AGENTS.md 2026-09-14 lesson): pretty-printed
    # indent=2 + trailing newline. A compact single-line rewrite produces a
    # 114K-line diff; the "compact" comment in the 09-13 script was the bug.
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"records={n} touched={touched} {SRC}={cnt[SRC]} verified_total={meta['data_quality']['verified_total']}")
