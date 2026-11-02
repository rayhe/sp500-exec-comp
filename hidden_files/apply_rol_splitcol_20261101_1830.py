#!/usr/bin/env python3
"""308th review (2026-11-01 18:30 PT): ROL split-column SCT repair.

The tier-1 column-drop detector (detect_columndrop_siblings_20261101_1830.py)
flagged 9 ROL rows. Filing arbitration against the 2026 DEF 14A SCT
(acc. 0000084839-26-000014, filed 2026-03-17; raw HTML at goal
hidden_files/dq_20261101_1830/rol_2026_def14a.htm, SCT dumped to
rol_2026_sct_dump.txt) shows a NEW corruption sub-family: ROL's SCT splits
Equity Awards into RSA and PSU sub-columns. The parser handled the split
correctly for the 2024 rows (stock_awards = RSA+PSU, 14-key enriched rows)
but dropped the RSA sub-column on the legacy 2023/2025 rows, shifting
PSU->non_equity_incentive, NEIP->all_other, and recomputing the total
(BALL column-drop family, variant C: split-column). Gary Rollins 2025 had
no equity at all but the parse additionally dropped All Other $624,393 and
kept total = salary.

All 10 legacy rows (5 NEOs x 2023/2025) repaired filing-verbatim below;
the 2026 proxy SCT prints 2025/2024/2023 so it is authoritative for all
three years. The 2024 rows foot against the filing already (verified
no-change). Pay-ratio section independently confirms Gahlhoff 2025 total
$8,966,870 and discloses 137:1 (median $65,116).

Row schema: legacy omitted-zero rows keep their schema; stock_awards /
all_other keys are ADDED only where the filing value is non-zero (material
values must be stored). Titles and _total_source ('verified') untouched
(305th/306th precedent).
"""
import json
import shutil
import statistics
import sys
from datetime import datetime

sys.path.insert(0, "/home/hatch/repos/sp500-exec-comp/hidden_files")
import phantom_record

REPO = "/home/hatch/repos/sp500-exec-comp"
DATA = f"{REPO}/data/compensation.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M")
BACKUP = f"{REPO}/data/compensation_backup_{STAMP}_pre_rol_splitcol.json"

# (name, year): filing-verbatim components. stock_awards = RSA + PSU.
REPAIRS = {
    ("Gary W. Rollins", 2025): dict(salary=1449000, stock_awards=0,
        non_equity_incentive=0, all_other=624393, total=2073393),
    ("Gary W. Rollins", 2023): dict(salary=1449000, stock_awards=2431015,
        non_equity_incentive=2148142, all_other=545489, total=6573646),
    ("John F. Wilson", 2025): dict(salary=600000, stock_awards=844118,
        non_equity_incentive=457500, all_other=47756, total=1949374),
    ("John F. Wilson", 2023): dict(salary=400000, stock_awards=445658,
        non_equity_incentive=355000, all_other=38163, total=1238821),
    ("Jerry E. Gahlhoff, Jr", 2025): dict(salary=1100000, stock_awards=6128643,
        non_equity_incentive=1683000, all_other=55227, total=8966870),
    ("Jerry E. Gahlhoff, Jr", 2023): dict(salary=1000000, stock_awards=3918025,
        non_equity_incentive=1785000, all_other=40864, total=6743889),
    ("Kenneth D. Krause", 2025): dict(salary=765000, stock_awards=2636101,
        non_equity_incentive=780300, all_other=49707, total=4231108),
    ("Kenneth D. Krause", 2023): dict(salary=702000, stock_awards=1572044,
        non_equity_incentive=835380, all_other=228470, total=3337894),
    ("Elizabeth B. Chandler", 2025): dict(salary=578000, stock_awards=1193351,
        non_equity_incentive=442170, all_other=44720, total=2258241),
    ("Elizabeth B. Chandler", 2023): dict(salary=538200, stock_awards=449727,
        non_equity_incentive=480344, all_other=36019, total=1504290),
}

# pre-repair stored totals asserted before any write (old-value guard)
OLD_TOTALS = {
    ("Gary W. Rollins", 2025): 1449000,
    ("Gary W. Rollins", 2023): 4400057,
    ("John F. Wilson", 2025): 1298490,
    ("John F. Wilson", 2023): 902173,
    ("Jerry E. Gahlhoff, Jr", 2025): 4510095,
    ("Jerry E. Gahlhoff, Jr", 2023): 4079070,
    ("Kenneth D. Krause", 2025): 2449013,
    ("Kenneth D. Krause", 2023): 2056586,
    ("Elizabeth B. Chandler", 2025): 1482068,
    ("Elizabeth B. Chandler", 2023): 1167072,
}


def main():
    shutil.copy2(DATA, BACKUP)
    print("backup:", BACKUP)
    data = json.load(open(DATA, encoding="utf-8"))
    cos = data["companies"]
    rol = next(c for c in cos if c["ticker"] == "ROL")

    fixed = 0
    for e in rol["executives"]:
        key = (e["name"], e["year"])
        if key not in REPAIRS:
            continue
        assert e["total"] == OLD_TOTALS[key], \
            f"unexpected stored total for {key}: {e['total']}"
        assert e.get("_total_source") == "verified", \
            f"unexpected _total_source for {key}"
        r = REPAIRS[key]
        # filing-verbatim footing: sal + stk + neip + ao == total
        # (ROL SCT has no bonus/option/pension columns; dashes -> 0)
        assert r["salary"] + r["stock_awards"] + r["non_equity_incentive"] \
            + r["all_other"] == r["total"], f"filing row does not foot: {key}"
        e["salary"] = r["salary"]
        if r["stock_awards"]:
            e["stock_awards"] = r["stock_awards"]
        e["non_equity_incentive"] = r["non_equity_incentive"]
        e["all_other"] = r["all_other"]
        e["total"] = r["total"]
        e["_repair_note_20261101_1830"] = (
            "2026-11-01 18:30 PT (308th review): 2026 DEF 14A SCT "
            "(acc. 0000084839-26-000014) splits Equity Awards into RSA/PSU "
            "sub-columns; legacy parse dropped the RSA sub-column "
            "(PSU->NEIP, NEIP->All Other shift, total recomputed). "
            "Repaired filing-verbatim; stock_awards = RSA + PSU.")
        fixed += 1
    assert fixed == 10, f"expected 10 rows fixed, got {fixed}"

    # company aggregates, anchor FY2025 scoped (section-5 semantics)
    rows25 = [e for e in rol["executives"] if e["year"] == 2025]
    assert len(rows25) == 5
    rol["total_neo_compensation"] = sum(e["total"] for e in rows25)
    assert rol["total_neo_compensation"] == 19478986
    rol["neo_count"] = 5
    gahl = next(e for e in rows25 if e["name"] == "Jerry E. Gahlhoff, Jr")
    rol["total_compensation"] = gahl["total"]
    assert rol["total_compensation"] == 8966870
    # pay-ratio: 2026 proxy discloses 137:1, PEO $8,966,870, median $65,116
    rol["pay_ratio"] = 137
    rol["median_worker_pay"] = 65116

    # section-17 aggregate recompute (guard's exact semantics)
    ceo_pays = [c["total_compensation"] for c in cos
                if c.get("total_compensation", 0) > 0]
    worker_pays = [c["median_worker_pay"] for c in cos
                   if c.get("median_worker_pay") and c["median_worker_pay"] > 0]
    ratios = [c["pay_ratio"] for c in cos
              if c.get("pay_ratio") is not None and c["pay_ratio"] > 0]
    agg = data["metadata"]["aggregate_stats"]
    agg["median_ceo_pay"] = int(statistics.median(ceo_pays))
    agg["mean_ceo_pay"] = int(statistics.mean(ceo_pays))
    agg["max_ceo_pay"] = max(ceo_pays)
    agg["min_ceo_pay"] = min(ceo_pays)
    agg["median_worker_pay"] = int(statistics.median(worker_pays))
    agg["median_pay_ratio"] = int(statistics.median(ratios))

    sector_pays = {}
    for c in cos:
        if c.get("total_compensation", 0) > 0:
            sector_pays.setdefault(c.get("sector", "Unknown"), []).append(
                c["total_compensation"])
    sm = data["metadata"]["sector_medians"]
    for s, p in sector_pays.items():
        e = sm[s]
        e["median_ceo_pay"] = int(statistics.median(p))
        e["count"] = len(p)
        e["min"] = min(p)
        e["max"] = max(p)

    # DQ-batch timestamp convention
    data["metadata"]["last_dq_repair"] = "2026-11-01"
    data["last_updated"] = "2026-11-01"

    json.dump(data, open(DATA, "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    open(DATA, "a", encoding="utf-8").write("\n")
    print("repaired 10 ROL rows; company aggregates + section-17 recomputed")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp="2026-11-01 18:30 PT")
    print(f"phantom delta: ${delta:,}")


if __name__ == "__main__":
    main()
