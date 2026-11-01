#!/usr/bin/env python3
"""2026-11-01 06:30 PT (302nd review): ORCL co-CEO anchor adjudication.

Deferred by the 284th review (apply_anchor_promotion_batch_20261030_1930.py):
ORCL's FY2026 proxy (DEF 14A, filed 2026-09-25, acc. 0001193125-26-402816)
names TWO principal executive officers (co-CEOs appointed 2025-09-22 after
Catz's transition), and the dataset had no co-CEO anchor convention.
This run establishes the convention and promotes the anchor.

Co-CEO anchor convention (302nd review): the company anchor is the
FIRST-LISTED co-CEO in the filed SCT; the filed pay ratio used is that PEO's
filed ratio. Precedent: NFLX (Ted Sarandos, first-listed/higher, anchor;
Peters stored as co-CEO row) and KKR (Joseph Y. Bae, first-listed/higher,
anchor; Nuttall stored as co-CEO row). Tie-break if order were ambiguous:
the higher filed SCT total.

Filing (re-read this run, EDGAR UA Kit/1.0):
- SCT order: Ellison, Clayton M. Magouyrk ($627,472,419), Michael D. Sicilia
  ($256,606,752), Maxson, Catz, Hura, Levey, Kehring. Magouyrk is first-listed
  among the co-CEOs AND the higher-paid: both tests agree.
- CEO Pay Ratio section: "the ratios of the annual total compensation of each
  of our CEOs, Clayton M. Magouyrk and Michael D. Sicilia, to the annual total
  compensation of our median compensated employee worldwide ... was 6,623 to 1
  for Mr. Magouyrk and 2,709 to 1 for Mr. Sicilia"; Magouyrk total
  $627,472,419; Sicilia total $256,606,752; median global employee $94,740.
- Leadership transition prose: "On September 22, 2025 ... the Board appointed
  Mr. Magouyrk and Mr. Sicilia as Chief Executive Officers of Oracle."
  -> ceo_tenure {2025, September, high, prose} already stored by the FY2026
  enrichment batch; kept unchanged.

Company-level edits (anchor fields only; exec rows untouched):
- ceo_name: "Safra A. Catz" -> "Clayton M. Magouyrk"
- total_compensation: 1,113,417 -> 627,472,419 (filed SCT total, matches the
  stored 2026 Magouyrk exec row exactly)
- pay_ratio: 11 -> 6623 (filed ratio; 627472419/94740 = 6623.04 -> 6623)
- median_worker_pay: 98,899 -> 94,740 (filed)
- source: "SEC DEF 14A 2025 -- FY2025 CEO" -> "SEC DEF 14A 2026 - FY2026 CEO"
  (284th-review hyphen convention for FY2026-promoted anchors)
- aggregate_stats + sector_medians recomputed with check_metadata_consistency.py
  section-17 exact semantics (guard-exact _anchor_row_for). Top-level legacy
  scalar fields are NOT recomputed (283rd precedent).
- Sicilia stays stored as a co-CEO exec row (no data loss); the anchor is a
  single-company representative by convention, same as NFLX/KKR.

No exec-total changes -> phantom counter untouched (exec sum delta $0).
"""

import json
import os
import statistics

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(
    REPO, "hidden_files",
    "compensation_backup_20261101_0630_pre_orclanchor.json",
)


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
    c = by["ORCL"]

    # pre-write assertions: filed anchor values vs stored rows
    mag = [e for e in c["executives"]
           if e["name"] == "Clayton M. Magouyrk" and e["year"] == 2026]
    assert len(mag) == 1, "expected exactly one Magouyrk 2026 row"
    assert mag[0]["total"] == 627472419, "Magouyrk SCT total mismatch"
    assert mag[0]["title"] == "Director and Chief Executive Officer", \
        "Magouyrk title drift: %r" % mag[0]["title"]
    # co-CEO SCT order: Magouyrk listed before Sicilia in stored rows
    order = [e["name"] for e in c["executives"] if e["year"] == 2026]
    assert order.index("Clayton M. Magouyrk") < order.index("Michael D. Sicilia"), \
        "co-CEO SCT order assumption broken"

    exec_total_before = sum(int(round(e.get("total") or 0))
                            for c2 in d["companies"] for e in c2["executives"])

    old = {k: c.get(k) for k in
           ("ceo_name", "total_compensation", "pay_ratio", "median_worker_pay",
            "source", "ceo_tenure")}
    c["ceo_name"] = "Clayton M. Magouyrk"
    c["total_compensation"] = 627472419
    c["pay_ratio"] = 6623
    c["median_worker_pay"] = 94740
    c["source"] = "SEC DEF 14A 2026 - FY2026 CEO"
    # ceo_tenure kept: {2025, September, high, prose} = 2025-09-22 co-CEO appt
    print("ORCL old:", old)
    print("ORCL new:", {k: c.get(k) for k in
          ("ceo_name", "total_compensation", "pay_ratio", "median_worker_pay",
           "source", "ceo_tenure")})

    recompute_aggregates(d["companies"], d["metadata"])
    print("aggregate_stats:", d["metadata"]["aggregate_stats"])

    stamp = ("302nd review (2026-11-01 06:30 PT): ORCL co-CEO anchor adjudication "
             "- establishes the co-CEO convention (anchor = first-listed co-CEO "
             "in the filed SCT; NFLX/KKR precedent) and promotes the FY2026 "
             "anchor from Safra A. Catz ($1,113,417 / 11:1 / $98,899) to Clayton "
             "M. Magouyrk ($627,472,419 / 6,623:1 / $94,740), all filing-verbatim "
             "from the 2026-09-25 DEF 14A (acc. 0001193125-26-402816; Magouyrk "
             "first-listed and higher-paid vs Sicilia $256,606,752 / 2,709:1); "
             "aggregate_stats + sector_medians recomputed (section-17 "
             "semantics); ceo_tenure kept {2025, September, prose} = 2025-09-22 "
             "co-CEO appointment.")
    notes = d["metadata"].get("notes", [])
    if not any(isinstance(n, str) and n.startswith("302nd review") for n in notes):
        notes.append(stamp)

    exec_total_after = sum(int(round(e.get("total") or 0))
                           for c2 in d["companies"] for e in c2["executives"])
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
