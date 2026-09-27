#!/usr/bin/env python3
"""DQ 2026-09-26 23:30 PT: repair LDOS salary-drop column-shift family (3 NEO rows).

Detection: the 19:30 PT bullseye sweep (d = 2*all_other - total == adjacent-year
salary within 1%) hit LDOS Christopher R. Cage 2024. Filing-by-filing expansion
per the 15:30/19:30 precedent found the same corruption family is bigger than
the heuristic hit: 3 rows in the LDOS 2026 DEF 14A SCT (acc. 0001336920-26-000138,
filed 2026-03-19, FY2025 proxy with FY2024/FY2023 SCT rows).

Corruption class: salary-cell drop on FY2023/FY2024 rows, every component shifted
one column left (filing.bon->stored.sal, filing.stk->stored.bon,
filing.opt->stored.stk, filing.neip->stored.opt, filing.ao->stored.neip,
filing.total->stored.all_other), stored total recomputed ~2x phantom.
Bell 2023 bullseye is exact too (2*9,187,541 - 17,557,774 = 817,308 = filing sal)
but the adjacent-year salary (Bell 2024 = 1,306,539) was too far for the 1%
heuristic, which is why only Cage 2024 tripped it.

Repaired filing-verbatim (raw HTML table cells, digit-by-digit):
- Bell 2023: sal 817,308 / bon 1,450,000 / stk 3,468,492 / opt 900,004 /
  neip 2,538,000 / ao 13,737 / total 9,187,541 (foots $0)
- Cage 2024: sal 807,003 / bon 5,000 / stk 1,781,048 / opt 392,513 /
  neip 1,465,595 / ao 43,562 / total 4,494,721 (foots $0)
- Antal 2024: sal 438,462 / bon 255,000 / stk 1,643,023 / opt 240,033 /
  neip 1,120,200 / ao 40,651 / total 3,737,369 (foots $0)

Also verified CLEAN (stored == filing verbatim, untouched): Bell 2025/2024,
Cage 2025/2023, Gruensfelder 2025, Antal 2025, Fautsch 2025.

The parallel BE bullseye (Daniel Berenbaum 2025) was CLEARED as a false
positive: the BE 2026 DEF 14A SCT (acc. 0001628280-26-024237, filed
2026-04-08) prints Berenbaum 2025 exactly as stored (sal 218,942, ao 584,083
incl. $575,000 severance per fn 10, total 803,025; separated May 1, 2025).
All other BE SCT rows also match stored verbatim (incl. Joshi 2024 with the
footnote-8 scrivener's-error correction 32,423/8,058,211, and Kurzymski 2025
whose +$339,200 filing-side gap was already documented 2026-09-25).
BE evidence preserved in goal hidden_files/dq_20260926_2330/.

Idempotent: pre-write assertions on the exact stored values abort on drift;
post-repair footing assertions require $0 for all 3 rows.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")

FILING_URL = ("https://www.sec.gov/Archives/edgar/data/1336920/"
              "000133692026000138/ldos-20260319.htm")

REPAIRS = [
    # (ticker, name, year, expected stored values, filing-verbatim values)
    ("LDOS", "Thomas A. Bell", 2023,
     {"salary": 1450000, "bonus": 3468492, "stock_awards": 900004,
      "option_awards": 2538000, "non_equity_incentive": 13737,
      "pension_nqdc": 0, "all_other": 9187541, "total": 17557774,
      "_total_source": "verified"},
     {"salary": 817308, "bonus": 1450000, "stock_awards": 3468492,
      "option_awards": 900004, "non_equity_incentive": 2538000,
      "pension_nqdc": 0, "all_other": 13737, "total": 9187541}),
    ("LDOS", "Christopher R. Cage", 2024,
     {"salary": 5000, "bonus": 1781048, "stock_awards": 392513,
      "option_awards": 1465595, "non_equity_incentive": 43562,
      "pension_nqdc": 0, "all_other": 4494721, "total": 8182439,
      "_total_source": "verified"},
     {"salary": 807003, "bonus": 5000, "stock_awards": 1781048,
      "option_awards": 392513, "non_equity_incentive": 1465595,
      "pension_nqdc": 0, "all_other": 43562, "total": 4494721}),
    ("LDOS", "Daniel J. Antal", 2024,
     {"salary": 255000, "bonus": 1643023, "stock_awards": 240033,
      "option_awards": 1120200, "non_equity_incentive": 40651,
      "pension_nqdc": 0, "all_other": 3737369, "total": 7036276,
      "_total_source": "verified"},
     {"salary": 438462, "bonus": 255000, "stock_awards": 1643023,
      "option_awards": 240033, "non_equity_incentive": 1120200,
      "pension_nqdc": 0, "all_other": 40651, "total": 3737369}),
]

NOTE = ("DQ 2026-09-26 23:30 PT: salary-drop column-shift repair. Parser dropped "
        "the Salary cell on this FY2023/FY2024 SCT row, shifting every component "
        "one column left (bon->sal, stk->bon, opt->stk, neip->opt, ao->neip, "
        "printed total->all_other; stored total recomputed ~2x phantom). Repaired "
        "filing-verbatim from the 2026 DEF 14A SCT (acc. 0001336920-26-000138, "
        "filed 2026-03-19): values read digit-by-digit from raw HTML table cells, "
        "components foot to the printed total with $0 delta. Same filing's "
        "Bell 2025/2024, Cage 2025/2023, Gruensfelder 2025, Antal 2025, Fautsch "
        "2025 rows verified clean and untouched. %s" % FILING_URL)


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    repaired = []
    for ticker, name, year, expect, filing in REPAIRS:
        matches = []
        for c in data["companies"]:
            if c.get("ticker") != ticker:
                continue
            for e in c.get("executives", []):
                if e.get("name") == name and e.get("year") == year:
                    matches.append(e)
        assert len(matches) == 1, f"{ticker} {name} {year}: {len(matches)} matches"
        e = matches[0]
        for k, v in expect.items():
            assert e.get(k) == v, (f"{ticker} {name} {year}: pre-write drift on "
                                   f"{k}: stored {e.get(k)!r} != expected {v!r}")
        for k, v in filing.items():
            e[k] = v
        e["_total_source"] = "def14a_verified_20260926"
        e["_repair_note_20260926"] = NOTE
        comp = sum(filing[k] for k in ("salary", "bonus", "stock_awards",
                                       "option_awards", "non_equity_incentive",
                                       "pension_nqdc", "all_other"))
        assert comp == filing["total"] == e["total"], \
            f"{ticker} {name} {year}: footing {comp} vs total {e['total']}"
        repaired.append((ticker, name, year))

    # Re-anchor LDOS company aggregates on the FY2024 SCT (anchor-year convention)
    for c in data["companies"]:
        if c.get("ticker") != "LDOS":
            continue
        fy = c.get("fiscal_year")
        rows = [e for e in c.get("executives", []) if e.get("year") == fy]
        old = c.get("total_neo_compensation")
        new = sum(e.get("total") or 0 for e in rows)
        c["total_neo_compensation"] = new
        assert c.get("neo_count") == len(rows) == 3
        print(f"LDOS total_neo_compensation: {old:,} -> {new:,}")
        # CEO anchor (Bell FY2024) is not one of the repaired rows; assert it
        assert c.get("ceo_name") == "Thomas A. Bell"
        assert c.get("total_compensation") == 12460240
        break

    # Metadata buckets: verified -3, def14a_verified_20260926 +3
    meta = data["metadata"]
    for block in ("data_quality", "data_quality_detailed"):
        b = meta[block]
        assert b["verified"] >= 3
        b["verified"] -= 3
        b["def14a_verified_20260926"] = b.get("def14a_verified_20260926", 0) + 3
    meta["last_dq_repair"] = "2026-09-26"
    meta["last_updated"] = "2026-09-26"
    data["last_updated"] = "2026-09-26"

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")

    phantom = ((17557774 - 9187541) + (8182439 - 4494721)
               + (7036276 - 3737369))
    print(f"repaired {len(repaired)} rows: {repaired}")
    print(f"phantom compensation removed: ${phantom:,}")

    # Verify formatting convention matches the repo's (1-space indent, ESCAPED
    # non-ASCII: indent=1, ensure_ascii=True). The 2026-09-26 19:30 PT log note
    # claiming "literal non-ASCII" is inverted; HEAD has \u2014-style escapes.
    with open(JSON_PATH, encoding="utf-8") as f:
        raw_txt = f.read()
    assert raw_txt.startswith('{\n "metadata"'), "indent convention drifted"
    assert "\\u2014" in raw_txt, "ensure_ascii convention drifted"
    print("formatting convention OK (indent=1, ensure_ascii=True)")


if __name__ == "__main__":
    main()
