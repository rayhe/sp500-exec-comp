#!/usr/bin/env python3
"""2026-11-01 13:00 PT DQ batch (305th review): missing-NEO-row restoration.

Executes the 304th review's candidate #1. The 2026 DEF 14A SCTs (raw filings at
goal hidden_files/dq_20261101_1030/, fetched and parsed by the 304th run) show
anchor-year NEO rows the dataset does not have:

- VZ FY2025 SCT (vz014688_def14a.htm, 6 NEOs): dataset has 4; MISSING:
  Sowmyanarayan Sampath (Former EVP and Group CEO - Verizon Consumer,
  $18,901,142) and Kyle Malady (EVP and Group CEO - Verizon Business,
  $12,762,860). The 4 stored rows (Schulman/Skiadas/Venkatesh/Vestberg)
  re-verified filing-verbatim this run: all 8 components match the SCT
  exactly, zero drift.
- KVUE FY2025 SCT (kvue-20260408.htm, 7 NEOs): dataset has 6; MISSING:
  Paul Ruh (Former Chief Financial Officer, $3,214,020). The 6 stored rows
  foot and match the SCT exactly, zero drift.

All 3 new rows are anchor-year (2025) rows, appended at the END of each
company's executives list per the new-row convention, all 12 keys with
explicit zeros (batch-4/5/6/7/8/9/10 convention), _total_source "verified"
(matching the 274th-review fy2026-enrichment precedent, so no LABEL_TO_KEY
guard edit is needed; VERIFIED_KEYS buckets them into verified_total).

Company aggregates recomputed anchor-year scoped:
- VZ: total_neo_compensation 88,924,854 -> 120,588,856; neo_count 4 -> 6
- KVUE: total_neo_compensation 44,895,950 -> 48,109,970; neo_count 6 -> 7

metadata: description -> "518 companies, 7305 NEO records, 517 companies
enriched"; data_quality.verified 5842 -> 5845; verified_total 7257 -> 7260
(7260/7305 = 99.38% -> 99.4% headline, one-decimal boundary unchanged);
last_dq_repair stays 2026-11-01 (already today's date); top-level last_updated
stays 2026-11-01 (DQ-batch convention).

phantom_record: restored +$34,878,022 filing-verbatim (negative delta per the
phantom convention) -> record_batch() bumps batches 77 -> 78; the batch
script also re-syncs the dataq-phantom-block static fallback in js/app.js
(section 4f requirement).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
BACKUP_PATH = os.path.join(HERE, "compensation_backup_20261101_1300_pre_missingneo.json")

STAMP = "2026-11-01 13:00 PT"
SRC = "verified"

# (ticker, name, title, year, salary, bonus, stock, options, neip, pension, all_other, total)
NEW_ROWS = [
    ("VZ", "Sowmyanarayan Sampath",
     "Former Executive Vice President and Group CEO \u2013 Verizon Consumer",
     2025, 1200000, 0, 15000015, 0, 2400000, 1277, 299850, 18901142),
    ("VZ", "Kyle Malady",
     "Executive Vice President and Group CEO \u2013 Verizon Business",
     2025, 1100000, 0, 9750061, 0, 1650000, 5268, 257531, 12762860),
    ("KVUE", "Paul Ruh",
     "Former Chief Financial Officer",
     2025, 324007, 0, 1351566, 550800, 0, 0, 987647, 3214020),
]

EXPECTED_PRE_COUNT = 7302


def build_row(spec):
    (ticker, name, title, year, salary, bonus, stock, options, neip,
     pension, all_other, total) = spec
    # explicit key mapping per ticker schema, never positional zip
    row = {
        "name": name,
        "title": title,
        "year": year,
        "salary": salary,
        "bonus": bonus,
        "stock_awards": stock,
        "option_awards": options,
        "non_equity_incentive": neip,
        "pension_nqdc": pension,
        "all_other": all_other,
        "total": total,
        "_total_source": SRC,
    }
    footing = (salary + bonus + stock + options + neip + pension + all_other)
    assert footing == total, f"{name}: components sum {footing} != {total}"
    return row


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    companies = data["companies"]
    pre_count = sum(len(c.get("executives", [])) for c in companies)
    assert pre_count == EXPECTED_PRE_COUNT, f"pre count {pre_count} != {EXPECTED_PRE_COUNT}"

    for spec in NEW_ROWS:
        ticker = spec[0]
        comp = next(c for c in companies if c["ticker"] == ticker)
        existing = {(e["name"], e["year"]) for e in comp["executives"]}
        assert (spec[1], spec[3]) not in existing, f"duplicate row {spec[1]} {spec[3]}"
        comp["executives"].append(build_row(spec))

    # company aggregates: anchor-fiscal-year scoped
    agg_expect = {"VZ": (120588856, 6), "KVUE": (48109970, 7)}
    for ticker, (want_total, want_n) in agg_expect.items():
        comp = next(c for c in companies if c["ticker"] == ticker)
        fy = comp["fiscal_year"]
        yr_rows = [e for e in comp["executives"] if e["year"] == fy]
        got_total = sum(e["total"] for e in yr_rows)
        got_n = len(yr_rows)
        assert got_total == want_total, f"{ticker} total_neo {got_total} != {want_total}"
        assert got_n == want_n, f"{ticker} neo_count {got_n} != {want_n}"
        comp["total_neo_compensation"] = got_total
        comp["neo_count"] = got_n

    post_count = sum(len(c.get("executives", [])) for c in companies)
    assert post_count == EXPECTED_PRE_COUNT + len(NEW_ROWS), post_count

    meta = data["metadata"]
    dq = meta["data_quality"]
    dq["verified"] = dq["verified"] + len(NEW_ROWS)
    dq["verified_total"] = dq["verified_total"] + len(NEW_ROWS)
    assert dq["verified_total"] == 7260, dq["verified_total"]
    meta["description"] = "518 companies, 7305 NEO records, 517 companies enriched"
    assert meta["last_dq_repair"] == "2026-11-01"
    assert data["last_updated"] == "2026-11-01"

    # canonical serialization: indent=1, ensure_ascii=False, trailing newline
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")

    # phantom campaign counter: restored rows = negative delta
    sys.path.insert(0, HERE)
    import phantom_record
    delta = phantom_record.record_batch(
        pre_path=BACKUP_PATH,
        data_path=JSON_PATH,
        stamp=STAMP,
    )
    print(f"phantom delta: ${delta:,}")
    restored = 18901142 + 12762860 + 3214020
    assert delta == -restored, f"phantom delta {delta} != -{restored}"
    print(f"rows: {pre_count} -> {post_count} (+{len(NEW_ROWS)}); "
          f"VZ total_neo 120,588,856 x6; KVUE total_neo 48,109,970 x7")


if __name__ == "__main__":
    main()
