#!/usr/bin/env python3
"""314th review (2026-11-02 06:30 PT): tranche-5 tier-1 arbitration repairs.

VRTX (12 rows): the 2026 DEF 14A SCT (acc. 0000875320-26-000153) has columns
  Salary | Bonus | Stock Awards(1) | Non-Equity Incentive Plan Compensation |
  All Other Compensation | Total -- NO Option Awards column, NO pension column.
  The legacy parse misfiled filing Stock Awards -> stored non_equity_incentive
  and filing NEIP -> stored pension_nqdc, with stored stock_awards = 0
  (new variant H: stock-drop right-shift on an option-less SCT). All Other
  survived; every stored total foots exactly against the misfiled mapping,
  which is why only Kewalramani 2025 (all_other $423,351 >= $300k) tripped
  tier-1 -- the other 11 rows are the documented all_other-gate blind spot.

FAST (2 rows): Florness 2025/2024. The 2026 DEF 14A SCT
  (acc. 0000815556-26-000017) carries a standalone "(5)" footnote-marker cell
  on Florness's Salary cell ("This amount includes $50,000 paid to Mr.
  Florness ... as one of our directors"). The legacy parse consumed the marker
  as a data cell, shifting Option Awards -> non_equity_incentive,
  NEIP -> all_other, dropping the genuine All Other cell ($2,941 / $2,754)
  and recomputing the total. Florness 2023 was already repaired filing-verbatim
  (def14a_verified_20260910); all other FAST NEOs have no marker cell and
  parsed correctly (spot-checked Watts/Tunnicliff/Lisowski/Miller/Soderberg/
  Lewis 2025 against the filing -- all byte-equal).

False positives adjudicated this run (stored byte-equal to primary SCTs,
no data changes): CHTR Winfrey 2025, CPB Anderson 2026, DVA Rodriguez 2023,
EFX Horvath 2025, LII Maskara 2023, LYV Rapino 2023.

Conventions: old-value guards on every repaired field; exact-footing
assertions; backup before write; compensation.json round-trips with
ensure_ascii=False, indent=1, trailing newline; __main__ honored.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import phantom_record

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(REPO, "data",
                      "compensation_backup_20261102_0630_pre_vrtx_fast.json")
STAMP = "2026-11-02 06:30 PT"

VRTX_ACC = "0000875320-26-000153"
VRTX_URL = ("https://www.sec.gov/Archives/edgar/data/875320/"
            "000087532026000153/vrtx-20260402.htm")
FAST_ACC = "0000815556-26-000017"
FAST_URL = ("https://www.sec.gov/Archives/edgar/data/815556/"
            "000081555626000017/fast-20260225.htm")

# (name, year, salary, filing_stock, filing_neip, filing_all_other, filing_total)
VRTX_ROWS = [
    ("Reshma Kewalramani", 2025, 1600000, 15002270, 4118640, 423351, 21144261),
    ("Reshma Kewalramani", 2024, 1541154, 15002202, 4941600, 53712, 21538668),
    ("Reshma Kewalramani", 2023, 1500000, 15001894, 4050000, 42547, 20594441),
    ("Charles F Wagner Jr", 2025, 974808, 5250817, 1965000, 51184, 8241809),
    ("Charles F Wagner Jr", 2024, 876443, 5250328, 1821150, 51519, 7999440),
    ("Charles F Wagner Jr", 2023, 825000, 5250552, 1256063, 40136, 7371751),
    ("Carmen Bozic", 2025, 835000, 4375531, 1378251, 57539, 6646321),
    ("Amit Sachdev", 2025, 700000, 4900522, 1155420, 21301, 6777243),
    ("Nia Tatsis", 2025, 750000, 4900522, 1282163, 42235, 6974920),
    ("Stuart A Arbuckle", 2025, 521486, 9341927, 0, 132934, 9996347),
    ("Stuart A Arbuckle", 2024, 941154, 6234857, 2130000, 77452, 9383463),
    ("Stuart A Arbuckle", 2023, 900000, 6234712, 1822500, 41737, 8998949),
]

# (name, year, salary, filing_option, filing_neip, filing_all_other, filing_total)
FAST_ROWS = [
    ("Daniel L. Florness", 2025, 750000, 861387, 2569000, 2941, 4183328),
    ("Daniel L. Florness", 2024, 750000, 867883, 75250, 2754, 1695887),
]

VRTX_NOTE = (
    f"{STAMP} (314th review): 2026 DEF 14A SCT (acc. {VRTX_ACC}) has no "
    "Option Awards / pension columns; legacy parse misfiled Stock Awards -> "
    "non_equity_incentive and NEIP -> pension_nqdc with stock_awards=0 "
    "(variant H). Repaired filing-verbatim."
)
FAST_NOTE = (
    f"{STAMP} (314th review): 2026 DEF 14A SCT (acc. {FAST_ACC}); the (5) "
    "footnote-marker cell on Salary shifted Option->non_equity_incentive, "
    "NEIP->all_other, dropped All Other and recomputed total. Repaired "
    "filing-verbatim."
)


def foot(row):
    g = lambda k: row.get(k) if isinstance(row.get(k), (int, float)) else 0
    return (g("salary") + g("bonus") + g("stock_awards") + g("option_awards")
            + g("non_equity_incentive") + g("pension_nqdc") + g("all_other"))


def main():
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    by_ticker = {c["ticker"]: c for c in d["companies"]}

    def find_row(ticker, name, year):
        c = by_ticker[ticker]
        hits = [e for e in c["executives"]
                if e["name"] == name and e["year"] == year]
        assert len(hits) == 1, f"{ticker} {name} {year}: {len(hits)} hits"
        return c, hits[0]

    # ---- VRTX: variant-H relabel (total-neutral) ----
    for name, year, sal, f_stock, f_neip, f_all, f_total in VRTX_ROWS:
        c, e = find_row("VRTX", name, year)
        # old-value guards: stored state must match the known corrupt mapping
        assert e["salary"] == sal, (name, year, "salary")
        assert e.get("stock_awards") == 0, (name, year, "stock_awards")
        assert e["non_equity_incentive"] == f_stock, (name, year, "neip==filing stock")
        assert e["pension_nqdc"] == f_neip, (name, year, "pension==filing neip")
        assert e["all_other"] == f_all, (name, year, "all_other")
        assert e["total"] == f_total, (name, year, "total")
        # repair
        e["stock_awards"] = f_stock
        e["non_equity_incentive"] = f_neip
        e["pension_nqdc"] = 0
        e["_accession"] = VRTX_ACC
        e["_filing_url"] = VRTX_URL
        e["_repair_note_20261102_0630"] = VRTX_NOTE
        assert foot(e) == e["total"], (name, year, "footing", foot(e), e["total"])

    # ---- FAST: (5)-marker shift repair (total changes) ----
    for name, year, sal, f_opt, f_neip, f_all, f_total in FAST_ROWS:
        c, e = find_row("FAST", name, year)
        assert e["salary"] == sal, (name, year, "salary")
        assert e.get("stock_awards") == 0, (name, year, "stock_awards")
        assert e.get("option_awards") == 0, (name, year, "option_awards")
        assert e["non_equity_incentive"] == f_opt, (name, year, "neip==filing option")
        assert e["all_other"] == f_neip, (name, year, "all_other==filing neip")
        assert e["pension_nqdc"] == 0, (name, year, "pension")
        # repair
        e["option_awards"] = f_opt
        e["non_equity_incentive"] = f_neip
        e["all_other"] = f_all
        e["total"] = f_total
        e["_accession"] = FAST_ACC
        e["_filing_url"] = FAST_URL
        e["_repair_note_20261102_0630"] = FAST_NOTE
        assert foot(e) == e["total"], (name, year, "footing", foot(e), e["total"])

    # ---- FAST anchor-FY2025 aggregate: Florness 2025 total +$2,941 ----
    fc = by_ticker["FAST"]
    pre_agg = fc["total_neo_compensation"]
    anchor_rows = [e for e in fc["executives"] if e["year"] == fc["fiscal_year"]]
    recomputed = sum(e["total"] for e in anchor_rows)
    assert len(anchor_rows) == fc["neo_count"], "FAST anchor row count"
    assert recomputed == pre_agg + 2941, (recomputed, pre_agg)
    fc["total_neo_compensation"] = recomputed

    # ---- write ----
    shutil.copy2(DATA, BACKUP)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")

    delta = phantom_record.record_batch(
        pre_path=BACKUP, data_path=DATA, stamp=f"{STAMP} (314th review)")
    print(f"phantom delta: ${delta:,}")
    assert delta == -5695, f"unexpected phantom delta {delta}"
    print("OK: 12 VRTX + 2 FAST rows repaired; FAST aggregate",
          f"{pre_agg} -> {recomputed}")


if __name__ == "__main__":
    main()
