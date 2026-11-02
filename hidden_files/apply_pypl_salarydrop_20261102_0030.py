#!/usr/bin/env python3
"""311th review (2026-11-02 01:00 PT): PYPL salary-drop left-shift repair.

The tier-1 column-drop sibling detector
(hidden_files/detect_columndrop_siblings_20261101_1830.py) flagged 3 PYPL rows
(Chriss 2024, Miller 2023, Gill 2023). Filing arbitration against the 2026
DEF 14A SCT (acc. 0001193125-26-145721, filed 2026-04-24; raw HTML at goal
hidden_files/dq_20261102_0030/pypl_2026_def14a.htm, SCT TR-parsed from the
filing) gives a split verdict:

- Alex Chriss 2024: FALSE POSITIVE. Filing shows salary 1,250,000, bonus --,
  stock --, NEIP 4,975,000, all_other 433,527, total 6,658,527 -- byte-equal
  to the stored row. PayPal's SCT has no Option Awards and no Pension/NQDC
  columns (like Paycom's). No change.
- Jamie Miller 2023 + Michelle Gill 2023: CONFIRMED, new column-drop
  sub-family variant E ("salary-drop left-shift"). The legacy parse dropped
  the Salary cell on these two continuation rows and shifted every later
  column left by one, then recomputed the total:

      filing: salary | bonus     | stock     | NEIP | all_other | total
      stored: salary=filing.bonus | bonus=filing.stock | stock=0
              | neip=filing.all_other | all_other=filing.total
              | total=recomputed sum of the shifted values

  Miller 2023 filing: salary 100,962, bonus 3,000,000, stock 8,825,116,
  NEIP --, all_other 3,462, total 11,929,539 (stored was 3,000,000 /
  8,825,116 / 0 / 3,462 / 11,929,539 / 23,758,117).
  Gill 2023 filing: salary 80,769, bonus 1,000,000, stock 8,825,116,
  NEIP --, all_other 923, total 9,906,808 (stored was 1,000,000 /
  8,825,116 / 0 / 923 / 9,906,808 / 19,732,847).
  The dropped salaries are small partial-year figures ($100,962 / $80,769);
  the 2024/2025 rows of the same SCT parsed correctly, so this is a
  two-row parser glitch, not a systematic column mapping.

Filing-verbatim titles from the same SCT title blocks: Miller ->
"EVP, Chief Financial and Operating Officer" (stored "President and CEO",
a legacy misattribution -- Miller was never President/CEO); Gill ->
"EVP, General Manager, Small Business and Financial Services" (stored
"Executive Vice President"). Applied to all 6 Miller/Gill rows (2023-2025);
the 2026 proxy's title block covers the whole 3-year span for each person.
Chriss rows keep the contemporaneous "President and Chief Executive
Officer" (the 2026 proxy's retrospective "Former ..." label reflects his
status at filing time, not the fiscal years shown).

Company aggregates untouched: total_neo_compensation is anchor-FY2025
scoped ($91,405,702, sum of the 6 FY2025 rows, none repaired), so the
section-17 aggregate recompute is a no-op (309th-review precedent) and the
pay-ratio/median figures are untouched. Phantom delta for this batch is
+$21,654,617 of parser-invented compensation removed (stored totals were
inflated by the shift: 23,758,117 -> 11,929,539 and 19,732,847 -> 9,906,808).

PAYC tranche (same run, detector's other 3-flag cluster): all three
Richison rows FALSE POSITIVE. The 2026 DEF 14A SCT (acc.
0001193125-26-140064) shows Richison 2024/2023 with stock_awards = em-dash
(no equity granted; Paycom's SCT has no option column, Paycom grants no
options) -- stored rows byte-equal. Richison 2022 arbitrated against the
2025 DEF 14A SCT (acc. 0001193125-25-072358): salary 785,953, bonus --,
stock --, NEIP 1,538,816, all_other 813,649, total 3,138,418 -- byte-equal
to stored. No data changes for PAYC.

Filing-verbatim values re-read digit-by-digit from the raw filing HTML
(TR-level parse, tags stripped, &#160; treated as space).
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
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_pypl_salarydrop.json"

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

# (name, year): filing-verbatim full component mapping + title
REPAIRS = {
    ("Jamie Miller", 2023): dict(
        salary=100962, bonus=3000000, stock_awards=8825116, option_awards=0,
        non_equity_incentive=0, pension_nqdc=0, all_other=3462,
        total=11929539,
        title="EVP, Chief Financial and Operating Officer",
        old=dict(salary=3000000, bonus=8825116, stock_awards=0,
                 non_equity_incentive=3462, all_other=11929539,
                 total=23758117, title="President and CEO")),
    ("Michelle Gill", 2023): dict(
        salary=80769, bonus=1000000, stock_awards=8825116, option_awards=0,
        non_equity_incentive=0, pension_nqdc=0, all_other=923,
        total=9906808,
        title="EVP, General Manager, Small Business and Financial Services",
        old=dict(salary=1000000, bonus=8825116, stock_awards=0,
                 non_equity_incentive=923, all_other=9906808,
                 total=19732847, title="Executive Vice President")),
}

# title-only repairs (same filing's title blocks; numbers already verified)
TITLE_REPAIRS = {
    ("Jamie Miller", 2025): "EVP, Chief Financial and Operating Officer",
    ("Jamie Miller", 2024): "EVP, Chief Financial and Operating Officer",
    ("Michelle Gill", 2025):
        "EVP, General Manager, Small Business and Financial Services",
    ("Michelle Gill", 2024):
        "EVP, General Manager, Small Business and Financial Services",
}

NOTE = ("2026-11-02 01:00 PT (311th review): 2026 DEF 14A SCT (acc. "
        "0001193125-26-145721) shows variant E of the column-drop family "
        "(salary-drop left-shift): the legacy parse dropped the Salary cell "
        "on this continuation row and shifted bonus->salary, stock->bonus, "
        "all_other->NEIP, total->all_other, then recomputed the total. "
        "Repaired filing-verbatim; title filing-verbatim from the SCT title "
        "block; _total_source ('verified') untouched.")
TITLE_NOTE = ("2026-11-02 01:00 PT (311th review): title repaired "
              "filing-verbatim from the 2026 DEF 14A SCT title block (acc. "
              "0001193125-26-145721); components already verified, untouched.")


def main():
    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)
    data = json.load(open(DATA, encoding="utf-8"))
    cos = data["companies"]
    pypl = next(c for c in cos if c["ticker"] == "PYPL")

    fixed = 0
    for e in pypl["executives"]:
        key = (e["name"], e["year"])
        if key not in REPAIRS:
            continue
        r = REPAIRS[key]
        o = r["old"]
        # old-value guards: the stored row must look exactly like the
        # corrupted shape before we touch it
        assert e["total"] == o["total"], f"total guard failed for {key}"
        assert e["salary"] == o["salary"], f"salary guard failed for {key}"
        assert e["bonus"] == o["bonus"], f"bonus guard failed for {key}"
        assert e.get("stock_awards", 0) == o["stock_awards"], \
            f"stock guard failed for {key}"
        assert e.get("non_equity_incentive", 0) == o["non_equity_incentive"], \
            f"neip guard failed for {key}"
        assert e.get("all_other", 0) == o["all_other"], \
            f"all_other guard failed for {key}"
        assert e["title"] == o["title"], f"title guard failed for {key}"
        assert e.get("_total_source") == "verified", \
            f"source guard failed for {key}"
        for k in COMPS:
            e[k] = r[k]
        e["total"] = r["total"]
        e["title"] = r["title"]
        # repaired row must foot against the filing mapping; Miller 2023
        # carries the filing's own $1 arithmetic gap (components sum
        # 11,929,540 vs printed 11,929,539) -- stored verbatim, stays
        # 'verified' per the 2026-09-10 $1-delta taxonomy decision
        # (GLW/310th Nelson-2024 precedent)
        gap = abs(sum(e.get(k, 0) or 0 for k in COMPS) - e["total"])
        assert gap <= 1, f"repaired row gap too large: {key} ({gap})"
        if gap:
            print(f"note: {key} carries the filing's own ${gap} gap "
                  f"(stored verbatim)")
        e["_repair_note_20261102_0100"] = NOTE
        fixed += 1
    assert fixed == 2, f"expected 2 rows fixed, got {fixed}"

    t_fixed = 0
    for e in pypl["executives"]:
        key = (e["name"], e["year"])
        if key not in TITLE_REPAIRS:
            continue
        assert e.get("_total_source") == "verified", \
            f"source guard failed for title repair {key}"
        e["title"] = TITLE_REPAIRS[key]
        e["_repair_note_20261102_0100"] = TITLE_NOTE
        t_fixed += 1
    assert t_fixed == 4, f"expected 4 title repairs, got {t_fixed}"

    # company aggregates: anchor-FY2025 scoped, untouched by 2023 repairs
    rows25 = [e for e in pypl["executives"] if e["year"] == 2025]
    assert len(rows25) == 6, f"expected 6 FY2025 rows, got {len(rows25)}"
    assert sum(e["total"] for e in rows25) == pypl["total_neo_compensation"], \
        "FY2025 anchor drift"
    assert pypl["total_neo_compensation"] == 91405702
    assert pypl["neo_count"] == 6

    data["metadata"]["total_neo_records"] = 7307
    data["metadata"]["last_dq_repair"] = "2026-11-02"
    data["last_updated"] = "2026-11-02"

    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    open(DATA, "a", encoding="utf-8").write("\n")
    print("repaired 2 PYPL rows (variant E), 4 title-only repairs; "
          "aggregates untouched (FY2025 anchor intact)")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp="2026-11-02 01:00 PT")
    print(f"phantom delta: ${delta:,}")
    assert delta == 21654617, f"unexpected phantom delta: {delta}"


if __name__ == "__main__":
    main()
