#!/usr/bin/env python3
"""2026-09-25 19:30 PT: FE/TGT/USB "Former"-titled CEO-anchor adjudication
(backlog candidate #1 carry-over from the 14:45 PT 13-company batch).

Method (ORCL/NCLH 2026-09-25 06:00 PT precedent, 14:45 PT batch pattern):
for each company the latest DEF 14A was fetched from EDGAR (curl, UA
Kit/1.0) and read for (1) leadership-transition prose, (2) the filed CEO
Pay Ratio disclosure, (3) the anchor-year (FY2024) SCT row for the anchor
CEO. Local filing copies lived in /tmp/sp500-batch39 (ephemeral).

Adjudication results (all anchors KEPT per least-false-statement: the
anchor person was the filed FY2024 PEO in every case; no successor has a
filed FY2024 SCT row):
- FE (FirstEnergy, acc. 0001193125-26-138029): Brian X. Tierney is the
  sitting CEO (FY2025 pay-ratio disclosure names his $13,452,559 CEO comp;
  no transition prose). Anchor stays Tierney FY2024 $11,933,534
  (SCT-verified: 1,511,539 + 10,197,274 + 186,854 + 37,867). Filed FY2025
  ratio 84:1 (median $160,003): pay_ratio 100 -> 84, median 118,994 ->
  160,003. ceo_tenure untouched ({2023, June, high, prose}). HYGIENE: the
  "(former)" suffix on Tierney's 2024/2023 titles is a non-filing-verbatim
  parser artifact (same class as CPB's "Clouse Former" bleed, fixed 14:45
  PT) -> "Chair, President and CEO".
- TGT (Target, acc. 0001628280-26-027508): Brian C. Cornell was CEO
  through FY2025 (ended 2026-01-31); Michael J. Fiddelke assumed CEO eff
  2026-02-01; Cornell continues as Executive Chair. Anchor stays Cornell
  FY2024 $20,407,603 (SCT-verified: 1,400,000 + 785,400 + 16,087,492 +
  1,538,320 + 596,391; pension 0). All 13 TGT NEO rows already
  filing-verbatim (titles incl. "Chair & former Chief Executive Officer"
  and "Former EVP & Chief Operating Officer and current Chief Executive
  Officer" are the 2026 proxy SCT's own wording). Filed FY2025 ratio
  794:1 (median $27,506; Cornell $21,830,088): pay_ratio 753 -> 794,
  median 27,090 -> 27,506. ceo_tenure {2026, "Fiscal", high, prose} ->
  {2026, "February", high, prose}.
- USB (US Bancorp, acc. 0001104659-26-025844): Andrew Cecere was CEO
  2025-01-01 to 2025-04-15; Gunjan Kedia CEO since 2025-04-15; Cecere ->
  Executive Chairman (retires from Board at the 2026 annual meeting).
  Anchor stays Cecere FY2024 per least-false-statement. MAJOR FIND: USB's
  8 FY2023/FY2024 NEO rows carry salary-drop column-shift corruption (the
  class from the 2026-09-13/17/18 batches): salary cell dropped, stock
  landed in salary, NEIP in stock, pension in NEIP, all_other in pension,
  printed total in all_other, stored total recomputed ~2x. $74.8M phantom
  compensation removed. All 8 repaired filing-verbatim from the 2026
  proxy SCT (every repaired total foots exactly, $0 gap):
    Kedia 2024: 930,770 / 6,499,995 / 2,292,267 / 225,513 / 189,310 /
      10,137,855 (was 19,344,940)
    Kedia 2023: 725,000 / 3,500,000 / 1,173,050 / 220,797 / 130,447 /
      5,749,294 (was 10,773,588)
    Cecere 2024: 1,400,000 / 11,000,024 / 4,929,400 / 1,926,261 / 83,642 /
      19,339,327 (was 37,278,654)
    Cecere 2023: 1,350,000 / 10,500,000 / 3,794,175 / 7,210,212 / 62,570 /
      22,916,957 (was 44,483,914)
    Stern 2024: 700,000 / 2,700,000 / 1,408,400 / 89,164 / 19,606 /
      4,917,170 (was 9,134,340)
    Stern 2023: 527,308 / 600,000 / 607,260 / 91,970 / 18,600 /
      1,845,138 (was 3,162,968)
    Dolan 2024: 815,000 / 4,999,995 / 2,049,725 / 691,796 / 34,007 /
      8,590,523 (was 16,366,046)
    Dolan 2023: 780,000 / 4,500,000 / 1,409,265 / 1,857,078 / 32,331 /
      8,578,674 (was 16,377,348)
  USB SCT has no Bonus and no Option columns (nulls stored per dataset
  convention). The 7 FY2025 rows (Kedia, Cecere, Stern, Richard, Philipson,
  Barcelos, Dolan) verified clean against the same SCT (Dolan 2025 NEIP
  cell is genuinely blank in the filing; raw-cell verified).
  Company-level: total_compensation 37,278,654 -> 19,339,327 (repaired
  anchor); total_neo_compensation 82,123,980 -> 42,984,875 (re-anchored on
  FY2024 SCT totals); pay_ratio 215 -> 178; median 90,217 -> 95,307 (filed
  FY2025: Kedia annualized $16,980,162, median $95,307, ratio 178:1);
  ceo_tenure {2025, null, medium, table} -> {2025, "April", high, prose}.

Run from repo root.
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE,
    "compensation_backup_20260925_1930_pre_formeranchors2.json")
README_PATH = os.path.join(HERE, "..", "README.md")
APPJS_PATH = os.path.join(HERE, "..", "js", "app.js")

SRC = "def14a_verified_20260925"
NOTE = "2026-09-25 19:30 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]


def foot(e):
    return sum((e.get(k) or 0) for k in COMP8)


# filing-verbatim component values from the primary DEF 14A SCTs
# (salary, bonus, stock, option, neip, pension_nqdc, all_other, total)
USB_SCT = {
    ("Gunjan Kedia", 2024): (930770, 0, 6499995, 0, 2292267, 225513, 189310,
                             10137855),
    ("Gunjan Kedia", 2023): (725000, 0, 3500000, 0, 1173050, 220797, 130447,
                             5749294),
    ("Andrew Cecere", 2024): (1400000, 0, 11000024, 0, 4929400, 1926261,
                              83642, 19339327),
    ("Andrew Cecere", 2023): (1350000, 0, 10500000, 0, 3794175, 7210212,
                              62570, 22916957),
    ("John C. Stern", 2024): (700000, 0, 2700000, 0, 1408400, 89164, 19606,
                              4917170),
    ("John C. Stern", 2023): (527308, 0, 600000, 0, 607260, 91970, 18600,
                              1845138),
    ("Terrance R. Dolan", 2024): (815000, 0, 4999995, 0, 2049725, 691796,
                                  34007, 8590523),
    ("Terrance R. Dolan", 2023): (780000, 0, 4500000, 0, 1409265, 1857078,
                                  32331, 8578674),
}

ACC = {
    "FE": "0001193125-26-138029",
    "TGT": "0001628280-26-027508",
    "USB": "0001104659-26-025844",
}

# ---------------- pre-write assertions ----------------
n0 = sum(len(c["executives"]) for c in data["companies"])
assert n0 == 7030, f"row count {n0} != 7030"

# FE title-hygiene artifact pre-change shape
fe = companies["FE"]
fe_tierney = [e for e in fe["executives"] if e["name"] == "Brian X. Tierney"
              and e["year"] in (2023, 2024)]
assert len(fe_tierney) == 2, f"FE Tierney 23/24 rows {len(fe_tierney)} != 2"
assert all(e["title"] == "Chair, President and CEO (former)"
           for e in fe_tierney), "FE Tierney title drifted"
assert fe["ceo_tenure"] == {"year": 2023, "month": "June",
                            "confidence": "high", "sources": ["prose"]}, \
    "FE ceo_tenure drifted"

# TGT tenure pre-change shape
tgt = companies["TGT"]
assert tgt["ceo_tenure"] == {"year": 2026, "month": "Fiscal",
                             "confidence": "high", "sources": ["prose"]}, \
    "TGT ceo_tenure drifted"

# USB corruption pre-change shape (salary == filing stock_awards on all 8)
usb = companies["USB"]
usb_shifted = []
for (nm, yr), vals in USB_SCT.items():
    hits = [e for e in usb["executives"] if e["name"] == nm and e["year"] == yr]
    assert len(hits) == 1, f"USB {nm} {yr}: {len(hits)} hits"
    e = hits[0]
    assert e["salary"] == vals[2], \
        f"USB {nm} {yr}: salary {e['salary']} != filing stock {vals[2]}"
    assert e["all_other"] == vals[7], \
        f"USB {nm} {yr}: all_other {e['all_other']} != filing total {vals[7]}"
    usb_shifted.append(e)
print("pre-write assertions OK (7030 rows; FE title artifact x2; TGT tenure; "
      "USB 8 salary-shift rows confirmed)")

# ---------------- USB column-shift repairs ----------------
for (nm, yr), vals in USB_SCT.items():
    e = [x for x in usb["executives"] if x["name"] == nm and x["year"] == yr][0]
    (sal, bon, stk, opt, neip, pen, oth, tot) = vals
    e["salary"] = sal
    e["bonus"] = bon
    e["stock_awards"] = stk
    e["option_awards"] = opt
    e["non_equity_incentive"] = neip
    e["pension_nqdc"] = pen
    e["all_other"] = oth
    e["total"] = tot
    e["_total_source"] = SRC
    e["_accession"] = ACC["USB"]
    e["_parse_note"] = (
        f"{NOTE}: salary-drop column-shift EDGAR repair vs primary DEF 14A "
        f"SCT (acc. {ACC['USB']}): salary cell dropped, stock->salary, "
        f"NEIP->stock, pension->NEIP, all_other->pension, printed total->"
        f"all_other, stored total recomputed ~2x. Filing-verbatim components "
        f"restored; total foots exactly ($0 gap). USB SCT carries no Bonus "
        f"or Option columns.")
for e in usb_shifted:
    assert foot(e) == e["total"], \
        f"USB {e['name']} {e['year']}: foot gap {foot(e) - e['total']}"
print("USB: 8 salary-shift rows repaired filing-verbatim, all foot $0")

# ---------------- company-level repairs ----------------
# FE
fe["pay_ratio"] = 84
fe["median_worker_pay"] = 160003
for e in fe_tierney:
    e["title"] = "Chair, President and CEO"
# anchor row relabel (Tierney 2024 already filing-verbatim, re-read today)
fe_anchor = [e for e in fe["executives"]
             if e["name"] == "Brian X. Tierney" and e["year"] == 2024][0]
assert fe_anchor["total"] == fe["total_compensation"] == 11933534
assert foot(fe_anchor) == fe_anchor["total"]
fe_anchor["_total_source"] = SRC
fe_anchor["_accession"] = ACC["FE"]
fe_anchor["_repair_note_20260925_1930"] = (
    f"{NOTE}: CEO-anchor adjudication - anchor kept on the filed FY2024 PEO "
    f"row per least-false-statement (Tierney is the sitting CEO; no "
    f"transition; no successor has a filed FY2024 SCT row); row re-read "
    f"against the primary DEF 14A SCT (acc. {ACC['FE']}): filing-verbatim "
    f"components, total foots exactly ($0 gap).")

# TGT
tgt["pay_ratio"] = 794
tgt["median_worker_pay"] = 27506
tgt["ceo_tenure"] = {"year": 2026, "month": "February",
                     "confidence": "high", "sources": ["prose"]}
tgt_anchor = [e for e in tgt["executives"]
              if e["name"] == "Brian C. Cornell" and e["year"] == 2024][0]
assert tgt_anchor["total"] == tgt["total_compensation"] == 20407603
assert foot(tgt_anchor) == tgt_anchor["total"]
assert re.search(r"chief executive|ceo", tgt_anchor["title"], re.I)
tgt_anchor["_total_source"] = SRC
tgt_anchor["_accession"] = ACC["TGT"]
tgt_anchor["_repair_note_20260925_1930"] = (
    f"{NOTE}: CEO-anchor adjudication - anchor kept on the filed FY2024 PEO "
    f"row per least-false-statement (Cornell was CEO through FY2025 ended "
    f"2026-01-31; Fiddelke CEO eff 2026-02-01; no successor has a filed "
    f"FY2024 SCT row); row re-read against the primary DEF 14A SCT (acc. "
    f"{ACC['TGT']}): filing-verbatim components, total foots exactly "
    f"($0 gap).")

# USB
usb["pay_ratio"] = 178
usb["median_worker_pay"] = 95307
usb["ceo_tenure"] = {"year": 2025, "month": "April",
                     "confidence": "high", "sources": ["prose"]}
usb_anchor = [e for e in usb["executives"]
              if e["name"] == "Andrew Cecere" and e["year"] == 2024][0]
usb["total_compensation"] = usb_anchor["total"]
assert usb["total_compensation"] == 19339327
assert foot(usb_anchor) == usb_anchor["total"]
assert re.search(r"chief executive|ceo", usb_anchor["title"], re.I)
fy24 = [e for e in usb["executives"] if e["year"] == 2024]
usb["total_neo_compensation"] = sum(e["total"] for e in fy24)
assert usb["total_neo_compensation"] == 42984875, \
    f"USB total_neo {usb['total_neo_compensation']} != 42984875"
print("company-level: FE 100->84 / 118994->160003 + title hygiene; "
      "TGT 753->794 / 27090->27506 + tenure Feb 2026; "
      "USB 215->178 / 90217->95307 + tenure Apr 2025 + "
      "total_compensation 37278654->19339327 + total_neo 82123980->42984875")

# ---------------- backup + metadata re-sync ----------------
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
assert recount.get(SRC) == src_before + 10, \
    f"new bucket recount {recount.get(SRC)} != {src_before + 10}"
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
print(f"headline: {vt:,} of {total:,} ({pct}) | {SRC}: +10 (bucket moves, "
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
assert "99.6% verified component-total consistency (7,000 of 7,030 records" \
    in head
audit = ("; 2026-09-25 19:30 PT batch: FE/TGT/USB 'Former'-titled CEO-anchor "
         "adjudication (backlog candidate #1 carry-over from the 14:45 PT "
         "13-company batch). All 3 FY2024 anchors kept per "
         "least-false-statement (anchor was the filed FY2024 PEO; no "
         "successor has a filed FY2024 SCT row): FE Tierney $11,933,534 "
         "(sitting CEO; pay ratio 100->84, median 118,994->$160,003; "
         "'(former)' title artifact on 2024/2023 rows -> 'Chair, President "
         "and CEO'), TGT Cornell $20,407,603 (CEO through FY2025 ended "
         "2026-01-31; Fiddelke CEO eff 2026-02-01, Cornell -> Executive "
         "Chair; pay ratio 753->794, median 27,090->$27,506; ceo_tenure "
         "'Fiscal'->'February' 2026), USB Cecere $19,339,327 (CEO "
         "2025-01-01 to 2025-04-15; Kedia CEO since 2025-04-15; Cecere -> "
         "Executive Chairman; pay ratio 215->178, median 90,217->$95,307; "
         "ceo_tenure -> {2025, April, high, prose}). MAJOR: USB salary-drop "
         "column-shift repair on 8 FY2023/FY2024 NEO rows (Kedia/Cecere/"
         "Stern/Dolan x 2023/2024), $74,846,860 phantom removed, all "
         "repaired totals foot exactly; USB aggregates re-anchored "
         "(total_compensation 37,278,654->$19,339,327, total_neo "
         "82,123,980->$42,984,875). 10 rows relabeled "
         "def14a_verified_20260925 (bucket moves only); headline buckets "
         "99.6% (7,000/7,030) unchanged. 'Former'-CEO-anchor DQ class now "
         "fully adjudicated (16/16).")
assert head.rstrip("\n").endswith("."), "audit-trail anchor lost"
lines[10] = head.rstrip("\n") + audit + "\n"
with open(README_PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README audit-trail appended (headline unchanged)")

# js/app.js: pay-ratio dataq fallback re-sync (section 4d recount-exact)
with open(APPJS_PATH, encoding="utf-8") as f:
    js = f.read()
old_fb = ("388 of 512 screened companies\\' disclosed ratios match "
          "<code>total_compensation / median_worker_pay</code> within 3% "
          "tolerance; 14 cluster near 2x, 11 near 0.5x, 99 differ otherwise.")
new_fb = (f"{within} of {pr_n} screened companies\\' disclosed ratios match "
          f"<code>total_compensation / median_worker_pay</code> within 3% "
          f"tolerance; {twox} cluster near 2x, {half} near 0.5x, {other} "
          f"differ otherwise.")
assert old_fb in js, "app.js pay-ratio fallback pre-change text drifted"
js = js.replace(old_fb, new_fb)
with open(APPJS_PATH, "w", encoding="utf-8") as f:
    f.write(js)
print(f"js/app.js pay-ratio fallback re-synced "
      f"(388/14/11/99 -> {within}/{twox}/{half}/{other})")

print("done")
