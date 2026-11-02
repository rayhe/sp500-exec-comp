#!/usr/bin/env python3
"""317th review (2026-11-02 13:00 PT): FDX missing-NEO restoration.

Queuing source: 316th review (dq_20261102_1030/VERIFICATION.md) — the FDX 2024
DEF 14A SCT (acc. 0001308179-24-000696, filed 2024-08-12) names 6 NEOs but
compensation.json carries only 3 (Subramaniam, Dietrich, Krishnasamy) for the
FY2022-FY2024 proxy years. Missing: Mark R. Allen (2024/2023), Robert B. Carter
(2024/2023/2022), Michael C. Lenz (2024/2023/2022).

Values transcribed filing-verbatim from the extracted SCT grid at
goal hidden_files/dq_20261102_1030/sct_fdx2024.txt (which cross-checks against
the already-verified Subramaniam/Dietrich/Krishnasamy rows: all byte-equal, so
the grid transcription is trusted). Titles are SCT-verbatim word order with the
filing's line-breaks normalized to spaces; pension blank cells -> 0 (Dietrich
2024 precedent). Rows appended at END of the FDX executives list (standing
convention). FDX anchor year is FY2026, so these historical rows do not move
anchor-scoped company aggregates; record_batch() records the restoration as
genuine restored compensation (Phantom batch 89).
"""

import json
import shutil
import sys

sys.path.insert(0, "hidden_files")
import phantom_record  # noqa: E402

DATA = "data/compensation.json"
BACKUP = "data/compensation_backup_20261102_1315_pre_fdx_neos.json"

ACC = "0001308179-24-000696"
URL = ("https://www.sec.gov/Archives/edgar/data/1048911/000130817924000696/"
       "fdx4341161-def14a.htm")
NOTE = ("2026-11-02 13:00 PT (317th review): missing-NEO rows restored "
        "filing-verbatim from the 2024 DEF 14A SCT (acc. 0001308179-24-000696, "
        "filed 2024-08-12; SCT grid at goal hidden_files/dq_20261102_1030/"
        "sct_fdx2024.txt). Blank filing pension cells -> 0; all 8 totals foot "
        "exactly against the 8-component sum.")

COMPS = ("salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other")

# (name, title, year, salary, bonus, stock, option, NEIP, pension, all_other, total)
NEW_ROWS = [
    ("Mark R. Allen",
     "Executive Vice President, General Counsel and Secretary",
     2024, 766390, 0, 908967, 1197846, 1108038, 0, 1185827, 5167068),
    ("Mark R. Allen",
     "Executive Vice President, General Counsel and Secretary",
     2023, 745254, 0, 908915, 1197782, 1885125, 0, 649101, 5386177),
    ("Robert B. Carter",
     "Executive Vice President, FedEx Information Services and Chief Information Officer",
     2024, 962084, 0, 908967, 1197846, 1251562, 0, 796101, 5116560),
    ("Robert B. Carter",
     "Executive Vice President, FedEx Information Services and Chief Information Officer",
     2023, 935552, 0, 908915, 1197782, 1885125, 0, 750625, 5677999),
    ("Robert B. Carter",
     "Executive Vice President, FedEx Information Services and Chief Information Officer",
     2022, 911281, 0, 690849, 888214, 364148, 0, 597740, 3452232),
    ("Michael C. Lenz",
     "Former Executive Vice President and Chief Financial Officer (Former Principal Financial Officer)",
     2024, 508229, 0, 970498, 1499985, 974330, 103951, 2028814, 6085807),
    ("Michael C. Lenz",
     "Former Executive Vice President and Chief Financial Officer (Former Principal Financial Officer)",
     2023, 864167, 0, 970190, 1499884, 1885125, 136117, 686770, 6042253),
    ("Michael C. Lenz",
     "Former Executive Vice President and Chief Financial Officer (Former Principal Financial Officer)",
     2022, 747788, 0, 892653, 1155096, 322057, 184314, 634765, 3936673),
]


def foot(row):
    return sum(row[c] for c in COMPS)


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    by_ticker = {c["ticker"]: c for c in d["companies"]}
    fdx = by_ticker["FDX"]

    for name, title, year, sal, bon, stk, opt, neip, pen, oth, tot in NEW_ROWS:
        assert not [e for e in fdx["executives"]
                    if e["name"] == name and e["year"] == year], \
            f"{name} {year} already present"
        row = {
            "name": name,
            "title": title,
            "year": year,
            "salary": sal,
            "bonus": bon,
            "stock_awards": stk,
            "option_awards": opt,
            "non_equity_incentive": neip,
            "pension_nqdc": pen,
            "all_other": oth,
            "total": tot,
            "_total_source": "verified",
            "_accession": ACC,
            "_filing_url": URL,
            "_repair_note_20261102_1315": NOTE,
        }
        assert foot(row) == tot, f"footing mismatch: {name} {year}"
        fdx["executives"].append(row)

    shutil.copy2(DATA, BACKUP)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")

    restored_expected = sum(r[10] for r in NEW_ROWS)
    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA,
        stamp="2026-11-02 13:00 PT (317th review)")
    assert delta == -restored_expected, f"unexpected phantom delta {delta}"
    print("rows_added: 8, restored:", restored_expected)
    print("record_batch delta:", delta)


if __name__ == "__main__":
    main()
