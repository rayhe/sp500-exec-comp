#!/usr/bin/env python3
"""2026-09-25 14:00 PT: 13-company "Former"-titled CEO-anchor adjudication.

Backlog candidate #1 (panel 2026-09-25 03:40 / 06:35 / 07:45 / 11:30 PT):
the 13 remaining "Former"-titled CEO anchors (CHD CPB EXE HPQ HSIC INCY KR
MAS MNST PNW PRU SWK WDC). FE/TGT/USB are the same class but were not
panel-prioritized; they carry over to the next run.

Method (ORCL/NCLH 2026-09-25 06:00 PT precedent): for each company the
latest DEF 14A was fetched from EDGAR (curl, UA Kit/1.0) and read for
(1) leadership-transition prose, (2) the filed CEO Pay Ratio disclosure,
(3) the anchor-year (FY2024) SCT row for the anchor CEO. Local filing
copies lived in /tmp/sp500-batch38 (ephemeral, not committed).

Adjudication results (all anchors KEPT per least-false-statement: the
anchor person was the filed FY2024 PEO in every case; no successor has a
filed FY2024 SCT row):
- CHD (Church & Dwight, acc. 0001193125-26-115994): Farrell retired as
  President/CEO eff 2025-04-01 (Chairman to 2025-09-30); Richard A.
  Dierker appointed President/CEO eff 2025-04-02. Anchor stays Farrell
  FY2024 $12,284,216 (SCT-verified: 1,231,633 + 2,015,000 + 6,045,000 +
  2,499,000 + 493,583). Filed FY2025 pay ratio 120.7:1 (median $81,203;
  CEO Dierker $9,799,678): pay_ratio 157 -> 120.7, median 77,988 -> 81,203.
  ceo_tenure -> {2025, April, high, prose}.
- CPB (Campbell's, acc. 0001308179-25-000618): Mick J. Beekhuizen became
  CEO eff 2025-02-01 (Clouse out). Anchor stays Mark A. Clouse FY2024
  $12,260,000. Filed FY2025 ratio 128:1 (median $77,798; Beekhuizen
  annualized $9,927,739): pay_ratio 167 -> 128, median 73,352 -> 77,798.
  ceo_tenure -> {2025, February, high, prose}. HYGIENE: ceo_name "Mark A"
  -> "Mark A. Clouse" and 3 SCT rows ("Mark A" / "Clouse Former, President
  and Chief Executive Officer") -> "Mark A. Clouse" / "Former President
  and Chief Executive Officer" (filing's SCT principal-position wording,
  verbatim).
- EXE (Expand Energy, acc. 0001104659-26-048155): Dell'Osso was CEO for
  FY2025 ($9,879,106 = pay-ratio CEO comp); Steck Wichterich appointed
  Interim President/CEO 2026-02-06. Anchor stays Dell'Osso FY2024
  $8,974,550. Filed FY2025 ratio 62:1 (median $158,503): pay_ratio 58 ->
  62, median 154,646 -> 158,503. ceo_tenure was corrupt ({ceo_name:
  "Chris Lacy", start_year 2023} - Lacy is the EVP/GC/corporate secretary
  who signed the proxy, never CEO) -> {2026, February, high, prose}.
- HPQ (acc. 0000047217-26-000015): Lores was CEO for FY2025
  ($23,103,812); stepped down eff 2026-02-02; Bruce Broussard Interim CEO
  since Feb 2026. Anchor stays Lores FY2024 $19,360,127. Filed FY2025
  ratio 297:1 (median $77,679): pay_ratio 278 -> 297, median 69,571 ->
  77,679. ceo_tenure -> {2026, February, high, prose}.
- HSIC (acc. 0001193125-26-146317): Bergman retired as CEO eff
  2026-03-01 (continues as Chairman). Anchor stays Bergman FY2024
  $11,640,272. Filed FY2025 ratio 152:1 (median $78,954; Bergman
  $12,030,340): pay_ratio unchanged 152, median 76,751 -> 78,954.
  ceo_tenure -> {2026, March, high, prose}.
- INCY (acc. 0000879169-26-000031): Hoppenot retired as President/CEO
  June 2025; Meury is current CEO. Anchor stays Hoppenot FY2024
  $17,459,546. Filed FY2025 ratio 110.47:1 (median $295,914; Meury
  annualized $32,688,692): pay_ratio 68 -> 110.47, median 255,918 ->
  295,914. ceo_tenure -> {2025, June, high, prose}.
- KR (acc. 0001104659-26-060250): McMullen out; David J. Sargent Interim
  CEO Mar 2025 - Feb 2026 (Chairman since Mar 2025); Gregory S. Foran
  elected CEO eff Feb 2026. Anchor stays McMullen FY2024 $15,631,028.
  Filed FY2025 ratio 417:1 (median $34,552; Interim CEO $14,400,108):
  pay_ratio 457 -> 417, median 34,213 -> 34,552. ceo_tenure ->
  {2026, February, high, prose}.
- MAS (acc. 0001193125-26-151241): Jonathon Nudi became President/CEO
  2025-07-07 (Allman out). Anchor stays Allman FY2024 $10,651,821. Filed
  FY2025 ratio 249:1 (median $52,107; combined Allman+Nudi $12,949,607):
  pay_ratio 208 -> 249, median 51,203 -> 52,107. ceo_tenure ->
  {2025, July, high, prose}.
- MNST (acc. 0001104659-26-035990): Sacks resigned as Co-CEO eff
  2025-06-12 11:59pm (remains Chairman); Hilton H. Schlosberg served as
  CEO in 2025. Anchor stays Sacks FY2024 $17,709,651. Filed FY2025 ratio
  218:1 (median $88,521; Schlosberg $19,282,630): pay_ratio 173 -> 218,
  median 102,247 -> 88,521. ceo_tenure -> {2025, June, high, prose}.
- PNW (acc. 0001628280-26-023516): Ted Geisler appointed Chairman/
  President/CEO eff 2025-04-01 (Guldner out). Anchor stays Guldner FY2024
  $10,974,308. Filed FY2025 ratio 42:1 (median $182,127; combined
  Guldner+Geisler $7,600,209): pay_ratio 65 -> 42, median 168,002 ->
  182,127. ceo_tenure -> {2025, April, high, prose}.
- PRU (acc. 0001104659-26-035162): Andrew F. Sullivan became CEO eff
  2025-03-31 succeeding Lowrey; Lowrey Executive Chairman to 2026-03-10,
  then Senior Advisor to 2026-06-30 retirement. Anchor stays Lowrey FY2024
  $28,168,258. Filed FY2025 ratio 198:1 (median $100,551; Sullivan
  $19,913,520): pay_ratio 293 -> 198, median 96,126 -> 100,551.
  ceo_tenure -> {2025, March, high, prose}.
- SWK (acc. 0001140361-26-008170): Christopher J. Nelson succeeded Allan
  as President/CEO eff 2025-10-01 (Allan -> Executive Chair). Anchor
  stays Allan FY2024 $16,000,281. Filed FY2025 ratio 179:1 (median
  $47,897; Nelson annualized $8,579,210): pay_ratio 208 -> 179, median
  76,984 -> 47,897. ceo_tenure -> {2025, October, high, prose}.
- WDC (acc. 0001628280-25-044298): Goeckeler resigned -> CEO of Sandisk;
  Irving Tan CEO since Feb 2025 (tenure already transition-encoded,
  verified, untouched). Anchor stays Goeckeler FY2024 $17,690,772. Filed
  FY2025 ratio 1,321:1 (median $8,740; Tan $11,547,685): pay_ratio 1649 ->
  1321, median 10,726 -> 8,740.

All 13 anchor rows re-verified against the primary SCTs (anchor totals
confirmed in-filing; components foot exactly, $0 gaps) and relabeled
-> def14a_verified_20260925 (bucket move only; row count 7,030 and
verified_total 7,000 unchanged).

Run from repo root.
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260925_1400_pre_formeranchors.json")
README_PATH = os.path.join(HERE, "..", "README.md")
APPJS_PATH = os.path.join(HERE, "..", "js", "app.js")

SRC = "def14a_verified_20260925"
NOTE = "2026-09-25 14:00 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]


def foot(e):
    return sum((e.get(k) or 0) for k in COMP8)


TICKERS = ["CHD", "CPB", "EXE", "HPQ", "HSIC", "INCY", "KR",
           "MAS", "MNST", "PNW", "PRU", "SWK", "WDC"]

ACC = {
    "CHD": "0001193125-26-115994", "CPB": "0001308179-25-000618",
    "EXE": "0001104659-26-048155", "HPQ": "0000047217-26-000015",
    "HSIC": "0001193125-26-146317", "INCY": "0000879169-26-000031",
    "KR": "0001104659-26-060250", "MAS": "0001193125-26-151241",
    "MNST": "0001104659-26-035990", "PNW": "0001628280-26-023516",
    "PRU": "0001104659-26-035162", "SWK": "0001140361-26-008170",
    "WDC": "0001628280-25-044298",
}

# (pay_ratio, median_worker_pay, tenure) repairs; tenure None = untouched
REPAIRS = {
    "CHD": (120.7, 81203, {"year": 2025, "month": "April",
                           "confidence": "high", "sources": ["prose"]}),
    "CPB": (128, 77798, {"year": 2025, "month": "February",
                         "confidence": "high", "sources": ["prose"]}),
    "EXE": (62, 158503, {"year": 2026, "month": "February",
                         "confidence": "high", "sources": ["prose"]}),
    "HPQ": (297, 77679, {"year": 2026, "month": "February",
                         "confidence": "high", "sources": ["prose"]}),
    "HSIC": (152, 78954, {"year": 2026, "month": "March",
                          "confidence": "high", "sources": ["prose"]}),
    "INCY": (110.47, 295914, {"year": 2025, "month": "June",
                              "confidence": "high", "sources": ["prose"]}),
    "KR": (417, 34552, {"year": 2026, "month": "February",
                        "confidence": "high", "sources": ["prose"]}),
    "MAS": (249, 52107, {"year": 2025, "month": "July",
                         "confidence": "high", "sources": ["prose"]}),
    "MNST": (218, 88521, {"year": 2025, "month": "June",
                          "confidence": "high", "sources": ["prose"]}),
    "PNW": (42, 182127, {"year": 2025, "month": "April",
                         "confidence": "high", "sources": ["prose"]}),
    "PRU": (198, 100551, {"year": 2025, "month": "March",
                          "confidence": "high", "sources": ["prose"]}),
    "SWK": (179, 47897, {"year": 2025, "month": "October",
                         "confidence": "high", "sources": ["prose"]}),
    "WDC": (1321, 8740, None),
}

ANCHOR_NAMES = {
    "CHD": "Matthew T. Farrell", "CPB": "Mark A. Clouse",
    "EXE": "Domenic J. Dell'Osso Jr", "HPQ": "Enrique J. Lores",
    "HSIC": "Stanley M. Bergman", "INCY": "Herv\xe9 Hoppenot",
    "KR": "W. Rodney McMullen", "MAS": "Keith J. Allman",
    "MNST": "Rodney C. Sacks", "PNW": "Jeffrey B. Guldner",
    "PRU": "Charles F. Lowrey", "SWK": "Donald Allan, Jr.",
    "WDC": "David V. Goeckeler",
}

# ---------------- pre-write assertions ----------------
n0 = sum(len(c["executives"]) for c in data["companies"])
assert n0 == 7030, f"row count {n0} != 7030"

# CPB hygiene pre-change shape
cpb = companies["CPB"]
assert cpb["ceo_name"] == "Mark A", "CPB ceo_name drifted"
cpb_clouse = [e for e in cpb["executives"] if e["name"] == "Mark A"]
assert len(cpb_clouse) == 3, f"CPB Mark A rows {len(cpb_clouse)} != 3"
assert all(e["title"] == "Clouse Former, President and Chief Executive Officer"
           for e in cpb_clouse), "CPB bleed title drifted"

# every anchor row: exactly one per company, pairs with total_compensation,
# foots exactly, title carries a CEO token
anchor_rows = {}
for t in TICKERS:
    c = companies[t]
    rows = [e for e in c["executives"]
            if e["name"] in (c["ceo_name"], ANCHOR_NAMES[t])
            and e["year"] == c["fiscal_year"]]
    assert len(rows) == 1, f"{t}: anchor rows {len(rows)}"
    e = rows[0]
    assert e["total"] == c["total_compensation"], \
        f"{t}: anchor total {e['total']} != company {c['total_compensation']}"
    gap = abs(foot(e) - e["total"])
    assert gap == 0, f"{t}: anchor foot gap {gap}"
    assert re.search(r"chief executive|ceo", e["title"], re.I), \
        f"{t}: anchor title lacks CEO token: {e['title']!r}"
    anchor_rows[t] = e
print("pre-write assertions OK (7030 rows; 13 anchors pair, foot $0, CEO token)")

# EXE tenure corruption pre-change shape
exe = companies["EXE"]
assert exe["ceo_tenure"] == {"ceo_name": "Chris Lacy", "start_year": 2023,
                             "confidence": "medium", "source": "manual"}, \
    "EXE ceo_tenure drifted"

# WDC tenure already transition-encoded; assert before no-op
assert companies["WDC"]["ceo_tenure"] == {
    "year": 2025, "month": "February", "confidence": "high",
    "sources": ["prose"]}, "WDC ceo_tenure drifted"

# ---------------- CPB name/title hygiene ----------------
for e in cpb_clouse:
    e["name"] = "Mark A. Clouse"
    e["title"] = "Former President and Chief Executive Officer"
cpb["ceo_name"] = "Mark A. Clouse"
print("CPB hygiene: ceo_name + 3 SCT rows -> Mark A. Clouse / "
      "Former President and Chief Executive Officer")

# ---------------- aggregate repairs ----------------
for t in TICKERS:
    c = companies[t]
    pr, mw, tenure = REPAIRS[t]
    c["pay_ratio"] = pr
    c["median_worker_pay"] = mw
    if tenure is not None:
        c["ceo_tenure"] = tenure
print("aggregates repaired: 13 pay ratios + medians refreshed to filed "
      "FY2025 disclosures; 12 tenures transition-encoded (WDC untouched)")

# ---------------- relabel the 13 re-verified anchor rows ----------------
for t in TICKERS:
    e = anchor_rows[t]
    e["_total_source"] = SRC
    e["_accession"] = ACC[t]
    e["_repair_note_20260925_1400"] = (
        f"{NOTE}: CEO-anchor adjudication - anchor kept on the filed "
        f"FY{e['year']} PEO row per least-false-statement (no successor has "
        f"a filed FY{e['year']} SCT row); row re-read against the primary "
        f"DEF 14A SCT (acc. {ACC[t]}): filing-verbatim components, total "
        f"foots exactly ($0 gap).")
print(f"relabeled 13 anchor rows -> {SRC}")

# ---------------- metadata re-sync ----------------
shutil.copy(JSON_PATH, BACKUP)
print("backup:", BACKUP)
with open(BACKUP, encoding="utf-8") as bf:
    bdata = json.load(bf)
src_before = sum(1 for co in bdata["companies"] for e in co["executives"]
                 if e.get("_total_source") == SRC)
print(f"pre-existing {SRC} rows in backup: {src_before}")

recount = {}
for co in data["companies"]:
    for e in co["executives"]:
        recount[e.get("_total_source", "?")] = \
            recount.get(e.get("_total_source", "?"), 0) + 1
assert recount.get(SRC) == src_before + 13, \
    f"new bucket recount {recount.get(SRC)} != {src_before + 13}"
for block_name in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_name]
    for k, v in recount.items():
        if k in block or k.startswith("def14a_verified") or k in (
                "verified", "component_mismatch", "rounding", "recomputed"):
            block[k] = v
    block["verified_total"] = (recount.get("verified", 0)
                               + sum(v for k, v in recount.items()
                                     if k.startswith("def14a_verified")))
    block["last_audit"] = "2026-09-25"
assert sum(recount.values()) == 7030
dq = data["metadata"]["data_quality"]
vt, total = dq["verified_total"], 7030
assert (vt, total) == (7000, 7030), f"unexpected buckets {(vt, total)}"
pct = f"{vt / total * 100:.1f}%"
assert pct == "99.6%", f"unexpected headline {vt}/{total} {pct}"
data["metadata"]["last_updated"] = "2026-09-25"
data["metadata"]["last_dq_repair"] = "2026-09-25"
data["last_updated"] = "2026-09-25"
print(f"headline: {vt:,} of {total:,} ({pct}) | {SRC}: +13 (bucket move, "
      f"row count unchanged)")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
    f.write("\n")

# ---------------- pay-ratio screen recount (guard 4d rule) ----------------
within = twox = half = other = 0
for c in data["companies"]:
    pr = c.get("pay_ratio")
    mw = c.get("median_worker_pay")
    ct = c.get("total_compensation")
    if pr in (None, 0) or mw in (None, 0) or ct is None:
        continue
    r = (ct / mw) / pr
    if abs(r - 1) <= max(2 / pr, 0.03):
        within += 1
    elif 1.9 <= r <= 2.1:
        twox += 1
    elif 0.4 <= r <= 0.6:
        half += 1
    else:
        other += 1
pr_n = within + twox + half + other
print(f"pay-ratio screen: {within} of {pr_n} within; "
      f"{twox} near 2x, {half} near 0.5x, {other} differ")

# ---------------- static-copy sync ----------------
with open(README_PATH, encoding="utf-8") as f:
    lines = f.readlines()
head = lines[10]
assert "99.6% verified component-total consistency (7,000 of 7,030 records" in head
audit = ("; 2026-09-25 14:00 PT batch: 13-company 'Former'-titled CEO-anchor "
         "adjudication (backlog candidate #1, panel 2026-09-25 03:40 PT). All "
         "13 FY2024 anchors kept per least-false-statement (anchor was the "
         "filed FY2024 PEO; no successor has a filed FY2024 SCT row): CHD "
         "Farrell $12,284,216 (Dierker CEO eff 2025-04-02), CPB Clouse "
         "$12,260,000 (Beekhuizen CEO eff 2025-02-01; ceo_name + 3 rows "
         "hygiene 'Mark A'/'Clouse Former, ...' -> 'Mark A. Clouse'/'Former "
         "President and Chief Executive Officer'), EXE Dell'Osso $8,974,550 "
         "(Wichterich interim CEO eff 2026-02-06; corrupt ceo_tenure 'Chris "
         "Lacy' -> {2026, February, high, prose}), HPQ Lores $19,360,127 "
         "(stepped down 2026-02-02; Broussard interim), HSIC Bergman "
         "$11,640,272 (retired CEO eff 2026-03-01), INCY Hoppenot "
         "$17,459,546 (retired Jun 2025; Meury CEO), KR McMullen $15,631,028 "
         "(Sargent interim Mar 2025-Feb 2026; Foran CEO eff Feb 2026), MAS "
         "Allman $10,651,821 (Nudi CEO eff 2025-07-07), MNST Sacks "
         "$17,709,651 (resigned Co-CEO eff 2025-06-12; Schlosberg CEO), PNW "
         "Guldner $10,974,308 (Geisler CEO eff 2025-04-01), PRU Lowrey "
         "$28,168,258 (Sullivan CEO eff 2025-03-31), SWK Allan $16,000,281 "
         "(Nelson CEO eff 2025-10-01), WDC Goeckeler $17,690,772 (Tan CEO "
         "since Feb 2025). Pay ratios + medians refreshed to the filed "
         "FY2025 disclosures (e.g. CHD 157->$120.7, INCY 68->$110.47, KR "
         "457->417, WDC 1649->1321); 12 ceo_tenures transition-encoded "
         "{year, month, high, prose} (WDC already correct); 13 anchor SCT "
         "rows re-verified filing-verbatim and relabeled "
         "def14a_verified_20260925 (bucket move only); headline buckets "
         "99.6% (7,000/7,030) unchanged. FE/TGT/USB carry over (same class, "
         "not panel-prioritized).")
assert head.rstrip("\n").endswith("."), "audit-trail anchor lost"
lines[10] = head.rstrip("\n") + audit + "\n"
with open(README_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README audit-trail appended (headline unchanged)")

# js/app.js: pay-ratio dataq fallback re-sync (section 4d recount-exact)
with open(APPJS_PATH, encoding="utf-8") as f:
    js = f.read()
old_fb = ("401 of 512 screened companies\\' disclosed ratios match "
          "<code>total_compensation / median_worker_pay</code> within 3% "
          "tolerance; 14 cluster near 2x, 10 near 0.5x, 87 differ otherwise.")
new_fb = (f"{within} of {pr_n} screened companies\\' disclosed ratios match "
          f"<code>total_compensation / median_worker_pay</code> within 3% "
          f"tolerance; {twox} cluster near 2x, {half} near 0.5x, {other} "
          f"differ otherwise.")
assert old_fb in js, "app.js pay-ratio fallback pre-change text drifted"
js = js.replace(old_fb, new_fb)
with open(APPJS_PATH, "w", encoding="utf-8") as f:
    f.write(js)
print(f"js/app.js pay-ratio fallback re-synced "
      f"(401/14/10/87 -> {within}/{twox}/{half}/{other})")

print("done")
