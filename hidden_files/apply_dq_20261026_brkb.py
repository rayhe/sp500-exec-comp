"""DQ repair 2026-10-26: BRK-B SCT rows -> 2026 DEF 14A verbatim.

Finding (232nd review audit): BRK-B was the ONLY company whose
fiscal_year (2024) lagged its proxy_fiscal_year (2025), and its stored
2023/2024 SCT rows gave all four NEOs exactly $100,000 (Buffett's salary
pattern copied across NEOs) with no Buffett 2025 row at all. The prior
_index_note's claim ("no FY2025 Buffett SCT row exists") is FALSE.

Primary source: Berkshire Hathaway 2026 DEF 14A, filed 2026-03-13,
accession 0001193125-26-106253 (d882687ddef14a.htm), Summary
Compensation Table (three years ended 2025-12-31):
  Buffett 2025: salary 100,000 + other 289,488 (security) = 389,488
  Buffett 2024: salary 100,000 + other 305,111 = 405,111
  Buffett 2023: salary 100,000 + other 313,595 = 413,595
  Abel    2025: 22,000,000 + 17,500 = 22,017,500 (unchanged)
  Abel    2024: 21,000,000 + 17,250 = 21,017,250
  Abel    2023: 20,000,000 + 16,500 = 20,016,500
  Jain: identical to Abel all three years.
  Hamburg 2025: 4,312,500 + 17,500 = 4,330,000 (unchanged)
  Hamburg 2024: 4,062,500 + 18,546 = 4,081,046
  Hamburg 2023: 3,812,500 + 40,961 = 3,853,461
All other components are 0 (Berkshire pays no bonus/equity to NEOs).

Cross-check: the pay-vs-performance panel in the SAME filing already
carries these PEO totals (2025 389,488; 2024 405,111; 2023 413,595)
and non-PEO averages that foot to the repaired rows (2025: mean of
22,017,500 + 22,017,500 + 4,330,000 = 16,121,667; 2024: 15,371,849).
PvP file needs no change.

Company anchor: Buffett was PEO for all of FY2025 (retired as CEO
2026-01-01; Abel CEO from 2026-01-01 per the same proxy), so the
anchor advances to FY2025 with Buffett, NOT to Abel: the proxy's pay
ratio disclosure is Buffett-based (median $93,709, 4.16:1), and no
Abel-based pay ratio exists until the 2027 proxy. total_neo for
FY2025 = 389,488 + 22,017,500 + 22,017,500 + 4,330,000 = 48,754,488.
"""
import json

PATH = "data/compensation.json"
ACC = "0001193125-26-106253"

# (name, year) -> (salary, all_other, total)
FIX = {
    ("Warren E. Buffett", 2023): (100000, 313595, 413595),
    ("Warren E. Buffett", 2024): (100000, 305111, 405111),
    ("Gregory E. Abel", 2023): (20000000, 16500, 20016500),
    ("Gregory E. Abel", 2024): (21000000, 17250, 21017250),
    ("Ajit Jain", 2023): (20000000, 16500, 20016500),
    ("Ajit Jain", 2024): (21000000, 17250, 21017250),
    ("Marc D. Hamburg", 2023): (3812500, 40961, 3853461),
    ("Marc D. Hamburg", 2024): (4062500, 18546, 4081046),
}

NOTE = (
    "2026-10-26: repaired to 2026 DEF 14A SCT verbatim (acc. "
    + ACC
    + ", filed 2026-03-13); prior stored row was incorrect."
)

with open(PATH) as f:
    data = json.load(f)

company = next(c for c in data["companies"] if c["ticker"] == "BRK-B")
assert company["filing_url"].endswith("d882687ddef14a.htm"), company["filing_url"]

changed = 0
for e in company["executives"]:
    key = (e["name"], e["year"])
    if key in FIX:
        sal, other, total = FIX[key]
        e["salary"] = sal
        e["all_other"] = other
        e["total"] = total
        e["_total_source"] = "verified"
        e["_repair_note"] = NOTE
        # Drop the 2026-09-04 _fix_note on these rows: it described the
        # old (wrong) row state ("zeroed all_other"), which the filing
        # values now supersede.
        e.pop("_fix_note", None)
        changed += 1
assert changed == 8, changed

# Add the missing Buffett FY2025 row, grouped with his other rows.
assert not any(
    e["name"] == "Warren E. Buffett" and e["year"] == 2025
    for e in company["executives"]
)
buffett_idx = max(
    i for i, e in enumerate(company["executives"]) if e["name"] == "Warren E. Buffett"
)
company["executives"].insert(
    buffett_idx + 1,
    {
        "name": "Warren E. Buffett",
        "title": "Chief Executive Officer/Chairman",
        "year": 2025,
        "salary": 100000,
        "bonus": 0,
        "stock_awards": 0,
        "option_awards": 0,
        "non_equity_incentive": 0,
        "pension_nqdc": 0,
        "all_other": 289488,
        "total": 389488,
        "_total_source": "verified",
        "_repair_note": (
            "2026-10-26: added; missing from stored data. 2026 DEF 14A SCT "
            "verbatim (acc. " + ACC + "): salary 100,000 + personal/home "
            "security 289,488 = 389,488."
        ),
    },
)

company["fiscal_year"] = 2025
company["total_compensation"] = 389488
company["source"] = "SEC DEF 14A 2026 \u2014 FY2025 CEO"
company["median_worker_pay"] = 93709
company["pay_ratio"] = 4.16
company["total_neo_compensation"] = 48754488
company["neo_count"] = 4
company["_index_note"] = (
    "CEO transition: Warren E. Buffett was PEO for all of FY2025 (retired as "
    "CEO 2026-01-01; Gregory E. Abel CEO from 2026-01-01, per the 2026 DEF "
    "14A). Anchor is FY2025 with Buffett because the 2026 proxy's pay-ratio "
    "disclosure is Buffett-based (median $93,709, 4.16:1); display switches "
    "to Abel when the 2027 proxy discloses an Abel-based pay ratio. SCT rows "
    "repaired 2026-10-26 to filing-verbatim values (acc. 0001193125-26-106253): "
    "prior stored 2023/2024 rows wrongly gave all four NEOs $100,000 and the "
    "Buffett FY2025 row was missing."
)

# Internal consistency assertions (mirror guard section 5/6).
fy = company["fiscal_year"]
rows = [e for e in company["executives"] if e["year"] == fy]
assert sum(e["total"] for e in rows) == 48754488, sum(e["total"] for e in rows)
assert len(rows) == 4
assert any(
    e["name"] == company["ceo_name"] and e["total"] == company["total_compensation"]
    for e in company["executives"]
)
for e in company["executives"]:
    comp_sum = sum(
        e[k]
        for k in (
            "salary",
            "bonus",
            "stock_awards",
            "option_awards",
            "non_equity_incentive",
            "pension_nqdc",
            "all_other",
        )
    )
    assert comp_sum == e["total"], (e["name"], e["year"], comp_sum, e["total"])

with open(PATH, "w") as f:
    json.dump(data, f, indent=1, ensure_ascii=False)
    f.write("\n")
print("BRK-B repaired: 8 rows corrected, 1 row added, anchor advanced to FY2025")
