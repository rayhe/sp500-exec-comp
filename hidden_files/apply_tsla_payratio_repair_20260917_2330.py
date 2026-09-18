"""DQ repair 2026-09-17 23:30 PT: TSLA FY2025 pay-ratio + median-worker-pay + sparse-row fix.

Primary source: Tesla, Inc. 10-K/A Amendment No. 1 for FY ended 2025-12-31,
filed 2026-04-30 (SEC EDGAR 1318605 / tm2611837d1_10ka.htm), Item 11.

Verified filing-verbatim this run:
  - SCT: Elon Musk 2025 Stock Awards $158,359,009,867 (fn.3: $132,298,849,867
    2025 CEO Performance Award max grant-date fair value + $26,060,160,000
    2025 CEO Interim Award, forfeited in full April 2026); Salary/Bonus/
    Option Awards/NEIP/All Other all "---" (= 0); Total $158,359,009,867.
  - Pay-ratio disclosure: "Mr. Musk's 2025 annual total compensation, as
    reported under 'Summary Compensation Table,' was $158,359,009,867 ...
    The median 2025 annual total compensation of all other qualifying
    employees ... was $62,786. Consequently, the applicable ratio of such
    amounts for 2025 was 2,522,203:1."
  - Cross-check: 158,359,009,867 / 62,786 = 2,522,202.9 ~= 2,522,203.

Repairs:
  1. companies[TSLA].pay_ratio: 0 -> 2522203 (was the only 0 in the dataset;
     TSLA was excluded from every pay_ratio>0 screen: medians, scatter,
     Extreme Ratios insight, dataq pay-ratio consistency screen).
  2. companies[TSLA].median_worker_pay: 57243 -> 62786 (stale prior-year value).
  3. Musk 2025 exec row: add the six missing zero component keys
     (salary/bonus/option_awards/non_equity_incentive/pension_nqdc/all_other)
     so it matches the full 12-key schema of the other 6,784 rows.
     It was the only row of 6,785 missing the salary key.

No bucket moves, no row-count change, company totals unchanged.
"""
import json, shutil, sys

PATH = "data/compensation.json"

with open(PATH, encoding="utf-8") as f:
    d = json.load(f)

n_rows_before = sum(len(c.get("executives", [])) for c in d["companies"])

tsla = next(c for c in d["companies"] if c.get("ticker") == "TSLA")
assert tsla["pay_ratio"] == 0, f"unexpected pay_ratio {tsla['pay_ratio']}"
assert tsla["median_worker_pay"] == 57243, f"unexpected mw {tsla['median_worker_pay']}"

tsla["pay_ratio"] = 2522203
tsla["median_worker_pay"] = 62786

musk25 = next(
    e for e in tsla["executives"]
    if e.get("name") == "Elon Musk" and e.get("year") == 2025
)
assert musk25["stock_awards"] == 158359009867
assert musk25["total"] == 158359009867
for k in ("salary", "bonus", "option_awards", "non_equity_incentive",
          "pension_nqdc", "all_other"):
    assert k not in musk25, f"{k} unexpectedly present"
    musk25[k] = 0

# 8-component foot (pension_nqdc + 7 SCT components)
foot = (musk25["salary"] + musk25["bonus"] + musk25["stock_awards"]
        + musk25["option_awards"] + musk25["non_equity_incentive"]
        + musk25["pension_nqdc"] + musk25["all_other"])
assert foot == musk25["total"], f"foot {foot} != total {musk25['total']}"

# pay-ratio cross-check against filing numbers
r = (tsla["total_compensation"] / tsla["median_worker_pay"]) / tsla["pay_ratio"]
assert abs(r - 1) < 1e-6, f"ratio cross-check failed: {r}"

n_rows_after = sum(len(c.get("executives", [])) for c in d["companies"])
assert n_rows_before == n_rows_after == 6785, (n_rows_before, n_rows_after)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
    f.write("\n")

print("OK: TSLA pay_ratio 0->2522203, median_worker_pay 57243->62786, "
      "Musk 2025 row normalized to 12 keys; 8-component foot exact; "
      "ratio cross-check |r-1| = %.2e; rows %d" % (abs(r - 1), n_rows_after))
