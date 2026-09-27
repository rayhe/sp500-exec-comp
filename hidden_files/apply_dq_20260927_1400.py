#!/usr/bin/env python3
"""DQ 2026-09-27 14:00 PT: repair GNRC (5) + CTSH (12) + INVH (4) = 21 rows.

Continuation of the DG/PCG/FITB salary-drop column-shift campaign. Guard
section-8 tripwire flagged 26 candidates / 12 tickers; this batch repairs the
three largest families (GNRC 5, CTSH 4 candidates, INVH 4 candidates) plus 8
sibling rows found broken during the filing re-reads.

Filing re-reads (raw HTML table cells, digit-by-digit):
- GNRC: 2026 DEF 14A SCT (acc. 0001104659-26-051499, filed 2026-04-29),
  table 90 (Salary|Bonus|Stock|Options|NEIP|All Other|Total - NO pension
  column). 2023/2024 columns cross-checked identical vs the 2025 DEF 14A
  SCT (acc. 0001104659-25-040848, table 89).
  Shift signature: parser dropped the Salary cell, filing.stock->stored.bonus,
  filing.options->stored.stock_awards, filing.neip->stored.option_awards,
  filing.all_other->stored.non_equity_incentive, filing.total->stored.all_other,
  stored.total recomputed ~2x.
  NOTE: GNRC Taffe 2023 components sum to 2,231,414 but the filing prints
  2,231,115 - a genuine $299 FILING-SIDE arithmetic inconsistency present in
  BOTH the 2025 and 2026 proxies (digit-by-digit re-read confirmed; NOT a
  transposition). Relabeled component_mismatch per taxonomy (SBUX/FDS precedent).
- CTSH: 2026 DEF 14A SCT (acc. 0001308179-26-000290, filed 2026-04-17),
  table 164 (Salary|Bonus|Stock Awards|NEIP Comp.|All Other Comp.|SEC Total -
  NO options column). 2023/2024 columns cross-checked identical vs the 2025
  DEF 14A SCT (acc. 0001359948-25-000472, table 137); NO restatements.
  Two shift sub-families: (a) 2025 rows: salary cell dropped, stored.bonus=
  filing.salary, stored.all_other=filing.stock, stored.total recomputed;
  (b) 2023/2024 rows: parser mapped filing columns onto wrong stored fields
  (stored.stock_awards=filing.bonus / stored.neip=filing.stock / etc.),
  dropping the NEIP and All Other components, stored.total recomputed.
  Kumar 2024, Kim 2024, Kim 2025 were already correct and are untouched.
- INVH: 2026 DEF 14A SCT (acc. 0001193125-26-126310, filed 2026-03-26),
  table 266 (Salary|Bonus|Stock|Options|NEIP|All Other|Total).
  Olsen 2023/2024: same salary-drop shift as GNRC.
  Solls: the 2026 proxy SCT has a FILING-SIDE YEAR MISALIGNMENT - its Solls
  "2024" column (512,116/950,031/504,946/13,200/1,980,293) is actually 2023
  data and its "2023" column (500,000/1,852,203/364,462/12,200/2,728,865) is
  actually 2022 data; the true 2024 column is missing. Decisive evidence: the
  2025 DEF 14A SCT (acc. 0000950170-25-049911, table 144) AND the 2024 DEF 14A
  SCT (acc. 0001193125-24-085370, filed 2024-04-03, table 323) both agree:
  Solls 2023 = (512,116/950,031/504,946/13,200/1,980,293),
  Solls 2022 = (500,000/1,852,203/364,462/12,200/2,728,865),
  Solls 2024 = (523,077/1,000,036/666,437/13,800/2,203,350).
  Every other INVH NEO's 2023/2024 columns agree across all three proxies -
  the slip is isolated to Solls in the 2026 proxy. Repaired to the true
  values: 2024 from the 2025 proxy, 2023 confirmed by the 2024 proxy.
  All four repair rows foot exactly.

Anchor re-anchors (FY2024 sums):
  GNRC 20,785,267 -> 17,323,762 (Wilde -1,494,611; Ragen -1,966,894)
  CTSH 37,379,426 -> 40,131,135 (Dalal +1,469,009; Gummadi +580,643; Ayyar +702,057)
  INVH 27,939,900 -> 24,540,685 (Olsen -2,154,095; Solls -1,245,120)
Net batch delta: -$3.55M (GNRC -$7.81M incl. 2023 rows, CTSH +$12.29M net
understatement corrected, INVH -$8.04M incl. 2023 rows).
20 rows relabeled verified -> def14a_verified_20260927; Taffe 2023 ->
component_mismatch. verified_total 7046 -> 7045; component_mismatch 32 -> 33.
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "data", "compensation.json")
COMP = ["salary", "bonus", "stock_awards", "option_awards",
        "non_equity_incentive", "pension_nqdc", "all_other", "total"]

shutil.copy2(PATH, os.path.join(HERE, "compensation_backup_20260927_1400_pre_dqbatch.json"))

# (ticker, name, year, stored-now drift assertion, filing-verbatim repair, new label)
ROWS = [
    # ---- GNRC (2026 DEF 14A table 90; cross-checked 2025 DEF 14A table 89) ----
    ("GNRC", "Erik Wilde", 2023,
     dict(salary=0, bonus=489636, stock_awards=245490, option_awards=459427,
          non_equity_incentive=12250, pension_nqdc=0, all_other=1630669, total=2837472),
     dict(salary=423866, bonus=0, stock_awards=489636, option_awards=245490,
          non_equity_incentive=459427, pension_nqdc=0, all_other=12250, total=1630669),
     "def14a_verified_20260927"),
    ("GNRC", "Erik Wilde", 2024,
     dict(salary=0, bonus=655359, stock_awards=218442, option_awards=600656,
          non_equity_incentive=20154, pension_nqdc=0, all_other=1942050, total=3436661),
     dict(salary=447439, bonus=0, stock_awards=655359, option_awards=218442,
          non_equity_incentive=600656, pension_nqdc=0, all_other=20154, total=1942050),
     "def14a_verified_20260927"),
    ("GNRC", "York Ragen", 2023,
     dict(salary=0, bonus=874316, stock_awards=438418, option_awards=0,
          non_equity_incentive=19846, pension_nqdc=0, all_other=1857580, total=3190160),
     dict(salary=525000, bonus=0, stock_awards=874316, option_awards=438418,
          non_equity_incentive=0, pension_nqdc=0, all_other=19846, total=1857580),
     "def14a_verified_20260927"),
    ("GNRC", "York Ragen", 2024,
     dict(salary=0, bonus=984387, stock_awards=328138, option_awards=632936,
          non_equity_incentive=21433, pension_nqdc=0, all_other=2512044, total=4478938),
     dict(salary=545150, bonus=0, stock_awards=984387, option_awards=328138,
          non_equity_incentive=632936, pension_nqdc=0, all_other=21433, total=2512044),
     "def14a_verified_20260927"),
    ("GNRC", "Norman Taffe", 2023,
     dict(salary=0, bonus=1495415, stock_awards=248777, option_awards=50160,
          non_equity_incentive=10106, pension_nqdc=0, all_other=2231115, total=4035573),
     dict(salary=426956, bonus=0, stock_awards=1495415, option_awards=248777,
          non_equity_incentive=50160, pension_nqdc=0, all_other=10106, total=2231115),
     "component_mismatch"),  # $299 filing-side delta, both proxies agree
    # ---- CTSH (2026 DEF 14A table 164; cross-checked 2025 DEF 14A table 137) ----
    ("CTSH", "Ravi Kumar", 2025,
     dict(salary=0, bonus=1300000, stock_awards=0, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=15824498, total=17124498),
     dict(salary=1300000, bonus=0, stock_awards=15824498, option_awards=0,
          non_equity_incentive=4394000, pension_nqdc=0, all_other=13950, total=21532448),
     "def14a_verified_20260927"),
    ("CTSH", "Ravi Kumar", 2023,
     dict(salary=966036, bonus=0, stock_awards=750000, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=20252245, total=21968281),
     dict(salary=966036, bonus=750000, stock_awards=20252245, option_awards=0,
          non_equity_incentive=585224, pension_nqdc=0, all_other=9900, total=22563405),
     "def14a_verified_20260927"),
    ("CTSH", "Jatin Dalal", 2025,
     dict(salary=0, bonus=825000, stock_awards=0, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=4848082, total=5673082),
     dict(salary=825000, bonus=0, stock_awards=4848082, option_awards=0,
          non_equity_incentive=1394250, pension_nqdc=0, all_other=13950, total=7081282),
     "def14a_verified_20260927"),
    ("CTSH", "Jatin Dalal", 2024,
     dict(salary=750000, bonus=0, stock_awards=150000, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=7742990, total=8642990),
     dict(salary=750000, bonus=150000, stock_awards=7742990, option_awards=0,
          non_equity_incentive=804975, pension_nqdc=0, all_other=664034, total=10111999),
     "def14a_verified_20260927"),
    ("CTSH", "Jatin Dalal", 2023,
     dict(salary=60096, bonus=0, stock_awards=150000, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=3077457, total=3287553),
     dict(salary=60096, bonus=150000, stock_awards=3077457, option_awards=0,
          non_equity_incentive=18203, pension_nqdc=0, all_other=47958, total=3353714),
     "def14a_verified_20260927"),
    ("CTSH", "Surya Gummadi", 2025,
     dict(salary=0, bonus=800005, stock_awards=0, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=3835194, total=4635199),
     dict(salary=800005, bonus=0, stock_awards=3835194, option_awards=0,
          non_equity_incentive=984000, pension_nqdc=0, all_other=13450, total=5632649),
     "def14a_verified_20260927"),
    ("CTSH", "Surya Gummadi", 2024,
     dict(salary=725011, bonus=0, stock_awards=0, option_awards=0,
          non_equity_incentive=3195505, pension_nqdc=0, all_other=0, total=3920516),
     dict(salary=725011, bonus=0, stock_awards=3195505, option_awards=0,
          non_equity_incentive=569343, pension_nqdc=0, all_other=11300, total=4501159),
     "def14a_verified_20260927"),
    ("CTSH", "Surya Gummadi", 2023,
     dict(salary=650000, bonus=0, stock_awards=750000, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=2787355, total=4187355),
     dict(salary=650000, bonus=750000, stock_awards=2787355, option_awards=0,
          non_equity_incentive=102960, pension_nqdc=0, all_other=10050, total=4300365),
     "def14a_verified_20260927"),
    ("CTSH", "John Kim", 2023,
     dict(salary=700000, bonus=0, stock_awards=0, option_awards=0,
          non_equity_incentive=3220248, pension_nqdc=0, all_other=0, total=3920248),
     dict(salary=700000, bonus=0, stock_awards=3220248, option_awards=0,
          non_equity_incentive=212030, pension_nqdc=0, all_other=12950, total=4145228),
     "def14a_verified_20260927"),
    ("CTSH", "Balu Ganesh Ayyar", 2025,
     dict(salary=0, bonus=732941, stock_awards=0, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=1767627, total=2500568),
     dict(salary=732941, bonus=0, stock_awards=1767627, option_awards=0,
          non_equity_incentive=1355941, pension_nqdc=0, all_other=9369, total=3865878),
     "def14a_verified_20260927"),
    ("CTSH", "Balu Ganesh Ayyar", 2024,
     dict(salary=716860, bonus=0, stock_awards=0, option_awards=0,
          non_equity_incentive=1757936, pension_nqdc=0, all_other=0, total=2474796),
     dict(salary=716860, bonus=0, stock_awards=1757936, option_awards=0,
          non_equity_incentive=693276, pension_nqdc=0, all_other=8781, total=3176853),
     "def14a_verified_20260927"),
    ("CTSH", "Balu Ganesh Ayyar", 2023,
     dict(salary=713264, bonus=0, stock_awards=0, option_awards=0,
          non_equity_incentive=1817442, pension_nqdc=0, all_other=0, total=2530706),
     dict(salary=713264, bonus=0, stock_awards=1817442, option_awards=0,
          non_equity_incentive=320184, pension_nqdc=0, all_other=8459, total=2859349),
     "def14a_verified_20260927"),
    # ---- INVH (2026 DEF 14A table 266; Solls years fixed per 2025+2024 proxies) ----
    ("INVH", "Jonathan S. Olsen", 2023,
     dict(salary=0, bonus=1200045, stock_awards=0, option_awards=447645,
          non_equity_incentive=13200, pension_nqdc=0, all_other=2060909, total=3721799),
     dict(salary=400019, bonus=0, stock_awards=1200045, option_awards=0,
          non_equity_incentive=447645, pension_nqdc=0, all_other=13200, total=2060909),
     "def14a_verified_20260927"),
    ("INVH", "Jonathan S. Olsen", 2024,
     dict(salary=0, bonus=1500054, stock_awards=0, option_awards=640241,
          non_equity_incentive=13800, pension_nqdc=0, all_other=2684864, total=4838959),
     dict(salary=530769, bonus=0, stock_awards=1500054, option_awards=0,
          non_equity_incentive=640241, pension_nqdc=0, all_other=13800, total=2684864),
     "def14a_verified_20260927"),
    ("INVH", "Mark A. Solls", 2023,
     dict(salary=0, bonus=1852203, stock_awards=0, option_awards=364462,
          non_equity_incentive=12200, pension_nqdc=0, all_other=2728865, total=4957730),
     dict(salary=512116, bonus=0, stock_awards=950031, option_awards=0,
          non_equity_incentive=504946, pension_nqdc=0, all_other=13200, total=1980293),
     "def14a_verified_20260927"),
    ("INVH", "Mark A. Solls", 2024,
     dict(salary=0, bonus=950031, stock_awards=0, option_awards=504946,
          non_equity_incentive=13200, pension_nqdc=0, all_other=1980293, total=3448470),
     dict(salary=523077, bonus=0, stock_awards=1000036, option_awards=0,
          non_equity_incentive=666437, pension_nqdc=0, all_other=13800, total=2203350),
     "def14a_verified_20260927"),
]

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)
C = {c["ticker"]: c for c in data["companies"]}

ANCHOR_EXPECT = {"GNRC": 20785267, "CTSH": 37379426, "INVH": 27939900}
for t, exp in ANCHOR_EXPECT.items():
    got = C[t]["total_neo_compensation"]
    assert got == exp, (t, got, exp)

COMP8 = ["salary", "bonus", "stock_awards", "option_awards",
         "non_equity_incentive", "pension_nqdc", "pension_change", "all_other"]

n_repaired = 0
for tick, name, yr, stored_now, repair, label in ROWS:
    co = C[tick]
    e = next(x for x in co["executives"] if x["name"] == name and x["year"] == yr)
    cur = {k: (e.get(k) if isinstance(e.get(k), int) else 0) for k in COMP}
    assert cur == stored_now, (tick, name, yr, cur, stored_now)  # drift assertion
    assert e.get("_total_source") == "verified", (tick, name, yr, e.get("_total_source"))
    e.update(repair)
    e["_total_source"] = label
    # footing check (allow the documented filing-side deltas)
    s = sum(repair.get(k, 0) for k in COMP8)
    delta = abs(s - repair["total"])
    if label == "component_mismatch":
        assert delta == 299, (tick, name, yr, delta)
    else:
        assert delta == 0, (tick, name, yr, delta, s, repair["total"])
    n_repaired += 1

# re-anchor FY2024 company totals
for tick in ("GNRC", "CTSH", "INVH"):
    co = C[tick]
    co["total_neo_compensation"] = sum(
        x["total"] for x in co["executives"] if x["year"] == 2024)
    print(tick, "anchor 2024:", ANCHOR_EXPECT[tick], "->", co["total_neo_compensation"])

assert C["GNRC"]["total_neo_compensation"] == 17323762
assert C["CTSH"]["total_neo_compensation"] == 40131135
assert C["INVH"]["total_neo_compensation"] == 24540685

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=1)
print("repaired:", n_repaired)
