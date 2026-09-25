#!/usr/bin/env python3
"""Roster-add batch 2026-09-24 23:30 PT (backlog #11): enrich BK->BNY, VRT, LITE,
MMC->MRSH, BE, FOXA, COHR, FDXF from latest DEF 14As (FDXF: 10-K Part III).
Extraction evidence: goal hidden_files/sct_fill_20260924_2330/*.json.
Independently verified by parent: all 97 rows foot within $1 (every delta has a
filing_gap_note); 7/8 CEO anchors pair exactly once (LITE normalized
'Michael E. Hurlston'->'Michael Hurlston'); all disclosed pay ratios recompute
within 0.3%; FDXF confirmed real via S&P DJI PR (spin-off completed 2026-06-01,
added to S&P 500 2026-06-02 replacing EPAM); MMC->MRSH ticker change confirmed
via company announcement (effective 2026-01-14); BNY ticker confirmed via SEC
company_tickers.json (both BK and BNY list CIK 1390777; current trading: BNY).
"""
import json, re, shutil, os, collections, gzip

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/sct_fill_20260924_2330")
COMP_PATH = os.path.join(REPO, "data/compensation.json")
NET_PATH = os.path.join(REPO, "data/peer-network.json")
LABEL = "def14a_verified_20260924"

# --- backups ---
for src, tag in ((COMP_PATH, "compensation"), (NET_PATH, "peer-network")):
    dst = os.path.join(REPO, "hidden_files", f"{tag}_backup_20260924_2330_pre_roster11.json")
    shutil.copy2(src, dst)
    print("backup:", dst)

comp = json.load(open(COMP_PATH))
net = json.load(open(NET_PATH))
existing = {c["ticker"] for c in comp["companies"]}
for t in ["BNY", "VRT", "LITE", "MRSH", "BE", "FOXA", "COHR", "FDXF"]:
    assert t not in existing, f"{t} already in table"

def cik10(c):
    return str(c).zfill(10)

def archives_dir(cik, acc):
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/"

# filing_url per company: Archives directory of the filing (always a real EDGAR page)
def filing_url_for(cik, acc):
    if acc:
        return archives_dir(cik, acc)
    # LITE: accession not captured; use the EDGAR company filing index
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik10(cik)}&type=DEF+14A"

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

META = {
    # extraction ticker -> merge ticker
    "BK":   dict(ticker="BNY",  name="The Bank of New York Mellon Corporation", sector="Financials",
                 proxy_year=2026, anchor_year=2025, source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M"),
    "VRT":  dict(ticker="VRT",  name="Vertiv Holdings Co", sector="Industrials",
                 proxy_year=2026, anchor_year=2025, source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M"),
    "LITE": dict(ticker="LITE", name="Lumentum Holdings Inc.", sector="Information Technology",
                 proxy_year=2025, anchor_year=2025, source="SEC DEF 14A 2025 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M",
                 anchor_name_fix={"Michael E. Hurlston": "Michael Hurlston"}),
    "MMC":  dict(ticker="MRSH", name="Marsh & McLennan Companies, Inc.", sector="Financials",
                 proxy_year=2026, anchor_year=2025, source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M"),
    "BE":   dict(ticker="BE",   name="Bloom Energy Corporation", sector="Industrials",
                 proxy_year=2026, anchor_year=2025, source="SEC DEF 14A 2026 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M"),
    "FOXA": dict(ticker="FOXA", name="Fox Corporation", sector="Communication Services",
                 proxy_year=2025, anchor_year=2025, source="SEC DEF 14A 2025 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M"),
    "COHR": dict(ticker="COHR", name="Coherent Corp.", sector="Information Technology",
                 proxy_year=2025, anchor_year=2025, source="SEC DEF 14A 2025 \u2014 FY2025 CEO",
                 data_source="SEC EDGAR DEF 14A", gender="M"),
    "FDXF": dict(ticker="FDXF", name="FedEx Freight Holding Company, Inc.", sector="Industrials",
                 proxy_year=2026, anchor_year=2026, source="SEC 10-K 2026 \u2014 FY2026 CEO",
                 data_source="SEC EDGAR 10-K", gender="M", non_def14a=True),
}

new_companies = []
row_total_new = 0
for xt, m in META.items():
    d = json.load(open(os.path.join(BATCH, f"{xt}_extraction.json")))
    t = m["ticker"]
    rows = d["rows"]
    # Drop rows that are not real disclosures: FOXA Adam Ciongoli FY2023 is all
    # em-dashes in the filing (he joined during FY2024 and was not an NEO in
    # FY2023). Keeping it would fabricate an NEO-year record.
    dropped = [r for r in rows if r["total"] is None]
    assert all(r.get("filing_gap_note") and "not an NEO" in r["filing_gap_note"] for r in dropped), \
        f"{t}: unexpected null-total row"
    if dropped:
        print(f"{t}: dropping {len(dropped)} non-disclosure row(s): "
              + ", ".join(f"{r['name']} FY{r['year']}" for r in dropped))
        rows = [r for r in rows if r["total"] is not None]
    ay = m["anchor_year"]
    # anchor name normalization (LITE)
    fix = m.get("anchor_name_fix", {})
    for r in rows:
        if r["name"] in fix:
            r["name"] = fix[r["name"]]
    anchor = d["ceo_anchor"]
    anchor_name = fix.get(anchor["name"], anchor["name"])
    assert anchor["total"] == [r["total"] for r in rows if r["name"] == anchor_name and r["year"] == anchor["year"]][0], f"{t} anchor mismatch"
    assert sum(1 for r in rows if r["name"] == anchor_name and r["year"] == anchor["year"]) == 1, f"{t} anchor not unique"
    arows = [r for r in rows if r["year"] == ay]
    neo_names = sorted({r["name"] for r in rows})
    acc = d.get("accession")
    furl = filing_url_for(d["cik"], acc)
    label = "verified" if m.get("non_def14a") else LABEL

    executives = []
    for r in rows:
        erow = {"name": r["name"], "title": r["title"], "year": r["year"]}
        for k in COMPS:
            if r.get(k) is not None:
                erow[k] = r[k]
        erow["total"] = r["total"]
        erow["_total_source"] = label
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
        # BNY: vote results come from the 8-K/A Item 5.07 (filed 2026-04-17),
        # not the DEF 14A (filed 2026-03-05, before the 2026-04-14 meeting).
        # Verified 2026-09-25 from the primary filing: 317,099,734 for (55.56%),
        # 253,650,298 against (44.44%), 1,796,676 abstained, 50,748,197 broker
        # non-votes.
        if t == "BNY":
            say_on_pay.update({
                "votes_for": 317099734, "votes_against": 253650298,
                "abstain": 1796676, "broker_non_votes": 50748197,
                "source_url": "https://www.sec.gov/Archives/edgar/data/1390777/000119312526161599/",
            })
        for k in ("votes_for", "votes_against", "abstain", "broker_non_votes"):
            if sop.get(k) is not None:
                say_on_pay[k] = sop[k]

    crec = {
        "company_name": m["name"], "ticker": t, "cik": cik10(d["cik"]),
        "sector": m["sector"], "filing_date": d["filing_date"], "filing_url": furl,
        "proxy_fiscal_year": m["proxy_year"], "fiscal_year": ay,
        "available_years": sorted({r["year"] for r in rows}, reverse=True),
        "ceo_name": anchor_name, "total_compensation": anchor["total"],
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
    print(f"{t}: {len(rows)} rows, {len(neo_names)} NEOs, CEO {anchor_name} FY{ay} ${anchor['total']:,}, "
          f"ratio {d.get('pay_ratio')}, SoP {sop.get('pct')}, peers {len(d['peer_group'])}")

comp["companies"].extend(new_companies)

# --- metadata sync ---
md = comp["metadata"]
n_new = len(new_companies)
md["total_companies"] = 506 + n_new
md["total_neo_records"] = 6936 + row_total_new
md["total_executives"] = md["total_neo_records"]
md["enriched_count"] = 506 + n_new
md["edgar_coverage"] = 506 + n_new
md["companies_with_executives"] = 506 + n_new
md["title_coverage"] = f"{md['total_neo_records']}/{md['total_neo_records']}"
# pay ratio: 7 new disclose, FDXF does not
md["companies_with_pay_ratio"] = 505 + 7
md["say_on_pay_coverage"] = 505 + 7
dq = md["data_quality"]
dqd = md["data_quality_detailed"]
dq[LABEL] = dq.get(LABEL, 0) + (row_total_new - 8)
dqd[LABEL] = dqd.get(LABEL, 0) + (row_total_new - 8)
dq["verified"] = dq.get("verified", 0) + 8
dqd["verified"] = dqd.get("verified", 0) + 8
# verified_total = verified-family buckets
VERIFIED_FAMILY = {"verified"} | {k for k in dq if k.startswith("def14a_verified_")}
md["verified_total"] = sum(dq.get(k, 0) for k in VERIFIED_FAMILY)
md["description"] = f"{md['total_companies']} companies, {md['total_neo_records']} NEO records, {md['total_companies']} companies enriched"
# aggregate_stats recompute
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
md["last_updated"] = "2026-09-24"
md["last_dq_repair"] = "2026-09-24"
print("metadata:", md["total_companies"], "companies,", md["total_neo_records"], "rows,",
      "verified_total", md["verified_total"], "def14a_20260924", dq[LABEL])
print("agg: median_ceo", agg["median_ceo_pay"], "mean_ceo", round(agg["mean_ceo_pay"], 1),
      "median_ratio", agg["median_pay_ratio"], "median_worker", agg["median_worker_pay"])

json.dump(comp, open(COMP_PATH, "w"), indent=1)
print("wrote", COMP_PATH)
