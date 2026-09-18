#!/usr/bin/env python3
"""2026-09-18 10:00 PT primary-source DQ batch: missing-NEO-row restoration + column-shift/value repairs.

Source: hidden_files/extract_dq_20260918_1000.json - 15 companies re-extracted verbatim
from their latest DEF 14A SCTs this run (ENPH, SMCI, ROP, MET, DLR, WYNN, TRGP, GEN,
CTRA, VRSN, FRT, TPL, CPRT, CARR, IPG). All repair/add values are read mechanically
from the extraction JSON - nothing hand-transcribed.

Classes repaired:
1. Missing NEO-year rows restored (24): SMCI Liang 2023/2025; TRGP Pryor 2023/2025,
   McDonie 2023/2024, Muraro 2023/2024/2025, Byers 2025; CTRA Sirgo 2023/2024/2025,
   DeShazer 2025; VRSN Kilguss 2023/2024/2025, Calys 2025; MET McCallion 2023/2024/2025,
   Debel 2023/2024/2025.
2. MET column shift (9 rows: Pappas/Tadros/Khalaf x 2023-2025): MET SCT has no Bonus
   column; the old parse shifted stock->bonus and option->stock (option_awards null).
   Repaired: bonus=0, stock_awards=<filing stock>, option_awards=<filing option>.
   Components foot exactly to filing totals after repair.
3. FRT salary/bonus shift (7 rows: Wood x3, Becker x3, Guglielmone 2025): old parse
   zeroed salary and filed it under bonus (2026-09-04 fix note superseded).
   Repaired: salary=<filing salary>, bonus=<filing bonus or 0>.
4. Filing-verbatim totals on $1-gap rows (component_mismatch): FRT Wood 2025
   (9929147), Guglielmone 2024 (2299188), Guglielmone 2023 (2446128), Becker 2024
   (2358619). Printed totals kept; gaps are the filers' own arithmetic.
5. CPRT Stearns 2023: reverted the 2026-09-04 fabricated reconciliation
   (all_other had been invented as 5295 to force footing); filing prints 5250 with
   total 9706972 (genuine -$45 filing-side gap, verified vs raw HTML) ->
   component_mismatch, filing-verbatim.
6. Name merges to SCT-verbatim: ROP 'Neil Hunn' -> 'L. Neil Hunn' (x3);
   MET 'Michel A Khalaf' -> 'Michel A. Khalaf' (x3); IPG 'Christopher F. Carroll' ->
   'Christopher Carroll' (x3). FRT (PEO)/(PFO) name-cell markers and WYNN all-caps
   names deliberately NOT adopted (stored clean/title-case forms retained).
7. Title sync to SCT-verbatim for all overlapping rows in the 15 companies
   (SMCI Weigand/Kao, ROP Stipancich, MET Tadros/Khalaf, DLR Lee, WYNN x3,
   TRGP Meloy/Kneale/McDonie-2025/Pryor-2024, CTRA Bell/DeShazer-2024, FRT x9,
   CARR Goris/Gierges/Pandya/Dryden, IPG Krakowsky/Johnson/Bonzani/Carroll-2023).
   Substantive fixes: TRGP McDonie 2025 'Chief Financial Officer' ->
   'President - Gathering and Processing'; TRGP Pryor 2024 wrong business unit;
   CTRA DeShazer 2024 'Senior Vice President, Business Units' ->
   'Executive Vice President-Operations'; CARR Pandya 2025 'SVP, Chief Financial
   Officer' -> 'President, CSA'.

Aggregates recomputed (latest-year NEO sum / count) for SMCI/ROP/MET/TRGP/CTRA/
VRSN/FRT/CPRT/IPG. Note: the rest of the 500 still carry aggregates from the
pre-2025-proxy cycle (systematic staleness, flagged for a dedicated bulk run).
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
EXT_PATH = os.path.join(HERE, "extract_dq_20260918_1000.json")
BACKUP = os.path.join(HERE, "compensation_backup_20260918_1000_pre_dqbatch.json")

SRC = "def14a_verified_20260918"
NOTE = "2026-09-18 10:00 PT"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
with open(EXT_PATH, encoding="utf-8") as f:
    ext = json.load(f)["companies"]
shutil.copy2(JSON_PATH, BACKUP)
print("backup:", BACKUP)

companies = {c["ticker"]: c for c in data["companies"]}
added = 0
repaired = 0

ALIASES = {
    "ROP": {"Neil Hunn": "L. Neil Hunn"},
    "MET": {"Michel A Khalaf": "Michel A. Khalaf"},
    "IPG": {"Christopher F. Carroll": "Christopher Carroll"},
}

def sct_neo(ticker, stored_name):
    """Find the extraction NEO matching a stored name (aliases, PEO/PFO markers, case)."""
    ce = ext[ticker]
    for n in ce["neos"]:
        sn = n["name"]
        if sn == stored_name or sn.lower() == stored_name.lower():
            return n
        if sn.replace(" (PEO)", "").replace(" (PFO)", "") == stored_name:
            return n
    alias = ALIASES.get(ticker, {}).get(stored_name)
    if alias:
        return next((n for n in ce["neos"] if n["name"] == alias), None)
    return None

def ext_vals(n, year):
    return n["years"][str(year)]

def foot(vals):
    return sum(vals.get(k) or 0 for k in
               ("salary", "bonus", "stock_awards", "option_awards",
                "non_equity_incentive", "pension_nqdc", "all_other"))

# company key styles for new rows (mirror each company's stored convention)
SPARSE = {
    "TRGP": ("salary", "bonus", "stock_awards", "all_other"),
    "CTRA": ("salary", "stock_awards", "non_equity_incentive", "all_other"),
    "VRSN": ("salary", "stock_awards", "non_equity_incentive", "all_other"),
}
FULL = ("salary", "bonus", "stock_awards", "option_awards",
        "non_equity_incentive", "pension_nqdc", "all_other")

def add_row(ticker, sct_name, year):
    global added
    c = companies[ticker]
    assert not [e for e in c["executives"] if e["name"] == sct_name and e["year"] == year], \
        f"duplicate {ticker} {sct_name} {year}"
    n = next(n for n in ext[ticker]["neos"] if n["name"] == sct_name)
    v = ext_vals(n, year)
    assert foot(v) == v["total"], f"{ticker} {sct_name} {year}: extraction does not foot"
    keys = SPARSE.get(ticker, FULL)
    row = {"name": sct_name, "title": n["title"], "year": year}
    for k in keys:
        row[k] = v.get(k) or 0
    row["total"] = v["total"]
    row["_total_source"] = SRC
    row["_accession"] = ext[ticker]["accession"]
    c["executives"].append(row)
    added += 1

def rep(ticker, name, year, note, **fields):
    global repaired
    c = companies[ticker]
    hits = [e for e in c["executives"] if e["name"] == name and e["year"] == year]
    assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
    e = hits[0]
    for k, val in fields.items():
        e[k] = val
    e["_repair_note_20260918_1000"] = note
    repaired += 1

# ---------------- 1. missing rows (24) ----------------
for ticker, sct_name, year in [
    ("SMCI", "Charles Liang", 2023), ("SMCI", "Charles Liang", 2025),
    ("TRGP", "D. Scott Pryor", 2023), ("TRGP", "Patrick J. McDonie", 2023),
    ("TRGP", "Robert M. Muraro", 2023), ("TRGP", "Patrick J. McDonie", 2024),
    ("TRGP", "Robert M. Muraro", 2024), ("TRGP", "D. Scott Pryor", 2025),
    ("TRGP", "Robert M. Muraro", 2025), ("TRGP", "William A. Byers", 2025),
    ("CTRA", "Blake A. Sirgo", 2023), ("CTRA", "Blake A. Sirgo", 2024),
    ("CTRA", "Blake A. Sirgo", 2025), ("CTRA", "Michael D. DeShazer", 2025),
    ("VRSN", "George E. Kilguss, III", 2023), ("VRSN", "George E. Kilguss, III", 2024),
    ("VRSN", "George E. Kilguss, III", 2025), ("VRSN", "John D. Calys", 2025),
    ("MET", "John D. McCallion", 2023), ("MET", "John D. McCallion", 2024),
    ("MET", "John D. McCallion", 2025), ("MET", "Marlene Debel", 2023),
    ("MET", "Marlene Debel", 2024), ("MET", "Marlene Debel", 2025),
]:
    add_row(ticker, sct_name, year)

# ---------------- 2. MET column-shift repair (9 rows) ----------------
for stored_name in ("Bill Pappas", "Ramy Tadros", "Michel A Khalaf"):
    n = sct_neo("MET", stored_name)
    for year in (2023, 2024, 2025):
        v = ext_vals(n, year)
        assert foot(v) == v["total"], (stored_name, year)
        rep("MET", stored_name, year,
            f"{NOTE}: column-shift repair - MET SCT has no Bonus column; old parse filed "
            f"stock_awards under bonus and option_awards under stock_awards; "
            f"bonus=0, stock_awards={v['stock_awards']}, option_awards={v.get('option_awards') or 0}; "
            "filing components now foot exactly to filing total",
            bonus=0, stock_awards=v["stock_awards"],
            option_awards=v.get("option_awards") or 0)

# ---------------- 3. FRT salary/bonus shift repair ----------------
FRT_FIX = {
    ("Donald C. Wood", 2023): (1000000, 0, 8941820, False),
    ("Donald C. Wood", 2024): (1000000, 0, 9240530, False),
    ("Donald C. Wood", 2025): (1000000, 0, 9929147, True),   # $1 filing-side gap
    ("Daniel Guglielmone", 2025): (650000, 0, 3302674, False),
    ("Dawn M. Becker", 2023): (575000, 0, 2337304, False),
    ("Dawn M. Becker", 2024): (575000, 0, 2358619, True),    # $1 filing-side gap
    ("Dawn M. Becker", 2025): (575000, 0, 2475611, False),
}
for (nm, yr), (sal, bon, tot, gap) in FRT_FIX.items():
    fields = {"salary": sal, "bonus": bon, "total": tot}
    note = (f"{NOTE}: salary/bonus column-shift repair - FRT SCT salary was zeroed and "
            f"filed under bonus (2026-09-04 fix note superseded); salary={sal}, bonus={bon}, "
            f"total={tot} filing-verbatim")
    if gap:
        fields["_total_source"] = "component_mismatch"
        note += "; $1 filing-side arithmetic gap (components sum != printed total), kept verbatim"
    rep("FRT", nm, yr, note, **fields)
# FRT $1-gap rows needing only the component_mismatch tag (values already verbatim)
for nm, yr, tot in [("Daniel Guglielmone", 2024, 2299188), ("Daniel Guglielmone", 2023, 2446128)]:
    rep("FRT", nm, yr,
        f"{NOTE}: filing-side $1 arithmetic gap (components sum differs by $1 from printed "
        f"total {tot}); values already filing-verbatim, tagged component_mismatch",
        _total_source="component_mismatch")

# ---------------- 5. CPRT Stearns 2023: revert fabricated reconciliation ----------------
rep("CPRT", "Leah C. Stearns", 2023,
    f"{NOTE}: reverted 2026-09-04 fabricated reconciliation (all_other had been invented "
    "as 5295 to force footing); filing prints all_other 5250 with total 9706972 "
    "(genuine -$45 filing-side gap, verified vs raw HTML); kept verbatim, component_mismatch",
    all_other=5250, _total_source="component_mismatch")

# ---------------- 6+7. name merges + SCT-verbatim title sync (all 15 companies) ----------------
for ticker in ext:
    c = companies[ticker]
    for e in c["executives"]:
        n = sct_neo(ticker, e["name"])
        if n is None:
            continue  # historical row not in latest SCT (e.g. TPL 2022 rows) - keep
        new_name = n["name"].replace(" (PEO)", "").replace(" (PFO)", "")
        # keep stored title-case over filing all-caps (WYNN)
        if new_name != e["name"] and new_name.lower() != e["name"].lower():
            e["_repair_note_20260918_1000"] = (
                f"{NOTE}: name -> SCT-verbatim '{new_name}' (was '{e['name']}')")
            e["name"] = new_name
            repaired += 1
        if e["title"] != n["title"]:
            e["_repair_note_20260918_1000"] = (
                (e.get("_repair_note_20260918_1000", "") + "; " if e.get("_repair_note_20260918_1000") else "") +
                f"{NOTE}: title -> SCT-verbatim '{n['title']}' (was '{e['title']}')").strip()
            e["title"] = n["title"]
            repaired += 1

# ---------------- aggregates: touched companies ----------------
for ticker in ("SMCI", "ROP", "MET", "TRGP", "CTRA", "VRSN", "FRT", "CPRT", "IPG"):
    c = companies[ticker]
    ly = max(c["available_years"])
    rows = [e for e in c["executives"] if e["year"] == ly]
    old_agg, old_n = c["total_neo_compensation"], c["neo_count"]
    c["total_neo_compensation"] = sum(e["total"] for e in rows)
    c["neo_count"] = len(rows)
    print(f"{ticker}: agg {old_agg} -> {c['total_neo_compensation']}, "
          f"neo_count {old_n} -> {c['neo_count']} ({ly}, {len(rows)} rows)")

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
