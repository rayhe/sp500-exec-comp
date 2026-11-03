#!/usr/bin/env python3
"""2026-11-02 21:00 PT (321st review): 12-company CEO-anchor promotion batch.

Continuation of the 284th-review (2026-10-30) FY2026 anchor-promotion queue.
The 13 companies whose company.fiscal_year was already 2026 (post-enrichment)
but whose anchor fields were still pinned to the FY2025 CEO were re-checked
against fresh primary DEF 14As fetched from EDGAR with the declared UA
("Kit/1.0 (factoryfactorykit@gmail.com)"). 12 promote cleanly: each FY2026
PEO SCT total matches the already-stored 2026 exec row exactly, and the filed
FY2026 pay-ratio disclosure (CEO total / median / ratio) cross-foots.

CPRT is DEFERRED (transition ambiguity, documented in the metadata note):
its FY2026 SCT lists A. Jayson Adair as Executive Chairman and CEO ($351,386,
$1 salary) alongside former CEO Jeffrey Liaw ($2,064,740), but the filed
pay-ratio disclosure is computed on Liaw (42:1, median $48,661), not on the
current CEO. Promoting the anchor to Adair while keeping the filed 42:1 ratio
(or inventing a 7:1 ratio) would be incoherent; needs a transition
adjudication like the ORCL co-CEO precedent. CPRT FY2026 exec rows (all 3)
are already stored; nothing missing.

Filings (all re-read this run; FOX/FOXA share one filing):
- AZO  acc. 0001104659-26-119175, filed 2026-10-27: Daniele $11,236,964 /
  median $29,450 / 381:1 (11236964/29450 = 381.6).
- CLX  acc. 0001552781-26-000516, filed 2026-10-07: Rendle $14,000,460 /
  median $83,267 / 168:1 (168.1).
- CSCO acc. 0001308179-26-000439, filed 2026-10-29: Robbins $48,527,813 /
  median $223,675 / 217:1 (217.0).
- FDS  acc. 0001628280-26-067145, filed 2026-10-26: Viswanathan $62,046,674 /
  median $18,413 / 3,370:1 (3369.7). Headline ratio used; filing also gives
  833:1 excluding make-whole awards and annualizing LTI. Tenure: "named CEO
  effective September 8, 2025" -> {2025, September, high, prose}. Viswanathan
  succeeded Snow on 2025-09-08; Snow FY2026 stub row ($337,164) already stored.
- FOX/FOXA acc. 0001628280-26-062480, filed 2026-09-17: Murdoch $31,019,117 /
  median $104,998 / 295:1 (295.4).
- KLAC acc. 0001193125-26-397898, filed 2026-09-22: Wallace $29,954,476 /
  median $99,696 / 300:1 (300.4).
- LRCX acc. 0000707549-26-000047, filed 2026-09-24: Archer $40,354,475 /
  median $80,764 / 500:1 (499.7).
- MDT  acc. 0001613103-26-000010, filed 2026-08-17: Martha $22,940,252 /
  median $75,587 / 303:1 (303.5 -> filed 303).
- MSFT acc. 0001193125-26-427849, filed 2026-10-21: Nadella $90,628,977 /
  median $215,057 / 421:1 (421.4).
- NWSA acc. 0001104659-26-109969, filed 2026-09-23: Thomson $19,745,396 /
  median $96,277 / 205:1 (205.1).
- STX  acc. 0001137789-26-000207, filed 2026-09-08: Mosley $26,918,702 /
  median $12,550 / 2,145:1 (2144.9).

company-level edits (anchor fields only; exec rows untouched):
- ceo_name (FDS only), total_compensation, pay_ratio, median_worker_pay,
  source -> "SEC DEF 14A 2026 - FY2026 CEO", ceo_tenure (FDS only).
- aggregate_stats + sector_medians recomputed with
  check_metadata_consistency.py section-17 exact semantics (guard-exact
  _anchor_row_for). Top-level legacy scalar fields are NOT recomputed
  (283rd precedent).

Screens run this review (no repairs needed, all documented true negatives):
- Full 7,318-row component recompute: only $1 filing-rounding diffs plus 4
  already-documented $2 filer-side gaps (EVRG/IR/MKC/MTB, Oct-25 notes) and
  44 component_mismatch rows, all labeled.
- Small-NEO-count screen: ENPH (2 NEOs) verified against its 2026 proxy SCT
  ("Ms. Yang was our only non-CEO NEO in 2025"); DLR (3) and ROP (3) SCTs
  re-read filing-verbatim, stored rows match exactly.
- EDGAR efts sweep for DEF 14A filed 2026-10-30..2026-11-02: 20 filings, zero
  from S&P 500 roster companies.
- Stale-year screen: only documented acquired/delisted names (ANSS, DAY,
  HES, IPG, JNPR, K, WBA) plus VMRK (no DEF 14A yet, watch item).

No exec-total changes -> phantom counter untouched (exec sum delta $0).
"""

import json
import os
import statistics

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(
    REPO, "data",
    "compensation_backup_20261102_2100_pre_fy2026anchor2.json",
)

PROMOTIONS = {
    "AZO": {"total_compensation": 11236964, "pay_ratio": 381,
            "median_worker_pay": 29450},
    "CLX": {"total_compensation": 14000460, "pay_ratio": 168,
            "median_worker_pay": 83267},
    "CSCO": {"total_compensation": 48527813, "pay_ratio": 217,
             "median_worker_pay": 223675},
    "FDS": {"ceo_name": "Sanoke Viswanathan",
            "total_compensation": 62046674, "pay_ratio": 3370,
            "median_worker_pay": 18413,
            "ceo_tenure": {"year": 2025, "month": "September",
                           "confidence": "high", "sources": ["prose"]}},
    "FOX": {"total_compensation": 31019117, "pay_ratio": 295,
            "median_worker_pay": 104998},
    "FOXA": {"total_compensation": 31019117, "pay_ratio": 295,
             "median_worker_pay": 104998},
    "KLAC": {"total_compensation": 29954476, "pay_ratio": 300,
             "median_worker_pay": 99696},
    "LRCX": {"total_compensation": 40354475, "pay_ratio": 500,
             "median_worker_pay": 80764},
    "MDT": {"total_compensation": 22940252, "pay_ratio": 303,
            "median_worker_pay": 75587},
    "MSFT": {"total_compensation": 90628977, "pay_ratio": 421,
             "median_worker_pay": 215057},
    "NWSA": {"total_compensation": 19745396, "pay_ratio": 205,
             "median_worker_pay": 96277},
    "STX": {"total_compensation": 26918702, "pay_ratio": 2145,
            "median_worker_pay": 12550},
}


def recompute_aggregates(companies, meta):
    ceo_pays = [c["total_compensation"] for c in companies
                if c.get("total_compensation", 0) > 0]
    worker_pays = [c["median_worker_pay"] for c in companies
                   if c.get("median_worker_pay") and c["median_worker_pay"] > 0]
    ratios = [c["pay_ratio"] for c in companies
              if c.get("pay_ratio") is not None and c["pay_ratio"] > 0]
    meta["aggregate_stats"] = {
        "total_companies": len(companies),
        "companies_with_pay_ratio": len(ratios),
        "median_ceo_pay": int(statistics.median(ceo_pays)),
        "mean_ceo_pay": int(statistics.mean(ceo_pays)),
        "max_ceo_pay": max(ceo_pays),
        "min_ceo_pay": min(ceo_pays),
        "median_worker_pay": int(statistics.median(worker_pays)) if worker_pays else 0,
        "median_pay_ratio": int(statistics.median(ratios)) if ratios else 0,
    }

    def anchor_row_for(c):
        ceo, fy, tot = c.get("ceo_name", ""), c.get("fiscal_year"), \
            c.get("total_compensation", 0)
        if not tot:
            return None
        rows = [e for e in c.get("executives", [])
                if e.get("name") == ceo and e.get("year") == fy]
        if not rows:
            rows = [e for e in c.get("executives", []) if e.get("total") == tot]
        return rows[0] if rows else None

    sector_pays = {}
    for c in companies:
        if c.get("total_compensation", 0) > 0:
            sector_pays.setdefault(c.get("sector", "Unknown"),
                                   []).append(c["total_compensation"])
    sector_cov = {}
    for c in companies:
        a = anchor_row_for(c)
        if a is None:
            continue
        s = c.get("sector", "Unknown")
        r = sector_cov.setdefault(s, {"ver": 0, "doc": 0, "undoc": 0})
        src = a.get("_total_source") or ""
        if src.startswith("verified") or src.startswith("def14a_verified"):
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


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    by = {c["ticker"]: c for c in d["companies"]}

    exec_total_before = sum(int(round(e.get("total") or 0))
                            for c in d["companies"] for e in c["executives"])

    for t, p in PROMOTIONS.items():
        c = by[t]
        # Guard: promotion total must match an already-stored FY2026 exec row
        rows = [e for e in c["executives"]
                if e["year"] == 2026 and e["total"] == p["total_compensation"]]
        assert rows, f"{t}: no stored FY2026 row matches {p['total_compensation']}"
        old = {k: c.get(k) for k in
               ("ceo_name", "total_compensation", "pay_ratio", "median_worker_pay")}
        if "ceo_name" in p:
            c["ceo_name"] = p["ceo_name"]
        c["total_compensation"] = p["total_compensation"]
        c["pay_ratio"] = p["pay_ratio"]
        c["median_worker_pay"] = p["median_worker_pay"]
        c["source"] = "SEC DEF 14A 2026 - FY2026 CEO"
        if "ceo_tenure" in p:
            c["ceo_tenure"] = p["ceo_tenure"]
        print(t, old, "->", c["ceo_name"], p["total_compensation"],
              p["pay_ratio"], p["median_worker_pay"])

    recompute_aggregates(d["companies"], d["metadata"])
    print("aggregate_stats:", d["metadata"]["aggregate_stats"])

    stamp = ("321st review (2026-11-02 21:00 PT): 12-company CEO-anchor promotion "
             "batch (AZO/CLX/CSCO/FDS/FOX/FOXA/KLAC/LRCX/MDT/MSFT/NWSA/STX) - "
             "company anchors moved from the FY2025 CEO to the FY2026 PEO "
             "(filing-verbatim SCT totals + pay-ratio disclosures from fresh "
             "Aug-Oct 2026 DEF 14As: AZO Daniele $11,236,964 / 381:1 / $29,450; "
             "CLX Rendle $14,000,460 / 168:1 / $83,267; CSCO Robbins $48,527,813 / "
             "217:1 / $223,675; FDS Viswanathan $62,046,674 / 3,370:1 / $18,413 "
             "(headline ratio; 833:1 ex make-whole also filed; succeeded Snow "
             "2025-09-08, tenure {2025, September, prose}); FOX/FOXA Murdoch "
             "$31,019,117 / 295:1 / $104,998; KLAC Wallace $29,954,476 / 300:1 / "
             "$99,696; LRCX Archer $40,354,475 / 500:1 / $80,764; MDT Martha "
             "$22,940,252 / 303:1 / $75,587; MSFT Nadella $90,628,977 / 421:1 / "
             "$215,057; NWSA Thomson $19,745,396 / 205:1 / $96,277; STX Mosley "
             "$26,918,702 / 2,145:1 / $12,550); aggregate_stats + sector_medians "
             "recomputed (section-17 semantics). CPRT DEFERRED: FY2026 SCT names "
             "Adair (Executive Chairman and CEO, $351,386) as current CEO but the "
             "filed pay-ratio disclosure is computed on former CEO Liaw (42:1 / "
             "$48,661) - needs a transition adjudication, not a blind promotion. "
             "Screens clean: full footing scan (only $1 rounding + 4 documented "
             "$2 gaps + 44 labeled component_mismatch rows); ENPH/DLR/ROP "
             "small-NEO sets verified filing-verbatim; EDGAR Oct 30-Nov 2 DEF "
             "14A sweep found 0 S&P 500 filers.")
    notes = d["metadata"].get("notes", [])
    if not any(isinstance(n, str) and n.startswith("321st review") for n in notes):
        notes.append(stamp)

    exec_total_after = sum(int(round(e.get("total") or 0))
                           for c in d["companies"] for e in c["executives"])
    assert exec_total_after == exec_total_before, \
        f"exec totals moved {exec_total_before} -> {exec_total_after} (must not)"
    print("exec-total delta: $0 (phantom counter untouched)")

    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump(json.load(open(DATA, encoding="utf-8")), f,
                  ensure_ascii=False, indent=1)
        f.write("\n")
    print("backup:", BACKUP)

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote", DATA)


if __name__ == "__main__":
    main()
