#!/usr/bin/env python3
"""2026-11-24 21:00 PT MU FY2026 enrichment (582nd review).

Watch hit: the daily FY2026-proxy watch (scripts/watch_fy2026.py, re-run
2026-11-24 ~21:00 PT) found Micron's new DEF 14A filed 2026-11-24
(acc 0000723125-26-000034) -- the first Dec-2026-wave proxy. Source filing:
https://www.sec.gov/Archives/edgar/data/723125/000072312526000034/mu-20261124.htm
SCT table 78, "Fiscal 2026 Summary Compensation Table".

Findings:
- FY2026 SCT covers 5 NEOs x FY2026/2025/2024. All 10 overlap rows
  (2025+2024) cross-checked filing-verbatim against stored, 0 deltas.
- +5 FY2026 rows: Mehrotra 39,723,944; Murphy 13,506,363;
  Bhatia 14,653,666; DeBoer 12,365,624; Sadana 14,816,418.
  FY2026 NEO sum 95,066,015. PvP cross-check: PEO FY2026 SCT total
  39,723,944 and non-PEO average 13,835,518 both match the new proxy's
  Item 402(v) table exactly ((13,506,363+14,653,666+12,365,624+14,816,418)/4
  = 13,835,517.75 -> 13,835,518).
- DQ repair (same batch): the stored "Sumit Sadana 2023" row
  (salary 1,255,476 / stock 23,750,005 / total 25,276,953) is a
  misattribution. The stored FY2025 proxy SCT (mu-20251125.htm, table 85)
  shows those exact numbers on Mehrotra's 2023 row, and Sadana's real
  2023 row is salary 715,007 / stock 8,500,024 / all other 16,500 /
  total 9,231,531. The stored data had NO Mehrotra-2023 row at all.
  Fix: rename the row to Mehrotra 2023 (title per the FY2025 proxy),
  add Sadana 2023 filing-verbatim.
- Gap-fill from the same FY2025 proxy SCT: Mark Murphy 2023 was missing
  (salary 639,827 / stock 7,749,991 / all other 14,284 / total 8,404,102).
  Bhatia 2023 and DeBoer 2023 stored rows verified filing-verbatim.
- Company-level: fiscal_year 2025->2026, CEO total 30,940,146->39,723,944,
  median worker pay 64,042->105,482, pay ratio 469->377 (both from the
  new proxy's Item 402(u) disclosure), filing 2025-11-25->2026-11-24.
- Say-on-pay (95.1%, Jan 2026 meeting) and board independence (8/7)
  unchanged: the next vote is the Jan 2027 meeting, and the FY2026 proxy
  still seats 8 directors, 7 independent.
- PvP panel NOT updated in this batch: MU's Item 402(v) row is a wave-39
  task (same as MSFT, whose FY2026 SCT landed without a PvP update).

Totals: +7 rows (5x FY2026, Sadana 2023, Murphy 2023), +$112,701,648
restored filing-verbatim; 1 total-neutral rename (Sadana->Mehrotra 2023).
"""
import json
import os
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20261124_2100_pre_fy2026mu.json")

shutil.copy2(JSON_PATH, BACKUP)

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

companies = {c["ticker"]: c for c in data["companies"]}
mu = companies["MU"]

STATS = {"new": 0, "repaired": 0, "checked": 0, "deltas": 0}

FIELDS = ["salary", "bonus", "stock_awards", "option_awards",
          "non_equity_incentive", "pension_nqdc", "all_other", "total"]


def mkrow(name, title, year, salary, bonus, stock, option, neip, pension,
          all_other, total):
    assert salary + bonus + stock + option + neip + pension + all_other == total, \
        (name, year, salary, bonus, stock, option, neip, pension, all_other, total)
    return {"name": name, "title": title, "year": year, "salary": salary,
            "bonus": bonus, "stock_awards": stock, "option_awards": option,
            "non_equity_incentive": neip, "pension_nqdc": pension,
            "all_other": all_other, "total": total, "_total_source": "verified"}


def crosscheck(ticker, filing_rows):
    """filing_rows: list of (name, year, comp-dict). Returns new-row specs."""
    c = companies[ticker]
    stored = {(e["name"], e["year"]): e for e in c["executives"]}
    new = []
    for name, year, comp in filing_rows:
        key = (name, year)
        if key in stored:
            STATS["checked"] += 1
            s = stored[key]
            for f in FIELDS:
                sv = s.get(f)
                if sv != comp[f] and not (sv is None and comp[f] == 0):
                    print("DELTA", ticker, name, year, f, "stored", sv,
                          "filing", comp[f])
                    STATS["deltas"] += 1
        else:
            new.append((name, year, comp))
    return new


def comp(salary, stock, neip, all_other, total):
    return {"salary": salary, "bonus": 0, "stock_awards": stock,
            "option_awards": 0, "non_equity_incentive": neip,
            "pension_nqdc": 0, "all_other": all_other, "total": total}


# ---- FY2026 proxy SCT (mu-20261124.htm table 78) ----
TITLES_2026 = {
    "Sanjay Mehrotra": "Chairman and Chief Executive Officer",
    "Mark Murphy": "Executive Vice President and Chief Financial Officer",
    "Manish Bhatia": "President and Chief Operating Officer",
    "Scott DeBoer": "President and Chief Technology and Products Officer",
    "Sumit Sadana": "Former Executive Vice President and Chief Business Officer",
}
F2026 = [
    ("Sanjay Mehrotra", 2026, comp(1477885, 30000144, 6380000, 1865915, 39723944)),
    ("Sanjay Mehrotra", 2025, comp(1446185, 25360029, 3894990, 238942, 30940146)),
    ("Sanjay Mehrotra", 2024, comp(1416909, 23749623, 4847433, 46161, 30060126)),
    ("Mark Murphy", 2026, comp(873476, 9999857, 2328953, 304077, 13506363)),
    ("Mark Murphy", 2025, comp(815956, 9000040, 1185425, 115284, 11116705)),
    ("Mark Murphy", 2024, comp(765654, 8499848, 1540313, 26188, 10832003)),
    ("Manish Bhatia", 2026, comp(901652, 11000018, 2493120, 258876, 14653666)),
    ("Manish Bhatia", 2025, comp(842277, 9499906, 1397801, 21932, 11761916)),
    ("Manish Bhatia", 2024, comp(791203, 8999852, 1590000, 17250, 11398305)),
    ("Scott DeBoer", 2026, comp(810490, 9249964, 2083536, 221634, 12365624)),
    ("Scott DeBoer", 2025, comp(749323, 8249981, 1199999, 25312, 10224615)),
    ("Scott DeBoer", 2024, comp(690668, 7249849, 1335600, 18450, 9294567)),
    ("Sumit Sadana", 2026, comp(921057, 11000018, 2546776, 348567, 14816418)),
    ("Sumit Sadana", 2025, comp(861332, 9499906, 1427883, 25101, 11814222)),
    ("Sumit Sadana", 2024, comp(819452, 8999852, 1803656, 17250, 11640210)),
]
new26 = crosscheck("MU", F2026)
assert STATS["deltas"] == 0, STATS
assert len(new26) == 5, new26  # exactly the FY2026 rows are new
for name, year, c in new26:
    assert year == 2026
    mu["executives"].append(mkrow(name, TITLES_2026[name], year,
                                  c["salary"], 0, c["stock_awards"], 0,
                                  c["non_equity_incentive"], 0,
                                  c["all_other"], c["total"]))
    STATS["new"] += 1

# ---- FY2025 proxy SCT (mu-20251125.htm table 85): 2023 rows ----
# Mehrotra 2023 is stored under Sadana's name; Murphy 2023 is missing;
# Sadana's real 2023 row is missing; Bhatia/DeBoer 2023 stored verbatim.
stored = {(e["name"], e["year"]): e for e in mu["executives"]}
sad23 = stored[("Sumit Sadana", 2023)]
assert (sad23["salary"], sad23["stock_awards"], sad23["all_other"],
        sad23["total"]) == (1255476, 23750005, 271472, 25276953), sad23
sad23["name"] = "Sanjay Mehrotra"
sad23["title"] = "Chairman, President and Chief Executive Officer"
STATS["repaired"] += 1
# verify the other two stored 2023 rows against the FY2025 proxy SCT
for name, year, c in [
        ("Manish Bhatia", 2023, comp(667020, 8250009, 0, 17118, 8934147)),
        ("Scott DeBoer", 2023, comp(571046, 6500022, 0, 18352, 7089420))]:
    s = stored[(name, year)]
    for f in FIELDS:
        assert s.get(f) == c[f] or (s.get(f) is None and c[f] == 0), \
            ("DELTA", name, year, f, s.get(f), c[f])
    STATS["checked"] += 1
have = {(e["name"], e["year"]) for e in mu["executives"]}
for name, title, year, c in [
        ("Sumit Sadana", "Executive Vice President and Chief Business Officer",
         2023, comp(715007, 8500024, 0, 16500, 9231531)),
        ("Mark Murphy", "Executive Vice President and Chief Financial Officer",
         2023, comp(639827, 7749991, 0, 14284, 8404102))]:
    assert (name, year) not in have, ("dup", name, year)
    mu["executives"].append(mkrow(name, title, year, c["salary"], 0,
                                  c["stock_awards"], 0,
                                  c["non_equity_incentive"], 0,
                                  c["all_other"], c["total"]))
    STATS["new"] += 1

# ---- company-level ----
mu["fiscal_year"] = 2026
mu["proxy_fiscal_year"] = 2026
mu["total_compensation"] = 39723944
mu["median_worker_pay"] = 105482
mu["pay_ratio"] = 377
mu["filing_date"] = "2026-11-24"
mu["filing_url"] = ("https://www.sec.gov/Archives/edgar/data/723125/"
                    "000072312526000034/mu-20261124.htm")
mu["source"] = "SEC DEF 14A 2026 \u2014 FY2026 CEO"
mu["available_years"] = [2026, 2025, 2024, 2023]
mu["neo_count"] = 5
mu["total_neo_compensation"] = sum(e["total"] for e in mu["executives"]
                                   if e["year"] == 2026)
assert mu["total_neo_compensation"] == 95066015, mu["total_neo_compensation"]
assert len(mu["executives"]) == 20, len(mu["executives"])

# ---- metadata (same semantics as scripts/check_metadata_consistency.py) ----
n = sum(len(c["executives"]) for c in data["companies"])
meta = data["metadata"]
meta["description"] = ("518 companies, %d NEO records, 517 companies enriched" % n)
meta["total_neo_records"] = n
meta["total_executives"] = n
meta["total_neos"] = n
meta["last_updated"] = "2026-11-24"
meta["last_dq_repair"] = "2026-11-24"
data["last_updated"] = "2026-11-24"
# all 7 new rows carry titles, so title gaps stay 0
meta["title_coverage"] = "%d/%d" % (n, n)

cnt = {}
for c in data["companies"]:
    for e in c["executives"]:
        lab = e.get("_total_source")
        cnt[lab] = cnt.get(lab, 0) + 1
verified_total = sum(v for k, v in cnt.items()
                     if k == "verified" or str(k).startswith("def14a_verified_"))
for block_key in ("data_quality", "data_quality_detailed"):
    block = meta[block_key]
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
meta["verified_total"] = verified_total

# aggregate_stats + sector_medians, guard section 17 semantics
comp_list = data["companies"]
ceo_pays = [c["total_compensation"] for c in comp_list
            if c.get("total_compensation", 0) > 0]
worker_pays = [c["median_worker_pay"] for c in comp_list
               if c.get("median_worker_pay") and c["median_worker_pay"] > 0]
ratios = [c["pay_ratio"] for c in comp_list
          if c.get("pay_ratio") is not None and c["pay_ratio"] > 0]
meta["aggregate_stats"] = {
    "total_companies": len(comp_list),
    "companies_with_pay_ratio": len(ratios),
    "median_ceo_pay": int(statistics.median(ceo_pays)),
    "mean_ceo_pay": int(statistics.mean(ceo_pays)),
    "max_ceo_pay": max(ceo_pays),
    "min_ceo_pay": min(ceo_pays),
    "median_worker_pay": int(statistics.median(worker_pays)) if worker_pays else 0,
    "median_pay_ratio": int(statistics.median(ratios)) if ratios else 0,
}


def _anchor_row_for(c):
    ceo, fy, tot = c.get("ceo_name", ""), c.get("fiscal_year"), c.get("total_compensation", 0)
    if not tot:
        return None
    rows = [e for e in c.get("executives", [])
            if e.get("name") == ceo and e.get("year") == fy]
    if not rows:
        rows = [e for e in c.get("executives", []) if e.get("total") == tot]
    return rows[0] if rows else None


def _is_verified_source(src):
    return bool(src) and (src.startswith("verified")
                          or src.startswith("def14a_verified"))


sector_pays = {}
for c in comp_list:
    if c.get("total_compensation", 0) > 0:
        sector_pays.setdefault(c.get("sector", "Unknown"), []).append(
            c["total_compensation"])
sector_cov = {}
for c in comp_list:
    a = _anchor_row_for(c)
    if a is None:
        continue
    s = c.get("sector", "Unknown")
    r = sector_cov.setdefault(s, {"ver": 0, "doc": 0, "undoc": 0})
    src = a.get("_total_source") or ""
    if _is_verified_source(src):
        r["ver"] += 1
    elif a.get("_note"):
        r["doc"] += 1
    else:
        r["undoc"] += 1
sm = {}
for s, p in sector_pays.items():
    cov = sector_cov.get(s, {"ver": 0, "doc": 0, "undoc": 0})
    sm[s] = {
        "median_ceo_pay": int(statistics.median(p)),
        "count": len(p),
        "min": min(p),
        "max": max(p),
        "verified_anchors": cov["ver"],
        "documented_anchors": cov["doc"],
        "undocumented_anchors": cov["undoc"],
        "verified_pct": round(100.0 * cov["ver"] / len(p), 1),
    }
meta["sector_medians"] = sm

with open(JSON_PATH, "w", encoding="utf-8") as f:
    f.write(json.dumps(data, indent=1, ensure_ascii=False))
    f.write("\n")

print("STATS:", STATS)
print("total NEO records:", n, "| verified_total:", verified_total)
print("aggregate_stats:", json.dumps(meta["aggregate_stats"]))
print("IT sector:", json.dumps(sm["Information Technology"]))

# ---- phantom campaign counter (guard check_phantom_delta_sync S3) ----
sys.path.insert(0, os.path.join(REPO, "hidden_files"))
import phantom_record
delta = phantom_record.record_batch(
    pre_path=BACKUP,
    data_path=JSON_PATH,
    stamp="2026-11-24 21:00 PT",
)
print("phantom delta: $%s" % f"{delta:,}")
with open(JSON_PATH, encoding="utf-8") as f:
    post = json.load(f)
print("phantom block:", json.dumps(post["metadata"]["phantom_removed"]))
