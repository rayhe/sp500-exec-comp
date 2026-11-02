#!/usr/bin/env python3
"""312th review (2026-11-02 02:30 PT): ARE column-drop + marker-cell-shift repair.

The tier-1 column-drop sibling detector
(hidden_files/detect_columndrop_siblings_20261101_1830.py) flagged 2 ARE rows
(Binda 2023, Kass 2023). Filing arbitration against the 2026 DEF 14A SCT
(acc. 0001035443-26-000031, filed 2026-04-01; raw HTML at goal
hidden_files/dq_20261102_0230/are_2026_def14a.htm, SCT TR-parsed from the
filing) found 7 corrupted rows, not 2:

Variant E (salary-drop left-shift, the 311th-review PYPL sub-family):
the legacy parse dropped the Salary cell on the four 2023 continuation rows
and shifted bonus->salary, stock->bonus, NEIP->stock, pension->NEIP,
all_other->pension, total->all_other, then recomputed the total. The
detector only flagged Binda/Kass 2023 because Marcus/Moglia 2023 carry
non-zero filing NEIP, so the shifted rows kept stored stock_awards > 0 --
a detector blind spot (cf. ROL Gary Rollins 2025, 308th review).
  Marcus 2023 filing: 1,255,000 / 2,000,000 / 8,089,293 / 2,823,750 /
      1,028,016 / 289,271 / 15,485,330 (foots exact; stored total 29,715,660)
  Moglia 2023 filing: 780,000 / 25,000 / 7,222,595 / 1,755,000 / 38,415 /
      48,357 / 9,869,367 (foots exact; stored total 18,958,734)
  Binda 2023 filing: 531,000 / 950,000 / 4,035,302 / -- / 128,780 / 46,098 /
      5,691,180 (foots exact; stored total 10,851,360)
  Kass 2023 filing: 625,000 / 1,755,000 / 6,516,082 / -- / 6,163 / 43,500 /
      8,945,745 (foots exact; stored total 17,266,490)

New sub-family variant F (standalone footnote-marker cell shift): the 2025
SCT rows whose Bonus cell carries a standalone footnote-marker cell
((3) Marcus $2M performance bonus award, (5) Binda $20k anniversary bonus,
(7) Cole $10k anniversary bonus) had the marker cell consumed as the Stock
Awards value, shifting stock->NEIP, NEIP->pension, pension->all_other. The
grant-date cross-check is decisive: the SCT Stock Awards column equals the
Grants of Plan-Based Awards table sum for each exec
(Marcus 1,272,996+1,580,026+2,151,183=5,004,205; Binda 406,119+3,600,000=
4,006,119; Cole 64,425+990,000+2,250,000=3,304,425).
  Marcus 2025 filing: 1,345,000 / 2,000,000 / 5,004,205 / 3,026,250 / -- /
      197,341 (fn.4 insurance premiums) / 11,572,796 (foots exact; the
      legacy parse also dropped the $197,341 All Other cell and recomputed
      the total at 11,375,455 -- +$197,341 genuine comp restored)
  Binda 2025 filing: 695,000 / 1,015,000 / 4,006,119 / -- / 2,018 / -- /
      5,718,137 (foots exact; pure relabel, total unchanged)
  Cole 2025 filing: 595,000 / 760,000 / 3,304,425 / -- / 775 / -- /
      4,660,200 (foots exact; pure relabel, total unchanged)

The DG tranche of the same detector run: Vasos 2025 + Vasos 2024 both
FALSE POSITIVE. The 2026 DEF 14A SCT (acc. 0001104659-26-040394, filed
2026-04-07; goal hidden_files/dq_20261102_0230/dg_2026_def14a.htm) shows
em-dash stock AND option cells for Vasos 2025/2024 (no equity granted; the
grants table confirms "--" for Vasos both years) -- stored rows byte-equal
(Paycom/Regeneron pattern). No data changes for DG.

Titles and _total_source ('verified') untouched per the 305th/306th ROL
precedent: the 2023 rows are continuation rows with no filing-time title,
and the filing's title block is a retrospective label for historical years
(PYPL-Chriss 311th precedent).

Filing-verbatim values re-read digit-by-digit from the raw filing HTML
(TR-level parse, tags stripped). All 7 repaired rows foot exactly (no
$1-$2 filing-side gaps).
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
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_are_columndrop.json"

COMPS = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "all_other"]

# (name, year): filing-verbatim full component mapping; old = stored shape
REPAIRS = {
    # --- variant E: salary-drop left-shift (2023 continuation rows) ---
    ("Joel S. Marcus", 2023): dict(
        salary=1255000, bonus=2000000, stock_awards=8089293, option_awards=0,
        non_equity_incentive=2823750, pension_nqdc=1028016, all_other=289271,
        total=15485330,
        old=dict(salary=2000000, bonus=8089293, stock_awards=2823750,
                 option_awards=0, non_equity_incentive=1028016,
                 pension_nqdc=289271, all_other=15485330, total=29715660)),
    ("Peter M. Moglia", 2023): dict(
        salary=780000, bonus=25000, stock_awards=7222595, option_awards=0,
        non_equity_incentive=1755000, pension_nqdc=38415, all_other=48357,
        total=9869367,
        old=dict(salary=25000, bonus=7222595, stock_awards=1755000,
                 option_awards=0, non_equity_incentive=38415,
                 pension_nqdc=48357, all_other=9869367, total=18958734)),
    ("Marc E. Binda", 2023): dict(
        salary=531000, bonus=950000, stock_awards=4035302, option_awards=0,
        non_equity_incentive=0, pension_nqdc=128780, all_other=46098,
        total=5691180,
        old=dict(salary=950000, bonus=4035302, stock_awards=0,
                 option_awards=0, non_equity_incentive=128780,
                 pension_nqdc=46098, all_other=5691180, total=10851360)),
    ("Hunter L. Kass", 2023): dict(
        salary=625000, bonus=1755000, stock_awards=6516082, option_awards=0,
        non_equity_incentive=0, pension_nqdc=6163, all_other=43500,
        total=8945745,
        old=dict(salary=1755000, bonus=6516082, stock_awards=0,
                 option_awards=0, non_equity_incentive=6163,
                 pension_nqdc=43500, all_other=8945745, total=17266490)),
    # --- variant F: standalone footnote-marker cell shift (2025 rows) ---
    ("Joel S. Marcus", 2025): dict(
        salary=1345000, bonus=2000000, stock_awards=5004205, option_awards=0,
        non_equity_incentive=3026250, pension_nqdc=0, all_other=197341,
        total=11572796,
        old=dict(salary=1345000, bonus=2000000, stock_awards=0,
                 option_awards=0, non_equity_incentive=5004205,
                 pension_nqdc=3026250, all_other=0, total=11375455)),
    ("Marc E. Binda", 2025): dict(
        salary=695000, bonus=1015000, stock_awards=4006119, option_awards=0,
        non_equity_incentive=0, pension_nqdc=2018, all_other=0,
        total=5718137,
        old=dict(salary=695000, bonus=1015000, stock_awards=0,
                 option_awards=0, non_equity_incentive=4006119,
                 pension_nqdc=0, all_other=2018, total=5718137)),
    ("John Hart Cole", 2025): dict(
        salary=595000, bonus=760000, stock_awards=3304425, option_awards=0,
        non_equity_incentive=0, pension_nqdc=775, all_other=0,
        total=4660200,
        old=dict(salary=595000, bonus=760000, stock_awards=0,
                 option_awards=0, non_equity_incentive=3304425,
                 pension_nqdc=0, all_other=775, total=4660200)),
}

NOTE = ("2026-11-02 02:30 PT (312th review): 2026 DEF 14A SCT (acc. "
        "0001035443-26-000031) shows (a) variant E of the column-drop family "
        "(salary-drop left-shift) on the four 2023 continuation rows: the "
        "legacy parse dropped the Salary cell and shifted bonus->salary, "
        "stock->bonus, NEIP->stock, pension->NEIP, all_other->pension, "
        "total->all_other, then recomputed the total; and (b) new variant F: "
        "a standalone footnote-marker cell on the Bonus column (Marcus (3), "
        "Binda (5), Cole (7)) was consumed as the Stock Awards value, "
        "shifting stock->NEIP, NEIP->pension, pension->all_other (Marcus 2025 "
        "also dropped the $197,341 All Other cell, restored). Stock Awards "
        "values cross-checked against the Grants of Plan-Based Awards table "
        "sums. Repaired filing-verbatim; titles and _total_source "
        "('verified') untouched.")


def main():
    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)
    data = json.load(open(DATA, encoding="utf-8"))
    cos = data["companies"]
    are = next(c for c in cos if c["ticker"] == "ARE")

    fixed = 0
    for e in are["executives"]:
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
        assert e.get("option_awards", 0) == o["option_awards"], \
            f"option guard failed for {key}"
        assert e.get("non_equity_incentive", 0) == o["non_equity_incentive"], \
            f"neip guard failed for {key}"
        assert e.get("pension_nqdc", 0) == o["pension_nqdc"], \
            f"pension guard failed for {key}"
        assert e.get("all_other", 0) == o["all_other"], \
            f"all_other guard failed for {key}"
        assert e.get("_total_source") == "verified", \
            f"source guard failed for {key}"
        for k in COMPS:
            e[k] = r[k]
        e["total"] = r["total"]
        # repaired rows must foot exactly against the filing mapping
        gap = abs(sum(e.get(k, 0) or 0 for k in COMPS) - e["total"])
        assert gap == 0, f"repaired row gap: {key} ({gap})"
        e["_repair_note_20261102_0230"] = NOTE
        fixed += 1
    assert fixed == 7, f"expected 7 rows fixed, got {fixed}"

    # company aggregates: anchor-FY2025 scoped; the Marcus 2025 total moved
    # (+197,341), so total_neo_compensation is recomputed with the guard's
    # exact section-5 semantics (sum of exec totals for fiscal_year)
    fy = are["fiscal_year"]
    assert fy == 2025, f"unexpected ARE fiscal_year: {fy}"
    rows25 = [e for e in are["executives"] if e["year"] == fy]
    assert len(rows25) == 6, f"expected 6 FY2025 rows, got {len(rows25)}"
    are["total_neo_compensation"] = sum(e["total"] for e in rows25)
    assert are["total_neo_compensation"] == 40471929, \
        f"unexpected FY2025 anchor sum: {are['total_neo_compensation']}"
    assert are["neo_count"] == 6
    # CEO anchor (Moglia 2025) untouched: pay ratio / median / anchor total
    assert are["total_compensation"] == 8844053
    assert are["pay_ratio"] == 92
    assert are["median_worker_pay"] == 193000

    data["metadata"]["total_neo_records"] = 7307
    data["metadata"]["last_dq_repair"] = "2026-11-02"
    data["last_updated"] = "2026-11-02"

    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    open(DATA, "a", encoding="utf-8").write("\n")
    print("repaired 7 ARE rows (4x variant E, 3x variant F); "
          "total_neo_compensation 40274588->40471929")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp="2026-11-02 02:30 PT")
    print(f"phantom delta: ${delta:,}")
    assert delta == 36603281, f"unexpected phantom delta: {delta}"


if __name__ == "__main__":
    main()
