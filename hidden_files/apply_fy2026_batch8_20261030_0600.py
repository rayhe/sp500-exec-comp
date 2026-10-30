#!/usr/bin/env python3
"""2026-10-30 06:00 PT FY2026 enrichment batch 8: GIS/FDX/PG/PH/TPR/TPL.

Source proxies (all DEF 14A, fetched 2026-10-30):
- GIS  General Mills      filed 2026-08-13  acc 0001628280-26-056619  FY2026 (y/e May 31, 2026)
- FDX  FedEx              filed 2026-08-17  acc 0001104659-26-097836  FY2026 (y/e May 31, 2026)
- PG   Procter & Gamble   filed 2026-08-28  acc 0001193125-26-372211  FY2026 (y/e Jun 30, 2026)
- PH   Parker-Hannifin    filed 2026-09-18  acc 0001308179-26-000394  FY2026 (y/e Jun 30, 2026)
- TPR  Tapestry           filed 2026-09-25  acc 0001116132-26-000024  FY2026 (y/e ~Jun 27, 2026)
- TPL  Texas Pacific Land filed 2026-09-25  acc 0001104659-26-110963  delayed 2026 annual meeting, FY2025 SCT (no new rows)

Findings:
- GIS: 8 overlaps cross-checked filing-verbatim, 0 deltas; +7 rows (5x2026, Thissen 2025/2024 gap-fill)
- FDX: 5 overlaps verbatim; 2 stored column-shift parse errors repaired filing-verbatim
        (Dietrich 2024, Krishnasamy 2024); +6 rows (2026)
- PG:  prior ingest labeled fiscal years "2025-26"->2025 (off by one vs dataset
        end-year convention used by GIS/FDX/CSCO/MSFT/ORCL). Relabel stored
        2025->2026, 2024->2025 (values already filing-verbatim). Stored 2023/2022
        rows additionally column-shifted (salary column dropped); replaced
        filing-verbatim from the 2026 proxy (2023-24) and 2024 proxy (2022-23);
        +5 rows 2022 (2021-22 from 2024 proxy).
- PH:  4 overlaps verbatim (2025); 4 stored column-shift parse errors repaired
        filing-verbatim (Parmentier/Leombruno/Ross/Leonti 2024); +5 rows (2026);
        None->0 normalization on 2025 bonus/pension.
- TPR: 9 overlaps verbatim; +5 rows (2026).
- TPL: 9 overlaps verbatim; filing_date/url updated to latest DEF 14A, no data change.

All CEO anchors continue (Harmening, Subramaniam, Jejurikar, Parmentier, Crevoiserat, Glover).
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
PROX = "/tmp/proxies"

shutil.copy2(JSON_PATH, os.path.join(
    HERE, "compensation_backup_20261030_0600_pre_fy2026batch8.json"))

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

companies = {c["ticker"]: c for c in data["companies"]}

STATS = {"new": 0, "repaired": 0, "relabeled": 0, "checked": 0, "deltas": 0}


def mkrow(name, title, year, salary, bonus, stock, option, neip, pension, all_other, total):
    assert salary + bonus + stock + option + neip + pension + all_other == total, \
        (name, year, salary, bonus, stock, option, neip, pension, all_other, total)
    return {"name": name, "title": title, "year": year, "salary": salary,
            "bonus": bonus, "stock_awards": stock, "option_awards": option,
            "non_equity_incentive": neip, "pension_nqdc": pension,
            "all_other": all_other, "total": total, "_total_source": "verified"}


def add_rows(ticker, rows):
    c = companies[ticker]
    have = {(e["name"], e["year"]) for e in c["executives"]}
    for r in rows:
        assert (r["name"], r["year"]) not in have, ("dup", ticker, r["name"], r["year"])
        c["executives"].append(r)
        have.add((r["name"], r["year"]))
        STATS["new"] += 1


def repair_row(ticker, name, year, **kw):
    c = companies[ticker]
    for e in c["executives"]:
        if e["name"] == name and e["year"] == year:
            for k, v in kw.items():
                e[k] = v
            STATS["repaired"] += 1
            return
    raise AssertionError(("row not found", ticker, name, year))


def crosscheck(ticker, filing_rows):
    """filing_rows: list of (name, year, dict-of-components). Returns new-row specs."""
    c = companies[ticker]
    stored = {(e["name"], e["year"]): e for e in c["executives"]}
    fields = ["salary", "bonus", "stock_awards", "option_awards",
              "non_equity_incentive", "pension_nqdc", "all_other", "total"]
    new = []
    for name, year, comp in filing_rows:
        key = (name, year)
        if key in stored:
            STATS["checked"] += 1
            s = stored[key]
            for f in fields:
                sv = s.get(f)
                if sv != comp[f] and not (sv is None and comp[f] == 0):
                    print("DELTA", ticker, name, year, f, "stored", sv, "filing", comp[f])
                    STATS["deltas"] += 1
        else:
            new.append((name, year, comp))
    return new


# ---------------- GIS ----------------
gis = json.load(open(os.path.join(PROX, "GIS_sct.json")))
GIS_TITLES = {
    "Jeffrey L. Harmening": "Chairman of the Board & CEO",
    "Dana M. McNabb": "Chief Operating Officer",
    "Kofi A. Bruce": "Chief Financial Officer",
    "Jaime Montemayor": "Chief Digital, Technology & Transformation Officer",
    "Karen Wilson Thissen": "General Counsel & Secretary",
}
gis_filing = []
for r in gis:
    for y in r["years"]:
        gis_filing.append((r["name"], y["year"], {
            "salary": y["salary"], "bonus": 0, "stock_awards": y["stock_awards"],
            "option_awards": y["option_awards"], "non_equity_incentive": y["non_equity_incentive"],
            "pension_nqdc": y["pension_nqdc"], "all_other": y["all_other"], "total": y["total"]}))
gis_new = crosscheck("GIS", gis_filing)
add_rows("GIS", [mkrow(n, GIS_TITLES[n], yr,
                       c["salary"], 0, c["stock_awards"], c["option_awards"],
                       c["non_equity_incentive"], c["pension_nqdc"], c["all_other"], c["total"])
                 for n, yr, c in gis_new])
gc = companies["GIS"]
gc["filing_date"] = "2026-08-13"
gc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/40704/000162828026056619/gis-20260810.htm"
gc["fiscal_year"] = 2026
gc["proxy_fiscal_year"] = 2026
gc["available_years"] = [2026, 2025, 2024, 2023]
gc["neo_count"] = 5
gc["total_compensation"] = 14018052
gc["total_neo_compensation"] = sum(
    e["total"] for e in gc["executives"] if e["year"] == 2026)
assert gc["total_neo_compensation"] == 30443580

# ---------------- FDX ----------------
fdx = json.load(open(os.path.join(PROX, "FDX_raw.json")))


def fdx_split(nt):
    nt = re.sub(r"\s*\(\d+\)", "", nt).strip()
    m = re.search(r"\s+(Former\s+)?(Executive Vice President|Senior Vice President|Vice President|President|Chief|Chairman|CEO)", nt)
    assert m, nt
    return nt[:m.start()].strip(), nt[m.start():].strip()


fdx_filing = []
for n in fdx:
    name, title = fdx_split(n["name_title"])
    v = n["nums"]
    fdx_filing.append((name, n["year"], title, {
        "salary": v[0], "bonus": v[1], "stock_awards": v[2], "option_awards": v[3],
        "non_equity_incentive": v[4], "pension_nqdc": v[5], "all_other": v[6], "total": v[7]}))
# cross-check on (name, year) ignoring title
fc = companies["FDX"]
stored_fdx = {(e["name"], e["year"]): e for e in fc["executives"]}
fields = ["salary", "bonus", "stock_awards", "option_awards",
          "non_equity_incentive", "pension_nqdc", "all_other", "total"]
fdx_new = []
for name, year, title, comp in fdx_filing:
    key = (name, year)
    if key in stored_fdx:
        STATS["checked"] += 1
        s = stored_fdx[key]
        for f in fields:
            if s.get(f) != comp[f]:
                print("DELTA FDX", name, year, f, "stored", s.get(f), "filing", comp[f])
                STATS["deltas"] += 1
    else:
        fdx_new.append((name, title, year, comp))
add_rows("FDX", [mkrow(n, t, yr,
                       c["salary"], c["bonus"], c["stock_awards"], c["option_awards"],
                       c["non_equity_incentive"], c["pension_nqdc"], c["all_other"], c["total"])
                 for n, t, yr, c in fdx_new])
# repair the two column-shifted 2024 rows filing-verbatim (keep stored titles)
repair_row("FDX", "John W. Dietrich", 2024,
           salary=822505, bonus=100000, stock_awards=970540, option_awards=1500081,
           non_equity_incentive=867785, pension_nqdc=0, all_other=867762, total=5128673)
repair_row("FDX", "Sriram Krishnasamy", 2024,
           salary=627300, bonus=1237500, stock_awards=1151667, option_awards=1197846,
           non_equity_incentive=808852, pension_nqdc=154764, all_other=816161, total=5994090)
fc["filing_date"] = "2026-08-17"
fc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/1048911/000110465926097836/tm2531093-3_def14a.htm"
fc["fiscal_year"] = 2026
fc["proxy_fiscal_year"] = 2026
fc["available_years"] = [2026, 2025, 2024, 2023]
fc["neo_count"] = 6
fc["total_compensation"] = 27554018
fc["total_neo_compensation"] = sum(e["total"] for e in fc["executives"] if e["year"] == 2026)
assert fc["total_neo_compensation"] == 81054950, fc["total_neo_compensation"]

# ---------------- PG ----------------
pg = companies["PG"]
# 1. drop the column-shifted 2023/2022 rows (to be replaced filing-verbatim)
pg["executives"] = [e for e in pg["executives"] if e["year"] not in (2022, 2023)]
# 2. relabel 2025->2026, 2024->2025 (values already filing-verbatim per cross-check)
for e in pg["executives"]:
    if e["year"] == 2025:
        e["year"] = 2026
        STATS["relabeled"] += 1
    elif e["year"] == 2024:
        e["year"] = 2025
        STATS["relabeled"] += 1
    if e.get("non_equity_incentive") is None:
        e["non_equity_incentive"] = 0  # P&G SCT has no NEIP payouts; prior ingest omitted the key
    if e.get("pension_nqdc") is None:
        e["pension_nqdc"] = 0  # prior ingest omitted zero-valued pension keys
# 3. verify relabeled rows match the 2026 proxy filing-verbatim
pg26 = json.load(open(os.path.join(PROX, "PG_raw.json")))
pg26_bykey = {}
for n in pg26:
    nm = re.sub(r"\s*\d+$", "", n["name"]).strip()
    pg26_bykey[(nm, n["year"])] = n["nums"]
for e in pg["executives"]:
    if e["year"] in (2025, 2026):
        nums = pg26_bykey[(e["name"], e["year"])]
        want = dict(salary=nums[0], bonus=nums[1], stock_awards=nums[2], option_awards=nums[3],
                    non_equity_incentive=nums[4], pension_nqdc=nums[5], all_other=nums[6], total=nums[7])
        for f, v in want.items():
            assert e.get(f) == v, ("PG relabel mismatch", e["name"], e["year"], f, e.get(f), v)
        STATS["checked"] += 1
# 4. insert correct 2024 rows (2026 proxy 2023-24 column)
PG24_TITLES = {
    "Shailesh G. Jejurikar": "President and Chief Executive Officer",
    "Jon R. Moeller": "Executive Chairman of the Board",
    "Andre Schulten": "Chief Financial Officer",
    "Ma. Fatima D. Francisco": "Former CEO - Baby, Feminine and Family Care",
}
pg24_rows = []
for n in pg26:
    if n["year"] == 2024:
        nm = re.sub(r"\s*\d+$", "", n["name"]).strip()
        v = n["nums"]
        pg24_rows.append(mkrow(nm, PG24_TITLES[nm], 2024,
                               v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]))
add_rows("PG", pg24_rows)
# 5. insert correct 2023 rows (2024 proxy 2022-23 column)
pg24p = json.load(open(os.path.join(PROX, "PG2024_raw.json")))
NAME_FIX = {"Shailesh Jejurikar": "Shailesh G. Jejurikar",
            "R. Alexandra Keith 6": "R. Alexandra Keith",
            "R. Alexandra Keith": "R. Alexandra Keith"}
for n in pg24p:
    nm = NAME_FIX.get(n["name"], n["name"])
    nm = re.sub(r"\s*\d+$", "", nm).strip()
    v = n["nums"]
    if n["year"] == 2023:
        add_rows("PG", [mkrow(nm, n["title"], 2023,
                              v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7])])
    elif n["year"] == 2022:
        add_rows("PG", [mkrow(nm, n["title"], 2022,
                              v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7])])
pg["fiscal_year"] = 2026
pg["proxy_fiscal_year"] = 2026
pg["available_years"] = [2026, 2025, 2024, 2023, 2022]
pg["neo_count"] = 8
pg["total_compensation"] = 18976742
pg["total_neo_compensation"] = sum(e["total"] for e in pg["executives"] if e["year"] == 2026)
# filing_date/url already 2026-08-28 / pg-20260826.htm

# ---------------- PH ----------------
ph = json.load(open(os.path.join(PROX, "PH_raw.json")))
PH_TITLES = {
    "Jennifer A. Parmentier": "Chairman of the Board and Chief Executive Officer",
    "Todd M. Leombruno": "Executive Vice President and Chief Financial Officer",
    "Andrew D. Ross": "President and Chief Operating Officer",
    "Matthew A. Jacobson": "Vice President and President - Filtration Group",
    "Joseph R. Leonti": "Executive Vice President, General Counsel and Secretary",
}
ph_filing = []
for n in ph:
    name = n["name"]
    if name == "Matthew A. Jacobson Vice":
        name = "Matthew A. Jacobson"
    v = n["nums"]
    ph_filing.append((name, n["year"], {
        "salary": v[0], "bonus": 0, "stock_awards": v[1], "option_awards": v[2],
        "non_equity_incentive": v[3], "pension_nqdc": v[4], "all_other": v[5], "total": v[6]}))
phc = companies["PH"]
stored_ph = {(e["name"], e["year"]): e for e in phc["executives"]}
ph_new = []
for name, year, comp in ph_filing:
    key = (name, year)
    if key in stored_ph:
        STATS["checked"] += 1
        s = stored_ph[key]
        for f in fields:
            if s.get(f) != comp[f] and not (s.get(f) is None and comp[f] == 0):
                print("DELTA PH", name, year, f, "stored", s.get(f), "filing", comp[f])
                STATS["deltas"] += 1
    else:
        ph_new.append((name, year, comp))
add_rows("PH", [mkrow(n, PH_TITLES[n], yr,
                      c["salary"], 0, c["stock_awards"], c["option_awards"],
                      c["non_equity_incentive"], c["pension_nqdc"], c["all_other"], c["total"])
                for n, yr, c in ph_new])
# repair the four column-shifted 2024 rows filing-verbatim (keep stored titles)
repair_row("PH", "Jennifer A. Parmentier", 2024,
           salary=1383333, bonus=0, stock_awards=5959762, option_awards=6460290,
           non_equity_incentive=3961507, pension_nqdc=0, all_other=970295, total=18735187)
repair_row("PH", "Todd M. Leombruno", 2024,
           salary=891667, bonus=0, stock_awards=1761895, option_awards=1909274,
           non_equity_incentive=1547577, pension_nqdc=1164044, all_other=465139, total=7739596)
repair_row("PH", "Andrew D. Ross", 2024,
           salary=920000, bonus=0, stock_awards=2022228, option_awards=2191343,
           non_equity_incentive=1836265, pension_nqdc=1941924, all_other=226061, total=9137821)
repair_row("PH", "Joseph R. Leonti", 2024,
           salary=801667, bonus=0, stock_awards=957653, option_awards=1038803,
           non_equity_incentive=1113098, pension_nqdc=0, all_other=407055, total=4318276)
# None -> 0 normalization on 2025 rows (filing shows em-dash = 0)
for e in phc["executives"]:
    if e["year"] == 2025:
        if e.get("bonus") is None:
            e["bonus"] = 0
        if e.get("pension_nqdc") is None:
            e["pension_nqdc"] = 0
phc["filing_date"] = "2026-09-18"
phc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/76334/000130817926000394/ph-20260915.htm"
phc["fiscal_year"] = 2026
phc["proxy_fiscal_year"] = 2026
phc["available_years"] = [2026, 2025, 2024, 2023]
phc["neo_count"] = 5
phc["total_compensation"] = 22761169
phc["total_neo_compensation"] = sum(e["total"] for e in phc["executives"] if e["year"] == 2026)
assert phc["total_neo_compensation"] == 52540309, phc["total_neo_compensation"]

# ---------------- TPR ----------------
tpr = json.load(open(os.path.join(PROX, "TPR_raw.json")))
tprc = companies["TPR"]
stored_tpr = {(e["name"], e["year"]): e for e in tprc["executives"]}
tpr_new = []
for n in tpr:
    v = n["nums"]
    comp = {"salary": v[0], "bonus": 0, "stock_awards": v[2], "option_awards": v[3],
            "non_equity_incentive": v[4], "pension_nqdc": 0, "all_other": v[5], "total": v[6]}
    key = (n["name"], n["year"])
    if key in stored_tpr:
        STATS["checked"] += 1
        s = stored_tpr[key]
        for f in fields:
            if s.get(f) != comp[f] and not (s.get(f) is None and comp[f] == 0):
                print("DELTA TPR", n["name"], n["year"], f, "stored", s.get(f), "filing", comp[f])
                STATS["deltas"] += 1
    else:
        title = n["title"] or "Chief People Officer"
        tpr_new.append((n["name"], title, n["year"], comp))
add_rows("TPR", [mkrow(n, t, yr,
                      c["salary"], 0, c["stock_awards"], c["option_awards"],
                      c["non_equity_incentive"], 0, c["all_other"], c["total"])
                for n, t, yr, c in tpr_new])
tprc["filing_date"] = "2026-09-25"
tprc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/1116132/000111613226000024/tpr-20260924.htm"
tprc["fiscal_year"] = 2026
tprc["proxy_fiscal_year"] = 2026
tprc["available_years"] = [2026, 2025, 2024, 2023]
tprc["neo_count"] = 5
tprc["total_compensation"] = 33986485
tprc["total_neo_compensation"] = sum(e["total"] for e in tprc["executives"] if e["year"] == 2026)
assert tprc["total_neo_compensation"] == 56559249, tprc["total_neo_compensation"]

# ---------------- TPL ----------------
tplc = companies["TPL"]
tplc["filing_date"] = "2026-09-25"
tplc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/1811074/000110465926110963/tm264934-6_def14a.htm"

# ---------------- metadata ----------------
n = sum(len(c["executives"]) for c in data["companies"])
data["metadata"]["description"] = (
    "518 companies, %d NEO records, 517 companies enriched" % n)
data["metadata"]["total_neo_records"] = n
data["metadata"]["total_executives"] = n
data["metadata"]["total_neos"] = n
data["metadata"]["last_updated"] = "2026-10-30"
data["metadata"]["last_dq_repair"] = "2026-10-30"

# data_quality buckets recount from live _total_source labels
cnt = {}
for c in data["companies"]:
    for e in c["executives"]:
        lab = e.get("_total_source")
        cnt[lab] = cnt.get(lab, 0) + 1
verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
for block_key in ("data_quality", "data_quality_detailed"):
    block = data["metadata"][block_key]
    ordered = {}
    for k in sorted(cnt.keys()):
        if k not in ("verified_total", "last_audit"):
            ordered[k] = cnt[k]
    if "rounding" not in ordered:
        ordered["rounding"] = 0
    ordered["verified_total"] = verified_total
    ordered["last_audit"] = block.get("last_audit", "2026-09-28")
    block.clear()
    block.update(ordered)
data["metadata"]["verified_total"] = verified_total

with open(JSON_PATH, "w", encoding="utf-8") as f:
    f.write(json.dumps(data, indent=1, ensure_ascii=False))
    f.write("\n")

print("STATS:", STATS)
print("total NEO records:", n, "| verified_total:", verified_total)