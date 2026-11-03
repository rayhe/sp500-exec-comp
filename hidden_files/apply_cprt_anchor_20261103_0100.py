#!/usr/bin/env python3
"""2026-11-03 01:00 PT (323rd review; renumbered from 322nd by the
numbering-correction commit: the Nov 2 JS-fix iteration already holds
the 322nd slot in the iteration log): CPRT FY2026 anchor adjudication.

Deferred by the 321st review (apply_anchor_promotion_batch_20261102_2100.py):
CPRT's FY2026 proxy (DEF 14A, filed 2026-10-22, acc. 0001193125-26-428904)
lists A. Jayson Adair as Executive Chairman and CEO ($351,386, $1 salary)
alongside former CEO Jeffrey Liaw ($2,064,740), but the filed pay-ratio
disclosure is computed on Liaw (42:1, median $48,661), not on Adair.

Adjudication: the anchor stays Liaw and promotes to his FY2026 figures.
Why this is not a blind promotion to Adair, and not a keep-stale-FY2025:
- Transition timing: announced June 29, 2026; Adair appointed CEO
  effective July 31, 2026, succeeding Liaw, who stepped down and resigned
  from the Board the same day. FY2026 ended July 31, 2026, so Liaw was
  CEO for the whole fiscal year except its last day.
- Filing treatment: the pay-ratio section names "Jeffrey Liaw, former
  chief executive officer" and uses his SCT total ($2,064,740) against
  median $48,661 for 42:1 (2064740/48661 = 42.43, filed 42). The PvP
  footnote states Adair "again became our chief executive officer
  effective July 31, 2026 but is treated as a non-PEO NEO for fiscal
  2026" - Liaw is the FY2026 PEO by the filing's own terms.
- Promoting to Adair ($351,386) while keeping the filed 42:1 ratio, or
  inventing a 7:1 ratio (351386/48661 = 7.22), would both be incoherent
  with the filed disclosure. Promoting to Liaw FY2026 keeps the anchor
  triple (name, total, median, ratio) exactly as filed.
- ceo_tenure unchanged: it tracks the anchor person (Liaw, April 2024),
  and the anchor person does not change. Next promotion (FY2027 proxy)
  must move the anchor to Adair and set tenure to July 2026; that is
  noted in VERIFICATION.md, not done here.

Company-level edits (anchor fields only; exec rows untouched):
- total_compensation: 2,072,692 (Liaw FY2025) -> 2,064,740 (Liaw FY2026)
- pay_ratio: 49 -> 42 (filed)
- median_worker_pay: 42,139 -> 48,661 (filed)
- source: "SEC DEF 14A 2025 - FY2025 CEO" -> "SEC DEF 14A 2026 - FY2026 CEO"
  (321st-review hyphen convention for FY2026-promoted anchors)
- ceo_name unchanged: Jeffrey Liaw
- aggregate_stats + sector_medians recomputed with
  check_metadata_consistency.py section-17 exact semantics (guard-exact
  _anchor_row_for). Top-level legacy scalar fields are NOT recomputed
  (283rd precedent).

Screens run this review (no other repairs needed):
- Anchor-total screen: CPRT was the SOLE company whose anchor total
  disagreed with its own anchor-year exec row (company 2,072,692 vs
  Liaw 2026 row 2,064,740). After this fix the screen is empty.
- Stale-anchor screen: only documented name-variant fallbacks (AMZN
  Andy/Andrew R. Jassy, MET Michel A. Khalaf, ROP Neil/L. Neil Hunn)
  and the VMRK zero-row stub remain.
- Full footing scan: only $1 rounding diffs, documented $2 gaps, and
  the 44 labeled component_mismatch rows (unchanged).
- Pay-ratio band screen: CPRT stays within tolerance before and after
  (old ratio-of-ratios 1.004, new 1.010), so the live counts stay
  118 within / 2 near 2x / 13 near 0.5x / 381 differ, and the js/app.js
  4d fallback copy needs no change.

No exec-total changes -> phantom counter untouched (exec sum delta $0).
"""

import json
import os
import statistics

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(
    REPO, "data",
    "compensation_backup_20261103_0100_pre_cprt_anchor.json",
)


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
            sector_pays.setdefault(c.get("sector", "Unknown"), []).append(
                c["total_compensation"])
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
    c = by["CPRT"]

    # Old-value guards: fail closed if the 321st-deferred state moved.
    assert c["ceo_name"] == "Jeffrey Liaw", c["ceo_name"]
    assert c["total_compensation"] == 2072692, c["total_compensation"]
    assert c["pay_ratio"] == 49, c["pay_ratio"]
    assert c["median_worker_pay"] == 42139, c["median_worker_pay"]
    assert c["fiscal_year"] == 2026, c["fiscal_year"]

    # Promotion target must match an already-stored FY2026 exec row.
    rows = [e for e in c["executives"]
            if e["year"] == 2026 and e["name"] == "Jeffrey Liaw"]
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["total"] == 2064740, row
    assert row["title"] == "Former Chief Executive Officer", row["title"]
    # Exact footing on the anchor row.
    comps = [row[k] for k in ("salary", "bonus", "stock_awards",
                              "option_awards", "non_equity_incentive",
                              "pension_nqdc", "all_other")]
    assert all(v is not None for v in comps)
    assert sum(comps) == row["total"], (sum(comps), row["total"])
    # Filed pay-ratio cross-foot: 2064740/48661 = 42.43 -> filed 42.
    assert round(2064740 / 48661) == 42

    # All three stored FY2026 rows must already be filing-verbatim.
    expected_2026 = {
        "A. Jayson Adair": 351386,
        "Jeffrey Liaw": 2064740,
        "Leah C. Stearns": 3980437,
    }
    stored_2026 = {e["name"]: e["total"] for e in c["executives"]
                   if e["year"] == 2026}
    assert stored_2026 == expected_2026, stored_2026

    exec_total_before = sum(int(round(e.get("total") or 0))
                            for co in d["companies"] for e in co["executives"])

    c["total_compensation"] = 2064740
    c["pay_ratio"] = 42
    c["median_worker_pay"] = 48661
    c["source"] = "SEC DEF 14A 2026 - FY2026 CEO"
    print("CPRT anchor: Liaw 2072692/49/42139 -> 2064740/42/48661")

    recompute_aggregates(d["companies"], d["metadata"])
    print("aggregate_stats:", d["metadata"]["aggregate_stats"])
    print("Industrials:", d["metadata"]["sector_medians"]["Industrials"])

    stamp = ("322nd review (2026-11-03 01:00 PT): CPRT FY2026 anchor "
             "adjudication (321st-review deferral resolved) - anchor stays "
             "Jeffrey Liaw and promotes to his FY2026 figures "
             "($2,064,740 / 42:1 / $48,661) from the 2026-10-22 DEF 14A "
             "(acc. 0001193125-26-428904): Liaw was CEO for FY2026 except "
             "its last day (Adair appointed CEO effective July 31, 2026, "
             "the fiscal year-end date; Liaw stepped down and resigned "
             "from the Board the same day), the filed pay-ratio "
             "disclosure is computed on Liaw, and the PvP footnote "
             "treats Adair as a non-PEO NEO for FY2026, so Liaw is the "
             "FY2026 PEO by the filing's own terms. Promoting to Adair "
             "($351,386) would have broken the filed 42:1 ratio or "
             "required inventing a 7:1 ratio. Anchor-total screen now "
             "empty (CPRT was the sole company whose anchor total "
             "disagreed with its anchor-year row). ceo_tenure unchanged "
             "(tracks anchor person Liaw, April 2024); next promotion "
             "(FY2027 proxy) must move the anchor to Adair with tenure "
             "July 2026. aggregate_stats + sector_medians recomputed "
             "(section-17 semantics); pay-ratio band counts unchanged "
             "(CPRT within tolerance before and after), so the js/app.js "
             "4d fallback copy needs no change.")
    notes = d["metadata"].get("notes", [])
    if not any(isinstance(n, str) and n.startswith("322nd review")
               for n in notes):
        notes.append(stamp)

    exec_total_after = sum(int(round(e.get("total") or 0))
                           for co in d["companies"] for e in co["executives"])
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
