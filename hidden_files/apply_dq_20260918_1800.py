#!/usr/bin/env python3
"""2026-09-18 18:00 PT primary-source DQ batch: missing-NEO-row restoration,
column-shift repair, identity re-attribution, title-bleed cleanup.

All values verified verbatim against the companies' latest DEF 14A Summary
Compensation Tables (re-fetched from EDGAR this run; raw filings + ledger in
the goal hidden workspace dq_20260918_1800/). Nothing hand-transcribed: every
value below was re-extracted post-compaction with a robust table parser after
the pre-compaction extraction method was found to hallucinate component values
(VTR/NEE). Corrections from that audit are baked in:
  - VTR stored components were CORRECT as-filed; only titles + 4 missing rows.
  - NEE Brian Bolster 2024 corrected to filing (628,462/1,500,000/5,324,182/
    679,996/1,236,900/0/244,870/9,614,410).
  - SYY Ronald L. Phillips 2024 discovered as a second missing FY2024 NEO row
    (2024 proxy SCT lists 5 FY2024 NEOs; dataset had 3).
  - WTW "pension drop" was a phantom (script used wrong field name); WTW
    values already correct, titles only.

Classes repaired:
1. Missing NEO rows restored (20): VTR x4 (Probst/Bulgarelli/Hutchens/Roberts
   2024); NEE x8 (Pimentel 2024, Sieving 2024/2023, Crews 2025/2024/2023,
   Kujawa 2024, Bolster 2024); IP x2 (Hamic 2025, Roman 2025); SYY x2
   (Peck 2024, Phillips 2024); STLD x1 (Graham 2024); PSA x1 (Russell 2024);
   AKAM x1 (McGowan 2023); DOV x1 (Bors 2023).
2. IP column shift (10 rows): IP SCT has no Option Awards column; the old
   parse filed NEIP under option_awards and pension under non_equity_incentive.
   Repaired: option_awards=0, non_equity_incentive=<filed NEIP>,
   pension_nqdc=<filed pension>. Components foot exactly.
   IP 'Lance T Loeffler' 2023/2024 rows are W. Thomas Hamic's (renamed, title
   fixed). Lance 2025 is legitimate.
   IP Roman 2025: $1,635,000 severance has no schema field; folded into
   all_other (1,841,167 = 1,635,000 + 206,167 filed all-other) with a note
   preserving the split; components foot to filing total.
3. AKAM identity re-attribution + all_other drops + Leighton 2023 shift:
   'Rick McConnell' 2024 -> Paul Joseph 2024; 'Robert Blumofe' 2023 ->
   Paul Joseph 2023; 'Paul Joseph' 2023 -> Mani Sundaram 2023. Filed
   $6,000/$9,000/$6,173 all-other restored on 2024/2025 rows (totals corrected).
   Leighton 2023 salary/bonus shift repaired (salary=1, stock=13,384,974).
   Joseph title -> 'EVP, Global Sales and Services' (was 'EVP and General
   Counsel').
4. Title repairs (SCT-verbatim): VTR x11 (one-row title shift + Cafaro/Bulgarelli
   footnote bleed), WTW x14 (footnote bleed + trailing honorifics), NEE Bolster
   2025 ('Chairman' -> 'President and Chief Executive Officer of NextEra
   Energy Resources').
5. MKTX adjudicated: Christophe Roupie was NOT a 2024 NEO (2026 DEF 14A lists
   Bieler, McVey, McPherson, Panchal, Gerosa). No row added; gap closed as
   adjudicated, not missing.

Aggregates re-anchored to fiscal_year (2024) on all 9 touched tickers; PSA CEO
anchor moves to Russell's FY2024 total (9,502,226), resolving the known
CEO-anchor transition trip.
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260918_1800_pre_dqbatch.json")

SRC = "def14a_verified_20260918"
NOTE = "2026-09-18 18:00 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

added = 0
repaired = 0

def foot(e):
    return sum((e.get(k) or 0) for k in (
        "salary", "bonus", "stock_awards", "option_awards",
        "non_equity_incentive", "pension_nqdc", "all_other"))

def get(ticker, name, year):
    hits = [e for e in companies[ticker]["executives"]
            if e["name"] == name and e["year"] == year]
    assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
    return hits[0]

def accession(ticker):
    u = companies[ticker]["filing_url"]
    m = re.search(r"/(\d{10}-\d{2}-\d{6})/", u)
    return m.group(1) if m else ""

# ---------------- pre-write assertions ----------------
n0 = sum(len(c["executives"]) for c in data["companies"])
assert n0 == 6843, f"row count {n0} != 6843"
# spot-check stored values we will mutate
assert get("IP", "Lance T Loeffler", 2024)["option_awards"] == 1104460
assert get("IP", "Lance T Loeffler", 2024)["non_equity_incentive"] == 0
assert get("AKAM", "Rick McConnell", 2024)["total"] == 4772293
assert get("AKAM", "Dr. F. Thomson Leighton", 2023)["bonus"] == 13384974
assert get("AKAM", "Dr. F. Thomson Leighton", 2023)["salary"] == 0
assert get("AKAM", "Paul Joseph", 2023)["stock_awards"] == 3644849
assert get("AKAM", "Robert Blumofe", 2023)["stock_awards"] == 3847084
assert get("VTR", "Debra A. Cafaro", 2025)["total"] == 17501073
assert get("VTR", "Debra A. Cafaro", 2025)["salary"] == 1162720
assert get("WTW", "Carl Hess", 2025)["title"] == "CEO Mr"
assert get("PSA", "Joseph D. Russell, Jr", 2025)["total"] == 9909777
assert companies["PSA"]["total_compensation"] == 9909777
print("pre-write assertions OK")

def add_row(ticker, name, title, year, note, _verbatim_mismatch=False, **vals):
    global added
    c = companies[ticker]
    assert not [e for e in c["executives"] if e["name"] == name and e["year"] == year], \
        f"duplicate {ticker} {name} {year}"
    row = {"name": name, "title": title, "year": year}
    row.update(vals)
    if _verbatim_mismatch:
        row["_total_source"] = "component_mismatch"
        note += ("; genuine filing-side arithmetic gap (components sum "
                 f"{foot(row):,} vs printed total {row['total']:,}), kept verbatim")
    else:
        assert foot(row) == row["total"], f"{ticker} {name} {year} does not foot"
        row["_total_source"] = SRC
    row["_accession"] = accession(ticker)
    row["_repair_note_20260918_1800"] = note
    c["executives"].append(row)
    added += 1

def rep(ticker, name, year, note, **fields):
    global repaired
    e = get(ticker, name, year)
    for k, v in fields.items():
        e[k] = v
    e["_total_source"] = SRC
    prev = e.get("_repair_note_20260918_1800", "")
    e["_repair_note_20260918_1800"] = (prev + "; " if prev else "") + note
    repaired += 1

def rep_title(ticker, name, year, new_title):
    global repaired
    e = get(ticker, name, year)
    if e["title"] != new_title:
        e["_repair_note_20260918_1800"] = (
            (e.get("_repair_note_20260918_1800", "") + "; " if e.get("_repair_note_20260918_1800") else "") +
            f"{NOTE}: title -> SCT-verbatim '{new_title}' (was '{e['title']}')")
        e["title"] = new_title
        repaired += 1

# ---------------- 1a. VTR: 4 missing 2024 rows ----------------
VTR_T = {
    "Debra A. Cafaro": "Chairman and Chief Executive Officer",
    "Robert F. Probst": "Executive Vice President and Chief Financial Officer",
    "Peter J. Bulgarelli": "Executive Vice President, Outpatient Medical and Research, Ventas, Inc. President and CEO, Lillibridge Healthcare Services, Inc.",
    "J. Justin Hutchens": "Executive Vice President, Senior Housing and Chief Investment Officer",
    "Carey S. Roberts": "Executive Vice President, General Counsel, Ethics & Compliance Officer and Corporate Secretary",
}
for nm, yr, sal, stk, neip, ao, tot in [
    ("Robert F. Probst", 2024, 699111, 2901171, 1552152, 42471, 5194905),
    ("Peter J. Bulgarelli", 2024, 596923, 2093163, 985591, 31140, 3706817),
    ("J. Justin Hutchens", 2024, 630000, 2717695, 1398713, 31114, 4777522),
    ("Carey S. Roberts", 2024, 571198, 2003002, 1026321, 29539, 3630060),
]:
    add_row("VTR", nm, VTR_T[nm], yr,
            f"{NOTE}: missing FY2024 NEO row restored from 2026 DEF 14A SCT (2025 proxy cross-checked)",
            salary=sal, stock_awards=stk, non_equity_incentive=neip,
            all_other=ao, total=tot)
for e in companies["VTR"]["executives"]:
    rep_title("VTR", e["name"], e["year"], VTR_T[e["name"]])

# ---------------- 1b. NEE: 8 missing rows ----------------
for nm, ti, yr, sal, bon, stk, opt, neip, pen, ao, tot, *rest in [
    ("Armando Pimentel, Jr.", "President and Chief Executive Officer of Florida Power & Light Company", 2024, 1000000, 0, 6532879, 1199996, 1970000, 359127, 289155, 11351157),
    ("Charles E. Sieving", "Executive Vice President & General Counsel", 2024, 1274300, 0, 2775559, 509900, 1775100, 525247, 225166, 7085272),
    ("Charles E. Sieving", "Executive Vice President & General Counsel", 2023, 1274300, 0, 2665736, 509894, 1641300, 423332, 207615, 6772178, True),
    ("Terrell Kirk Crews II", "Former Executive Vice President Chief Risk Officer of NextEra Energy", 2025, 784405, 0, 2234077, 419093, 1094000, 240443, 117339, 4889357),
    ("Terrell Kirk Crews II", "Former Executive Vice President Chief Risk Officer of NextEra Energy", 2024, 730300, 0, 2132490, 391689, 950800, 227823, 112415, 4545517),
    ("Terrell Kirk Crews II", "Former Executive Vice President Chief Risk Officer of NextEra Energy", 2023, 730300, 0, 2048115, 391691, 940600, 204299, 103552, 4418556, True),
    ("Rebecca J. Kujawa", "President and Chief Executive Officer of NextEra Energy Resources", 2024, 1100000, 0, 7403858, 1359996, 2090000, 453542, 195464, 12602860),
    ("Brian W. Bolster", "President and Chief Executive Officer of NextEra Energy Resources", 2024, 628462, 1500000, 5324182, 679996, 1236900, 0, 244870, 9614410),
]:
    add_row("NEE", nm, ti, yr,
            f"{NOTE}: missing NEO row restored from 2026 DEF 14A SCT",
            _verbatim_mismatch=bool(rest),
            salary=sal, bonus=bon, stock_awards=stk, option_awards=opt,
            non_equity_incentive=neip, pension_nqdc=pen, all_other=ao, total=tot)
rep_title("NEE", "Brian W. Bolster", 2025,
          "President and Chief Executive Officer of NextEra Energy Resources")

# ---------------- 1c/2. IP: column shift + renames + 2 new rows ----------------
for e in companies["IP"]["executives"]:
    old_opt, old_neip = e.get("option_awards") or 0, e.get("non_equity_incentive") or 0
    rep("IP", e["name"], e["year"],
        f"{NOTE}: column-shift repair - IP SCT has no Option Awards column; old parse filed "
        f"NEIP ({old_opt}) under option_awards and pension ({old_neip}) under non_equity_incentive; "
        "now option_awards=0, non_equity_incentive=<filed NEIP>, pension_nqdc=<filed pension>; foots exactly",
        option_awards=0, non_equity_incentive=old_opt, pension_nqdc=old_neip)
    assert foot(get("IP", e["name"], e["year"])) == get("IP", e["name"], e["year"])["total"]
# Loeffler 2023/2024 are Hamic's rows
for yr in (2023, 2024):
    e = get("IP", "Lance T Loeffler", yr)
    e["_repair_note_20260918_1800"] += (
        f"; {NOTE}: identity -> SCT-verbatim 'W. Thomas Hamic' (2026 DEF 14A SCT "
        f"lists Hamic, not Loeffler, for these rows); title -> SCT-verbatim")
    e["name"] = "W. Thomas Hamic"
    e["title"] = "Executive Vice President and President, PS NA"
    repaired += 1
add_row("IP", "W. Thomas Hamic", "Executive Vice President and President, PS NA", 2025,
        f"{NOTE}: missing FY2025 NEO row restored from 2026 DEF 14A SCT",
        salary=750000, bonus=0, stock_awards=2727170, option_awards=0,
        non_equity_incentive=659250, pension_nqdc=177320, all_other=191179, total=4504919)
add_row("IP", "Joy N. Roman", "Former Senior Vice President, Chief People and Strategy Officer", 2025,
        f"{NOTE}: missing FY2025 NEO row restored from 2026 DEF 14A SCT; $1,635,000 severance "
        "has no schema field - folded into all_other (1,841,167 = 1,635,000 severance + 206,167 "
        "filed all-other); components foot to filing total 6,016,552",
        salary=259423, bonus=500000, stock_awards=3199295, option_awards=0,
        non_equity_incentive=216667, pension_nqdc=0, all_other=1841167, total=6016552)

# ---------------- 1d. SYY: Peck + Phillips 2024 ----------------
add_row("SYY", "Thomas R. Peck, Jr.", "Executive Vice President, Chief Information and Digital Officer", 2024,
        f"{NOTE}: missing FY2024 NEO row restored from 2026 DEF 14A SCT",
        salary=726354, bonus=0, stock_awards=2029257, option_awards=514479,
        non_equity_incentive=687000, pension_nqdc=0, all_other=55877, total=4012967)
add_row("SYY", "Ronald L. Phillips", "Executive Vice President and Chief Human Resources Officer", 2024,
        f"{NOTE}: missing FY2024 NEO row restored from 2024 DEF 14A SCT (5 FY2024 NEOs filed; "
        "dataset had 3 - Phillips has no interior year-gap so the gap screen missed him)",
        salary=682363, bonus=0, stock_awards=1635867, option_awards=415180,
        non_equity_incentive=646000, pension_nqdc=0, all_other=80620, total=3460030)

# ---------------- 1e. STLD: Graham 2024 ----------------
add_row("STLD", "Christopher A. Graham", "Senior Vice President, Flat Roll Steel Group", 2024,
        f"{NOTE}: missing FY2024 NEO row restored from 2026 DEF 14A SCT",
        salary=670000, stock_awards=1823946, non_equity_incentive=1672320,
        all_other=70243, total=4236509)

# ---------------- 1f. PSA: Russell 2024 + CEO anchor ----------------
add_row("PSA", "Joseph D. Russell, Jr", "President and Chief Executive Officer", 2024,
        f"{NOTE}: missing FY2024 NEO row restored from 2026 DEF 14A SCT (stored 'Jr' without "
        "terminal period matches existing PSA identity; no duplicate created)",
        salary=1000000, bonus=0, stock_awards=4010813, option_awards=2882613,
        non_equity_incentive=1590000, all_other=18800, total=9502226)
companies["PSA"]["total_compensation"] = 9502226  # CEO anchor -> Russell FY2024

# ---------------- 1g/3. AKAM: re-attribution + all_other + Leighton shift + McGowan 2023 ----------------
# rename order avoids transient (name,year) collisions
e = get("AKAM", "Paul Joseph", 2023)
e["_repair_note_20260918_1800"] = (
    f"{NOTE}: identity -> SCT-verbatim 'Mani Sundaram' (2026 DEF 14A SCT: these are Sundaram's "
    f"2023 values; was misattributed to Paul Joseph); title -> SCT-verbatim")
e["name"] = "Mani Sundaram"
e["title"] = "EVP and GM, Security Technology Group"
repaired += 1
e = get("AKAM", "Robert Blumofe", 2023)
e["_repair_note_20260918_1800"] = (
    f"{NOTE}: identity -> SCT-verbatim 'Paul Joseph' (2026 DEF 14A SCT: these are Joseph's "
    f"2023 values 500,000/3,847,084/6,000/4,353,084; Blumofe was not a 2023 NEO); title -> SCT-verbatim")
e["name"] = "Paul Joseph"
e["title"] = "EVP, Global Sales and Services"
repaired += 1
rep("AKAM", "Rick McConnell", 2024,
    f"{NOTE}: identity -> SCT-verbatim 'Paul Joseph' (2026 DEF 14A SCT: these are Joseph's 2024 "
    "values; McConnell was not a 2024 NEO); filed $6,000 all-other restored (was dropped); "
    "title -> SCT-verbatim 'EVP, Global Sales and Services'",
    all_other=6000, total=4778293)
e = get("AKAM", "Rick McConnell", 2024)
e["name"] = "Paul Joseph"
e["title"] = "EVP, Global Sales and Services"
rep("AKAM", "Paul Joseph", 2025,
    f"{NOTE}: filed $9,000 all-other restored (was dropped); title 'EVP and General Counsel' -> "
    "SCT-verbatim 'EVP, Global Sales and Services'",
    all_other=9000, total=5328712, title="EVP, Global Sales and Services")
rep("AKAM", "Dr. F. Thomson Leighton", 2023,
    f"{NOTE}: salary/bonus column-shift repair - filing shows salary $1 and stock awards "
    "$13,384,974; old parse zeroed salary and filed stock under bonus",
    salary=1, bonus=0, stock_awards=13384974)
rep("AKAM", "Edward McGowan", 2024,
    f"{NOTE}: filed $6,000 all-other restored (was dropped)", all_other=6000, total=5532232)
rep("AKAM", "Edward McGowan", 2025,
    f"{NOTE}: filed $6,173 all-other restored (was dropped)", all_other=6173, total=6198315)
rep("AKAM", "Adam Karon", 2024,
    f"{NOTE}: filed $6,000 all-other restored (was dropped)", all_other=6000, total=6822621)
rep("AKAM", "Adam Karon", 2025,
    f"{NOTE}: filed $9,000 all-other restored (was dropped)", all_other=9000, total=7725594)
rep("AKAM", "Mani Sundaram", 2024,
    f"{NOTE}: filed $6,000 all-other restored (was dropped)", all_other=6000, total=4968079)
rep("AKAM", "Mani Sundaram", 2025,
    f"{NOTE}: filed $9,000 all-other restored (was dropped)", all_other=9000, total=5442327)
add_row("AKAM", "Edward McGowan", "EVP, CFO and Treasurer", 2023,
        f"{NOTE}: missing FY2023 NEO row restored from 2026 DEF 14A SCT",
        salary=515000, bonus=0, stock_awards=4852329, option_awards=0,
        non_equity_incentive=0, pension_nqdc=0, all_other=6000, total=5373329)
for e in companies["AKAM"]["executives"]:
    assert foot(e) == e["total"], f"AKAM {e['name']} {e['year']} does not foot"

# ---------------- 1h. DOV: Bors 2023 ----------------
add_row("DOV", "Kimberly K. Bors", "SVP & CHRO", 2023,
        f"{NOTE}: missing FY2023 NEO row restored from 2024 DEF 14A SCT (2026 proxy confirms "
        "2023 NEO status; historical row, FY2024 aggregates unchanged)",
        salary=480900, bonus=335784, stock_awards=553324, option_awards=356416,
        non_equity_incentive=0, pension_nqdc=0, all_other=41402, total=1767826)

# ---------------- 4. WTW: title cleanup ----------------
WTW_T = {
    "Carl Hess": "CEO",
    "Andrew Krasner": "CFO",
    "Julie Gebauer": "President, HWC",
    "Lucy Clarke": "President, R&B",
    "Matthew Furman": "General Counsel",
}
for e in companies["WTW"]["executives"]:
    rep_title("WTW", e["name"], e["year"], WTW_T[e["name"]])

# ---------------- aggregates: fiscal_year anchoring ----------------
EXPECTED = {
    "VTR": (5, 31747422), "NEE": (6, 66802814), "IP": (3, 31896458),
    "SYY": (5, 32360985), "STLD": (5, 33623537), "PSA": (5, 30431841),
    "AKAM": (5, 37166148), "DOV": (6, 33118186), "WTW": (5, 31527394),
}
for ticker, (exp_n, exp_tot) in EXPECTED.items():
    c = companies[ticker]
    fy = c["fiscal_year"]
    rows = [e for e in c["executives"] if e["year"] == fy]
    assert len(rows) == exp_n, f"{ticker}: {len(rows)} FY rows != {exp_n}"
    tot = sum(e["total"] for e in rows)
    assert tot == exp_tot, f"{ticker}: FY sum {tot} != {exp_tot}"
    old = (c["neo_count"], c["total_neo_compensation"])
    c["neo_count"], c["total_neo_compensation"] = exp_n, exp_tot
    print(f"{ticker}: neo_count {old[0]}->{exp_n}, total_neo {old[1]:,}->{exp_tot:,}")

# ---------------- metadata re-sync ----------------
n = sum(len(c["executives"]) for c in data["companies"])
assert n == 6863, f"total {n} != 6863"
dq = data["metadata"]["data_quality"]
recount = {}
for c in data["companies"]:
    for e in c["executives"]:
        recount[e.get("_total_source", "?")] = recount.get(e.get("_total_source", "?"), 0) + 1
for k in list(dq.keys()):
    if k in recount:
        dq[k] = recount[k]
assert sum(recount.values()) == n
data["metadata"]["total_neo_records"] = n
data["metadata"]["total_executives"] = n
data["metadata"]["description"] = f"500 companies, {n} NEO records, 500 companies enriched"
data["metadata"]["last_audit"] = "2026-09-18"
data["metadata"]["last_updated"] = "2026-09-18"

shutil.copy2(JSON_PATH, BACKUP)
print("backup:", BACKUP)
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))

print(f"added={added} repaired={repaired} total_records={n}")
print("verified_total =", recount.get("verified", 0) + sum(v for k, v in recount.items() if k.startswith("def14a_verified")))
print("component_mismatch =", recount.get("component_mismatch", 0))
