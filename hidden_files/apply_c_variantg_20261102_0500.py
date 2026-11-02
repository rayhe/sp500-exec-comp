#!/usr/bin/env python3
"""313th review (2026-11-02 05:00 PT): Citigroup column-drop SCT repair.

The tier-1 column-drop sibling detector
(hidden_files/detect_columndrop_siblings_20261101_1830.py) flagged 1 C row
(Mason 2024); filing arbitration against the 2025 DEF 14A SCT (acc.
0001145443-25-000075, filed 2025-03-18; raw HTML at goal
hidden_files/dq_20261102_0500/citi_2025_def14a.htm, SCT dumped to
citi_sct.txt) confirms a new sub-family of the column-drop corruption:

  Variant G (5 rows: Fraser 2024/2023, Mason 2024/2023, Morton 2024):
  legacy parse dropped the Salary cell, then shifted bonus->salary,
  stock->bonus, NEIP->option_awards, pension->non_equity_incentive;
  the genuine All Other cell was dropped and the filing Total was filed
  into all_other; stored total recomputed against the misfiled mapping
  (foots exactly). Unlike variant E, the NEIP cell lands in
  option_awards (not stock_awards) and the All Other cell does not
  survive anywhere. Sibling rows Raghavan 2024 (from the same filing)
  and Morton 2023 (def14a_verified_20260909) are filing-verbatim -
  byte-equal - so variant G is not whole-company; it hit rows whose
  name cell carries a title/continuation layout (Mason 2024 lead row
  "Mark Mason CFO", Fraser continuation rows, Morton 2024 lead row).

Filing-verbatim values re-read digit-by-digit from the raw filing HTML.
Titles and _total_source ('verified') untouched (305th-312th precedent).
Company aggregates untouched: anchor FY2025 rows unchanged
(total_compensation $95,757,800, total_neo_compensation $202,273,134,
pay_ratio 444, median $70,138 all intact), so the section-17 aggregate
recompute is a no-op and is skipped.

Also adjudicated in this review (FALSE POSITIVES, no changes):
  TDG Lisman 2022 / Murphy 2025 - 2023 + 2026 DEF 14As: TransDigm SCT
    has no Stock Awards column (options only); stored rows byte-equal.
  RDDT Huffman 2025/2024 - 2026 DEF 14A: already def14a_verified_20260926;
    stored rows byte-equal to the filing SCT (Huffman took no equity
    in 2024-2025; the 2023 IPO grants are stored filing-verbatim).
  ORCL Ellison 2024/2023 - 2025 DEF 14A SCT (acc. 0001193125-25-220801):
    already def14a_verified_20260925; stored rows byte-equal
    (salary $1, NEIP + All Other security costs, no equity).
"""
import json
import shutil
import sys
from datetime import datetime

sys.path.insert(0, "/home/hatch/repos/sp500-exec-comp/hidden_files")
import phantom_record

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_c_variantg.json"

# (name, year): filing-verbatim components from the 2025 DEF 14A SCT
# (Citi 2025 proxy SCT; table 330 in citi_2025_def14a.htm).
# Variant G: filing salary dropped; bonus->salary; stock->bonus;
# NEIP->option_awards; pension->non_equity_incentive; all_other dropped;
# filing total->all_other; total recomputed.
REPAIRS = {
    # Jane Fraser: filing 1,500,000 / 4,950,000 / 24,656,800 / -- / -- / 20,700 / 31,127,500
    ("Jane Fraser", 2024): dict(salary=1500000, bonus=4950000,
        stock_awards=24656800, option_awards=0,
        non_equity_incentive=0, pension_nqdc=0, all_other=20700,
        total=31127500),
    # Jane Fraser: filing 1,500,000 / 3,675,000 / 18,701,013 / 1,562,500 / -- / 19,800 / 25,458,313
    ("Jane Fraser", 2023): dict(salary=1500000, bonus=3675000,
        stock_awards=18701013, option_awards=0,
        non_equity_incentive=1562500, pension_nqdc=0, all_other=19800,
        total=25458313),
    # Mark Mason: filing 1,000,000 / 5,632,000 / 8,551,578 / -- / 2,799 / 20,700 / 15,207,077
    ("Mark Mason", 2024): dict(salary=1000000, bonus=5632000,
        stock_awards=8551578, option_awards=0,
        non_equity_incentive=0, pension_nqdc=2799, all_other=20700,
        total=15207077),
    # Mark Mason: filing 1,000,000 / 4,930,000 / 7,535,196 / 1,001,378 / 2,122 / 19,800 / 14,488,496
    ("Mark Mason", 2023): dict(salary=1000000, bonus=4930000,
        stock_awards=7535196, option_awards=0,
        non_equity_incentive=1001378, pension_nqdc=2122, all_other=19800,
        total=14488496),
    # Andrew Morton: filing 1,000,000 / 8,210,000 / 10,933,541 / 4,233,537 / -- / 45,085 / 24,422,163
    ("Andrew Morton", 2024): dict(salary=1000000, bonus=8210000,
        stock_awards=10933541, option_awards=0,
        non_equity_incentive=4233537, pension_nqdc=0, all_other=45085,
        total=24422163),
}

# pre-repair stored totals asserted before any write (old-value guard)
OLD_TOTALS = {
    ("Jane Fraser", 2024): 60734300,
    ("Jane Fraser", 2023): 49396826,
    ("Mark Mason", 2024): 29393454,
    ("Mark Mason", 2023): 27957192,
    ("Andrew Morton", 2024): 47799241,
}

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]


def main():
    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)
    data = json.load(open(DATA, encoding="utf-8"))
    cos = data["companies"]
    citi = next(c for c in cos if c["ticker"] == "C")

    fixed = 0
    for e in citi["executives"]:
        key = (e["name"], e["year"])
        if key not in REPAIRS:
            continue
        assert e["total"] == OLD_TOTALS[key], \
            f"unexpected stored total for {key}: {e['total']}"
        assert e.get("_total_source") == "verified", \
            f"unexpected _total_source for {key}"
        r = REPAIRS[key]
        # filing-verbatim footing: sal + bonus + stk + opt + neip + pen + ao == total
        assert sum(r.get(k, 0) for k in COMPS) == r["total"], \
            f"filing row does not foot: {key}"
        for k, v in r.items():
            e[k] = v
        e["_accession"] = "0001145443-25-000075"
        e["_filing_url"] = ("https://www.sec.gov/Archives/edgar/data/831001/"
                            "000114544325000075/citi4405291-def14a.htm")
        if key == ("Mark Mason", 2024):
            # The 2026-09-09 _parse_note described a repair to the CORRUPTED
            # row (it called $60,734,300 the "filing's stated SCT total"; the
            # filing's stated total is $15,207,077). Superseded by this
            # full filing-verbatim repair; keep _original_pension for
            # provenance.
            e.pop("_parse_note", None)
        e["_repair_note_20261102_0500"] = (
            "2026-11-02 05:00 PT (313th review): 2025 DEF 14A SCT "
            "(acc. 0001145443-25-000075) shows the column-drop family, "
            "new variant G: legacy parse dropped the Salary cell, then "
            "bonus->salary, stock->bonus, NEIP->option_awards, "
            "pension->non_equity_incentive; genuine All Other dropped, "
            "filing Total filed into all_other, stored total recomputed. "
            "Repaired filing-verbatim; titles and _total_source "
            "('verified') untouched.")
        fixed += 1
    assert fixed == 5, f"expected 5 rows fixed, got {fixed}"

    # anchor-year (FY2025) sanity: 2025 rows must be untouched and foot
    rows25 = [e for e in citi["executives"] if e["year"] == 2025]
    assert len(rows25) == 5
    assert sum(e["total"] for e in rows25) == citi["total_neo_compensation"] == 202273134
    assert citi["total_compensation"] == 95757800

    # DQ-batch timestamp convention
    data["metadata"]["last_dq_repair"] = "2026-11-02"
    data["last_updated"] = "2026-11-02"

    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    open(DATA, "a", encoding="utf-8").write("\n")
    print("repaired 5 C rows; company aggregates unchanged (FY2025 anchor intact)")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp="2026-11-02 05:00 PT")
    print(f"phantom delta: ${delta:,}")


if __name__ == "__main__":
    main()
