#!/usr/bin/env python3
"""Fix for roster-add batch 2026-09-24 23:30 PT: BK and MMC already existed in
the table (their FY2023-2025 SCT rows are numerically identical to the fresh
extraction, 0 field mismatches), so the BNY/MRSH records added as new
companies are duplicates. Correct treatment: in-place ticker-change +
FY2025 anchor refresh of the existing BK/MMC records, with row replacement
(the old rows carry corrupted titles, e.g. MMC's Doyle as 'Chief Executive
Officer of McKesson Specialty/US Oncology', and lack _accession/_filing_url).
Deletes the duplicate BNY/MRSH companies and recomputes metadata from scratch.
"""
import json, os, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP_PATH = os.path.join(REPO, "data/compensation.json")
BATCH = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/sct_fill_20260924_2330")
LABEL = "def14a_verified_20260924"
COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

comp = json.load(open(COMP_PATH))

def build_rows(xt):
    d = json.load(open(os.path.join(BATCH, f"{xt}_extraction.json")))
    acc = d.get("accession")
    furl = (f"https://www.sec.gov/Archives/edgar/data/{int(d['cik'])}/"
            f"{acc.replace('-', '')}/")
    rows = []
    for r in d["rows"]:
        erow = {"name": r["name"], "title": r["title"], "year": r["year"]}
        for k in COMPS:
            if r.get(k) is not None:
                erow[k] = r[k]
        erow["total"] = r["total"]
        erow["_total_source"] = LABEL
        erow["_accession"] = acc
        erow["_filing_url"] = furl
        s = sum((r.get(k) or 0) for k in COMPS)
        delta = r["total"] - s
        bits = [f"FY{r['year']} DEF 14A SCT, {r['name']} row.",
                f"Components foot {'exactly' if delta == 0 else f'with ${delta:+,} filing-side gap (verbatim)'}."]
        if r.get("filing_gap_note"):
            bits.append("Filing note: " + r["filing_gap_note"])
        erow["_note"] = " ".join(bits)
        rows.append(erow)
    return d, rows

# --- 1. drop the duplicate companies ---
before = len(comp["companies"])
comp["companies"] = [c for c in comp["companies"]
                     if c["ticker"] not in ("BNY", "MRSH")]
print(f"dropped duplicates: {before} -> {len(comp['companies'])} companies")

REFRESH = {
    "BK": dict(ticker="BNY", name="The Bank of New York Mellon Corporation",
               proxy_year=2026, ay=2025,
               source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
               ratio=1018, median=81987,
               say_on_pay={"approval_pct": 55.56, "filing_date": "2026-04-17",
                           "votes_for": 317099734, "votes_against": 253650298,
                           "abstain": 1796676, "broker_non_votes": 50748197,
                           "source_url": "https://www.sec.gov/Archives/edgar/data/1390777/000119312526161599/"}),
    "MMC": dict(ticker="MRSH", name="Marsh & McLennan Companies, Inc.",
                proxy_year=2026, ay=2025,
                source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
                ratio=330, median=76092,
                say_on_pay={"approval_pct": 88.05, "filing_date": "2026-05-22",
                            "source_url": None}),  # set below
}

for old_t, m in REFRESH.items():
    c = [x for x in comp["companies"] if x["ticker"] == old_t][0]
    d, rows = build_rows(old_t)
    ay = m["ay"]
    anchor = d["ceo_anchor"]
    acc = d.get("accession")
    furl = (f"https://www.sec.gov/Archives/edgar/data/{int(d['cik'])}/"
            f"{acc.replace('-', '')}/")
    arows = [r for r in rows if r["year"] == ay]
    c["ticker"] = m["ticker"]
    c["company_name"] = m["name"]
    c["executives"] = rows
    c["fiscal_year"] = ay
    c["proxy_fiscal_year"] = m["proxy_year"]
    c["available_years"] = sorted({r["year"] for r in rows}, reverse=True)
    c["ceo_name"] = anchor["name"]
    c["total_compensation"] = anchor["total"]
    c["source"] = m["source"]
    c["data_source"] = "SEC EDGAR DEF 14A"
    c["filing_date"] = d["filing_date"]
    c["filing_url"] = furl
    c["pay_ratio"] = m["ratio"]
    c["median_worker_pay"] = m["median"]
    sop = dict(m["say_on_pay"])
    if sop.get("source_url") is None:
        sop["source_url"] = furl
    c["say_on_pay"] = sop
    c["neo_count"] = len({r["name"] for r in rows})
    c["total_neo_compensation"] = sum(r["total"] for r in arows)
    print(f"{old_t}->{m['ticker']}: {len(rows)} rows replaced, FY{ay} anchor "
          f"{anchor['name']} ${anchor['total']:,}, ratio {m['ratio']}, "
          f"SoP {sop['approval_pct']}%")

# --- 2. recompute metadata from scratch ---
md = comp["metadata"]
n_cos = len(comp["companies"])
n_rows = sum(len(c["executives"]) for c in comp["companies"])
dq = collections.Counter()
for c in comp["companies"]:
    for e in c["executives"]:
        dq[e["_total_source"]] += 1
VERIFIED_FAMILY = {"verified"} | {k for k in dq if k.startswith("def14a_verified_")}
md["total_companies"] = n_cos
md["total_neo_records"] = n_rows
md["total_executives"] = n_rows
md["enriched_count"] = n_cos
md["edgar_coverage"] = n_cos
md["companies_with_executives"] = n_cos
md["title_coverage"] = f"{n_rows}/{n_rows}"
md["companies_with_pay_ratio"] = sum(1 for c in comp["companies"] if c.get("pay_ratio"))
md["say_on_pay_coverage"] = sum(1 for c in comp["companies"] if c.get("say_on_pay"))
md["data_quality"] = dict(dq)
md["data_quality_detailed"] = dict(dq)
md["verified_total"] = sum(dq.get(k, 0) for k in VERIFIED_FAMILY)
md["description"] = f"{n_cos} companies, {n_rows} NEO records, {n_cos} companies enriched"
ceo_totals = sorted(c["total_compensation"] for c in comp["companies"])
ratios = sorted(c["pay_ratio"] for c in comp["companies"] if c.get("pay_ratio"))
meds = sorted(c["median_worker_pay"] for c in comp["companies"] if c.get("median_worker_pay"))
def median(xs):
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
agg = md.get("aggregate_stats", {})
agg["median_ceo_pay"] = median(ceo_totals)
agg["mean_ceo_pay"] = sum(ceo_totals) / len(ceo_totals)
agg["median_pay_ratio"] = median(ratios)
agg["median_worker_pay"] = median(meds)
agg["min_ceo_pay"] = min(ceo_totals)
agg["max_ceo_pay"] = max(ceo_totals)
md["aggregate_stats"] = agg
for k in ("median_ceo_pay", "mean_ceo_pay", "median_pay_ratio",
          "median_worker_pay", "min_ceo_pay", "max_ceo_pay"):
    md[k] = agg[k]
md["last_updated"] = "2026-09-24"
md["last_dq_repair"] = "2026-09-24"
print("metadata:", n_cos, "companies,", n_rows, "rows, verified_total",
      md["verified_total"], "pay_ratio cos", md["companies_with_pay_ratio"],
      "sop cos", md["say_on_pay_coverage"])
print("dq buckets:", {k: dq[k] for k in sorted(dq) if 'def14a' in k or k in ('verified','component_mismatch')})

json.dump(comp, open(COMP_PATH, "w"), indent=1)
print("wrote", COMP_PATH)
