#!/usr/bin/env python3
"""Full-roster DEF 14A sweep for the S&P 500 Executive Compensation Tracker.

For every company in data/compensation.json, fetch its CIK submissions
JSON from data.sec.gov and take the most recent DEF 14A. Flag companies
where EDGAR's latest DEF 14A filingDate is NEWER than the stored
filing_date: those are proxies filed since the last enrichment batch
that the data does not yet carry. Each flag is classified mechanically:

  * same-accession: the EDGAR accession matches the accession in the
    stored filing_url (dashes stripped) -- the stored date is the
    document/cover date and EDGAR's filingDate is the acceptance date
    (+1/+2 days). Same filing, not a new proxy. This is the systematic
    recording convention, not drift.
  * new-accession: a genuinely different filing -- needs a human
    review (verify whether the SCT was already used, e.g. TSLA below).
  * no-stored-filing: the company carries no filing_date (VMRK).
  * no-def14a: EDGAR lists no DEF 14A for the CIK at all.

Known non-flags (537th review, 2026-11-20 -- re-check before
re-litigating):
  * TSLA 2026-10-19 DEF 14A (acc. 0001104659-26-116700) bears the
    FY2025 SCT; the 433rd review (2026-11-12) verified all 9 stored
    rows byte-identical against it. Company-level source STAYS the
    10-K/A per the 276th review's deliberate decision, so the sweep
    will keep flagging it as new-accession by design.
  * VMRK: no post-merger DEF 14A; EDGAR latest remains the pre-merger
    EQR 2026-04-14 proxy (acc. 0001193125-26-155007). VMRK shares CIK
    906107 with EQR (post-merger successor); EQR's own stored date
    matches that proxy, so EQR does not flag.
  * BX / ERIE / SKYD / FDXF: no DEF 14A on EDGAR (BX and KKR have
    none with comp tables; ERIE files DEF 14C; SKYD/FDXF never filed
    one). FOX/FOXA share CIK 0001754301 (known exec-name collision);
    the sweep fetches that CIK twice, once per ticker -- harmless.
  * The 7 same-accession quirks (document date vs acceptance date):
    CHRW, FTV, HON, IRM, MDT, ARES, XYZ.

537th-run result (2026-11-20 ~21:00 PT): 518 companies swept, 0
errors, 9 flags, 0 genuinely new filings -- 7 same-accession quirks,
TSLA new-accession already verified (433rd), VMRK no-stored-filing
known. Enrichment current through 2026-11-20.

Read-only against the repo (writes only the result JSON, default
goal hidden_files/sweep_def14a_latest.json). Rate: sequential,
~0.15s spacing, UA per the task body (SEC limit 10 req/s).

Usage:
  python3 scripts/sweep_def14a_full_roster.py [--out PATH]
"""
import argparse
import json
import os
import re
import time
import urllib.request

UA = "Kit/1.0 (factoryfactorykit@gmail.com)"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOAL_HIDDEN = os.path.join(
    os.environ.get("HOME", ""), "workspace", "goals",
    "s-p-500-executive-compensation-tracker", "hidden_files")
DEFAULT_OUT = os.path.join(GOAL_HIDDEN, "sweep_def14a_latest.json")

ACC_RE = re.compile(r"(\d{10})-(\d{2})-(\d{6})")


def stored_accession(filing_url):
    """Accession embedded in the stored filing_url, dashes stripped."""
    if not filing_url:
        return None
    m = ACC_RE.search(filing_url)
    if m:
        return "".join(m.groups())
    # Fallback: the /data/<cik>/<accession>/ path segment.
    parts = [p for p in filing_url.split("/") if p]
    for p in parts:
        if re.fullmatch(r"\d{18}", p):
            return p
    return None


def classify(row):
    edgar = row["edgar_latest_def14a"]
    if edgar is None:
        return "no-def14a"
    if not row["stored_filing_date"]:
        return "no-stored-filing"
    if not row["newer"]:
        return "current"
    edgar_acc = edgar["accession"].replace("-", "")
    if stored_accession(row.get("filing_url")) == edgar_acc:
        return "same-accession"
    return "new-accession"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    data = json.load(open(os.path.join(REPO, "data", "compensation.json"),
                          encoding="utf-8"))
    companies = data["companies"]

    results = []
    errors = []
    for i, c in enumerate(companies):
        cik = str(c.get("cik") or "").strip()
        if not cik:
            errors.append((c.get("ticker"), "no CIK"))
            continue
        padded = cik.zfill(10)
        url = "https://data.sec.gov/submissions/CIK%s.json" % padded
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                sub = json.load(r)
        except Exception as exc:  # noqa: BLE001 - record and move on
            errors.append((c.get("ticker"), "%s: %s"
                           % (type(exc).__name__, exc)))
            time.sleep(0.15)
            continue
        recent = sub.get("filings", {}).get("recent", {})
        latest = None
        for form, dt, acc in zip(recent.get("form", []),
                                 recent.get("filingDate", []),
                                 recent.get("accessionNumber", [])):
            if form == "DEF 14A":
                latest = {"date": dt, "accession": acc}
                break
        stored = c.get("filing_date") or ""
        row = {
            "ticker": c.get("ticker"),
            "cik": cik,
            "stored_filing_date": stored,
            "stored_proxy_fy": c.get("proxy_fiscal_year"),
            "filing_url": c.get("filing_url") or "",
            "edgar_latest_def14a": latest,
            "newer": bool(latest and latest["date"] > stored),
        }
        row["class"] = classify(row)
        results.append(row)
        if (i + 1) % 100 == 0:
            print("%d/518 swept, %d flags so far"
                  % (i + 1, sum(1 for r in results if r["newer"])),
                  flush=True)
        time.sleep(0.15)

    flags = [r for r in results if r["newer"]]
    print("done: %d companies, %d flags, %d errors"
          % (len(results), len(flags), len(errors)))
    for r in flags:
        print("FLAG %s: %s stored %s -> EDGAR %s (%s)"
              % (r["class"], r["ticker"], r["stored_filing_date"] or "-",
                 r["edgar_latest_def14a"]["date"],
                 r["edgar_latest_def14a"]["accession"]))
    for t, e in errors:
        print("ERROR:", t, e)
    json.dump({"results": results, "errors": errors},
              open(args.out, "w"), indent=1)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
