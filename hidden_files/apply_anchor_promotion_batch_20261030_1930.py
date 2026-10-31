#!/usr/bin/env python3
"""2026-10-30 19:30 PT (284th review): 4-company CEO-anchor promotion batch.

Backlog candidate #2 (panel 283rd review): ORCL co-CEO + CPB + EL + JKHY + WDC.
This run promotes the 4 non-co-CEO anchors; ORCL co-CEO adjudication needs a
dataset convention decision (no co-CEO convention exists) and stays queued.

Method: each FY2026 DEF 14A was fetched from EDGAR with the declared UA
("Kit/1.0 (factoryfactorykit@gmail.com; sp500-exec-comp data research)") and
read for (1) the FY2026 PEO in the SCT, (2) the filed FY2026 CEO Pay Ratio
disclosure, (3) leadership-transition prose for ceo_tenure. Local copies lived
in /tmp/anchor284 (ephemeral, not committed).

All four company anchors were stale: company.fiscal_year was already 2026
(post-enrichment) but ceo_name/total_compensation/pay_ratio/median_worker_pay
were still pinned to the FY2025 CEO. All four FY2026 PEO SCT totals match the
already-stored 2026 exec rows exactly (no row changes needed).

Filings (all re-read this run):
- CPB  acc. 0000016732-26-000031, filed 2026-10-07, doc cpb-20261007.htm
  Beekhuizen FY2026 $10,965,019 (stored row matches); median $72,257; ratio 152:1
  (10965019/72257 = 151.77 -> 152). Tenure: "named President and CEO effective
  February 1, 2025" -> {2025, February, high, prose} (already stored, kept).
- EL   acc. 0001104659-26-112176, filed 2026-09-30, doc tm2623505-1_def14a.htm
  de La Faverie FY2026 $20,585,784 (stored row matches); median $34,255; ratio
  601:1 (20585784/34255 = 600.99 -> 601). Tenure: "served as President and CEO
  since January 2025" -> {2025, January, high, prose}.
- JKHY acc. 0000779152-26-000088, filed 2026-10-02, doc jkhy-20261001.htm
  Adelson FY2026 $8,413,970 (stored row matches); median $96,615; ratio 87:1
  (8413970/96615 = 87.08 -> 87). Tenure: "appointed as CEO effective July 1,
  2024" -> {2024, July, high, prose}.
- WDC  acc. 0001628280-26-064909, filed 2026-10-05, doc wdc-20261005.htm
  Tan FY2026 $17,168,701 (stored row matches); median $11,787; ratio 1,457:1
  (17168701/11787 = 1456.7 -> 1457). Tenure: "served as our CEO since February
  2025" -> {2025, February, high, prose} (already stored, kept).

company-level edits (anchor fields only; exec rows untouched):
- ceo_name, total_compensation, pay_ratio, median_worker_pay,
  source -> "SEC DEF 14A 2026 - FY2026 CEO", ceo_tenure (EL/JKHY only).
- aggregate_stats + sector_medians recomputed with check_metadata_consistency.py
  section-17 exact semantics (guard-exact _anchor_row_for). Top-level legacy
  scalar fields (median_ceo_pay etc.) are NOT recomputed (283rd precedent: the
  guard only covers aggregate_stats; legacy scalars use older pipeline semantics).

No exec-total changes -> phantom counter untouched (exec sum delta $0).
"""

import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(
    REPO, "hidden_files",
    "compensation_backup_20261030_1930_pre_anchorpromotion.json",
)

PROMOTIONS = {
    "CPB": {
        "ceo_name": "Mick J. Beekhuizen",
        "total_compensation": 10965019,
        "pay_ratio": 152,
        "median_worker_pay": 72257,
    },
    "EL": {
        "ceo_name": "Stéphane de La Faverie",
        "total_compensation": 20585784,
        "pay_ratio": 601,
        "median_worker_pay": 34255,
        "ceo_tenure": {"year": 2025, "month": "January", "confidence": "high",
                       "sources": ["prose"]},
    },
    "JKHY": {
        "ceo_name": "Gregory R. Adelson",
        "total_compensation": 8413970,
        "pay_ratio": 87,
        "median_worker_pay": 96615,
        "ceo_tenure": {"year": 2024, "month": "July", "confidence": "high",
                       "sources": ["prose"]},
    },
    "WDC": {
        "ceo_name": "Irving Tan",
        "total_compensation": 17168701,
        "pay_ratio": 1457,
        "median_worker_pay": 11787,
    },
}


def recompute_aggregates(companies, meta):
    # section-17 exact semantics (check_metadata_consistency.py)
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
        old = {k: c.get(k) for k in
               ("ceo_name", "total_compensation", "pay_ratio", "median_worker_pay")}
        c["ceo_name"] = p["ceo_name"]
        c["total_compensation"] = p["total_compensation"]
        c["pay_ratio"] = p["pay_ratio"]
        c["median_worker_pay"] = p["median_worker_pay"]
        c["source"] = "SEC DEF 14A 2026 - FY2026 CEO"
        if "ceo_tenure" in p:
            c["ceo_tenure"] = p["ceo_tenure"]
        print(t, old, "->", p["ceo_name"], p["total_compensation"],
              p["pay_ratio"], p["median_worker_pay"])

    recompute_aggregates(d["companies"], d["metadata"])
    agg = d["metadata"]["aggregate_stats"]
    print("aggregate_stats:", agg)

    stamp = ("284th review (2026-10-30 19:30 PT): 4-company CEO-anchor promotion "
             "batch (CPB/EL/JKHY/WDC) - company anchors moved from the FY2025 CEO "
             "to the FY2026 PEO (filing-verbatim SCT totals + pay-ratio "
             "disclosures from the Oct-2026 DEF 14As: CPB Beekhuizen $10,965,019 / "
             "152:1 / $72,257; EL de La Faverie $20,585,784 / 601:1 / $34,255; "
             "JKHY Adelson $8,413,970 / 87:1 / $96,615; WDC Tan $17,168,701 / "
             "1,457:1 / $11,787); aggregate_stats + sector_medians recomputed "
             "(section-17 semantics); ORCL co-CEO stays queued (needs convention).")
    notes = d["metadata"].get("notes", [])
    if not any(isinstance(n, str) and n.startswith("284th review") for n in notes):
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
