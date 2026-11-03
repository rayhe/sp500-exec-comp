#!/usr/bin/env python3
"""320th review (2026-11-02 18:30 PT): ARE Diamond 2024 missing-NEO
restoration + Cole 2025 SCT title repair.

Trigger: the 319th review's queued candidate (1) -- the broad
pension>0 / NEIP==0 / stock>0 screen (133 rows). ARE was flagged as the
most suspicious cluster (8 rows), but arbitrating it against the primary
filing shows the screen's premise does not hold for ARE: the 2026 DEF 14A
SCT (acc. 0001035443-26-000031, filed 2026-04-01) carries a NEIP column
in which Binda/Kass/Cole/Diamond are all "--" in every year, while Bonus
is positive -- their cash incentive is Bonus, not NEIP, and the small
pension/NQDC values are genuine deferred-compensation changes (fn 2).
All 8 stored ARE screen rows are byte-equal to the filing (Binda
2025/2024/2023, Kass 2025/2024/2023, Cole 2025, Diamond 2025), so the
screen is a FALSE POSITIVE for ARE -- no component changes.

Real finds from the same filing read (the screen's per-row check missed
roster completeness):
  (a) NEW row: Lawrence J. Diamond FY2024. The 2026 SCT prints a full
      Diamond 2024 row; fn (8) says he "was not an NEO in 2023", so he
      WAS an NEO in 2024 and 2025, and the dataset carried only 2025.
      Filing-verbatim: salary 595,000 / bonus 575,000 / stock 2,186,861 /
      option column absent from this SCT (stored 0, ARE convention, as
      on every other ARE row) / NEIP "--" -> 0 / pension 23,680 /
      all other 51,528 / total 3,432,069 (foots exactly).
      Row appended at END of the ARE executives list per convention.
  (b) Title repair (total-neutral): John Hart Cole 2025 stored title
      "President and Regional Market Director - Greater Boston" is
      Kass's region/title pattern (title bleed). The 2026 SCT name cell
      reads "Co-President & Co-Regional Market Director - Seattle"
      (fn (6): not an NEO in 2023 or 2024, so 2025 is his only SCT row).
      Hyphen-minus form matches the dataset's ARE title convention
      (cf. Diamond 2025's stored title, normalized the same way in the
      2026-09-24 repair note).

Phantom: missing-row restoration, delta = -$3,432,069 (restored grows,
gross_removed unchanged).

Evidence: browser read-only extraction from the exact EDGAR URL
https://www.sec.gov/Archives/edgar/data/1035443/000103544326000031/are-20260331.htm
(2026 Proxy Statement, Schedule 14A, dated April 1, 2026); the 8
stored screen rows were re-compared field-by-field against that
extraction and match exactly.
"""
import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
STAMP = "20261102_1830"
BACKUP = os.path.join(
    REPO, "data", f"compensation_backup_{STAMP}_pre_are_diamond2024.json")

NEW_ROW = {
    "name": "Lawrence J. Diamond",
    "title": "Co-Chief Operating Officer and Regional Market Director - Maryland",
    "year": 2024,
    "salary": 595000,
    "bonus": 575000,
    "stock_awards": 2186861,
    "option_awards": 0,
    "non_equity_incentive": 0,
    "pension_nqdc": 23680,
    "all_other": 51528,
    "total": 3432069,
    "_total_source": "verified",
    "_accession": "0001035443-26-000031",
    "_filing_url": ("https://www.sec.gov/Archives/edgar/data/1035443/"
                    "000103544326000031/are-20260331.htm"),
    "_repair_note_20261102_1830": (
        "2026-11-02 18:30 PT (320th review): Diamond FY2024 restored "
        "filing-verbatim from the 2026 DEF 14A SCT (acc. "
        "0001035443-26-000031, filed 2026-04-01; fn (8) not an NEO in "
        "2023, so 2024 is a genuine NEO year the dataset had missed). "
        "NEIP '--' -> 0; no Option Awards column in this SCT -> 0 per "
        "ARE convention. Total foots exactly."),
}

COMPONENT_KEYS = ("salary", "bonus", "stock_awards", "option_awards",
                  "non_equity_incentive", "pension_nqdc", "all_other")


def foot(row):
    return sum(row.get(k) or 0 for k in COMPONENT_KEYS)


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    are = next(c for c in d["companies"] if c.get("ticker") == "ARE")
    rows = are["executives"]

    # not-present guard for the new row
    assert not any(r.get("name") == "Lawrence J. Diamond"
                   and r.get("year") == 2024 for r in rows), \
        "Diamond 2024 already present"

    # exact-footing assertion on the new row
    assert foot(NEW_ROW) == NEW_ROW["total"] == 3432069, "new row misfoots"

    # Cole 2025 title repair with old-value guard, total-neutral
    hits = [r for r in rows if r.get("name") == "John Hart Cole"
            and r.get("year") == 2025]
    assert len(hits) == 1, f"expected 1 Cole 2025 hit, got {len(hits)}"
    cole = hits[0]
    assert cole["title"] == "President and Regional Market Director \u2013 Greater Boston", \
        f"old-value guard failed for Cole 2025: {cole['title']!r}"
    before = {k: cole.get(k) for k in COMPONENT_KEYS + ("total",)}
    cole["title"] = "Co-President & Co-Regional Market Director - Seattle"
    after = {k: cole.get(k) for k in COMPONENT_KEYS + ("total",)}
    assert before == after, "title repair moved components for Cole 2025"

    # append the new row at END per convention
    rows.append(NEW_ROW)

    # exact-footing re-assertion on every ARE verified row
    for r in rows:
        if r.get("_total_source") == "verified":
            assert foot(r) == r["total"], f"misfoot: {r['name']} {r['year']}"

    shutil.copy2(DATA, BACKUP)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"backup: {BACKUP}")
    print("1 title repair (Cole 2025) + 1 restored row (Diamond 2024, $3,432,069)")

    # phantom counters (restoration batch: negative delta)
    sys.path.insert(0, os.path.join(REPO, "hidden_files"))
    import phantom_record
    delta = phantom_record.record_batch(pre_path=BACKUP, data_path=DATA,
                                        stamp="2026-11-02 18:30 PT")
    print(f"phantom delta: ${delta:,}")
    assert delta == -3432069, f"unexpected phantom delta {delta}"
    print("phantom delta asserted == -$3,432,069")


if __name__ == "__main__":
    main()
