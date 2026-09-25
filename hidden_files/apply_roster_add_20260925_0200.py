#!/usr/bin/env python3
"""Roster-add batch 2026-09-25 02:00 PT (backlog #12): add ILMN (Illumina,
re-added to S&P 500 effective 2026-09-21) and P (Everpure, Inc., formerly
Pure Storage, added to S&P 500 effective 2026-09-21) from latest DEF 14As.
S&P DJI quarterly-rebalance announcement 2026-09-04; membership verified
against the announcement by both extractors.
Extraction evidence: goal hidden_files/sct_fill_20260925_0200/*.json.
Independently verified by parent: all 25 rows foot exactly ($0 gaps);
both CEO anchors pair exactly once; both pay ratios recompute to the
filed values; SoP vote counts from primary 8-K Item 5.07 filings.
Everpure identity: SEC company_tickers.json lists CIK 1474432 / ticker P /
"Everpure, Inc." (same CIK as Pure Storage); rename Pure Storage->Everpure
effective 2026-02-23 per 8-K 0001474432-26-000011 (Item 5.03); ticker
PSTG->P effective 2026-04-17 (company PR, CUSIP unchanged). The 2026-05-01
DEF 14A was already filed as "Everpure, Inc."
ILMN: deSouza (PEO to Jun 2023) -> Dadswell (interim, to Sep 2023) ->
Thaysen (since Sep 2023); per-year PEO tuples in the extraction transitions.
"""
import json, os, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/sct_fill_20260925_0200")
COMP_PATH = os.path.join(REPO, "data/compensation.json")
LABEL = "def14a_verified_20260925"

shutil.copy2(COMP_PATH, os.path.join(REPO, "hidden_files",
             "compensation_backup_20260925_0200_pre_roster12.json"))
print("backup written")

comp = json.load(open(COMP_PATH))
existing = {c["ticker"] for c in comp["companies"]}
for t in ["ILMN", "P"]:
    assert t not in existing, f"{t} already in table"

def cik10(c):
    return str(c).zfill(10)

def filing_url_for(cik, acc):
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

META = {
    "ILMN": dict(ticker="ILMN", name="Illumina, Inc.", sector="Health Care",
                 proxy_year=2026, anchor_year=2025,
                 source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M",
                 sop_votes={"votes_for": 121746792, "votes_against": 8464596,
                            "abstain": 404097, "broker_non_votes": 10428546,
                            "source_url": "https://www.sec.gov/Archives/edgar/data/1110803/000111080326000124/"}),
    "P":    dict(ticker="P", name="Everpure, Inc.", sector="Information Technology",
                 proxy_year=2026, anchor_year=2026,
                 source="SEC DEF 14A 2026 \u2014 FY2026 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M",
                 sop_votes={"votes_for": 232565874, "votes_against": 24698847,
                            "abstain": 4931257, "broker_non_votes": 42723676,
                            "source_url": "https://www.sec.gov/Archives/edgar/data/1474432/000147443226000066/"}),
}

new_companies = []
row_total_new = 0
for xt, m in META.items():
    d = json.load(open(os.path.join(BATCH, f"{xt}_extraction.json")))
    t = m["ticker"]
    rows = d["rows"]
    dropped = [r for r in rows if r["total"] is None]
    assert not dropped, f"{t}: unexpected null-total rows"
    ay = m["anchor_year"]
    anchor = d["ceo_anchor"]
    anchor_rows = [r for r in rows if r["name"] == anchor["name"] and r["year"] == anchor["year"]]
    assert len(anchor_rows) == 1, f"{t} anchor not unique"
    assert anchor_rows[0]["total"] == anchor["total"], f"{t} anchor mismatch"
    arows = [r for r in rows if r["year"] == ay]
    neo_names = sorted({r["name"] for r in rows})
    acc = d.get("accession")
    furl = filing_url_for(d["cik"], acc)

    executives = []
    for r in rows:
        erow = {"name": r["name"], "title": r["title"], "year": r["year"]}
        for k in COMPS:
            if r.get(k) is not None:
                erow[k] = r[k]
        erow["total"] = r["total"]
        erow["_total_source"] = LABEL
        erow["_accession"] = acc
        erow["_filing_url"] = furl
        bits = [f"FY{ay} {m['source'].split(' \u2014 ')[0]} SCT, {r['name']} {r['year']} row."]
        s = sum((r.get(k) or 0) for k in COMPS)
        delta = r["total"] - s
        bits.append(f"Components foot {'exactly' if delta == 0 else f'with ${delta:+,} filing-side gap (verbatim)'}")
        if r.get("filing_gap_note"):
            bits.append("Filing note: " + r["filing_gap_note"])
        erow["_note"] = " ".join(bits)
        executives.append(erow)

    sop = d.get("say_on_pay") or {}
    say_on_pay = None
    if sop.get("pct") is not None:
        say_on_pay = {"approval_pct": sop["pct"], "filing_date": sop.get("filing_date"),
                      "source_url": furl}
        say_on_pay.update(m["sop_votes"])

    crec = {
        "company_name": m["name"], "ticker": t, "cik": cik10(d["cik"]),
        "sector": m["sector"], "filing_date": d["filing_date"], "filing_url": furl,
        "proxy_fiscal_year": m["proxy_year"], "fiscal_year": ay,
        "available_years": sorted({r["year"] for r in rows}, reverse=True),
        "ceo_name": anchor["name"], "total_compensation": anchor["total"],
        "source": m["source"],
        "ceo_gender": m["gender"],
        "say_on_pay": say_on_pay,
        "data_source": m["data_source"],
        "neo_count": len(neo_names),
        "total_neo_compensation": sum(r["total"] for r in arows),
        "executives": executives,
    }
    if d.get("median_worker_pay") is not None:
        crec["median_worker_pay"] = d["median_worker_pay"]
    if d.get("pay_ratio") is not None:
        crec["pay_ratio"] = d["pay_ratio"]
    new_companies.append(crec)
    row_total_new += len(rows)
    print(f"{t}: {len(rows)} rows, {len(neo_names)} NEOs, CEO {anchor['name']} FY{ay} ${anchor['total']:,}, "
          f"ratio {d.get('pay_ratio')}, SoP {sop.get('pct')}, peers {len(d['peer_group'])}")

comp["companies"].extend(new_companies)

# --- metadata sync ---
md = comp["metadata"]
n_new = len(new_companies)
md["total_companies"] = 512 + n_new
md["total_neo_records"] = 7005 + row_total_new
md["total_executives"] = md["total_neo_records"]
md["enriched_count"] = 512 + n_new
md["edgar_coverage"] = 512 + n_new
md["companies_with_executives"] = 512 + n_new
md["title_coverage"] = f"{md['total_neo_records']}/{md['total_neo_records']}"
# both new companies disclose pay ratio and say-on-pay
md["companies_with_pay_ratio"] = 510 + n_new
md["say_on_pay_coverage"] = 510 + n_new
dq = md["data_quality"]
dqd = md["data_quality_detailed"]
dq[LABEL] = dq.get(LABEL, 0) + row_total_new
dqd[LABEL] = dqd.get(LABEL, 0) + row_total_new
VERIFIED_FAMILY = {"verified"} | {k for k in dq if k.startswith("def14a_verified_")}
md["verified_total"] = sum(dq.get(k, 0) for k in VERIFIED_FAMILY)
dq["verified_total"] = md["verified_total"]
md["description"] = f"{md['total_companies']} companies, {md['total_neo_records']} NEO records, {md['total_companies']} companies enriched"
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
md["median_ceo_pay"] = agg["median_ceo_pay"]
md["mean_ceo_pay"] = agg["mean_ceo_pay"]
md["median_pay_ratio"] = agg["median_pay_ratio"]
md["median_worker_pay"] = agg["median_worker_pay"]
md["min_ceo_pay"] = agg["min_ceo_pay"]
md["max_ceo_pay"] = agg["max_ceo_pay"]
md["last_updated"] = "2026-09-25"
md["last_dq_repair"] = "2026-09-25"
print("metadata:", md["total_companies"], "companies,", md["total_neo_records"], "rows,",
      "verified_total", md["verified_total"], LABEL, dq[LABEL])

json.dump(comp, open(COMP_PATH, "w"), indent=1)
print("wrote", COMP_PATH)
