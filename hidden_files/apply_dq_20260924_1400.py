#!/usr/bin/env python3
"""2026-09-24 14:00 PT primary-source DQ batch: pension/NEIP-confusion queue
re-verification sweep (final 15).

Background: the 65-row pension/NEIP-confusion queue was drained 2026-09-19
(tranches 1-3; commit 333a4ed). The 11 column-shift repairs were relabeled
def14a_verified_20260919, but the false-positive rows kept the plain
"verified" label with only _reverify notes. This run re-fetched all 14
remaining DEF 14As from EDGAR (raw filings in goal hidden_files/
dq_20260924_1400/) and re-read every flagged SCT row primary-source.

Result: 15/15 confirmed FALSE POSITIVES - genuine filing-verbatim pension/
NQDC values with NEIP genuinely 0/'-'; all components foot exactly to the
printed total ($0 gap). No value changes. 10 SCT-verbatim title syncs
(name-prefix strips per title-hygiene convention + Former markers).

The 5 "repair" candidates from the same sweep (HIG Soni 2023, NDSN McDonough
2023/2024, NDSN Hopgood 2024, ETN Leonetti 2024) were already repaired
2026-09-19 14:00 PT (commit 333a4ed) - verified no-op, untouched here.
FE Tierney 2024 (def14a_verified_20260910) and APH Lampo 2023
(component_mismatch, genuine $63K filer-side gap) likewise already
classified - untouched.
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260924_1400_pre_dqbatch.json")

SRC = "def14a_verified_20260924"
NOTE = "2026-09-24 14:00 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
companies = {c["ticker"]: c for c in data["companies"]}

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
assert n0 == 6873, f"row count {n0} != 6873"

# (ticker, name, year, expected pension_nqdc, expected total)
PRE = [
    ("PFE", "D. Lankler", 2023, 196724, 5477798),
    ("PFE", "A. Bourla", 2023, 8440, 21562064),
    ("MOH", "Jeff D. Barlow", 2025, 159234, 4395324),
    ("MOH", "Debra J. Bacon", 2025, 8630, 2931727),
    ("AEP", "Charles E. Zebula", 2025, 151984, 556996),
    ("ARE", "Marc E. Binda", 2024, 129353, 5787452),
    ("ARE", "Hunter L. Kass", 2024, 6512, 8708376),
    ("ARE", "Lawrence J. Diamond", 2025, 2783, 2668545),
    ("ARE", "Hunter L. Kass", 2025, 1454, 7008198),
    ("ADP", "John C. Ayala", 2025, 93331, 6742344),
    ("BALL", "Scott A. Vail", 2025, 29588, 1998336),
    ("APH", "R.A. Norwitt", 2023, 8800, 10944707),
    ("CVS", "Thomas F. Cowhey", 2025, 3097, 6715138),
    ("C", "Mark Mason", 2025, 2886, 19535851),
    ("AVY", "Gregory S. Lovins", 2023, 821, 4050895),
]
for ticker, nm, yr, pen, tot in PRE:
    e = get(ticker, nm, yr)
    assert e["pension_nqdc"] == pen, f"{ticker} {nm} {yr}: pension {e['pension_nqdc']} != {pen}"
    assert e["total"] == tot, f"{ticker} {nm} {yr}: total {e['total']} != {tot}"
    assert e.get("_total_source") == "verified", \
        f"{ticker} {nm} {yr}: source {e.get('_total_source')} != verified"
    assert foot(e) == tot, f"{ticker} {nm} {yr}: stored components do not foot"
print("pre-write assertions OK (15 rows, all foot exactly)")


def relabel(ticker, name, year, note, title=None):
    """Row matches the filing; mark the primary re-verification."""
    global relabeled
    e = get(ticker, name, year)
    assert foot(e) == e["total"], \
        f"{ticker} {name} {year}: stored row does not foot"
    if title and e["title"] != title:
        note += f"; title -> SCT-verbatim '{title}' (was '{e['title']}')"
        e["title"] = title
    e["_total_source"] = SRC
    e["_accession"] = accession(ticker)
    prev = e.get("_repair_note_20260924_1400", "")
    e["_repair_note_20260924_1400"] = (prev + "; " if prev else "") + note
    relabeled += 1


# ---------------- 15 false positives (filing-verbatim, no value changes) ----------------
FP = [
    ("PFE", "D. Lankler", 2023,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0000078003-26-000033, re-fetched "
     f"2026-09-24) pension column reads $196,724, NEIP $0 (2023 zero-payout "
     f"incentive year for all five PFE NEOs); fn (4): actuarial PV of "
     f"accumulated pension benefits; components foot exactly",
     "Chief Legal Officer, EVP"),
    ("PFE", "A. Bourla", 2023,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0000078003-26-000033) pension column "
     f"reads $8,440, NEIP $0; cross-corroborated by the Pay-vs-Performance "
     f"CEO SCT-to-CAP reconciliation (2023 deduction $8,440); foot exact",
     None),
    ("MOH", "Jeff D. Barlow", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001179929-26-000014, re-fetched "
     f"2026-09-24) 'Change in Nonqualified Deferred Comp. Earnings' reads "
     f"$159,234, NEIP $0 (MOH paid no 2025 cash bonuses); corroborated by a "
     f"second summary table in the same filing and the 2025 bonus table "
     f"(actual bonus $0 for all five NEOs); foot exact",
     None),
    ("MOH", "Debra J. Bacon", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001179929-26-000014) NQDC earnings "
     f"reads $8,630, NEIP $0; same corroborations as Barlow; fn (5): "
     f"first-time NEO in 2024; foot exact",
     None),
    ("AEP", "Charles E. Zebula", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0000004904-26-000022, re-fetched "
     f"2026-09-24) pension column reads $151,984, NEIP '-' (not eligible for "
     f"2025 annual incentive; departed EVP/CFO, partial-year salary "
     f"$147,789); fn (5): actuarial increase in combined qualified/ "
     f"nonqualified DB plans, no above-market NQDC earnings; foot exact",
     "Former Executive Vice President and Chief Financial Officer"),
    ("ARE", "Marc E. Binda", 2024,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001035443-26-000031, re-fetched "
     f"2026-09-24) pension column reads $129,353, NEIP '-' (Binda takes "
     f"Bonus, not NEIP; only Marcus and Moglia carry NEIP in this SCT); "
     f"foot exact",
     "Chief Financial Officer and Treasurer"),
    ("ARE", "Hunter L. Kass", 2024,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001035443-26-000031) pension column "
     f"reads $6,512, NEIP '-' (Bonus, not NEIP); fn (2): Pension Plan "
     f"terminated effective 12/31/2024; foot exact",
     "Co-President and Regional Market Director - Greater Boston"),
    ("ARE", "Lawrence J. Diamond", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001035443-26-000031) pension column "
     f"reads $2,783 (post-termination residual per fn 2), NEIP '-'; fn (8): "
     f"not an NEO in 2023; foot exact",
     "Co-Chief Operating Officer and Regional Market Director - Maryland"),
    ("ARE", "Hunter L. Kass", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001035443-26-000031) pension column "
     f"reads $1,454 (post-termination residual per fn 2), NEIP '-'; foot exact",
     "Co-President and Regional Market Director - Greater Boston"),
    ("ADP", "John C. Ayala", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2025 DEF 14A SCT (acc. 0001308179-25-000607, re-fetched "
     f"2026-09-24) pension column reads $93,331, NEIP $0; fn (3): PV "
     f"increase under cash-balance Pension Retirement Plan and frozen SORP "
     f"(Ayala elected FY2025 distribution); pro-rata $921,500 FY2025 bonus "
     f"under qualifying termination sits in All Other per terms; foot exact",
     "Former Chief Operating Officer"),
    ("BALL", "Scott A. Vail", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001104659-26-029499, re-fetched "
     f"2026-09-24) pension column reads $29,588, NEIP '-' (fn 3: Annual STIP "
     f"$0, LTCIC $0); fn (4) verbatim: '$29,588 aggregate change in pension "
     f"value ... benefit accruals during 2025 and assumption changes "
     f"12/31/2024 to 12/31/2025'; foot exact",
     None),
    ("APH", "R.A. Norwitt", 2023,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001104659-26-040688, re-fetched "
     f"2026-09-24) pension column reads $8,800, NEIP $0; fn (3) verbatim: "
     f"2023 actuarial-assumption-change increases $8,800/$2,600/$24,200 "
     f"(benefits frozen 12/31/2006); foot exact",
     None),
    ("CVS", "Thomas F. Cowhey", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001308179-26-000201, re-fetched "
     f"2026-09-24) pension column reads $3,097, NEIP $0; fn (6): column "
     f"reflects pension values (PVAB) only, no above-market NQDC earnings "
     f"(Aetna Pension Plan participant, frozen 12/31/2010); foot exact",
     "Former Executive Vice President and Chief Financial Officer"),
    ("C", "Mark Mason", 2025,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001206774-26-000185, re-fetched "
     f"2026-09-24) pension column reads $2,886, NEIP '-' (Citi grants no "
     f"options to NEOs; Option Awards column present but '-'); fn (6): PVAB "
     f"increases; Pension Benefits Table confirms 6.0 yrs credited service, "
     f"PVAB $58,520; foot exact",
     "CFO"),
    ("AVY", "Gregory S. Lovins", 2023,
     f"{NOTE}: pension/NEIP-confusion queue re-verification sweep - FALSE "
     f"POSITIVE; 2026 DEF 14A SCT (acc. 0001193125-26-102965, re-fetched "
     f"2026-09-24) pension column reads $821 (small actuarial change), NEIP "
     f"$0 (2023 AIP paid zero - Stander also $0 NEIP); foot exact",
     "SVP & Chief Financial Officer"),
]
for ticker, nm, yr, note, ti in FP:
    relabel(ticker, nm, yr, note, title=ti)

# ---------------- metadata re-sync ----------------
shutil.copy(JSON_PATH, BACKUP)
print("backup:", BACKUP)

n = sum(len(c["executives"]) for c in data["companies"])
assert n == 6873, f"total {n} != 6873 (rows added/dropped unexpectedly)"
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
    block["last_audit"] = "2026-09-24"
assert sum(recount.values()) == n
dq = data["metadata"]["data_quality"]
print("verified:", dq["verified"], "| component_mismatch:", dq["component_mismatch"],
      "| def14a_verified_20260924:", dq["def14a_verified_20260924"],
      "| verified_total:", dq["verified_total"])
data["metadata"]["last_updated"] = "2026-09-24"

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
    f.write("\n")

# ---------------- static-copy sync ----------------
vt, total = dq["verified_total"], n
pct = f"{vt / total * 100:.1f}%"
print("headline:", vt, "/", total, pct)
assert (vt, total, pct) == (6845, 6873, "99.6%"), f"unexpected headline {(vt, total, pct)}"

# README audit-trail append (convention: each batch extends line 11)
audit = ("; 2026-09-24 14:00 PT batch: pension/NEIP-confusion queue "
         "re-verification sweep (final 15): all 14 remaining DEF 14As "
         "re-fetched from EDGAR and every flagged SCT row re-read "
         "primary-source - 15/15 FALSE POSITIVES (genuine filing-verbatim "
         "pension/NQDC values with NEIP genuinely $0/'-'; all components "
         "foot exactly, $0 gap; 10 SCT-verbatim title syncs); the 5 column-"
         "shift candidates (HIG/NDSN/ETN) were already repaired 2026-09-19 "
         "14:00 PT (verified no-op); 15 rows relabeled def14a_verified_"
         "20260924; headline buckets unchanged at 99.6% (6,845/6,873).")
with open(os.path.join(HERE, "..", "README.md"), encoding="utf-8") as f:
    lines = f.readlines()
assert lines[10].rstrip("\n").endswith("."), "audit-trail anchor lost"
lines[10] = lines[10].rstrip("\n") + audit + "\n"
with open(os.path.join(HERE, "..", "README.md"), "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README audit trail appended")

print(f"relabeled={relabeled} total_records={n}")
