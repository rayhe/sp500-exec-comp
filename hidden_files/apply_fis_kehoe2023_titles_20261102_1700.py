#!/usr/bin/env python3
"""319th review (2026-11-02 17:00 PT): FIS Kehoe 2023 missing-row restoration +
whole-company SCT title repairs.

Batch contents:
  (a) NEW row: James Kehoe FY2023 ($12,852,097) filing-verbatim from the
      2026 DEF 14A SCT grid (acc. 0001136893-26-000026, filed 2026-04-28).
      NEO determination confirmed in the 2024 DEF 14A SCT (acc.
      0001193125-24-118098, filed 2024-04-26; grid is a graphic page, table
      content in the img alt-text layer): "James Kehoe, Corporate Executive
      Vice President and Chief Financial Officer(7)" listed as an FY2023
      named executive officer; footnotes (5)/(7) describe his 2023 NEIP and
      2023-08-21 EVP/CFO appointment. Row appended at END of the FIS
      executives list per convention.
      Values (2026 proxy, latest filing supersedes the 2024-proxy alt-text
      figures: salary 355,459->355,469, NEIP 761,530->761,056, total
      12,852,571->12,852,097; the 2026 row foots exactly, the 2024 alt-text
      row was $10 off its own printed total):
        salary 355,469 / bonus 1,700,000 / stock_awards 9,999,986 /
        option_awards blank in filing (key omitted, FIS schema convention) /
        non_equity_incentive 761,056 / pension_nqdc 0 (blank cell) /
        all_other 35,586 / total 12,852,097 (foots exactly).
  (b) Title repairs, all 11 existing FIS rows, filing-verbatim from the
      2026 DEF 14A SCT name cells (2025 proxy SCT confirms the same titles,
      incl. Kehoe/Bhathena never having been CEO/CFO respectively):
        Ferris 2025/2024/2023: "President and Chief Executive Officer"
          -> "Chief Executive Officer and President"
        Kehoe 2025/2024: "Chief Executive Officer and President"
          -> "Corporate Executive Vice President and Chief Financial Officer"
        Bhathena 2025/2024: "Chief Financial Officer"
          -> "Former Chief Product Technology Officer"
          (filing: "Former Chief Product Technology Officer (6)"; numeric
          footnote markers are never stored in titles - 0 in the dataset)
        Toohey 2025: "Executive Vice President"
          -> "Corporate Executive Vice President and Chief People Officer"
        Tsai 2025/2024/2023: "Chief People Officer"
          -> "Corporate Executive Vice President and Chief Legal Corporate
              Affairs Officer Corporate Secretary"
      Total-neutral (titles only); company aggregates, CEO totals, pay
      ratios, metadata buckets, dataq fallback figures all untouched.

Phantom: missing-row restoration, delta = -$12,852,097 (restored grows,
gross_removed unchanged).

Evidence: goal hidden_files/dq_20261102_1700/
  (fis_2024_def14a.htm, fis_2025_def14a.htm raw filings; 2024-proxy SCT
  alt-text grid; VERIFICATION.md to be written by the run).
"""
import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
STAMP = "20261102_1700"
BACKUP = os.path.join(
    REPO, "data", f"compensation_backup_{STAMP}_pre_fis_kehoe2023.json")

NEW_ROW = {
    "name": "James Kehoe",
    "title": "Corporate Executive Vice President and Chief Financial Officer",
    "year": 2023,
    "salary": 355469,
    "bonus": 1700000,
    "stock_awards": 9999986,
    # option_awards: blank cell in the 2026 SCT -> key omitted (FIS schema)
    "non_equity_incentive": 761056,
    "pension_nqdc": 0,
    "all_other": 35586,
    "total": 12852097,
    "_total_source": "verified",
    "_accession": "0001136893-26-000026",
    "_filing_url": ("https://www.sec.gov/Archives/edgar/data/1136893/"
                    "000113689326000026/fis-20260428.htm"),
    "_repair_note_20261102_1700": (
        "2026-11-02 17:00 PT (319th review): Kehoe FY2023 restored "
        "filing-verbatim from the 2026 DEF 14A SCT grid (acc. "
        "0001136893-26-000026, filed 2026-04-28; FY2023 NEO determination "
        "confirmed in the 2024 DEF 14A SCT, acc. 0001193125-24-118098). "
        "Latest filing supersedes the 2024-proxy alt-text figures "
        "(salary 355,459->355,469, NEIP 761,530->761,056). "
        "Blank filing option/pension cells -> key omitted / 0. "
        "Total foots exactly."),
}

TITLE_REPAIRS = {
    # (name, year) -> (old_title, new_title)
    ("Stephanie L Ferris", 2025): ("President and Chief Executive Officer",
                                   "Chief Executive Officer and President"),
    ("Stephanie L Ferris", 2024): ("President and Chief Executive Officer",
                                   "Chief Executive Officer and President"),
    ("Stephanie L Ferris", 2023): ("President and Chief Executive Officer",
                                   "Chief Executive Officer and President"),
    ("James Kehoe", 2025): ("Chief Executive Officer and President",
                            "Corporate Executive Vice President and Chief "
                            "Financial Officer"),
    ("James Kehoe", 2024): ("Chief Executive Officer and President",
                            "Corporate Executive Vice President and Chief "
                            "Financial Officer"),
    ("Firdaus Bhathena", 2025): ("Chief Financial Officer",
                                 "Former Chief Product Technology Officer"),
    ("Firdaus Bhathena", 2024): ("Chief Financial Officer",
                                 "Former Chief Product Technology Officer"),
    ("Robert Toohey", 2025): ("Executive Vice President",
                              "Corporate Executive Vice President and Chief "
                              "People Officer"),
    ("Caroline Tsai", 2025): ("Chief People Officer",
                              "Corporate Executive Vice President and Chief "
                              "Legal Corporate Affairs Officer Corporate "
                              "Secretary"),
    ("Caroline Tsai", 2024): ("Chief People Officer",
                              "Corporate Executive Vice President and Chief "
                              "Legal Corporate Affairs Officer Corporate "
                              "Secretary"),
    ("Caroline Tsai", 2023): ("Chief People Officer",
                              "Corporate Executive Vice President and Chief "
                              "Legal Corporate Affairs Officer Corporate "
                              "Secretary"),
}

COMPONENT_KEYS = ("salary", "bonus", "stock_awards", "option_awards",
                  "non_equity_incentive", "pension_nqdc", "all_other")


def foot(row):
    return sum(row.get(k) or 0 for k in COMPONENT_KEYS)


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    fis = next(c for c in d["companies"] if c.get("ticker") == "FIS")
    rows = fis["executives"]

    # not-present guard for the new row
    assert not any(r.get("name") == "James Kehoe" and r.get("year") == 2023
                   for r in rows), "Kehoe 2023 already present"

    # exact-footing assertion on the new row
    assert foot(NEW_ROW) == NEW_ROW["total"] == 12852097, "new row misfoots"

    # title repairs with old-value guards
    fixed = 0
    for (name, year), (old_t, new_t) in TITLE_REPAIRS.items():
        hits = [r for r in rows
                if r.get("name") == name and r.get("year") == year]
        assert len(hits) == 1, f"expected 1 hit for {(name, year)}, got {len(hits)}"
        r = hits[0]
        assert r["title"] == old_t, f"old-value guard failed for {(name, year)}: {r['title']!r}"
        # total-neutrality: components and total untouched
        before = {k: r.get(k) for k in COMPONENT_KEYS + ("total",)}
        r["title"] = new_t
        after = {k: r.get(k) for k in COMPONENT_KEYS + ("total",)}
        assert before == after, f"title repair moved components for {(name, year)}"
        fixed += 1
    assert fixed == 11, f"expected 11 title repairs, did {fixed}"

    # append the new row at END per convention
    rows.append(NEW_ROW)

    # exact-footing re-assertion on every FIS row touched
    for r in rows:
        if r.get("_total_source") == "verified":
            assert foot(r) == r["total"], f"misfoot: {r['name']} {r['year']}"

    shutil.copy2(DATA, BACKUP)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"backup: {BACKUP}")
    print("11 title repairs + 1 restored row (Kehoe 2023, $12,852,097)")

    # phantom counters (restoration batch: negative delta)
    sys.path.insert(0, os.path.join(REPO, "hidden_files"))
    import phantom_record
    delta = phantom_record.record_batch(pre_path=BACKUP, data_path=DATA,
                                        stamp="2026-11-02 17:00 PT")
    print(f"phantom delta: ${delta:,}")
    assert delta == -12852097, f"unexpected phantom delta {delta}"
    print("phantom delta asserted == -$12,852,097")


if __name__ == "__main__":
    main()
