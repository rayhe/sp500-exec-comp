#!/usr/bin/env python3
"""2026-10-30 18:00 PT FY2026 enrichment batch 10: TECH/EA (FY2026) + K (FY2024).

Source filings (all Part-III 10-K/A amendments, fetched 2026-10-30 with
declared UA "Kit/1.0 (factoryfactorykit@gmail.com; sp500-exec-comp data research)"):
- TECH  Bio-Techne   10-K/A filed 2026-10-28  acc 0001140361-26-041062  FY2026 (y/e Jun 30, 2026)
- EA    Electronic Arts 10-K/A filed 2026-07-28 acc 0001308179-26-000382 FY2026 (y/e Mar 31, 2026)
- K     Kellanova    10-K/A filed 2025-03-07  acc 0000055067-25-000127  FY2024 (y/e Dec 28, 2024)

Why 10-K/As, not DEF 14As:
- TECH filed the Part-III amendment ON the 120-day deadline (2026-10-28); no FY2026 DEF 14A exists.
- EA was taken private by the PIF/Silver Lake/Affinity $55B consortium (closed Aug 2026);
  no FY2026 DEF 14A will ever file. FY2026 rows are final.
- K (Kellanova) was acquired by Mars (closed Dec 11, 2025, delisted); no FY2025 DEF 14A
  will ever file. FY2024 rows are final.
- COST/ACN/MU/JBL 10-Ks (Oct-2026) carry no SCT; their FY2026 DEF 14As are expected
  Dec 2026 - left queued, nothing ingested. INTU (10-K only) likewise. DASH DEF 14C
  (2026-08-27) is a bylaws-consent filing with no compensation disclosure - non-actionable.
  ALB/EA/IBKR/MO 10-K/As checked: no SCT (EA's does carry FY2026 - ingested here).

Findings:
- TECH: 11 overlaps cross-checked filing-verbatim (all components), 0 deltas;
  Kelderman 2025 has a genuine $1 filer-side slip (components sum $8,151,180, filing
  prints $8,151,181; re-read digit-by-digit from raw 10-K/A HTML) -> relabeled
  verified->component_mismatch per the $1-slip taxonomy (kept at printed values);
  +6 FY2026 rows (Kelderman $9,474,592; Hippel $4,532,901; Geist $3,131,038;
  Crouse $1,537,832 2026-only NEO; Bohnen $2,384,352; McManus $3,396,886 -
  FY2026 NEO sum $24,457,601).
- EA: 10 overlaps cross-checked; the 10-K/A SCT exposes a systematic column-shift
  in the original FY2025-proxy parse: stock_awards stored as 0 with the stock
  value sitting in non_equity_incentive and the NEIP value in pension_nqdc
  (e.g. Wilson 2025: stock $25,710,910 stored as neip, NEIP $2,840,067 stored as
  pension; totals unaffected). All 13 stored EA rows repaired filing-verbatim
  (2024/2025 verified component-by-component vs the 10-K/A; 2023 rows come from
  the same FY2025-proxy SCT table, same systematic shift, totals preserved).
  +5 FY2026 rows (Wilson $38,649,984; Canfield $11,317,409; Miele $13,713,557
  title now "President, EA Entertainment & Central Development"; Singh $8,358,457;
  Schatz $8,458,379 - FY2026 NEO sum $80,497,786).
- K: 7 overlaps cross-checked filing-verbatim, 0 deltas; Lawlor 2022 stored with
  bonus $1,700,642 mislabeled as stock_awards (stock 0 / options $688,213 shifted
  one column right) - repaired filing-verbatim; +5 FY2024 rows (Cahillane
  $14,882,161; Banati $5,412,899; Amaya $3,485,118 2024-only NEO; Lawlor $3,401,532;
  Kapoor $3,844,190 - FY2024 NEO sum $31,025,900). K pension "—" cells with
  footnote (9) (pension-value decreases of $43K Amaya / $136K Lawlor) stored as 0
  per SEC SCT convention.

All CEO anchors continue (Kelderman, Wilson, Cahillane) - no new section-11 trips.
Phantom: +$135,981,287 genuine FY2026/FY2024 compensation restored filing-verbatim.
"""
import json
import os
import shutil
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
PROX = "/tmp/fy2026batch10"


def main():
    shutil.copy2(JSON_PATH, os.path.join(
        HERE, "compensation_backup_20261030_1800_pre_fy2026batch10.json"))

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    companies = {c["ticker"]: c for c in data["companies"]}
    return _apply(data, companies)


def _apply(data, companies):

    STATS = {"new": 0, "repaired": 0, "checked": 0, "deltas": 0, "relabeled_mismatch": 0}

    FIELDS = ["salary", "bonus", "stock_awards", "option_awards",
              "non_equity_incentive", "pension_nqdc", "all_other", "total"]


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


    def crosscheck(ticker, filing_rows, extra=None):
        """filing_rows: list of (name, year, dict-of-components). Returns new-row specs."""
        extra = extra or {}
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
                        print("DELTA", ticker, name, year, f, "stored", sv, "filing", comp[f])
                        STATS["deltas"] += 1
            else:
                new.append((name, year, comp))
        return new


    def load_raw(fn):
        rows = json.load(open(os.path.join(PROX, fn)))
        return [(r["name"], r["year"],
                 dict(zip(FIELDS, r["nums"]))) for r in rows]


    # ---------------- TECH ----------------
    TECH_TITLES = {
        "Kim Kelderman": "President and CEO",
        "James Hippel": "Executive Vice President and CFO",
        "William Geist": "President, Protein Sciences",
        "Steven Crouse": "President, Diagnostics and Spatial Biology",
        "Shane Bohnen": "Senior Vice President and General Counsel",
        "Matthew McManus": "Former President, Diagnostics and Spatial Biology",
    }
    tech_cross = load_raw("TECH_cross.json")
    tech_new = crosscheck("TECH", tech_cross)
    tech_2026 = [r for r in load_raw("TECH_raw.json") if r[1] == 2026]
    add_rows("TECH", [mkrow(n, TECH_TITLES[n], yr,
                           c["salary"], c["bonus"], c["stock_awards"], c["option_awards"],
                           c["non_equity_incentive"], c["pension_nqdc"], c["all_other"], c["total"])
                     for n, yr, c in tech_2026])
    assert STATS["deltas"] == 0, ("TECH deltas", STATS["deltas"])
    # Kelderman 2025 $1 filer-side slip -> component_mismatch (values kept printed-verbatim)
    tc = companies["TECH"]
    for e in tc["executives"]:
        if e["name"] == "Kim Kelderman" and e["year"] == 2025:
            assert e["_total_source"] == "verified"
            e["_total_source"] = "component_mismatch"
            STATS["relabeled_mismatch"] += 1
    tc["filing_date"] = "2026-10-28"
    tc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/842023/000114036126041062/ef20084361_10ka.htm"
    tc["data_source"] = "SEC EDGAR 10-K/A"
    tc["fiscal_year"] = 2026
    tc["proxy_fiscal_year"] = 2026
    tc["available_years"] = [2026, 2025, 2024, 2023]
    tc["neo_count"] = 6
    tc["total_compensation"] = 9474592
    tc["total_neo_compensation"] = sum(e["total"] for e in tc["executives"] if e["year"] == 2026)
    assert tc["total_neo_compensation"] == 24457601, tc["total_neo_compensation"]

    # ---------------- EA ----------------
    EA_TITLES = {
        "Andrew Wilson": "Chief Executive Officer",
        "Stuart Canfield": "Chief Financial Officer",
        "Laura Miele": "President, EA Entertainment & Central Development",
        "Mala Singh": "Chief People Officer",
        "Jacob Schatz": "Chief Legal Officer",
    }
    ea = load_raw("EA_raw.json")
    eac = companies["EA"]
    stored_ea = {(e["name"], e["year"]): e for e in eac["executives"]}
    # verify the systematic column-shift pattern on the 10 overlap rows first
    for name, year, comp in ea:
        if year not in (2024, 2025):
            continue
        s = stored_ea[(name, year)]
        assert s.get("stock_awards", 0) == 0, ("EA unexpected stock", name, year, s)
        assert s.get("non_equity_incentive") == comp["stock_awards"], (name, year)
        assert (s.get("pension_nqdc") or 0) == comp["non_equity_incentive"], (name, year)
        assert s.get("salary") == comp["salary"], (name, year)
        assert s.get("all_other") == comp["all_other"], (name, year)
        assert s.get("total") == comp["total"], (name, year)
        STATS["checked"] += 1
    # apply the relabel to ALL 13 stored EA rows (same FY2025-proxy SCT table, totals preserved)
    for e in eac["executives"]:
        stock = e.get("non_equity_incentive") or 0
        neip = e.get("pension_nqdc") or 0
        e["stock_awards"] = stock
        e["non_equity_incentive"] = neip
        e["pension_nqdc"] = 0
        STATS["repaired"] += 1
    ea_new = [(n, yr, c) for n, yr, c in ea if yr == 2026]
    add_rows("EA", [mkrow(n, EA_TITLES[n], yr,
                         c["salary"], c["bonus"], c["stock_awards"], c["option_awards"],
                         c["non_equity_incentive"], c["pension_nqdc"], c["all_other"], c["total"])
                   for n, yr, c in ea_new])
    eac["filing_date"] = "2026-07-28"
    eac["filing_url"] = "https://www.sec.gov/Archives/edgar/data/712515/000130817926000382/ea2026-10ka.htm"
    eac["data_source"] = "SEC EDGAR 10-K/A"
    eac["fiscal_year"] = 2026
    eac["proxy_fiscal_year"] = 2026
    eac["available_years"] = [2026, 2025, 2024, 2023]
    eac["neo_count"] = 5
    eac["total_compensation"] = 38649984
    eac["total_neo_compensation"] = sum(e["total"] for e in eac["executives"] if e["year"] == 2026)
    assert eac["total_neo_compensation"] == 80497786, eac["total_neo_compensation"]

    # ---------------- K ----------------
    K_TITLES = {
        "Steve Cahillane": "Chairman, President and Chief Executive Officer",
        "Amit Banati": "Vice Chairman and Chief Financial Officer",
        "Nico Amaya": "Senior Vice President & President, Kellanova North America",
        "David Lawlor": "Senior Vice President & President, Kellanova Europe",
        "Shumit Kapoor": "Senior Vice President & President, Kellanova AMEA",
    }
    k = load_raw("K_raw.json")
    kc = companies["K"]
    stored_k = {(e["name"], e["year"]): e for e in kc["executives"]}
    k_new = []
    for name, year, comp in k:
        key = (name, year)
        if key in stored_k:
            STATS["checked"] += 1
            s = stored_k[key]
            for f in FIELDS:
                sv = s.get(f)
                if sv != comp[f] and not (sv is None and comp[f] == 0):
                    # Lawlor 2022 stored column shift is repaired below; record expected delta
                    print("DELTA K", name, year, f, "stored", sv, "filing", comp[f])
                    STATS["deltas"] += 1
        else:
            k_new.append((name, year, comp))
    # repair Lawlor 2022: bonus $1,700,642 mislabeled as stock_awards, options shifted right
    repair_row("K", "David Lawlor", 2022,
               bonus=1700642, stock_awards=0, option_awards=688213,
               non_equity_incentive=0, pension_nqdc=0)
    add_rows("K", [mkrow(n, K_TITLES[n], yr,
                        c["salary"], c["bonus"], c["stock_awards"], c["option_awards"],
                        c["non_equity_incentive"], c["pension_nqdc"], c["all_other"], c["total"])
                  for n, yr, c in k_new])
    kc["filing_date"] = "2025-03-07"
    kc["filing_url"] = "https://www.sec.gov/Archives/edgar/data/55067/000005506725000127/k-20241228.htm"
    kc["data_source"] = "SEC EDGAR 10-K/A"
    kc["fiscal_year"] = 2024
    kc["proxy_fiscal_year"] = 2024
    kc["available_years"] = [2024, 2023, 2022, 2021]
    kc["neo_count"] = 5
    kc["total_compensation"] = 14882161
    kc["total_neo_compensation"] = sum(e["total"] for e in kc["executives"] if e["year"] == 2024)
    assert kc["total_neo_compensation"] == 31025900, kc["total_neo_compensation"]

    # ---------------- metadata ----------------
    n = sum(len(c["executives"]) for c in data["companies"])
    meta = data["metadata"]
    meta["description"] = "518 companies, %d NEO records, 517 companies enriched" % n
    meta["total_neo_records"] = n
    meta["total_executives"] = n
    meta["total_neos"] = n
    meta["last_updated"] = "2026-10-30"
    meta["last_dq_repair"] = "2026-10-30"
    meta["title_coverage"] = "%d/%d" % (n, n)

    # data_quality buckets recount from live _total_source labels (guard section 4)
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

    # aggregate_stats + sector_medians recompute from live company records (guard section 17)
    comp_list = data["companies"]
    ceo_pays = [c["total_compensation"] for c in comp_list if c.get("total_compensation", 0) > 0]
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
        fy = c.get("fiscal_year")
        ceo = c.get("ceo_name") or ""
        if fy is None or not ceo:
            return None
        parts = [p for p in "".join(ch if ch.isalnum() else " " for ch in ceo).lower().split()
                 if p not in ("jr", "sr", "ii", "iii", "iv", "v") and len(p) > 1]
        cf, cl = (parts[0], parts[-1]) if parts else ("", "")
        for e in c.get("executives", []):
            if e.get("year") != fy:
                continue
            ep = [p for p in "".join(ch if ch.isalnum() else " " for ch in (e.get("name") or "")).lower().split()
                  if p not in ("jr", "sr", "ii", "iii", "iv", "v") and len(p) > 1]
            if not ep:
                continue
            rf, rl = ep[0], ep[-1]
            if rl and rl == cl and rf and (rf == cf or rf[0] == cf[0]):
                return e
        return None


    sector_pays = {}
    for c in comp_list:
        if c.get("total_compensation", 0) > 0:
            sector_pays.setdefault(c.get("sector", "Unknown"), []).append(c["total_compensation"])
    sector_cov = {}
    for c in comp_list:
        a = _anchor_row_for(c)
        if a is None:
            continue
        s = c.get("sector", "Unknown")
        r = sector_cov.setdefault(s, {"ver": 0, "doc": 0, "undoc": 0})
        src = a.get("_total_source") or ""
        if src == "verified" or str(src).startswith("def14a_verified_"):
            r["ver"] += 1
        elif a.get("_note"):
            r["doc"] += 1
        else:
            r["undoc"] += 1
    sm = {}
    for s, p in sorted(sector_pays.items()):
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
        print("data_source mix:", {k: sum(1 for c in companies.values() if c.get("data_source") == k)
                                   for k in sorted(set(c.get("data_source") for c in companies.values()))})


if __name__ == "__main__":
    main()
