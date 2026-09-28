#!/usr/bin/env python3
"""DQ 2026-09-28 02:00 PT: repair the CPT queued investigation + PGR sibling.

CPT (Camden Property Trust, 12 rows = 4 NEOs x 3 years) was queued by the
2026-09-27 18:00/22:00 PT batches as a separate investigation: the 2025 rows
carry a salary==0/bonus==0 signature distinct from the salary-drop family.
Whole-company SCT re-read (raw HTML table cells, digit-by-digit, vs the 2026
DEF 14A SCT, acc. 0001628280-26-021581, filed 2026-03-27) shows TWO
corruption families in one company:

Family A - classic salary-drop column shift (CPT 2024/2023 rows, 8 rows):
the parser dropped the Salary cell; filing.stock->stored.salary,
filing.neip->stored.stock, filing.all_other->stored.neip,
filing.total->stored.all_other; stored.total recomputed ~1.9x phantom.

Family B - split-currency variant (CPT 2025 rows, 4 rows): the 2026-proxy SCT
renders the latest-year row with standalone "$" cells before each value
("2025 || $ || 764,909 || $ || 4,898,680 ...", same rendering as LW's
2026-07-30 proxy). The parser mapped filing.salary->stored.stock_awards,
filing.stock->stored.all_other, dropped filing NEIP and All Other, and
recomputed total = salary+stock. Stored UNDERSTATES the filing here
(negative phantom within the batch): Campo/Oden 2025 $5,663,589 vs filing
$8,317,514.

The sibling scan (salary==0 & bonus==0 & stock>0, 23 rows dataset-wide)
found PGR (Progressive, Griffith 2025) carrying the exact Family B
signature. Whole-company PGR SCT re-read (2026 DEF 14A SCT, acc.
0000080661-26-000099, filed 2026-03-23) shows the same two families:
Griffith 2025 = Family B (filing.salary 1,094,231->stored.stock_awards,
filing.stock 11,000,278->stored.all_other, NEIP 5,443,799 + All Other
167,616 dropped; stored $12,094,509 vs filing $17,705,924), and all five
2023 rows = Family A (salary-drop shift; e.g. Griffith 2023 stored
$30,279,005 vs filing $15,636,618). PGR 2024 rows and all other 2025 rows
verified clean vs stored.

2023/2024-column cross-checks vs the prior-year proxies (CPT 2025 DEF 14A
acc. 0000906345-25-000014; PGR 2025 DEF 14A acc. 0000080661-25-000018):
identical columns, no restatements.

CPT SCT NEIP composition spot-verified: NEIP = Performance Award Program
payout + cash portion of annual bonus (Campo 2025: 2,313,245 + 337,680 =
2,650,925), so the printed NEIP values are fully explained.

All other SCT rows in both companies verified clean vs stored (CPT: none
beyond the 12; PGR: Sauerland/Callahan/Bailo/Murphy 2025 + all 2024 rows).
No name artifacts. All 18 repaired rows foot exactly; 18 relabeled
def14a_verified_20260928.

Anchors (guard section 5: fiscal_year, NOT proxy_fiscal_year):
- CPT fiscal_year=2024: total_neo_compensation 41,193,426 -> 21,936,889;
  CEO total_compensation (Jessett) 7,676,133 -> 4,151,948 (filing-verbatim).
  CPT pay_ratio stays 109 (disclosed FY2024 ratio computed on Campo's
  filing-verbatim $7,224,768 SCT total; untouched).
- PGR fiscal_year=2024: 2024 rows were clean; aggregates already correct
  (33,733,783 / 16,377,514), asserted not rewritten.

Phantom removed: $52,230,124 (CPT $29,465,012 + PGR $22,765,112), all
positive (parser overstatement); the Family B understatements are absorbed
in the net per the phantom_record convention.
"""
import json
import sys

PATH = '/home/hatch/repos/sp500-exec-comp/data/compensation.json'
COMP = ['salary', 'bonus', 'stock_awards', 'option_awards',
        'non_equity_incentive', 'pension_nqdc', 'all_other']

# (ticker, name, year, current-stored values for drift assertion,
#  filing-verbatim fix, mismatch-or-None)
ROWS = [
    # ---- CPT: Richard J. Campo, Executive Chairman ----
    ('CPT', 'Richard J. Campo', 2025,
     {'salary': 0, 'bonus': 0, 'stock_awards': 764909, 'option_awards': 0,
      'non_equity_incentive': 0, 'pension_nqdc': 0, 'all_other': 4898680,
      'total': 5663589},
     {'salary': 764909, 'bonus': 0, 'stock_awards': 4898680, 'option_awards': 0,
      'non_equity_incentive': 2650925, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 8317514},
     None),  # Family B split-currency variant
    ('CPT', 'Richard J. Campo', 2024,
     {'salary': 4033076, 'bonus': 0, 'stock_awards': 2446558, 'option_awards': 0,
      'non_equity_incentive': 2504, 'pension_nqdc': 0, 'all_other': 7224768,
      'total': 13706906},
     {'salary': 742630, 'bonus': 0, 'stock_awards': 4033076, 'option_awards': 0,
      'non_equity_incentive': 2446558, 'pension_nqdc': 0, 'all_other': 2504,
      'total': 7224768},
     None),  # Family A salary-drop shift
    ('CPT', 'Richard J. Campo', 2023,
     {'salary': 4033131, 'bonus': 0, 'stock_awards': 2154173, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 6911304,
      'total': 13101608},
     {'salary': 721000, 'bonus': 0, 'stock_awards': 4033131, 'option_awards': 0,
      'non_equity_incentive': 2154173, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 6911304},
     None),  # Family A salary-drop shift
    # ---- CPT: D. Keith Oden, Executive Vice Chairman ----
    ('CPT', 'D. Keith Oden', 2025,
     {'salary': 0, 'bonus': 0, 'stock_awards': 764909, 'option_awards': 0,
      'non_equity_incentive': 0, 'pension_nqdc': 0, 'all_other': 4898680,
      'total': 5663589},
     {'salary': 764909, 'bonus': 0, 'stock_awards': 4898680, 'option_awards': 0,
      'non_equity_incentive': 2650925, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 8317514},
     None),  # Family B
    ('CPT', 'D. Keith Oden', 2024,
     {'salary': 4033076, 'bonus': 0, 'stock_awards': 2446558, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 7225264,
      'total': 13707898},
     {'salary': 742630, 'bonus': 0, 'stock_awards': 4033076, 'option_awards': 0,
      'non_equity_incentive': 2446558, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 7225264},
     None),  # Family A
    ('CPT', 'D. Keith Oden', 2023,
     {'salary': 4033131, 'bonus': 0, 'stock_awards': 2154173, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 6911304,
      'total': 13101608},
     {'salary': 721000, 'bonus': 0, 'stock_awards': 4033131, 'option_awards': 0,
      'non_equity_incentive': 2154173, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 6911304},
     None),  # Family A
    # ---- CPT: Alexander J. Jessett, Chief Executive Officer ----
    ('CPT', 'Alexander J. Jessett', 2025,
     {'salary': 0, 'bonus': 0, 'stock_awards': 646596, 'option_awards': 0,
      'non_equity_incentive': 0, 'pension_nqdc': 0, 'all_other': 3010548,
      'total': 3657144},
     {'salary': 646596, 'bonus': 0, 'stock_awards': 3010548, 'option_awards': 0,
      'non_equity_incentive': 1491031, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 5151175},
     None),  # Family B
    ('CPT', 'Alexander J. Jessett', 2024,
     {'salary': 2138233, 'bonus': 0, 'stock_awards': 1382952, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 4151948,
      'total': 7676133},
     {'salary': 627763, 'bonus': 0, 'stock_awards': 2138233, 'option_awards': 0,
      'non_equity_incentive': 1382952, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 4151948},
     None),  # Family A
    ('CPT', 'Alexander J. Jessett', 2023,
     {'salary': 2138181, 'bonus': 0, 'stock_awards': 1113842, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 3864502,
      'total': 7119525},
     {'salary': 609479, 'bonus': 0, 'stock_awards': 2138181, 'option_awards': 0,
      'non_equity_incentive': 1113842, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 3864502},
     None),  # Family A
    # ---- CPT: Laurie A. Baker, President and Chief Operating Officer ----
    ('CPT', 'Laurie A. Baker', 2025,
     {'salary': 0, 'bonus': 0, 'stock_awards': 584349, 'option_awards': 0,
      'non_equity_incentive': 0, 'pension_nqdc': 0, 'all_other': 2067433,
      'total': 2651782},
     {'salary': 584349, 'bonus': 0, 'stock_awards': 2067433, 'option_awards': 0,
      'non_equity_incentive': 1232953, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 3887735},
     None),  # Family B
    ('CPT', 'Laurie A. Baker', 2024,
     {'salary': 1616245, 'bonus': 0, 'stock_awards': 1148335, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 3334909,
      'total': 6102489},
     {'salary': 567329, 'bonus': 0, 'stock_awards': 1616245, 'option_awards': 0,
      'non_equity_incentive': 1148335, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 3334909},
     None),  # Family A
    ('CPT', 'Laurie A. Baker', 2023,
     {'salary': 1616215, 'bonus': 0, 'stock_awards': 991463, 'option_awards': 0,
      'non_equity_incentive': 3000, 'pension_nqdc': 0, 'all_other': 3161483,
      'total': 5772161},
     {'salary': 550805, 'bonus': 0, 'stock_awards': 1616215, 'option_awards': 0,
      'non_equity_incentive': 991463, 'pension_nqdc': 0, 'all_other': 3000,
      'total': 3161483},
     None),  # Family A
    # ---- PGR: Susan Patricia Griffith, President and CEO ----
    ('PGR', 'Susan Patricia Griffith', 2025,
     {'salary': 0, 'bonus': 0, 'stock_awards': 1094231, 'option_awards': 0,
      'non_equity_incentive': 0, 'pension_nqdc': 0, 'all_other': 11000278,
      'total': 12094509},
     {'salary': 1094231, 'bonus': 0, 'stock_awards': 11000278, 'option_awards': 0,
      'non_equity_incentive': 5443799, 'pension_nqdc': 0, 'all_other': 167616,
      'total': 17705924},
     None),  # Family B split-currency variant
    ('PGR', 'Susan Patricia Griffith', 2023,
     {'salary': 10000106, 'bonus': 0, 'stock_awards': 4424327,
      'option_awards': 0, 'non_equity_incentive': 217954, 'pension_nqdc': 0,
      'all_other': 15636618, 'total': 30279005},
     {'salary': 994231, 'bonus': 0, 'stock_awards': 10000106,
      'option_awards': 0, 'non_equity_incentive': 4424327, 'pension_nqdc': 0,
      'all_other': 217954, 'total': 15636618},
     None),  # Family A salary-drop shift
    # ---- PGR: John P. Sauerland, VP and CFO ----
    ('PGR', 'John P. Sauerland', 2023,
     {'salary': 2625224, 'bonus': 0, 'stock_awards': 1861298,
      'option_awards': 0, 'non_equity_incentive': 12000, 'pension_nqdc': 0,
      'all_other': 5195637, 'total': 9694159},
     {'salary': 697115, 'bonus': 0, 'stock_awards': 2625224,
      'option_awards': 0, 'non_equity_incentive': 1861298, 'pension_nqdc': 0,
      'all_other': 12000, 'total': 5195637},
     None),  # Family A
    # ---- PGR: Patrick K. Callahan, Personal Lines President ----
    ('PGR', 'Patrick K. Callahan', 2023,
     {'salary': 2437619, 'bonus': 0, 'stock_awards': 1727798,
      'option_awards': 0, 'non_equity_incentive': 12000, 'pension_nqdc': 0,
      'all_other': 4824532, 'total': 9001949},
     {'salary': 647115, 'bonus': 0, 'stock_awards': 2437619,
      'option_awards': 0, 'non_equity_incentive': 1727798, 'pension_nqdc': 0,
      'all_other': 12000, 'total': 4824532},
     None),  # Family A
    # ---- PGR: Karen B. Bailo, Commercial Lines President ----
    ('PGR', 'Karen B. Bailo', 2023,
     {'salary': 1500148, 'bonus': 0, 'stock_awards': 1057731,
      'option_awards': 0, 'non_equity_incentive': 12000, 'pension_nqdc': 0,
      'all_other': 3164110, 'total': 5733989},
     {'salary': 594231, 'bonus': 0, 'stock_awards': 1500148,
      'option_awards': 0, 'non_equity_incentive': 1057731, 'pension_nqdc': 0,
      'all_other': 12000, 'total': 3164110},
     None),  # Family A
    # ---- PGR: John Murphy, Claims President ----
    ('PGR', 'John Murphy', 2023,
     {'salary': 1450083, 'bonus': 0, 'stock_awards': 1026239,
      'option_awards': 0, 'non_equity_incentive': 12000, 'pension_nqdc': 0,
      'all_other': 3064861, 'total': 5553183},
     {'salary': 576539, 'bonus': 0, 'stock_awards': 1450083,
      'option_awards': 0, 'non_equity_incentive': 1026239, 'pension_nqdc': 0,
      'all_other': 12000, 'total': 3064861},
     None),  # Family A
]

NEW_ANCHORS = {
    # aggregate anchor = fiscal_year (guard section 5), NOT proxy_fiscal_year.
    # CPT fiscal_year=2024: 7,224,768+7,225,264+4,151,948+3,334,909.
    'CPT': 21936889,
}

NEW_CEO_TOTALS = {
    # guard section 6: CEO total_compensation must pair with the anchor-year
    # CEO's own SCT row. CPT CEO = Alexander J. Jessett, FY2024 filing total
    # $4,151,948 (stored was the corrupted $7,676,133).
    'CPT': ('Alexander J. Jessett', 4151948),
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
            delta = sum(fix[k] for k in COMP) - fix['total']
            assert delta == mismatch, \
                (f"MISMATCH-DELTA {ticker} {name} {year}: {delta}")
        phantom += e['total'] - fix['total']
        for k in COMP + ['total']:
            e[k] = fix[k]
        if mismatch is None:
            e['_total_source'] = 'def14a_verified_20260928'
        else:
            e['_total_source'] = 'component_mismatch'
        print(f"repaired {ticker} {year} {name}: "
              f"${cur['total']:,} -> ${fix['total']:,}")
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
    for ticker, (ceo_name, ceo_total) in NEW_CEO_TOTALS.items():
        c = cm[ticker]
        assert c['ceo_name'] == ceo_name, \
            f"CEO-NAME {ticker}: {c['ceo_name']} != {ceo_name}"
        row = next(e for e in c['executives']
                   if e['name'] == ceo_name and e['year'] == c['fiscal_year'])
        assert row['total'] == ceo_total, \
            f"CEO-TOTAL {ticker}: row {row['total']} != {ceo_total}"
        old = c['total_compensation']
        c['total_compensation'] = ceo_total
        print(f"{ticker} total_compensation {old:,} -> {ceo_total:,}")
    # PGR aggregates: 2024 rows were clean; assert already-correct, no rewrite
    pgr = cm['PGR']
    ps = sum(e['total'] for e in pgr['executives'] if e['year'] == 2024)
    assert ps == pgr['total_neo_compensation'] == 33733783, \
        f"PGR anchor drift: {ps} / {pgr['total_neo_compensation']}"
    print("PGR anchors already correct (2024 rows clean), untouched")
    d['last_updated'] = '2026-09-28'
    d['metadata']['last_dq_repair'] = '2026-09-28'
    json.dump(d, open(PATH, 'w'), indent=1)
    print(f"phantom removed: ${phantom:,}")


if __name__ == '__main__':
    main()
