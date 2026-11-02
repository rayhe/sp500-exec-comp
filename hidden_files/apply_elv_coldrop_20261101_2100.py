#!/usr/bin/env python3
"""309th review (2026-11-01 21:00 PT): ELV column-drop SCT repair.

The tier-1 column-drop sibling detector
(hidden_files/detect_columndrop_siblings_20261101_1830.py) flagged 8 ELV
rows. Filing arbitration against the 2026 DEF 14A SCT (acc.
0001156039-26-000031, filed 2026-03-27; raw HTML at goal
hidden_files/dq_20261101_2100/elv_2026_def14a.htm, SCT dumped to
elv_2026_sct_dump.txt) confirms the BALL column-drop family, both known
variants:

  Variant A (8 rows: Boudreaux/Haytaian/Norwood 2024+2023, Kaye/Kendrick
  2024): filing.stock -> stored non_equity_incentive, filing.option ->
  stored all_other; filing NEIP/pension/all_other dropped; stored total
  recomputed against the misfiled mapping (foots exactly).

  Variant B (1 row: Kaye 2023): filing.bonus -> stored stock_awards,
  filing.stock -> stored neip, filing.option -> stored all_other;
  stored bonus == 0; stored total == salary+stock+neip+all_other
  (foots exactly). Kaye's 2023 bonus is the footnote-(1) $2.5M one-time
  commencement cash award (repayable within 3 years).

All 5 FY2025 rows (the same filing's SCT) already match filing-verbatim;
no changes there. The 2026 proxy SCT prints 2025/2024/2023 so it is
authoritative for all three years. Kendrick has no 2023 NEO row (not an
NEO in FY2023), consistent with the filing.

Row schema: legacy omitted-zero rows keep their schema; stock_awards /
option_awards keys are ADDED where the filing value is non-zero
(material values must be stored). Titles and _total_source ('verified')
untouched (305th/306th/307th/308th precedent). Company aggregates
untouched: anchor FY2025 rows unchanged (total_compensation $22,582,314,
total_neo_compensation $51,408,755, pay_ratio, median all intact), so
section-17 aggregate recompute is a no-op and is skipped.

Filing-verbatim values re-read digit-by-digit from the raw filing HTML.
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
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_elv_coldrop.json"

# (name, year): filing-verbatim components from the 2026 DEF 14A SCT.
REPAIRS = {
    # Variant A: stock->neip, option->all_other shift
    ("Gail Boudreaux", 2024): dict(salary=1600000, stock_awards=12600032,
        option_awards=4199989, non_equity_incentive=1142400, all_other=929555,
        total=20471976),
    ("Gail Boudreaux", 2023): dict(salary=1600000, stock_awards=11850043,
        option_awards=3950036, non_equity_incentive=3648000, all_other=840960,
        total=21889039),
    ("Mark Kaye", 2024): dict(salary=900000, stock_awards=4125144,
        option_awards=1374953, non_equity_incentive=385560, all_other=87487,
        total=6873144),
    # Variant B: bonus->stock, stock->neip, option->all_other shift
    ("Mark Kaye", 2023): dict(salary=252692, bonus=2500000,
        stock_awards=10775411, option_awards=924613,
        non_equity_incentive=351748, all_other=54737, total=14859201),
    ("Peter Haytaian", 2024): dict(salary=950000, stock_awards=3600081,
        option_awards=1199997, non_equity_incentive=406980, all_other=188069,
        total=6345127),
    ("Peter Haytaian", 2023): dict(salary=944231, stock_awards=3225051,
        option_awards=1074976, non_equity_incentive=1314369, all_other=419424,
        total=6978051),
    ("Felicia Norwood", 2024): dict(salary=950000, stock_awards=3600081,
        option_awards=1199997, non_equity_incentive=406980, all_other=131888,
        total=6288946),
    ("Felicia Norwood", 2023): dict(salary=944231, stock_awards=3225051,
        option_awards=1074976, non_equity_incentive=1087754, all_other=143396,
        total=6475408),
    ("Morgan Kendrick", 2024): dict(salary=850000, stock_awards=3225249,
        option_awards=1074825, non_equity_incentive=510000, all_other=133400,
        total=5793474),
}

# pre-repair stored totals asserted before any write (old-value guard)
OLD_TOTALS = {
    ("Gail Boudreaux", 2024): 18400021,
    ("Gail Boudreaux", 2023): 17400079,
    ("Mark Kaye", 2024): 6400097,
    ("Mark Kaye", 2023): 14452716,
    ("Peter Haytaian", 2024): 5750078,
    ("Peter Haytaian", 2023): 5244258,
    ("Felicia Norwood", 2024): 5750078,
    ("Felicia Norwood", 2023): 5244258,
    ("Morgan Kendrick", 2024): 5150074,
}

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]


def main():
    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)
    data = json.load(open(DATA, encoding="utf-8"))
    cos = data["companies"]
    elv = next(c for c in cos if c["ticker"] == "ELV")

    fixed = 0
    for e in elv["executives"]:
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
        # legacy omitted-zero rows keep their schema: only non-zero
        # components (plus salary/total) are written; existing zero keys
        # (bonus, pension_nqdc) are left untouched.
        for k, v in r.items():
            e[k] = v
        variant = "B" if key == ("Mark Kaye", 2023) else "A"
        e["_repair_note_20261101_2100"] = (
            "2026-11-01 21:00 PT (309th review): 2026 DEF 14A SCT "
            "(acc. 0001156039-26-000031) shows the BALL column-drop family, "
            f"variant {variant}"
            + (": filing bonus->stock, stock->NEIP, option->All Other shift"
               if variant == "B"
               else ": filing stock->NEIP, option->All Other shift, "
                    "NEIP/pension/All Other dropped, total recomputed")
            + ". Repaired filing-verbatim; titles and _total_source "
            "('verified') untouched.")
        fixed += 1
    assert fixed == 9, f"expected 9 rows fixed, got {fixed}"

    # anchor-year (FY2025) sanity: 2025 rows must be untouched and foot
    rows25 = [e for e in elv["executives"] if e["year"] == 2025]
    assert len(rows25) == 5
    assert sum(e["total"] for e in rows25) == elv["total_neo_compensation"] == 51408755
    assert elv["total_compensation"] == 22582314

    # DQ-batch timestamp convention
    data["metadata"]["last_dq_repair"] = "2026-11-01"
    data["last_updated"] = "2026-11-01"

    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    open(DATA, "a", encoding="utf-8").write("\n")
    print("repaired 9 ELV rows; company aggregates unchanged (FY2025 anchor intact)")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp="2026-11-01 21:00 PT")
    print(f"phantom delta: ${delta:,}")


if __name__ == "__main__":
    main()
