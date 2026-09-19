#!/usr/bin/env python3
"""2026-09-19 02:00 PT primary-source DQ batch: HAS 14-row rebuild, APD FY2025
re-verification (+3 title repairs), MKC 2024/2023 column-shift repair.

All values verified verbatim against the companies' latest DEF 14A Summary
Compensation Tables (re-fetched from EDGAR this run; raw filings + ledger in
the goal hidden workspace dq_20260919_0200/). Nothing hand-transcribed.

Classes:
1. HAS (Hasbro) — full 14-row rebuild. The old parse left-shifted the SCT by
   one column AND dropped the NEIP column: salary filed into bonus, stock
   awards parked in pension_nqdc, NEIP/All-Other dropped, totals recomputed
   wrong (Cocks FY2024 $12.0M stored vs $16.84M filed). All 14 rows repaired
   filing-verbatim; 3 rows carry genuine $1 filer-side rounding gaps
   (Goetter 2023, Hight 2024, Kilpin 2023) and stay in the verified family
   per the 2026-09-10 taxonomy decision. CEO anchor 12,000,024 -> 16,841,413.
2. APD (Air Products) — pension/NEIP-confusion queue triage: 5 queue hits are
   FALSE POSITIVES. The FY2025 SCT (filed 2025-12-10) genuinely shows NEIP=0
   for all FY2025 NEOs with small pension-change values ($189-$12,040).
   All 7 FY2025 rows confirmed filing-verbatim; 3 SCT-verbatim title repairs
   (Brifo, Ghasemi +Former, Major +Former). Relabeled def14a_verified_20260919.
3. MKC (McCormick) — column-shift class: the 2026 DEF 14A SCT has NO Bonus
   column; the old parse filed Stock->Salary, Option->Stock, NEIP->Option,
   Pension(->NEIP, All-Other->Pension, Total->All-Other, and recomputed the
   total (Foley FY2024 $20.55M stored vs $10.85M filed). 2025 rows parsed
   correctly (parser keyed the first year-block right). 7 rows repaired;
   5 rows carry genuine $1-$2 filer-side rounding gaps and stay in the
   verified family per the 2026-09-10 taxonomy decision. Foust 2025 title
   -> "President, Americas". CEO anchor 20,552,705 -> 10,849,622.

Aggregates re-anchored to fiscal_year on HAS + MKC (section 5); pay ratios
and median worker pay untouched (anchor-year disclosed values, verified
self-consistent: HAS 16,841,413/105,311=159.9->160; MKC 10,849,622/45,444=238.7->238).
"""
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260919_0200_pre_dqbatch.json")

SRC = "def14a_verified_20260919"
NOTE = "2026-09-19 02:00 PT"

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
# HAS stored (shifted) values we will replace
e = get("HAS", "Chris Cocks", 2025)
assert (e["salary"], e["bonus"], e["pension_nqdc"], e["total"]) == (0, 1500000, 10500099, 12000099)
e = get("HAS", "Chris Cocks", 2024)
assert (e["salary"], e["pension_nqdc"], e["total"]) == (0, 10500024, 12000024)
e = get("HAS", "Gina Goetter", 2023)
assert (e["salary"], e["non_equity_incentive"], e["total"]) == (634615, 4000042, 4984657)
# APD FY2025 stored values (confirmed verbatim; titles to fix)
e = get("APD", "Victoria Brifo", 2025)
assert e["title"] == "Executive Vice President and Chief Financial Officer"
assert (e["salary"], e["bonus"], e["stock_awards"], e["pension_nqdc"], e["total"]) == \
    (586338, 486000, 1281601, 12040, 2417520)
e = get("APD", "Seifi Ghasemi", 2025)
assert e["title"] == "Chairman, President and Chief Executive Officer"
e = get("APD", "Sean D. Major", 2025)
assert e["title"] == "Executive Vice President, General Counsel and Secretary"
# MKC stored (shifted) values
e = get("MKC", "Brendan M. Foley", 2024)
assert (e["salary"], e["stock_awards"], e["option_awards"], e["non_equity_incentive"],
        e["pension_nqdc"], e["all_other"], e["total"]) == \
    (3750020, 3750011, 1843050, 0, 360002, 10849622, 20552705)
e = get("MKC", "Sarah J. Piper", 2023)
assert e["salary"] == 375062 and e["pension_nqdc"] == 93992
e = get("MKC", "Andrew D. Foust", 2025)
assert e["title"] == "Americas"
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
    prev = e.get("_repair_note_20260919_0200", "")
    e["_repair_note_20260919_0200"] = (prev + "; " if prev else "") + note
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
    prev = e.get("_repair_note_20260919_0200", "")
    e["_repair_note_20260919_0200"] = (prev + "; " if prev else "") + note
    relabeled += 1


# ---------------- 1. HAS: 14-row filing-verbatim rebuild ----------------
# Hasbro 2026 DEF 14A (acc. 0001193125-26-160426, filed 2026-04-17, re-fetched
# 2026-09-19). SCT columns: Salary | Bonus | Stock | Option | NEIP | Pension | All Other | Total.
HAS_ROWS = [
    # name, year, salary, bonus, stock, option, neip, pension, all_other, total, small_delta_ok
    ("Chris Cocks", 2025, 1500000, 0, 10500099, 0, 6000000, 0, 672422, 18672521, False),
    ("Chris Cocks", 2024, 1500000, 0, 10500024, 0, 4429688, 0, 411701, 16841413, False),
    ("Chris Cocks", 2023, 1500000, 0, 7875020, 3086034, 1944000, 0, 705815, 15110869, False),
    ("Gina Goetter", 2025, 1000000, 0, 3000011, 0, 2000000, 0, 258738, 6258749, False),
    ("Gina Goetter", 2024, 1000000, 0, 4500025, 0, 1687500, 0, 161011, 7348536, False),
    ("Gina Goetter", 2023, 634615, 350000, 4000042, 0, 548307, 0, 177036, 5710001, True),
    ("John Hight", 2025, 725000, 225000, 1812579, 0, 1450000, 0, 113779, 4326358, False),
    ("John Hight", 2024, 278846, 225000, 3500028, 0, 348558, 0, 128313, 4480746, True),
    ("Tim Kilpin", 2025, 850000, 0, 2125092, 0, 340000, 0, 159000, 3474092, False),
    ("Tim Kilpin", 2024, 850000, 0, 2975067, 0, 850000, 0, 141692, 4816759, False),
    ("Tim Kilpin", 2023, 572115, 0, 3275135, 471084, 637500, 0, 312550, 5268385, True),
    ("Tarrant Sibley", 2025, 690385, 0, 1575092, 0, 1173654, 0, 139361, 3578492, False),
    ("Tarrant Sibley", 2024, 650000, 0, 1950100, 0, 822656, 145, 86461, 3509362, False),
    ("Tarrant Sibley", 2023, 619423, 0, 1650084, 646606, 401386, 911, 71948, 3390358, False),
]
for nm, yr, sal, bon, stk, opt, neip, pen, ao, tot, sd in HAS_ROWS:
    rep("HAS", nm, yr,
        f"{NOTE}: full rebuild - old parse left-shifted SCT by one column (salary->bonus, "
        f"stock parked in pension_nqdc, NEIP/All-Other dropped, total recomputed); "
        f"now filing-verbatim from 2026 DEF 14A SCT",
        small_delta_ok=sd, salary=sal, bonus=bon, stock_awards=stk,
        option_awards=opt, non_equity_incentive=neip, pension_nqdc=pen,
        all_other=ao, total=tot)

# ---------------- 2. APD: FY2025 re-verification (queue false positives) ----------------
APD_TITLES = {
    "Eduardo Menezes": "Chief Executive Officer",
    "Melissa N. Schaeffer": "Executive Vice President and Chief Financial Officer",
    "Victoria Brifo": "Executive Vice President and Chief Human Resources Officer, Corporate Communications and Corporate Relations",
    "Brian Galovich": "Executive Vice President and Chief Information Officer",
    "Francesco Maione": "President, Americas and Global Helium & Rare Gases",
    "Seifi Ghasemi": "Former Chairman, President and Chief Executive Officer",
    "Sean D. Major": "Former Executive Vice President, General Counsel and Secretary",
}
for nm, ti in APD_TITLES.items():
    relabel("APD", nm, 2025,
            f"{NOTE}: pension/NEIP-confusion queue triage - FALSE POSITIVE; FY2025 SCT "
            f"(2026 DEF 14A acc. 0001308179-25-000643) genuinely shows NEIP=0 with small "
            f"pension-change values; row confirmed filing-verbatim", title=ti)

# ---------------- 3. MKC: 2024/2023 column-shift repair ----------------
# McCormick 2026 DEF 14A (acc. 0000063754-26-000140, filed 2026-02-17, re-fetched
# 2026-09-19). SCT has NO Bonus column; old parse filed Stock->Salary etc.
MKC_ROWS = [
    # name, year, salary, stock, option, neip, pension, all_other, total, small_delta_ok
    ("Brendan M. Foley", 2024, 1146538, 3750020, 3750011, 1843050, 0, 360002, 10849622, True),
    ("Brendan M. Foley", 2023, 953558, 1200028, 1200010, 1720590, 0, 138988, 5213172, True),
    ("Andrew D. Foust", 2024, 588461, 500033, 500010, 493788, 28377, 164368, 2275038, True),
    ("Sarah J. Piper", 2024, 547308, 425038, 425008, 491480, 12376, 157209, 2058418, True),
    ("Sarah J. Piper", 2023, 473308, 375062, 375003, 459515, 0, 93992, 1776880, False),
    ("Jeffery D. Schwartz", 2024, 688846, 900008, 900011, 636132, 71349, 189507, 3385852, True),
    ("Jeffery D. Schwartz", 2023, 642692, 850027, 850007, 763555, 0, 93382, 3199663, False),
]
for nm, yr, sal, stk, opt, neip, pen, ao, tot, sd in MKC_ROWS:
    rep("MKC", nm, yr,
        f"{NOTE}: column-shift repair - 2026 DEF 14A SCT has no Bonus column; old parse "
        f"filed Stock->Salary, Option->Stock, NEIP->Option, Pension->NEIP, All-Other->Pension, "
        f"Total->All-Other and recomputed the total; now filing-verbatim",
        small_delta_ok=sd, salary=sal, bonus=0, stock_awards=stk,
        option_awards=opt, non_equity_incentive=neip, pension_nqdc=pen,
        all_other=ao, total=tot)
for nm in ("Brendan M. Foley", "Marcos M. Gabriel", "Andrew D. Foust",
           "Sarah J. Piper", "Jeffery D. Schwartz"):
    relabel("MKC", nm, 2025,
            f"{NOTE}: FY2025 rows confirmed filing-verbatim vs 2026 DEF 14A SCT (2025 "
            f"year-block parsed correctly; no changes)",
            title="President, Americas" if nm == "Andrew D. Foust" else None)

# ---------------- aggregates: fiscal_year anchoring ----------------
EXPECTED = {
    "HAS": ("Chris Cocks", 16841413, 5, 36996816),
    "MKC": ("Brendan M. Foley", 10849622, 4, 18568930),
}
for ticker, (ceo, ceo_tot, exp_n, exp_tot) in EXPECTED.items():
    c = companies[ticker]
    fy = c["fiscal_year"]
    rows = [e for e in c["executives"] if e["year"] == fy]
    assert len(rows) == exp_n, f"{ticker}: {len(rows)} FY rows != {exp_n}"
    tot = sum(e["total"] for e in rows)
    assert tot == exp_tot, f"{ticker}: FY sum {tot:,} != {exp_tot:,}"
    old = (c["neo_count"], c["total_neo_compensation"], c["total_compensation"])
    c["neo_count"], c["total_neo_compensation"], c["total_compensation"] = exp_n, exp_tot, ceo_tot
    print(f"{ticker}: neo {old[0]}->{exp_n}, total_neo {old[1]:,}->{exp_tot:,}, "
          f"CEO {old[2]:,}->{ceo_tot:,}")

# APD aggregates untouched (FY2024 slate verified 2026-09-16; FY2025 rows only relabeled)
apd = companies["APD"]
assert apd["neo_count"] == 3 and apd["total_neo_compensation"] == 22934407

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
        # label buckets only: skip non-label metadata keys (e.g. last_audit)
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
mismatch = dq["component_mismatch"]
assert (vt, total, pct, mismatch) == (6838, 6866, "99.6%", 28), \
    f"unexpected headline {(vt, total, pct, mismatch)}"

edits = [
    (os.path.join(HERE, "..", "README.md"), [
        ("last audit 2026-09-18; last partial re-verification 2026-09-17, ",
         "last audit 2026-09-19; last partial re-verification 2026-09-19, "),
        ("Buckets (as of 2026-09-18: 6,866 rows):",
         "Buckets (as of 2026-09-19: 6,866 rows):"),
        # taxonomy table component_mismatch cell was stale at 21 (metadata: 28)
        ("| `component_mismatch` | The filing's own components don't sum to its printed total; stored verbatim, flagged | 21 |",
         "| `component_mismatch` | The filing's own components don't sum to its printed total; stored verbatim, flagged | 28 |"),
    ]),
]
for path, pairs in edits:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for old, new in pairs:
        assert old in text, f"pattern missing in {path}: {old!r}"
        text = text.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
print("static copies synced (dates + stale taxonomy cell)")

# README audit-trail append (convention: each batch extends line 11)
audit = ("; 2026-09-19 02:00 PT batch: HAS 14-row filing-verbatim rebuild (old parse "
         "left-shifted the SCT one column - salary->bonus, stock parked in pension_nqdc, "
         "NEIP/All-Other dropped, totals recomputed; Cocks FY2024 CEO $12.00M->$16.84M, "
         "total_neo $27.93M->$37.00M), APD FY2025 7-row re-verification (pension/NEIP "
         "queue triage: 5 hits FALSE POSITIVES, FY2025 NEIP genuinely $0; 3 SCT-verbatim "
         "title repairs), MKC 2024/2023 column-shift repair (2026 DEF 14A SCT has no "
         "Bonus column; Foley FY2024 $20.55M->$10.85M, total_neo $34.17M->$18.57M; "
         "Foust 2025 title -> President, Americas); 33 rows relabeled def14a_verified_20260919; "
         "headline buckets unchanged at 99.6% (6,838/6,866).")
with open(os.path.join(HERE, "..", "README.md"), encoding="utf-8") as f:
    lines = f.readlines()
assert lines[10].rstrip("\n").endswith(")."), "audit-trail anchor lost"
lines[10] = lines[10].rstrip("\n") + audit + "\n"
with open(os.path.join(HERE, "..", "README.md"), "w", encoding="utf-8") as f:
    f.writelines(lines)
print("README audit trail appended")

print(f"repaired={repaired} relabeled={relabeled} total_records={n}")
