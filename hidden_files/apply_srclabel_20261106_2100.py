#!/usr/bin/env python3
"""368th review (2026-11-06 21:00 PT): stale CEO-source labels on 13 FY2026
(1x FY2024) companies.

Finding: the company-level `source` string ("SEC DEF 14A <proxy-year> -
FY<fiscal-year> CEO") is the CEO-anchor provenance label, and three UI
spots derive the filing-form link label from it (table row link, NEO
panel link, Board Independence source link: js/app.js ~7894, ~10043,
~11013, via /10-K/ test on `source`). Twelve FY2026 anchor promotions
and one FY2024 promotion updated filing_date, filing_url, rows, median
pay and pay ratio but never updated `source`, so:

- 9x DEF 14A vintage stales (BR, CAG, CAH, CTAS, DRI, FDX, GIS, PH,
  TPR): label still reads "SEC DEF 14A 2025 - FY2025 CEO" while the
  anchor total is the FY2026 CEO total from the 2026 proxy. Cosmetic
  vintage lie in the provenance line.
- PG: yearless form "SEC EDGAR DEF 14A - FY2025 CEO" while the anchor
  is the FY2026 total ($18,976,742, Jejurikar) from the 2026-08-28
  DEF 14A. Same class, caught by the FY-vs-proxy_fiscal_year check
  rather than the proxy-year check.
- EA, TECH: label says DEF 14A 2025 but the FY2026 SCT came from a
  10-K/A (batch 10, 2026-10-30): EA 10-K/A filed 2026-07-28 (acc
  0001308179-26-000382), TECH 10-K/A filed 2026-10-28 (acc
  0001140361-26-041062). User-visible bug, not a nit: the NEO panel
  link reads "SEC Filing / View DEF 14A proxy statement on SEC EDGAR"
  and the Board Independence link reads "DEF 14A" for a 10-K/A, because
  the /10-K/ test sees neither "10-K" in `source` nor "10k.htm" in the
  URL (ea2026-10ka.htm / ef20084361_10ka.htm).
- K: label says DEF 14A 2024 FY2023 but the FY2024 anchor ($14,882,161,
  Cahillane) came from the 2025-03-07 10-K/A (acc 0000055067-25-000127,
  batch 10). Same mislabel class (URL k-20241228.htm carries no 10k
  marker either).

Fix: set each `source` to the anchor filing's true form + year + FY,
matching the SKYD precedent ("SEC 10-K/A 2026 - FY2025 CEO") and the
DEF 14A convention ("SEC DEF 14A 2026 - FY2026 CEO"). Every anchor
total is asserted == the stored FY2026 (K: FY2024) CEO SCT row total,
and every filing_date year is asserted == the new label year, before
writing. No NEO rows, totals, medians, ratios or aggregates change.

Also adjudicated in this run (no data change; see iteration log):
- ANSS/DAY/HES/JNPR: stored filing dates match each company's latest
  DEF 14A (2025-04-29 / 2025-03-13 / 2025-04-04 / 2025-04-16); all four
  were acquired in 2025 (Synopsys / Thoma Bravo / Chevron / HPE), so no
  FY2025 proxy will ever file. Final at FY2024, correctly stored.
- IPG: no DEF 14A filed in 2025 (EDGAR submissions confirm; the
  2025-01-30 DEFM14A merger proxy contains no Summary Compensation
  Table - 0 hits for SCT terms in the 2.5MB filing). Omnicom deal
  closed 2025-11-18; IPG stays at FY2023, final.
- VMRK: still no post-merger DEF 14A (AvalonBay/Equity Residential
  merger closed 2026-08-17); the 2026-04-14 DEF 14A on CIK 906107 is
  pre-merger EQR. Stub correctly deferred to the spring-2027 proxy.
- EFTS sweep 2026-10-30..2026-11-06: 60 DEF 14A filings, none from an
  S&P 500 name; COST/ACN/MU/JBL/INTU FY2026 proxies still queued for
  Dec 2026 per batch-10 notes.
- TSLA (queued, NOT fixed here): `source` says 10-K/A while
  filing_url points at the 2026-10-19 DEF 14A (acc 0001104659-26-116700;
  the 10-K/A is the separate 2026-04-30 acc 0001104659-26-053166). The
  NEO panel link therefore reads "SEC 10-K" for a DEF 14A URL. Needs
  SCT verification against the Oct-19 DEF 14A before deciding whether
  to repoint the URL to the 10-K/A or relabel the source to DEF 14A.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(REPO, "data",
                      "compensation_backup_20261106_2100_pre_srclabel.json")

# ticker -> (old source, new source, anchor fiscal year)
FIXES = {
    "BR": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "CAG": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "CAH": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "CTAS": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "DRI": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "FDX": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "GIS": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "PH": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "TPR": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC DEF 14A 2026 — FY2026 CEO", 2026),
    "PG": ("SEC EDGAR DEF 14A — FY2025 CEO", "SEC EDGAR DEF 14A — FY2026 CEO", 2026),
    "EA": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC 10-K/A 2026 — FY2026 CEO", 2026),
    "TECH": ("SEC DEF 14A 2025 — FY2025 CEO", "SEC 10-K/A 2026 — FY2026 CEO", 2026),
    "K": ("SEC DEF 14A 2024 — FY2023 CEO", "SEC 10-K/A 2025 — FY2024 CEO", 2024),
}


def main():
    shutil.copy2(JSON_PATH, BACKUP)
    print("backup:", BACKUP)

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    companies = {c["ticker"]: c for c in data["companies"]}

    for ticker, (old, new, anchor_fy) in sorted(FIXES.items()):
        c = companies[ticker]
        assert c["source"] == old, (ticker, c["source"], old)
        # Anchor total must be the stored CEO SCT row total for the anchor FY.
        rows = [e for e in c["executives"]
                if e["year"] == anchor_fy and e["name"] == c["ceo_name"]]
        assert len(rows) == 1, (ticker, len(rows))
        assert rows[0]["total"] == c["total_compensation"], (
            ticker, rows[0]["total"], c["total_compensation"])
        # Label year must equal the anchor filing's filing year.
        assert c["filing_date"].startswith(str(
            2026 if anchor_fy == 2026 else 2025)), (ticker, c["filing_date"])
        assert c["proxy_fiscal_year"] == anchor_fy, (
            ticker, c["proxy_fiscal_year"], anchor_fy)
        # Form agreement: 10-K/A labels only where data_source is 10-K/A.
        if "10-K/A" in new:
            assert c["data_source"] == "SEC EDGAR 10-K/A", (
                ticker, c["data_source"])
        else:
            assert "DEF 14A" in c["data_source"], (ticker, c["data_source"])
        c["source"] = new
        print(f"  {ticker}: {old!r} -> {new!r} "
              f"(anchor FY{anchor_fy} CEO ${rows[0]['total']:,})")

    data["last_updated"] = "2026-11-06"
    data["metadata"]["last_updated"] = "2026-11-06"
    data["metadata"]["last_dq_repair"] = "2026-11-06"
    data["metadata"]["notes"].append(
        "368th review 2026-11-06: stale CEO-source labels repaired on 13 "
        "companies. 9 DEF 14A vintage stales (BR, CAG, CAH, CTAS, DRI, FDX, "
        "GIS, PH, TPR) and PG (yearless form) said FY2025 while the anchor "
        "total is the FY2026 CEO total from the 2026 proxy; EA/TECH/K said "
        "DEF 14A while their anchors came from 10-K/As (EA 2026-07-28 acc "
        "0001308179-26-000382, TECH 2026-10-28 acc 0001140361-26-041062, K "
        "2025-03-07 acc 0000055067-25-000127), which mislabeled the NEO "
        "panel and Board Independence filing links as DEF 14A. All 13 "
        "anchor totals asserted == stored CEO SCT row totals; no NEO rows "
        "or aggregates changed. Laggard adjudication: ANSS/DAY/HES/JNPR "
        "acquired-final at FY2024; IPG has no 2025 DEF 14A and its DEFM14A "
        "carries no SCT (final at FY2023); VMRK still awaits its first "
        "post-merger proxy; no new FY2026 proxies in the 2026-10-30..11-06 "
        "EFTS sweep. TSLA source-vs-URL form question queued (needs SCT "
        "verification vs the 2026-10-19 DEF 14A)."
    )

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("wrote", JSON_PATH)
    print("fixed:", len(FIXES))


if __name__ == "__main__":
    main()
