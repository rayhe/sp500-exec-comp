#!/usr/bin/env python3
"""2026-11-26 01:00 PT INTU FY2026 enrichment (595th review).

Watch hit: the daily FY2026-proxy watch (scripts/watch_fy2026.py, re-run
2026-11-26 ~01:00 PT) confirms Intuit's new DEF 14A filed 2026-11-25
(acc 0000896878-26-000053) -- the second Dec-2026-wave proxy (MU landed
2026-11-24). Source filing:
https://www.sec.gov/Archives/edgar/data/896878/000089687826000053/intu-20261125.htm
SCT: "Fiscal Year 2026 Summary Compensation Table" (7-column form: no
Bonus, no Change in Pension/NQDC column -- all totals foot exactly with
bonus=0, pension=0, same as stored INTU rows).

Findings:
- FY2026 SCT covers 5 NEOs; only Goodarzi + Aujla carry 2025/2024 rows
  (new NEOs Hanebrink/Hilliard/Hotz show FY2026 only). All 4 overlap rows
  cross-checked filing-verbatim against stored, 0 deltas.
- +5 FY2026 rows: Goodarzi 36,784,881; Aujla 20,181,640;
  Hanebrink 11,191,522; Hilliard 9,966,015; Hotz 11,304,833.
  FY2026 NEO sum 89,428,891. PvP cross-check: PEO FY2026 SCT total
  36,784,881 and non-PEO average 13,161,003 both match the new proxy's
  Item 402(v) table exactly ((20,181,640+11,191,522+9,966,015+11,304,833)/4
  = 13,161,002.5 -> 13,161,003). The PvP table also independently confirms
  the stored FY2025 non-CEO average (16,179,358) and CEO total (36,845,552).
- Footnotes benign: (4) NQDCP deferrals already inside the SCT columns,
  (5)/(6)/(7) 401(k) matches + wellness awards inside All Other,
  (8) MSPP deferrals (Hilliard $91,125, Hotz $69,199) inside NEIP.
- Company-level: fiscal_year 2025->2026, CEO total 36,845,552->36,784,881,
  median worker pay 200,562->232,335, pay ratio 182->158 (both from the
  new proxy's Item 402(u) disclosure), filing 2025-11-26->2026-11-25.
  Goodarzi FY2026 title "Chairman and Chief Executive Officer" (Chairman
  since 2026; stored 2025/2024/2023 rows keep "President and CEO").
- Board: 12 nominees (was 10), 11 independent (91.7%), Goodarzi now holds
  Board Chair + CEO (chair_independent true->false), Vasant Prabhu is Lead
  Independent Director (lead false->true). Say-on-pay unchanged (93.15%,
  Jan 2026 meeting): the next vote is the Jan 20, 2027 meeting.
- PvP panel NOT updated in this batch: INTU's Item 402(v) row is a wave-39
  task (same as MU, whose FY2026 SCT landed without a PvP update).
- Known coverage note (queued candidate, NOT fixed here): the FY2026 SCT
  does not list former NEOs, so Laura A. Fennell 2024 (~$15,783,652,
  derived from the PvP non-CEO average 16,178,844 x 4 minus the three
  stored 2024 non-CEO totals) and the 2023 rows for Fennell/Clatterbuck/
  Chriss live only in older proxies (FY2024/FY2023 DEF 14As). A historical
  backfill would need those filings; the dataset convention is latest-proxy
  SCT coverage, so this stays a queued candidate.

Totals: +5 rows (all FY2026), +$89,428,891 restored filing-verbatim.
"""
import json
import os
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(HERE, "compensation_backup_20261126_0100_pre_fy2026intu.json")

shutil.copy2(JSON_PATH, BACKUP)

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

companies = {c["ticker"]: c for c in data["companies"]}
intu = companies["INTU"]

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


def comp(salary, stock, option, neip, all_other, total):
    return {"salary": salary, "bonus": 0, "stock_awards": stock,
            "option_awards": option, "non_equity_incentive": neip,
            "pension_nqdc": 0, "all_other": all_other, "total": total}


# ---- FY2026 proxy SCT (intu-20261125.htm) ----
TITLES_2026 = {
    "Sasan K. Goodarzi": "Chairman and Chief Executive Officer",
    "Sandeep S. Aujla": "Executive Vice President and Chief Financial Officer",
    "Anton Hanebrink": "Executive Vice President and Chief Corporate Strategy & Development Officer",
    "Caryl Hilliard": "Executive Vice President and Chief People & Places Officer",
    "Lauren Hotz": "Senior Vice President and Chief Accounting Officer",
}
F2026 = [
    ("Sasan K. Goodarzi", 2026, comp(1400000, 24202293, 8650088, 2520000, 12500, 36784881)),
    ("Sasan K. Goodarzi", 2025, comp(1300000, 24285384, 8650168, 2600000, 10000, 36845552)),
    ("Sasan K. Goodarzi", 2024, comp(1200000, 24247389, 8650027, 2280000, 194944, 36572360)),
    ("Sandeep S. Aujla", 2026, comp(800000, 18503840, 0, 864000, 13800, 20181640)),
    ("Sandeep S. Aujla", 2025, comp(800000, 11007870, 3625099, 960000, 11300, 16404269)),
    ("Sandeep S. Aujla", 2024, comp(770000, 10560586, 3500057, 877800, 11300, 15719743)),
    ("Anton Hanebrink", 2026, comp(725000, 9798922, 0, 652500, 15100, 11191522)),
    ("Caryl Hilliard", 2026, comp(675000, 8669715, 0, 607500, 13800, 9966015)),
    ("Lauren Hotz", 2026, comp(567788, 10263217, 0, 461328, 12500, 11304833)),
]
new26 = crosscheck("INTU", F2026)
assert STATS["deltas"] == 0, STATS
assert STATS["checked"] == 4, STATS
assert len(new26) == 5, new26  # exactly the FY2026 rows are new
for name, year, c in new26:
    assert year == 2026
    intu["executives"].append(mkrow(name, TITLES_2026[name], year,
                                    c["salary"], 0, c["stock_awards"],
                                    c["option_awards"],
                                    c["non_equity_incentive"], 0,
                                    c["all_other"], c["total"]))
    STATS["new"] += 1

# ---- company-level ----
intu["fiscal_year"] = 2026
intu["proxy_fiscal_year"] = 2026
intu["total_compensation"] = 36784881
intu["median_worker_pay"] = 232335
intu["pay_ratio"] = 158
intu["filing_date"] = "2026-11-25"
intu["filing_url"] = ("https://www.sec.gov/Archives/edgar/data/896878/"
                      "000089687826000053/intu-20261125.htm")
intu["source"] = "SEC DEF 14A 2026 \u2014 FY2026 CEO"
intu["available_years"] = [2026, 2025, 2024, 2023]
intu["neo_count"] = 5
intu["total_neo_compensation"] = sum(e["total"] for e in intu["executives"]
                                     if e["year"] == 2026)
assert intu["total_neo_compensation"] == 89428891, intu["total_neo_compensation"]
assert len(intu["executives"]) == 16, len(intu["executives"])
# say-on-pay unchanged: next vote is the Jan 20, 2027 meeting.
# board: 12 nominees, 11 independent; Goodarzi Chair+CEO, Prabhu Lead ID.
intu["board_independence"] = {
    "total_directors": 12,
    "independent_directors": 11,
    "independence_pct": 91.7,
    "chair_independent": False,
    "lead_independent_director": True,
    "source": ("DEF 14A 2026-11-25, 11 of 12 independent; Goodarzi Chair+CEO "
               "since 2026, Prabhu Lead Independent Director"),
    "source_url": intu["filing_url"],
}

# ---- metadata (same semantics as scripts/check_metadata_consistency.py) ----
n = sum(len(c["executives"]) for c in data["companies"])
meta = data["metadata"]
meta["description"] = ("518 companies, %d NEO records, 517 companies enriched" % n)
meta["total_neo_records"] = n
meta["total_executives"] = n
meta["total_neos"] = n
meta["last_updated"] = "2026-11-25"
meta["last_dq_repair"] = "2026-11-25"
data["last_updated"] = "2026-11-25"
# all 5 new rows carry titles, so title gaps stay 0
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
    stamp="2026-11-26 01:00 PT",
)
print("phantom delta: $%s" % f"{delta:,}")
with open(JSON_PATH, encoding="utf-8") as f:
    post = json.load(f)
print("phantom block:", json.dumps(post["metadata"]["phantom_removed"]))
