#!/usr/bin/env python3
"""DQ 2026-09-27 22:00 PT: repair salary-drop column-shift family across
AEE (4) + CHD (1) + JCI (2) + KMB (2) + WEC (2) + WRB (1) + XEL (5) = 17 rows,
plus the LW (6) split-currency / footnote-split-bonus family. 23 rows total.

Guard section-8 tripwire (salary==0, 1 < tot/ao < 2, $100K-$2.5M absolute gap)
flagged 13 rows / 8 tickers (AEE 3, CHD 1, JCI 1, KMB 2, LW 1, WEC 2, WRB 1,
XEL 2). Whole-company SCT re-reads (raw HTML table cells, digit-by-digit,
vs each company's 2026 DEF 14A SCT) caught 10 tripwire-miss siblings:

- Bonus-content shift variant (filing Bonus lands in stored.salary, nonzero
  salary cell, escapes both tripwire bands): AEE Singh 2023 ($250,000 bonus),
  JCI Brandt 2023 ($750,000 bonus), XEL Rome 2023 ($200,000), XEL Van Abel 2023
  ($200,000), XEL O'Connor 2023 ($100,000).
- Split-currency stock cell (LW's filing renders Stock Awards as a standalone
  "$" cell + separate number cell; parser dropped the value): LW Smith 2026
  ($90,121), LW Wilks 2026 ($59,712), LW Madarieta 2025 ($51,923). Stored
  totals were recomputed WITHOUT the stock value - phantom was NEGATIVE
  (stored understated). LW Wilks 2025 ($1,433,699) was misattributed to
  non_equity_incentive instead of dropped.
- Footnote-split bonus cell (Schroeder 2025 bonus renders as "(6)" + "--"
  cells; parser dropped stock_awards, shifted filing.stock->stored.options,
  filing.neip->stored.all_other): LW Schroeder 2025.

JCI Brandt 2023 is a genuine filing-side arithmetic inconsistency: filing
components sum to $4,314,666 vs printed total $3,965,627 (delta $349,039,
re-read digit-by-digit incl. raw cell markup, no footnote markers; Brandt is
not an NEO in the 2025 proxy so no restatement column exists to cross-check).
Stored filing-verbatim, total retained, labeled component_mismatch per the
2026-09-26 18:00 precedent.

Also repairs XEL name artifacts: "Tim O'ConnorFormer" -> "Tim O'Connor"
(filing: "Tim O'Connor (10) Former EVP, Chief Operations Officer") on all 3
year rows, "Ryan LongEVP" -> "Ryan Long", "Michael LambEVP" -> "Michael Lamb".

Filings re-read (all 2026 DEF 14A SCTs):
- AEE acc. 0001104659-26-037756 (filed 2026-03-31): Salary|Bonus|Stock|NEIP|
  Pension|All Other|Total - no options column
- CHD acc. 0001193125-26-115994 (filed 2026-03-19): Salary|Bonus|Stock|Options|
  NEIP|All Other|Total - no pension column
- JCI acc. 0001104659-26-004565 (filed 2026-01-16): Salary|Bonus|Stock/Unit|
  Option|NEIP|All Other|Total - no pension column
- KMB acc. 0001628280-26-020404 (filed 2026-03-23): Salary|Bonus|Stock|NEIP|
  All Other|Total - no options, no pension columns
- LW  acc. 0001679273-26-000036 (filed 2026-07-30): Fiscal Year|Salary|Bonus|
  Stock Awards ($+value split cells)|Option|NEIP|All Other|Total - no pension
- WEC acc. 0000783325-26-000035 (filed 2026-03-26): full 9-col SCT incl. pension
- WRB acc. 0001193125-26-170583 (filed 2026-04-22): Salary|Bonus|Stock|NEIP|
  All Other|Total - no options, no pension columns
- XEL acc. 0000072903-26-000063 (filed 2026-04-07): Salary|Bonus|Stock|NEIP|
  Pension|All Other|Total - no options column

All non-target rows in all 8 SCTs verified clean vs stored (CHD Dierker/Farrell/
McChesney/Raup/Read; JCI Oliver/Vandiepenbeeck/Scalia/Schlitz; KMB Hsu/Urdaneta/
Torres; WEC Lauber/Liu/Hooper/Kelsey; WRB Berkley x2/Baio/Welt/Shiel; XEL
Frenzel/Rome 2025/Long/Lamb/O'Connor 2025; AEE Lyons/Moehn/Schukar/Lindgren/
Birk 2025/Diya; LW Smith 2025/Gray 2026/Schroeder 2026/Schroeder 2024/
Madarieta 2026/Madarieta 2024) - untouched.

Phantom removed: $48,220,385 (LW split-currency rows were negative phantom:
stored understated by $285,162 total; the rest is classic ~2x overstatement).
LW FY2026 anchor re-anchored $10,395,359 -> $10,545,192 (+$90,121 Smith 2026,
+$59,712 Wilks 2026). All other repairs are non-anchor years.
22 rows relabeled def14a_verified_20260927; 1 (JCI Brandt 2023) component_mismatch.
CPT (Camden Property Trust, 4 rows Campo/Oden/Jessett/Baker 2025: salary==0
AND bonus==0, distinct signature) remains queued for its own investigation -
not the salary-drop family.
"""
import json

PATH = '/home/hatch/repos/sp500-exec-comp/data/compensation.json'
COMP = ['salary', 'bonus', 'stock_awards', 'option_awards',
        'non_equity_incentive', 'pension_nqdc', 'all_other']

# (ticker, name, year, current-stored values for drift assertion,
#  filing-verbatim repair, mismatch_delta_or_None)
ROWS = [
    # AEE - 2026 DEF 14A (no options column)
    ('AEE', 'Leonard P. Singh', 2024,
     dict(salary=0, bonus=1129033, stock_awards=723800, option_awards=0,
          non_equity_incentive=172700, pension_nqdc=77337, all_other=2727870,
          total=4830740),
     dict(salary=625000, bonus=0, stock_awards=1129033, option_awards=0,
          non_equity_incentive=723800, pension_nqdc=172700, all_other=77337,
          total=2727870), None),
    ('AEE', 'Leonard P. Singh', 2023,
     dict(salary=250000, bonus=1086882, stock_awards=565700, option_awards=0,
          non_equity_incentive=110328, pension_nqdc=104772, all_other=2702682,
          total=4820364),
     dict(salary=585000, bonus=250000, stock_awards=1086882, option_awards=0,
          non_equity_incentive=565700, pension_nqdc=110328, all_other=104772,
          total=2702682), None),  # bonus-content variant
    ('AEE', 'Mark C. Birk', 2024,
     dict(salary=0, bonus=1174177, stock_awards=787000, option_awards=0,
          non_equity_incentive=290634, pension_nqdc=72006, all_other=2973817,
          total=5297634),
     dict(salary=650000, bonus=0, stock_awards=1174177, option_awards=0,
          non_equity_incentive=787000, pension_nqdc=290634, all_other=72006,
          total=2973817), None),
    ('AEE', 'Mark C. Birk', 2023,
     dict(salary=0, bonus=1225254, stock_awards=617900, option_awards=0,
          non_equity_incentive=369238, pension_nqdc=70235, all_other=2892627,
          total=5175254),
     dict(salary=610000, bonus=0, stock_awards=1225254, option_awards=0,
          non_equity_incentive=617900, pension_nqdc=369238, all_other=70235,
          total=2892627), None),
    # CHD - 2026 DEF 14A (no pension column)
    ('CHD', 'Patrick D. de Maynadier', 2023,
     dict(salary=0, bonus=206456, stock_awards=619369, option_awards=521200,
          non_equity_incentive=102043, pension_nqdc=0, all_other=1957068,
          total=3406136),
     dict(salary=508000, bonus=0, stock_awards=206456, option_awards=619369,
          non_equity_incentive=521200, pension_nqdc=0, all_other=102043,
          total=1957068), None),
    # JCI - 2026 DEF 14A (no pension column)
    ('JCI', 'Julie Brandt', 2024,
     dict(salary=0, bonus=1360246, stock_awards=449999, option_awards=604800,
          non_equity_incentive=68411, pension_nqdc=0, all_other=3183456,
          total=5666912),
     dict(salary=700000, bonus=0, stock_awards=1360246, option_awards=449999,
          non_equity_incentive=604800, pension_nqdc=0, all_other=68411,
          total=3183456), None),
    ('JCI', 'Julie Brandt', 2023,
     dict(salary=750000, bonus=2649934, stock_awards=0, option_awards=221943,
          non_equity_incentive=7212, pension_nqdc=0, all_other=3965627,
          total=7594716),
     dict(salary=685577, bonus=750000, stock_awards=2649934, option_awards=0,
          non_equity_incentive=221943, pension_nqdc=0, all_other=7212,
          total=3965627), 349039),  # bonus-content variant + filing-side mismatch
    # KMB - 2026 DEF 14A (no options, no pension columns)
    ('KMB', 'Zackery Hicks', 2024,
     dict(salary=0, bonus=3000020, stock_awards=1272736, option_awards=0,
          non_equity_incentive=247458, pension_nqdc=0, all_other=5535214,
          total=10055428),
     dict(salary=1015000, bonus=0, stock_awards=3000020, option_awards=0,
          non_equity_incentive=1272736, pension_nqdc=0, all_other=247458,
          total=5535214), None),
    ('KMB', 'Jeffrey Melucci', 2023,
     dict(salary=0, bonus=2200105, stock_awards=1045804, option_awards=0,
          non_equity_incentive=171391, pension_nqdc=0, all_other=4258725,
          total=7676025),
     dict(salary=841425, bonus=0, stock_awards=2200105, option_awards=0,
          non_equity_incentive=1045804, pension_nqdc=0, all_other=171391,
          total=4258725), None),
    # LW - 2026 DEF 14A (split-currency stock cells; no pension column)
    ('LW', 'Michael J. Smith', 2026,
     dict(salary=1000000, bonus=0, stock_awards=0, option_awards=5704557,
          non_equity_incentive=7379936, pension_nqdc=0, all_other=1830000,
          total=15914493),
     dict(salary=1000000, bonus=0, stock_awards=90121, option_awards=5704557,
          non_equity_incentive=7379936, pension_nqdc=0, all_other=1830000,
          total=16004614), None),  # split-currency stock cell: "$" + 90,121
    ('LW', 'Sylvia J. Wilks', 2026,
     dict(salary=591539, bonus=0, stock_awards=0, option_awards=1411675,
          non_equity_incentive=2978967, pension_nqdc=0, all_other=693608,
          total=5675789),
     dict(salary=591539, bonus=0, stock_awards=59712, option_awards=1411675,
          non_equity_incentive=2978967, pension_nqdc=0, all_other=693608,
          total=5735501), None),  # split-currency stock cell: "$" + 59,712
    ('LW', 'Sylvia J. Wilks', 2025,
     dict(salary=464423, bonus=200000, stock_awards=0, option_awards=0,
          non_equity_incentive=1433699, pension_nqdc=0, all_other=0,
          total=2098122),
     dict(salary=464423, bonus=200000, stock_awards=1433699, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=26406,
          total=2124528), None),  # "$" + 1,433,699 misattributed to neip
    ('LW', 'Bernadette M. Madarieta', 2025,
     dict(salary=600000, bonus=0, stock_awards=0, option_awards=1129013,
          non_equity_incentive=0, pension_nqdc=0, all_other=0,
          total=1729013),
     dict(salary=600000, bonus=0, stock_awards=51923, option_awards=1129013,
          non_equity_incentive=0, pension_nqdc=0, all_other=0,
          total=1780936), None),  # split-currency stock cell: "$" + 51,923
    ('LW', 'Michael J. Smith', 2024,
     dict(salary=0, bonus=1985092, stock_awards=0, option_awards=0,
          non_equity_incentive=487839, pension_nqdc=0, all_other=3222931,
          total=5695862),
     dict(salary=750000, bonus=0, stock_awards=1985092, option_awards=0,
          non_equity_incentive=0, pension_nqdc=0, all_other=487839,
          total=3222931), None),  # salary-drop shift
    ('LW', 'Marc P.J.H. Schroeder', 2025,
     dict(salary=653315, bonus=0, stock_awards=0, option_awards=1081901,
          non_equity_incentive=0, pension_nqdc=0, all_other=623612,
          total=2358828),
     dict(salary=653315, bonus=0, stock_awards=1081901, option_awards=0,
          non_equity_incentive=623612, pension_nqdc=0, all_other=57150,
          total=2415978), None),  # footnote-split bonus: "(6)" + "--" cells
    # WEC - 2026 DEF 14A (full 9-col SCT)
    ('WEC', 'Robert M. Garvin', 2024,
     dict(salary=0, bonus=822725, stock_awards=157043, option_awards=881760,
          non_equity_incentive=161037, pension_nqdc=0, all_other=2663910,
          total=4686475),
     dict(salary=577692, bonus=0, stock_awards=822725, option_awards=157043,
          non_equity_incentive=881760, pension_nqdc=161037, all_other=63653,
          total=2663910), None),
    ('WEC', 'Robert M. Garvin', 2023,
     dict(salary=0, bonus=670539, stock_awards=175535, option_awards=788508,
          non_equity_incentive=156520, pension_nqdc=0, all_other=2405856,
          total=4196958),
     dict(salary=547418, bonus=0, stock_awards=670539, option_awards=175535,
          non_equity_incentive=788508, pension_nqdc=156520, all_other=67336,
          total=2405856), None),
    # WRB - 2026 DEF 14A (no options, no pension columns)
    ('WRB', 'Lucille T. Sgaglione', 2023,
     dict(salary=0, bonus=550013, stock_awards=1556515, option_awards=0,
          non_equity_incentive=106249, pension_nqdc=0, all_other=2919197,
          total=5131974),
     dict(salary=706420, bonus=0, stock_awards=550013, option_awards=0,
          non_equity_incentive=1556515, pension_nqdc=0, all_other=106249,
          total=2919197), None),
    # XEL - 2026 DEF 14A (no options column)
    ('XEL', 'Amanda Rome', 2024,
     dict(salary=0, bonus=2550098, stock_awards=355600, option_awards=0,
          non_equity_incentive=89370, pension_nqdc=45220, all_other=3740288,
          total=6780576),
     dict(salary=700000, bonus=0, stock_awards=2550098, option_awards=0,
          non_equity_incentive=355600, pension_nqdc=89370, all_other=45220,
          total=3740288), None),
    ('XEL', 'Amanda Rome', 2023,
     dict(salary=200000, bonus=1900049, stock_awards=541843, option_awards=0,
          non_equity_incentive=61965, pension_nqdc=46891, all_other=3406998,
          total=6157746),
     dict(salary=656250, bonus=200000, stock_awards=1900049, option_awards=0,
          non_equity_incentive=541843, pension_nqdc=61965, all_other=46891,
          total=3406998), None),  # bonus-content variant
    ('XEL', 'Brian Van Abel', 2023,
     dict(salary=200000, bonus=2600017, stock_awards=657900, option_awards=0,
          non_equity_incentive=346694, pension_nqdc=43301, all_other=4597912,
          total=8445824),
     dict(salary=750000, bonus=200000, stock_awards=2600017, option_awards=0,
          non_equity_incentive=657900, pension_nqdc=346694, all_other=43301,
          total=4597912), None),  # bonus-content variant
    ('XEL', "Tim O'ConnorFormer", 2024,
     dict(salary=0, bonus=1900101, stock_awards=431800, option_awards=0,
          non_equity_incentive=278386, pension_nqdc=47655, all_other=3457942,
          total=6115884),
     dict(salary=800000, bonus=0, stock_awards=1900101, option_awards=0,
          non_equity_incentive=431800, pension_nqdc=278386, all_other=47655,
          total=3457942), None),
    ('XEL', "Tim O'ConnorFormer", 2023,
     dict(salary=100000, bonus=2250018, stock_awards=679830, option_awards=0,
          non_equity_incentive=316471, pension_nqdc=36990, all_other=4158309,
          total=7541618),
     dict(salary=775000, bonus=100000, stock_awards=2250018, option_awards=0,
          non_equity_incentive=679830, pension_nqdc=316471, all_other=36990,
          total=4158309), None),  # bonus-content variant
]

# (ticker, old_name, new_name) - applied to ALL year rows
NAME_FIXES = [
    ('XEL', "Tim O'ConnorFormer", "Tim O'Connor"),
    ('XEL', 'Ryan LongEVP', 'Ryan Long'),
    ('XEL', 'Michael LambEVP', 'Michael Lamb'),
]

MISMATCH_NOTE = (
    "2026-09-27 22:00 PT: genuine filing-side arithmetic inconsistency in the "
    "JCI 2026 DEF 14A SCT (acc. 0001104659-26-004565): filing-printed components "
    "sum to $4,314,666 vs printed total $3,965,627 (delta $349,039). Re-read "
    "digit-by-digit against raw HTML table cells (no footnote markers on the "
    "row); Brandt is not an NEO in the 2025 proxy SCT so no restatement column "
    "exists to cross-check. Values stored filing-verbatim, printed total "
    "retained, classification component_mismatch."
)

NEW_ANCHORS = {
    # aggregate anchor = fiscal_year (guard section 5), NOT proxy_fiscal_year.
    # LW fiscal_year=2024: 10,395,359 - 2,472,931 (Smith 2024 repair) = 7,922,428.
    # The 2025/2026 repairs are non-anchor years for the aggregate.
    'LW': 7922428,
}


def main():
    d = json.load(open(PATH))
    companies = d['companies'] if isinstance(d, dict) else d
    cm = {c['ticker']: c for c in companies}
    phantom = 0
    for ticker, name, year, cur, fix, mismatch in ROWS:
        c = cm[ticker]
        e = next(e for e in c['executives']
                 if e['name'] == name and e['year'] == year)
        for k, v in cur.items():
            sv = e.get(k)
            assert (sv or 0) == (v or 0), (f"DRIFT {ticker} {name} {year}: "
                                          f"stored {k}={sv} != expected {v}")
        if mismatch is None:
            # filing-verbatim footing check
            assert sum(fix[k] for k in COMP) == fix['total'], \
                (f"FOOTING {ticker} {name} {year}")
        else:
            # genuine filing-side inconsistency: verify the documented delta
            delta = sum(fix[k] for k in COMP) - fix['total']
            assert delta == mismatch, \
                (f"MISMATCH-DELTA {ticker} {name} {year}: {delta}")
        phantom += e['total'] - fix['total']
        for k in COMP + ['total']:
            e[k] = fix[k]
        if mismatch is None:
            e['_total_source'] = 'def14a_verified_20260927'
        else:
            e['_total_source'] = 'component_mismatch'
            e['_parse_note'] = MISMATCH_NOTE
        print(f"repaired {ticker} {year} {name}: "
              f"${cur['total']:,} -> ${fix['total']:,}")
    for ticker, old, new in NAME_FIXES:
        c = cm[ticker]
        n = 0
        for e in c['executives']:
            if e['name'] == old:
                e['name'] = new
                n += 1
        print(f"renamed {ticker}: {old!r} -> {new!r} ({n} rows)")
        assert n > 0, f"NAME-FIX no rows matched {ticker} {old}"
    for ticker, new_total in NEW_ANCHORS.items():
        c = cm[ticker]
        old = c['total_neo_compensation']
        anchor_year = c['fiscal_year']  # guard section 5 convention
        s = sum(e['total'] for e in c['executives']
                if e['year'] == anchor_year)
        assert s == new_total, (f"ANCHOR {ticker} {anchor_year} sum "
                                f"{s} != {new_total}")
        c['total_neo_compensation'] = new_total
        print(f"{ticker} total_neo_compensation {old:,} -> {new_total:,}")
    d['last_updated'] = '2026-09-27'
    d['metadata']['last_dq_repair'] = '2026-09-27'
    json.dump(d, open(PATH, 'w'), indent=1)
    print(f"phantom removed: ${phantom:,}")


if __name__ == '__main__':
    main()
