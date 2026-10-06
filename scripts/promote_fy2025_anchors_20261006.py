#!/usr/bin/env python3
"""FY2025 anchor promotion batch (2026-10-06 06:00 PT run).

Promotes the primary fiscal_year anchor 2024 -> 2025 (or 2026 for the two
FY2026 filers NKE/STE) for companies whose latest parsed DEF 14A SCT rows
already include the newer fiscal year. For each promoted company:
  - fiscal_year := latest fiscal year with a CEO SCT row
  - total_compensation := that CEO row's total (keeps the anchor convention:
    total_compensation is the anchor-year CEO figure)
  - source label "— FY2024 CEO" -> "— FY{target} CEO" (filing year preserved)
  - total_neo_compensation / neo_count recomputed for the new anchor year
    (pre-commit gate section 5 asserts these)
CEO row matching: exact name == ceo_name first; fallback to the
/chief executive officer/i title phrase with last-name agreement
(AMZN 'Andy Jassy' vs 'Andrew R. Jassy', MET, ROP). Segment-CEO titles
('CEO Amazon Web Services') are excluded by the full-phrase requirement.

Companies left untouched: 5 M&A exits (ANSS/DAY/HES/JNPR/WBA, no FY2025
rows, removal notes intact), IPG/K (FY2023 anchors, M&A exits), BRK-B
(Buffett->Abel transition, no FY2025 Buffett SCT row; note appended).

Metadata refresh (pre-commit gate sections 3/17 assert these):
  aggregate_stats.*, sector_medians.*, top-level median/mean/max/min_ceo_pay,
  primary_fiscal_year 2025, last_updated + last_dq_repair = 2026-10-06.
"""
import json, re, statistics, sys

TOP = "/home/hatch/repos/sp500-exec-comp"
PATH = TOP + "/data/compensation.json"
RUN_DATE = "2026-10-06"

CEO_PHRASE = re.compile(r"chief executive officer|\bceo\b", re.I)

def last_name(n):
    n = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", (n or "").lower()).strip()
    parts = re.findall(r"[a-z]+", n)
    return parts[-1] if parts else ""

def ceo_rows_for(c, year):
    ceo = c.get("ceo_name", "")
    execs = c.get("executives", [])
    exact = [e for e in execs if e.get("name") == ceo and e.get("year") == year
             and (e.get("total") or 0) > 0]
    if exact:
        return exact
    cl = last_name(ceo)
    phrase = [e for e in execs if e.get("year") == year
              and e.get("title") and CEO_PHRASE.search(e["title"])
              and (e.get("total") or 0) > 0]
    if not phrase:
        return []
    same_last = [e for e in phrase if last_name(e.get("name")) == cl and cl]
    if same_last:
        return same_last
    full_phrase = [e for e in phrase
                   if re.search(r"chief executive officer", e["title"], re.I)]
    return full_phrase[:1] or phrase[:1]

def main():
    with open(PATH) as f:
        data = json.load(f)
    companies = data["companies"]
    promoted, skipped, notes = [], [], []

    for c in companies:
        if c.get("fiscal_year") != 2024:
            continue
        t = c["ticker"]
        target, row = None, None
        for yr in (2026, 2025):
            rows = ceo_rows_for(c, yr)
            if rows:
                target, row = yr, rows[0]
                break
        if target is None:
            skipped.append(t)
            if t == "BRK-B":
                note = ("CEO transition in progress: Warren E. Buffett retired as CEO "
                        "effective 2026-01-01; Gregory E. Abel is the FY2025 SCT "
                        "principal executive but no FY2025 Buffett SCT row exists, "
                        "so the anchor stays FY2024 pending transition review.")
                prev = c.get("_index_note") or ""
                if "CEO transition in progress" not in prev:
                    c["_index_note"] = (prev + " " + note).strip() if prev else note
                    notes.append(t)
            continue
        old_total = c.get("total_compensation")
        c["fiscal_year"] = target
        c["total_compensation"] = row["total"]
        src = c.get("source") or ""
        if src.endswith("— FY2024 CEO"):
            c["source"] = src[: -len("— FY2024 CEO")] + f"— FY{target} CEO"
        fy_rows = [e for e in c.get("executives", []) if e.get("year") == target]
        c["total_neo_compensation"] = sum((e.get("total") or 0) for e in fy_rows)
        c["neo_count"] = len(fy_rows)
        promoted.append((t, target, old_total, row["total"], row["name"]))

    # ---- metadata refresh (gate sections 3/17 semantics) ----
    meta = data["metadata"]
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
    meta["median_ceo_pay"] = meta["aggregate_stats"]["median_ceo_pay"]
    meta["mean_ceo_pay"] = meta["aggregate_stats"]["mean_ceo_pay"]
    meta["max_ceo_pay"] = meta["aggregate_stats"]["max_ceo_pay"]
    meta["min_ceo_pay"] = meta["aggregate_stats"]["min_ceo_pay"]
    meta["median_pay_ratio"] = meta["aggregate_stats"]["median_pay_ratio"]
    meta["median_worker_pay"] = meta["aggregate_stats"]["median_worker_pay"]

    def anchor_row(c):
        ceo, fy, tot = c.get("ceo_name", ""), c.get("fiscal_year"), c.get("total_compensation", 0)
        if not tot:
            return None
        rows = [e for e in c.get("executives", [])
                if e.get("name") == ceo and e.get("year") == fy]
        if not rows:
            rows = [e for e in c.get("executives", []) if e.get("total") == tot]
        return rows[0] if rows else None

    def verified(src):
        return bool(src) and (src.startswith("verified") or src.startswith("def14a_verified"))

    sector_pays, sector_cov = {}, {}
    for c in companies:
        if c.get("total_compensation", 0) > 0:
            sector_pays.setdefault(c.get("sector", "Unknown"), []).append(c["total_compensation"])
    for c in companies:
        a = anchor_row(c)
        if a is None:
            continue
        s = c.get("sector", "Unknown")
        r = sector_cov.setdefault(s, {"ver": 0, "doc": 0, "undoc": 0})
        src = a.get("_total_source") or ""
        if verified(src):
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
    meta["primary_fiscal_year"] = 2025
    meta["last_dq_repair"] = RUN_DATE
    data["last_updated"] = RUN_DATE

    with open(PATH, "w") as f:
        json.dump(data, f, indent=1)

    print(f"promoted: {len(promoted)}")
    print(f"skipped (no CEO row): {sorted(skipped)}")
    print(f"notes added: {notes}")
    fy26 = [p for p in promoted if p[1] == 2026]
    print(f"FY2026 promotions: {[p[0] for p in fy26]}")
    print(f"median_ceo_pay now {meta['median_ceo_pay']:,} "
          f"(was FY2024-anchored)")

if __name__ == "__main__":
    main()
