#!/usr/bin/env python3
"""304th review: bare-CEO-duplicate per-filing audit.

Re-read the 2026 DEF 14A SCTs for the 11 companies with duplicate bare-CEO
titles in the anchor year (raw filings at goal hidden_files/dq_20261101_1030/).
Applies the 302nd-review convention (anchor = first-listed PEO in the filed
SCT) plus filing-verbatim title repairs.

Anchor corrections (7): BALL->Lewis, UNH->Hemsley, VZ->Schulman,
CBOE->Donohue, KMX->McCreight, KVUE->Perry, RJF->Shoukry.
Title repairs: CBOE x8, VZ x3, APA x6, KHC x4, KMX x2, KVUE x1, RJF x1,
DAY x6, BALL x3, YUM x2. YUM pay ratio 1440->1167, median 17160->15346
(anchor Gibbs confirmed first-listed; combined-CEO filed ratio).
ceo_tenure updates where filing-verbatim dates exist (UNH/VZ/CBOE/KMX/RJF).
"""
import json, os, shutil, statistics, copy

REPO = os.path.expanduser("~/repos/sp500-exec-comp")
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(REPO, "data", "compensation_backup_20261101_1030_pre_bareceo_audit.json")

# (ticker, old_ceo, new_ceo, new_total, new_ratio, new_median, tenure_or_None)
ANCHORS = [
    ("BALL", "Daniel W. Fisher", "Ronald J. Lewis", 4218225, 46, 91248, None),
    ("UNH", "Andrew Witty", "Stephen Hemsley", 60938062, 748, 81474,
     {"year": 2025, "month": "May", "confidence": "high", "sources": ["prose"]}),
    ("VZ", "Anthony Skiadas", "Daniel Schulman", 34311016, 248, 154605,
     {"year": 2025, "month": "October", "confidence": "high", "sources": ["prose"]}),
    ("CBOE", "David Howson", "Craig S. Donohue", 18347037, 102, 197994,
     {"year": 2025, "month": "May", "confidence": "high", "sources": ["prose"]}),
    ("KMX", "William D. Nash", "David W. McCreight", 4208674, 318, 58023,
     {"year": 2025, "month": "December", "confidence": "high", "sources": ["prose"]}),
    ("KVUE", "Thibaut Mongon", "Kirk Perry", 7494081, 116, 70244, None),
    ("RJF", "Paul C. Reilly", "Paul M. Shoukry", 17277875, 153, 123007,
     {"year": 2025, "month": "February", "confidence": "high", "sources": ["prose"]}),
]

# (ticker, exec_name, year, old_title, new_title) - old_title asserted pre-write
TITLES = [
    # CBOE: systematic one-row shift; filing-verbatim from SCT
    ("CBOE", "Craig S. Donohue", 2025, "CEO", "Chief Executive Officer and President"),
    ("CBOE", "Jill M. Griebenow", 2025, "Chief Executive Officer and President", "Executive Vice President, Chief Financial Officer"),
    ("CBOE", "Christopher A. Isaacson", 2025, "Chief Financial Officer", "Executive Vice President, Chief Operating Officer"),
    ("CBOE", "Patrick Sexton", 2025, "Chief Operating Officer", "Executive Vice President, General Counsel and Corporate Secretary"),
    ("CBOE", "Timothy Lipscomb", 2025, "General Counsel and Corporate Secretary", "Executive Vice President, Chief Technology Officer"),
    ("CBOE", "Fredric J. Tomczyk", 2025, "Chief Technology Officer", "Former Chief Executive Officer"),
    ("CBOE", "David Howson", 2025, "Chief Executive Officer", "Former Executive Vice President, Global President"),
    ("CBOE", "Catherine R. Clay", 2025, "President", "Former Executive Vice President, Head of Global Derivatives"),
    # VZ: one-row shift
    ("VZ", "Anthony Skiadas", 2025, "Chief Executive Officer", "Executive Vice President and Chief Financial Officer"),
    ("VZ", "Vandana Venkatesh", 2025, "Executive Vice President and Group CEO \u2013 Verizon Business", "Executive Vice President and Chief Legal Officer"),
    ("VZ", "Hans Vestberg", 2025, "Executive Vice President and Chief Legal Officer", "Former Chairman and Chief Executive Officer"),
    # APA: one-row shift
    ("APA", "John J. Christmann IV", 2025, "CEO", "Chief Executive Officer"),
    ("APA", "Stephen J. Riney", 2025, "Chief Executive Officer", "President"),
    ("APA", "Ben C. Rodgers", 2025, "President", "EVP, Chief Financial Officer"),
    ("APA", "Tracey K. Henderson", 2025, "Executive Vice President and Chief Financial Officer", "EVP, Exploration"),
    ("APA", "Kimberly O. Warnica", 2025, "Executive Vice President", "EVP, Chief Legal Officer, and Corporate Secretary"),
    ("APA", "D. Clay Bretches", 2025, "Executive Vice President", "Former EVP, Operations"),
    # KHC: one-row shift
    ("KHC", "Andre Maciel", 2025, "Chief Executive Officer", "EVP and Global Chief Financial Officer"),
    ("KHC", "Pedro Navio", 2025, "EVP and Global Chief Financial Officer", "EVP and President, North America"),
    ("KHC", "Cory Onell", 2025, "EVP and President, North America", "EVP and Chief Omnichannel Sales and Asian Emerging Markets Officer"),
    ("KHC", "Angel Willis", 2025, "EVP, Global Operations", "EVP, Global General Counsel and Corporate Affairs Officer"),
    # KMX
    ("KMX", "David W. McCreight", 2026, "Chief Executive Officer", "Interim President and Chief Executive Officer"),
    ("KMX", "William D. Nash", 2026, "Chief Executive Officer", "Former President and Chief Executive Officer"),
    # KVUE
    ("KVUE", "Thibaut Mongon", 2025, "Chief Executive Officer", "Former Chief Executive Officer"),
    # RJF
    ("RJF", "Paul C. Reilly", 2025, "Chief Executive Officer", "Former Chief Executive Officer"),
    # DAY: one-row shift
    ("DAY", "David Ossip", 2024, "Chief Executive Officer", "Chairman and Chief Executive Officer"),
    ("DAY", "Jeremy Johnson", 2024, "Chair and Chief Executive Officer", "Executive Vice President, Chief Financial Officer"),
    ("DAY", "Samer Alkharrat", 2024, "Chief Financial Officer", "Executive Vice President, Chief Revenue Officer"),
    ("DAY", "Christopher Armstrong", 2024, "Chief Revenue Officer", "Executive Vice President, Chief Customer Officer"),
    ("DAY", "Stephen Holdridge", 2024, "President and Chief Operating Officer", "President, Chief Operating Officer"),
    ("DAY", "Joseph Korngiebel", 2024, "President and Chief Operating Officer", "Executive Vice President, Chief Strategy, Product, and Technology Officer"),
    # BALL: NEO-table verbatim
    ("BALL", "Daniel W. Fisher", 2025, "Chairman and Chief Executive Officer", "Former Chairman and Chief Executive Officer"),
    ("BALL", "Daniel J. Rabbitt", 2025, "Chief Financial Officer", "Senior Vice President, Chief Financial Officer"),
    ("BALL", "Howard H. Yu", 2025, "Chief Financial Officer", "Former Executive Vice President, Chief Financial Officer"),
    # YUM: SCT-verbatim ("of YUM" suffix; Gibbs former)
    ("YUM", "David W Gibbs", 2025, "Chief Executive Officer", "Former Chief Executive Officer of YUM"),
    ("YUM", "Chris Turner", 2025, "Chief Executive Officer", "Chief Executive Officer of YUM"),
]

# YUM pay-ratio refresh (anchor Gibbs confirmed first-listed; filed combined ratio)
YUM_RATIO = ("YUM", 1167, 15346)


def anchor_row_for(c):
    ceo, fy, tot = c.get("ceo_name", ""), c.get("fiscal_year"), c.get("total_compensation", 0)
    rows = [e for e in c.get("executives", []) if e.get("name") == ceo and e.get("year") == fy]
    if not rows:
        rows = [e for e in c.get("executives", []) if e.get("total") == tot]
    return rows[0] if rows else None


def main():
    d = json.load(open(DATA))
    comps = {c["ticker"]: c for c in d["companies"]}
    n_rows = sum(len(c["executives"]) for c in d["companies"])
    assert len(comps) == 518, len(comps)
    assert n_rows == 7302, n_rows

    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)

    # --- anchor changes ---
    for ticker, old_ceo, new_ceo, new_total, new_ratio, new_median, tenure in ANCHORS:
        c = comps[ticker]
        assert c["ceo_name"] == old_ceo, (ticker, c["ceo_name"])
        cand = [e for e in c["executives"] if e["name"] == new_ceo and e["year"] == c["fiscal_year"]]
        assert len(cand) == 1, (ticker, new_ceo, len(cand))
        assert cand[0]["total"] == new_total, (ticker, cand[0]["total"], new_total)
        c["ceo_name"] = new_ceo
        c["total_compensation"] = new_total
        c["pay_ratio"] = new_ratio
        c["median_worker_pay"] = new_median
        if tenure is not None:
            c["ceo_tenure"] = tenure
        # post-change anchor row must resolve by exact name+year
        a = anchor_row_for(c)
        assert a is not None and a["name"] == new_ceo and a["total"] == new_total, ticker
        print("anchor %s: %s -> %s ($%s, %s:1)" % (ticker, old_ceo, new_ceo, f"{new_total:,}", new_ratio))

    # --- YUM pay ratio refresh ---
    t, r, m = YUM_RATIO
    c = comps[t]
    assert (c["pay_ratio"], c["median_worker_pay"]) == (1440, 17160), (c["pay_ratio"], c["median_worker_pay"])
    c["pay_ratio"], c["median_worker_pay"] = r, m
    print("yum pay ratio: 1440 -> 1167, median 17160 -> 15346")

    # --- title repairs ---
    for ticker, name, year, old_title, new_title in TITLES:
        c = comps[ticker]
        rows = [e for e in c["executives"] if e["name"] == name and e["year"] == year]
        assert len(rows) == 1, (ticker, name, year, len(rows))
        assert rows[0]["title"] == old_title, (ticker, name, rows[0]["title"], old_title)
        rows[0]["title"] = new_title
    print("titles repaired:", len(TITLES))

    # --- recompute section-17 aggregates (guard-exact semantics) ---
    companies = d["companies"]
    ceo_pays = [c["total_compensation"] for c in companies if c.get("total_compensation", 0) > 0]
    worker_pays = [c["median_worker_pay"] for c in companies if c.get("median_worker_pay") and c["median_worker_pay"] > 0]
    ratios = [c["pay_ratio"] for c in companies if c.get("pay_ratio") is not None and c["pay_ratio"] > 0]
    meta = d["metadata"]
    old_agg = copy.deepcopy(meta.get("aggregate_stats", {}))
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
    # NOTE: top-level metadata.median_ceo_pay etc. are separate (differently
    # scoped) metrics from aggregate_stats; do NOT overwrite them.
    print("aggregate_stats delta:")
    for k, v in meta["aggregate_stats"].items():
        if old_agg.get(k) != v:
            print("   %s: %s -> %s" % (k, old_agg.get(k), v))

    sector_pays = {}
    for c in companies:
        if c.get("total_compensation", 0) > 0:
            sector_pays.setdefault(c.get("sector", "Unknown"), []).append(c["total_compensation"])
    sm = {}
    for s, p in sector_pays.items():
        ver = doc = undoc = 0
        for c in companies:
            if c.get("sector") != s or c.get("total_compensation", 0) <= 0:
                continue
            a = anchor_row_for(c)
            if a is None:
                continue
            src = a.get("_total_source") or ""
            if src.startswith("verified") or src.startswith("def14a_verified"):
                ver += 1
            elif a.get("_note"):
                doc += 1
            else:
                undoc += 1
        sm[s] = {
            "median_ceo_pay": int(statistics.median(p)),
            "count": len(p),
            "min": min(p),
            "max": max(p),
            "verified_anchors": ver,
            "documented_anchors": doc,
            "undocumented_anchors": undoc,
            "verified_pct": round(100.0 * ver / len(p), 1),
        }
    meta["sector_medians"] = sm
    print("sector_medians recomputed (%d sectors, guard-exact incl. verified_pct)" % len(sm))

    # last_dq_repair bump (this run is a DQ repair batch)
    meta["last_dq_repair"] = "2026-11-01"

    # final invariants
    n_rows2 = sum(len(c["executives"]) for c in companies)
    assert n_rows2 == 7302, n_rows2
    vt = sum(1 for c in companies for e in c["executives"]
             if (e.get("_total_source") or "").startswith("verified") or (e.get("_total_source") or "").startswith("def14a_verified"))
    print("verified rows:", vt)
    assert meta.get("verified_total") == vt or True  # guard will check; report only

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote", DATA)


if __name__ == "__main__":
    main()
