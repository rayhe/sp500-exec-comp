#!/usr/bin/env python3
"""2026-09-19 10:00 PT primary-source DQ batch: pension/NEIP-confusion queue
triage, second tranche (18 rows), + BMY/LII column-shift cascade repairs.

All values verified verbatim against the companies' latest DEF 14A Summary
Compensation Tables (re-fetched from EDGAR this run; raw filings in
/tmp/sct_batch/, ledger in the goal hidden workspace dq_20260919_1000/).
Nothing hand-transcribed.

Classes:
1. BMY (Bristol-Myers Squibb) - 5-row column-shift repair. The 2026 DEF 14A
   SCT has NO Option Awards column; the old parse filed NEIP->option_awards,
   All-Other->pension_nqdc, Total->all_other and RECOMPUTED the total as the
   sum of the misaligned components (roughly doubling it). Affected: Boerner
   2023 ($16.92M stored vs $8.46M filed), Elkins 2023 ($14.33M vs $7.17M),
   Massacesi 2025 ($20.15M vs $10.07M), Lenkowsky 2025 ($18.68M vs $9.34M),
   Meyers 2025 ($14.36M vs $7.18M). All 5 repaired filing-verbatim; titles
   synced SCT-verbatim (several were scrambled: Boerner 'Chair', Elkins
   'Chair and Chief Executive Officer', Massacesi 'EVP and Chief Financial
   Officer', Lenkowsky 'EVP and Chief Medical Officer, Head of Development',
   Meyers 'EVP and Chief Commercialization Officer'). The other 7 BMY rows
   (2024/2025 Boerner/Elkins/Hirawat, Hirawat 2023) were diffed clean.
2. LII (Lennox) - 3-row column-shift repair. The 2023 SCT rows carry '-' in
   the Stock/Option columns (no FY2023 equity grants); the old parse
   misaligned the row: NEIP->option_awards, pension->neip, all_other->pension,
   total->all_other, total recomputed. Affected: Maskara 2023 (salary $0
   stored vs $1,064,750 filed; total $8.90M vs $4.98M), Nassab 2023
   ($2.65M vs $1.59M), Sessa 2023 ($2.99M vs $1.78M). All 3 repaired
   filing-verbatim. The 2024/2025 rows (incl. Quenzer 2024) diffed clean.
3. False positives (10 rows): ROK Moret 2024 (genuine $4.20M pension-change;
   41-yr plan participant; FY2024 NEIP genuinely $0 for all NEOs), NSC Elkins
   2023 / George 2023 (genuine pension-change $1.28M/$0.18M; FY2023 NEIP $0
   for both NEOs), COST Galanti 2025 (genuine $594,005 pension/NQDC; NEIP '-'
   post-retirement; COST SCT has no options column), KR McMullen 2025
   (genuine $562,587 pension/NQDC incl. $227,673 preferential NQDC earnings
   per fn 2; resigned 2025-03-02) and 2024 (genuine $206,800 pension-change;
   FY2024 NEIP $0), MCO Tulenko 2025 (genuine $558,729 pension-change; NEIP
   '-' departed; $1 filing-side rounding gap), TFC Cummins 2025 (genuine
   $449,453 pension-change; NEIP '-' resigned 2025-01-13), BKR Magno 2025
   ($313,608) / 2024 ($215,678) (genuine pension-change; NEIP '-'; BKR SCT has
   no options column). All 10 confirmed filing-verbatim, no value changes;
   SCT-verbatim title syncs on ROK/COST/KR/NSC.

Aggregates re-anchored to fiscal_year on BMY only (LII repairs are FY2023
rows; LII FY2024 slate untouched): BMY total_neo $94.58M -> $67.99M
(neo_count 6 unchanged; CEO anchor Boerner FY2025 $21.88M unchanged, row
was already clean). Pay ratios and median worker pay untouched.
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260919_1000_pre_dqbatch.json")

SRC = "def14a_verified_20260919"
NOTE = "2026-09-19 10:00 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

repaired = 0
relabeled = 0

COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]


def foot(e):
    return sum((e.get(k) or 0) for k in COMP8)


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
assert n0 == 6866, f"row count {n0} != 6866"
# BMY stored (shifted) values we will replace
e = get("BMY", "Christopher S. Boerner, Ph.D.", 2023)
assert (e["option_awards"], e["pension_nqdc"], e["all_other"], e["total"]) == \
    (1567098, 311636, 8461833, 16923666)
e = get("BMY", "David V. Elkins", 2023)
assert (e["option_awards"], e["pension_nqdc"], e["all_other"], e["total"]) == \
    (866318, 311663, 7166300, 14332600)
e = get("BMY", "Cristian Massacesi", 2025)
assert (e["bonus"], e["option_awards"], e["pension_nqdc"], e["all_other"], e["total"]) == \
    (1125000, 660876, 44618, 10072950, 20145900)
e = get("BMY", "Adam Lenkowsky", 2025)
assert (e["option_awards"], e["non_equity_incentive"], e["pension_nqdc"], e["total"]) == \
    (1794732, 27060, 250029, 18680704)
e = get("BMY", "Greg Meyers", 2025)
assert (e["option_awards"], e["pension_nqdc"], e["all_other"], e["total"]) == \
    (1669036, 230277, 7181173, 14362346)
# LII stored (shifted) values we will replace
e = get("LII", "Alok Maskara", 2023)
assert (e["salary"], e["option_awards"], e["pension_nqdc"], e["all_other"], e["total"]) == \
    (0, 2729934, 1188979, 4983663, 8902576)
e = get("LII", "Joseph F. Nassab", 2023)
assert (e["salary"], e["option_awards"], e["pension_nqdc"], e["total"]) == \
    (0, 873893, 184994, 2649024)
e = get("LII", "Daniel M. Sessa", 2023)
assert (e["salary"], e["option_awards"], e["non_equity_incentive"], e["pension_nqdc"],
        e["all_other"], e["total"]) == (0, 907387, 253146, 49800, 1776583, 2986916)
print("pre-write assertions OK")


def rep(ticker, name, year, note, small_delta_ok=False, **fields):
    """Repair components filing-verbatim. small_delta_ok documents a genuine
    $1-$2 filer-side rounding gap (taxonomy 2026-09-10: stays verified family)."""
    global repaired
    e = get(ticker, name, year)
    for k, v in fields.items():
        e[k] = v
    gap = abs(foot(e) - e["total"])
    if small_delta_ok:
        assert gap in (1, 2), f"{ticker} {name} {year}: expected $1-$2 gap, got {gap}"
        note += f"; genuine ${gap} filer-side rounding gap (taxonomy 2026-09-10: stays verified)"
    else:
        assert gap == 0, f"{ticker} {name} {year}: components {foot(e):,} != total {e['total']:,}"
    e["_total_source"] = SRC
    e["_accession"] = accession(ticker)
    prev = e.get("_repair_note_20260919_1000", "")
    e["_repair_note_20260919_1000"] = (prev + "; " if prev else "") + note
    repaired += 1


def relabel(ticker, name, year, note, title=None):
    """Row already matches the filing; mark the primary re-verification."""
    global relabeled
    e = get(ticker, name, year)
    assert foot(e) - e["total"] in (0,) or abs(foot(e) - e["total"]) in (1, 2), \
        f"{ticker} {name} {year}: stored row does not match filing"
    if title and e["title"] != title:
        note += f"; title -> SCT-verbatim '{title}' (was '{e['title']}')"
        e["title"] = title
    e["_total_source"] = SRC
    e["_accession"] = accession(ticker)
    prev = e.get("_repair_note_20260919_1000", "")
    e["_repair_note_20260919_1000"] = (prev + "; " if prev else "") + note
    relabeled += 1


# ---------------- 1. BMY: column-shift repair ----------------
# Bristol-Myers Squibb 2026 DEF 14A (acc. 0000014272-26-000006, filed
# 2026-03-25, re-fetched 2026-09-19). SCT columns: Salary | Bonus | Stock |
# NEIP | Pension | All Other | Total (NO Option Awards column). Old parse
# filed NEIP->option_awards, All-Other->pension_nqdc, Total->all_other and
# recomputed the total from the misaligned components.
BMY_NOTE = (f"{NOTE}: column-shift repair - 2026 DEF 14A SCT has NO Option "
            f"Awards column; old parse filed NEIP->option_awards, "
            f"All-Other->pension_nqdc, Total->all_other and recomputed the "
            f"total (roughly doubling it); now filing-verbatim")
BMY_ROWS = [
    # name, year, salary, bonus, stock, option, neip, pension, all_other, total, title
    ("Christopher S. Boerner, Ph.D.", 2023, 1256921, 0, 5326178, 0, 1567098, 0,
     311636, 8461833, "Board Chair and Chief Executive Officer"),
    ("David V. Elkins", 2023, 1106176, 0, 4882143, 0, 866318, 0,
     311663, 7166300, "EVP and Chief Financial Officer"),
    ("Cristian Massacesi", 2025, 388462, 1125000, 7853994, 0, 660876, 0,
     44618, 10072950, "EVP, Chief Medical Officer, Head of Development"),
    ("Adam Lenkowsky", 2025, 1131731, 0, 6136800, 0, 1794732, 27060,
     250029, 9340352, "EVP, Chief Commercialization Officer"),
    ("Greg Meyers", 2025, 1072692, 0, 4209168, 0, 1669036, 0,
     230277, 7181173, "EVP, Chief Digital and Technology Officer"),
]
for nm, yr, sal, bon, stk, opt, neip, pen, ao, tot, ti in BMY_ROWS:
    e = get("BMY", nm, yr)
    rep("BMY", nm, yr, BMY_NOTE, salary=sal, bonus=bon, stock_awards=stk,
        option_awards=opt, non_equity_incentive=neip, pension_nqdc=pen,
        all_other=ao, total=tot)
    if e["title"] != ti:
        e["_repair_note_20260919_1000"] += f"; title -> SCT-verbatim '{ti}' (was '{e['title']}')"
        e["title"] = ti

# ---------------- 2. LII: 2023 column-shift repair ----------------
# Lennox 2026 DEF 14A (acc. 0001069202-26-000046, filed 2026-04-06,
# re-fetched 2026-09-19). The 2023 SCT rows carry '-' in Stock/Option
# columns; the old parse misaligned the row (NEIP->option_awards,
# pension->neip, all_other->pension, total->all_other, total recomputed).
LII_NOTE = (f"{NOTE}: column-shift repair - 2023 SCT rows carry '-' in the "
            f"Stock/Option columns; old parse misaligned the row "
            f"(NEIP->option_awards, pension->neip, all_other->pension, "
            f"total->all_other, total recomputed); now filing-verbatim")
LII_ROWS = [
    # name, year, salary, bonus, stock, option, neip, pension, all_other, total
    ("Alok Maskara", 2023, 1064750, 0, 0, 0, 2729934, 0, 1188979, 4983663),
    ("Joseph F. Nassab", 2023, 531250, 0, 0, 0, 873893, 0, 184994, 1590137),
    ("Daniel M. Sessa", 2023, 566250, 0, 0, 0, 907387, 253146, 49800, 1776583),
]
for nm, yr, sal, bon, stk, opt, neip, pen, ao, tot in LII_ROWS:
    rep("LII", nm, yr, LII_NOTE, salary=sal, bonus=bon, stock_awards=stk,
        option_awards=opt, non_equity_incentive=neip, pension_nqdc=pen,
        all_other=ao, total=tot)

# ---------------- 3. False positives (queue triage, no value changes) ----------------
FP = [
    ("ROK", "Blake D. Moret", 2024,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001308179-25-000665) genuinely shows pension-change $4,196,718 "
     f"with NEIP=0 (Moret is a 41-yr pension participant; fn 5: discount-rate "
     f"5.10% vs 6.10% prior year; all ROK NEOs show NEIP=0 for FY2024)",
     "President & Chief Executive Officer"),
    ("NSC", "Claude E. Elkins", 2023,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001193125-26-127620) genuinely shows pension-change $1,284,444 "
     f"with NEIP=0 (both NSC NEOs show NEIP=0 for FY2023)",
     "Executive Vice President & Chief Commercial Officer"),
    ("NSC", "Mark R. George", 2023,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001193125-26-127620) genuinely shows pension-change $183,588 "
     f"with NEIP=0 (both NSC NEOs show NEIP=0 for FY2023)",
     "President & Chief Executive Officer"),
    ("COST", "Richard A. Galanti", 2025,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2025 DEF 14A "
     f"SCT (acc. 0000909832-25-000159) genuinely shows pension/NQDC $594,005 "
     f"with NEIP '-' (post-retirement; COST SCT has no options column)",
     "Former Executive Vice President"),
    ("KR", "W. Rodney McMullen", 2025,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001104659-26-060250) genuinely shows pension/NQDC $562,587 "
     f"(incl. $227,673 preferential NQDC earnings per fn 2) with no NEIP/equity "
     f"(resigned 2025-03-02)",
     "Former Chairman and Chief Executive Officer"),
    ("KR", "W. Rodney McMullen", 2024,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001104659-26-060250) genuinely shows pension-change $206,800 "
     f"with NEIP=0 (stable across 2025 and 2026 proxies)",
     "Former Chairman and Chief Executive Officer"),
    ("MCO", "Stephen Tulenko", 2025,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001059556-26-000019) genuinely shows pension-change $558,729 "
     f"with NEIP '-' (Former President of Moody's Analytics, departed); $1 "
     f"filing-side rounding gap (components sum 5,420,279 vs printed 5,420,280)",
     None),
    ("TFC", "Hugh S. Cummins III", 2025,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001193125-26-107144) genuinely shows pension-change $449,453 "
     f"with NEIP '-' (resigned 2025-01-13; $6,188,702 severance in All Other)",
     None),
    ("BKR", "Georgia Magno", 2025,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001193125-26-130309) genuinely shows pension-change $313,608 "
     f"with NEIP '-' (BKR SCT has no options column)",
     None),
    ("BKR", "Georgia Magno", 2024,
     f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; 2026 DEF 14A "
     f"SCT (acc. 0001193125-26-130309) genuinely shows pension-change $215,678 "
     f"with NEIP '-' (BKR SCT has no options column)",
     None),
]
for ticker, nm, yr, note, ti in FP:
    relabel(ticker, nm, yr, note, title=ti)

# ---------------- aggregates: fiscal_year anchoring ----------------
c = companies["BMY"]
fy = c["fiscal_year"]
rows = [e for e in c["executives"] if e["year"] == fy]
assert len(rows) == 6, f"BMY: {len(rows)} FY rows != 6"
exp_tot = 67986217
tot = sum(e["total"] for e in rows)
assert tot == exp_tot, f"BMY: FY sum {tot:,} != {exp_tot:,}"
old = (c["neo_count"], c["total_neo_compensation"], c["total_compensation"])
c["neo_count"], c["total_neo_compensation"] = 6, exp_tot
# CEO anchor: Boerner FY2025 row was already clean; unchanged
ceo_rows = [e for e in rows if e["name"] == c["ceo_name"]]
assert len(ceo_rows) == 1 and ceo_rows[0]["total"] == c["total_compensation"] == 21879919
print(f"BMY: neo {old[0]}->{6}, total_neo {old[1]:,}->{exp_tot:,}, CEO {old[2]:,} unchanged")

# LII repairs are FY2023 rows; FY2024 slate untouched
c = companies["LII"]
rows = [e for e in c["executives"] if e["year"] == c["fiscal_year"]]
assert sum(e["total"] for e in rows) == c["total_neo_compensation"] == 18740939
print("LII: FY2024 aggregate unchanged at 18,740,939")

# ---------------- metadata re-sync ----------------
shutil.copy(JSON_PATH, BACKUP)
print("backup:", BACKUP)

n = sum(len(c["executives"]) for c in data["companies"])
assert n == 6866, f"total {n} != 6866 (rows added/dropped unexpectedly)"
recount = {}
for c in data["companies"]:
    for e in c["executives"]:
        recount[e.get("_total_source", "?")] = recount.get(e.get("_total_source", "?"), 0) + 1
for block_name in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_name]
    for k, v in recount.items():
        if isinstance(v, int) and (k in block or k.startswith("def14a_verified") or k in (
                "verified", "component_mismatch", "rounding", "recomputed")):
            block[k] = v
    assert SRC in block, f"{block_name} missing new bucket"
    block["verified_total"] = (recount.get("verified", 0)
                               + sum(v for k, v in recount.items()
                                     if k.startswith("def14a_verified")))
    block["last_audit"] = "2026-09-19"
assert sum(recount.values()) == n
dq = data["metadata"]["data_quality"]
print("verified:", dq["verified"], "| component_mismatch:", dq["component_mismatch"],
      "| def14a_verified_20260919:", dq["def14a_verified_20260919"],
      "| verified_total:", dq["verified_total"])
data["metadata"]["last_updated"] = "2026-09-19"

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
    f.write("\n")

# ---------------- static-copy sync ----------------
vt, total = dq["verified_total"], n
pct = f"{vt / total * 100:.1f}%"
print("headline:", vt, "/", total, pct)
assert (vt, total, pct) == (6838, 6866, "99.6%"), f"unexpected headline {(vt, total, pct)}"

# README audit-trail append (convention: each batch extends line 11)
audit = ("; 2026-09-19 10:00 PT batch: pension/NEIP-confusion queue triage tranche 2 "
         "(18 rows): BMY 5-row column-shift repair (2026 DEF 14A SCT has no Option "
         "Awards column; old parse filed NEIP->option_awards, All-Other->pension, "
         "Total->all_other and recomputed totals, roughly doubling them - Boerner "
         "2023 $16.92M->$8.46M, Elkins 2023 $14.33M->$7.17M, Massacesi 2025 "
         "$20.15M->$10.07M, Lenkowsky 2025 $18.68M->$9.34M, Meyers 2025 "
         "$14.36M->$7.18M; total_neo $94.58M->$67.99M; SCT-verbatim title syncs), "
         "LII 3-row 2023 column-shift repair ('-' Stock/Option columns misaligned "
         "the parse - Maskara $8.90M->$4.98M with salary $0->$1.06M, Nassab "
         "$2.65M->$1.59M, Sessa $2.99M->$1.78M), 10 queue hits FALSE POSITIVES "
         "(ROK/NSC/COST/KR/MCO/TFC/BKR: genuine pension-change values with NEIP "
         "genuinely $0/'-'; no value changes; 6 title syncs); 18 rows relabeled "
         "def14a_verified_20260919; headline buckets unchanged at 99.6% "
         "(6,838/6,866).")
with open(os.path.join(HERE, "..", "README.md"), encoding="utf-8") as f:
    lines = f.readlines()
assert lines[10].rstrip("\n").endswith("."), "audit-trail anchor lost"
lines[10] = lines[10].rstrip("\n") + audit + "\n"
with open(os.path.join(HERE, "..", "README.md"), "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README audit trail appended")

print(f"repaired={repaired} relabeled={relabeled} total_records={n}")
