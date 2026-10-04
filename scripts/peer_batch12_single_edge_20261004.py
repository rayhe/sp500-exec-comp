#!/usr/bin/env python3
"""Peer-network batch-12 single-edge adjudication (2026-10-04 10:00 PDT run).

Fourth batch of the 10-19 tier under the batch-8y tier rule: single-edge
adjudication against the latest DEF 14A (drop or mark verified, group
untouched). The next 13 heaviest pending one-edge sources (all 7 remaining
at total_out=13, plus the 6 heaviest at total_out=12), each with exactly one
queued cross-sector fingerprint edge, adjudicated filing-verbatim via EDGAR
(SEC Archives curl open all run; Kit/1.0 UA; sequential ~3s pacing; CIKs from
company_tickers_exchange.json cross-checked against the submissions name
field; no subagents per the task execution rule). Evidence: goal
hidden_files/peer-batch12-20261004/ (<TICKER>_def14a.htm + <TICKER>_def14a.txt
verbatim text + batch12_submissions.json accession/URL map + prescan.py).

Adjudications (13 DROPPED, 0 MARKED VERIFIED):
- ALL->PSA: zero "Public Storage" mentions. 2025 compensation peer group is
  12 insurers (AFLAC/AIG/AON/Chubb/Hartford/Humana/Manulife/Marsh
  McLennan/MetLife/Progressive/Prudential/Travelers; Liberty Mutual in
  benchmark only, not publicly traded) (DEF 14A 2026-04-10).
- APA->CHTR: zero "Charter Communications" mentions; 7 bare "Charter" hits
  are all corporate-charter/committee-charter boilerplate. 2025 TSR
  performance peer group is 22 E&P cos (Antero/Devon/Magnolia/Range/Chevron/
  Diamondback/Matador/SM/Chord/EOG/Murphy/Civitas/EQT/OXY/COP/Expand/Ovintiv/
  Coterra/XOM/Permian Resources) + S&P 500 index weighted twice (DEF 14A
  2026-04-09).
- FDS->NDAQ: 13 "Nasdaq" hits are all stock-market references (NASDAQ Stock
  Market, NASDAQ: NICE/PAYO/CCCS tickers, one exec bio "CFO of Nasdaq,
  Inc."). FY2025 compensation peer group is 13 cos (CoStar/MarketAxess/
  Donnelley Financial/Morningstar/Dun & Bradstreet(acquired)/MSCI/Equifax/
  Tradeweb/Fair Isaac/TransUnion/Gartner/Verisk/Guidewire). Nasdaq, Inc.
  appears ONLY in the separate FY2025 Reference Peer Group, used for
  compensation program design and governance practices and explicitly NOT
  for compensation level assessments; the stored edge claims
  group_type="primary" (DEF 14A 2025-10-27).
- HSY->CHTR: zero "Charter Communications" mentions; 11 bare "Charter" hits
  are all corporate-charter/committee-charter boilerplate. 2025 peer group is
  14 food/consumer cos (Church & Dwight/Keurig Dr Pepper/Campbell's/
  Colgate-Palmolive/Kimberly-Clark/Clorox/ConAgra/Lamb Weston/Kraft Heinz/
  General Mills/McCormick/Smucker/Hormel/Mondelez); Kellanova removed Dec
  2025 (DEF 14A 2026-03-25).
- HUBB->COF: zero "Capital One" mentions. 2025 peer group is 21 industrials
  (Acuity/EnerSys/Ingersoll Rand/Rockwell/AMETEK/Fortive/ITT/Sensata/
  Carlisle/Fortune Brands/Lennox/Snap-on/Donaldson/IDEX/Lincoln/Vertiv/
  Dover/ITW/Regal Rexnord/Xylem/Emerson); added Emerson + ITW, removed
  Curtiss-Wright + Woodward (DEF 14A 2026-03-23).
- LH->GIS: zero "General Mills" mentions. 2025 comparative peer group is 15
  life-science/healthcare cos (Agilent/Baxter/Becton Dickinson/Boston
  Scientific/Charles River/Edwards/Henry Schein/Hologic/Molina/Quest/
  Stryker/Tenet/UHS/Viatris/Zimmer Biomet); removed IQVIA, added Hologic +
  Tenet (DEF 14A 2026-04-10).
- MOH->PSA: zero "Public Storage" mentions. 2025 Compensation Study
  16-company peer group (AFL/BDX/BSX/CNC/CYH/DVA/ELV/HCA/HUM/LH/MET/PRU/
  DGX/THC/CI/UHS) (DEF 14A 2026-03-23).
- ATO->TGT: zero "Target Corporation"/"Target Corp"; 56 bare "Target" hits
  are all compensation jargon ("target compensation", "capped at target").
  Fiscal 2025 peer group is 16 utilities (Alliant/Ameren/Black Hills/
  CenterPoint/CMS/DTE/Evergy/National Fuel/NiSource/OGE/ONE Gas/PPL/
  Southwest Gas/Spire/WEC/Xcel); added DTE + PPL (DEF 14A 2025-12-19).
- CNC->GIS: zero "General Mills" mentions. 2025 peer group is 13 cos
  (Cigna/Elevance Health/Humana/Molina/UH/Cencora/Cardinal/McKesson/CVS/
  Walgreens/HCA/MetLife/Prudential); Walgreens drops out going forward
  (DEF 14A 2026-03-26).
- COO->GIS: zero "General Mills" mentions. Fiscal 2025 peer group is 17
  healthcare equipment/supplies cos (Agilent/Align/Bausch+Lomb/Bio-Rad/
  Charles River/DENTSPLY/DexCom/Edwards/Hologic/Illumina/Masimo/ResMed/
  Revvity/STERIS/Teleflex/Waters/Zimmer Biomet) (DEF 14A 2026-02-24).
- DASH->GIS: zero "General Mills" mentions. 2025 peer group is 16 cos
  (Airbnb/Instacart/Spotify/Block/PayPal/Stripe/Bookings.com/Pinterest/
  Toast/Coinbase/Roblox/Uber/eBay/Shopify/Expedia/Snap); removed Chewy
  (DEF 14A 2026-04-20).
- DD->GIS: zero "General Mills" mentions. 2025 peer group (revised Dec 2024
  for Electronics Separation) is 16 cos (AptarGroup/Fortive/Parker-Hannifin/
  Avantor/GE HealthCare/Regal Rexnord/Carlisle/Hubbell/Teleflex/Dover/ITW/
  Trane/Ecolab/ITT/Emerson/Nordson) (DEF 14A 2026-04-10).
- DHR->COF: zero "Capital One" mentions. Executive compensation peer group
  is 15 life-science cos (Abbott/AbbVie/Agilent/Amgen/Becton Dickinson/
  Boston Scientific/BMS/Eli Lilly/Gilead/IQVIA/J&J/Medtronic/Merck/Stryker/
  Thermo Fisher) (DEF 14A 2026-03-25).

This batch is drop-only (no genuine marks): no verified_cross_sector
change, so the mark_verified --check live-queue recompute stays symmetric
(pending drops 58 -> 45 with the 13 edge removals).
No REPAIR_SCRIPTS registration: the single-filing invariant requires a
wholesale-replaced edge set, which single-edge adjudication does not
produce (batch-9 process note (d) class).

Tier rule (batch-8y): total_out >= 20 -> full verbatim re-read + wholesale
replace; 10-19 -> single-edge adjudication (this batch and following);
<10 -> single-edge adjudication, lowest priority.
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> (dropped target, adjudicating filing)
DROPS = {
    'ALL':  ('PSA',  'DEF 14A 2026-04-10'),
    'APA':  ('CHTR', 'DEF 14A 2026-04-09'),
    'FDS':  ('NDAQ', 'DEF 14A 2025-10-27'),
    'HSY':  ('CHTR', 'DEF 14A 2026-03-25'),
    'HUBB': ('COF',  'DEF 14A 2026-03-23'),
    'LH':   ('GIS',  'DEF 14A 2026-04-10'),
    'MOH':  ('PSA',  'DEF 14A 2026-03-23'),
    'ATO':  ('TGT',  'DEF 14A 2025-12-19'),
    'CNC':  ('GIS',  'DEF 14A 2026-03-26'),
    'COO':  ('GIS',  'DEF 14A 2026-02-24'),
    'DASH': ('GIS',  'DEF 14A 2026-04-20'),
    'DD':   ('GIS',  'DEF 14A 2026-04-10'),
    'DHR':  ('COF',  'DEF 14A 2026-03-25'),
}

MARKS = {}  # drop-only batch


def main():
    bak = SRC.replace('.json', '_backup_20261004_1000_pre_batch12.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}
    n_before = len(edges)

    # 1. assert + drop each adjudicated edge (exactly one per source)
    for src, (tgt, filing) in sorted(DROPS.items()):
        assert src in by_ticker, f'{src}: not a node'
        assert tgt in by_ticker, f'{tgt}: not a node'
        matches = [e for e in edges if e['source'] == src and e['target'] == tgt]
        assert len(matches) == 1, f'{src}->{tgt}: expected 1 edge, found {len(matches)}'
        edges = [e for e in edges if not (e['source'] == src and e['target'] == tgt)]
        print(f'dropped {src}->{tgt} ({filing})')

    assert n_before - len(edges) == len(DROPS), 'drop count mismatch'
    print(f'edges: {n_before} -> {len(edges)}')

    # 2. mark filing-genuine edges (edge stays; verified list grows) - none this batch
    assert not MARKS, 'batch-12 is drop-only'

    # 3. recompute degrees exactly; report newly-zero-degree nodes
    from collections import Counter
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    for e in edges:
        assert e['source'] in by_ticker and e['target'] in by_ticker, \
            f"dangling edge {e['source']}->{e['target']}"
    for x in nodes:
        ni, no = indeg.get(x['ticker'], 0), outdeg.get(x['ticker'], 0)
        if ni == 0 and no == 0:
            print(f'NOTE: {x["ticker"]} now isolated (in=0, out=0)')
        x['in_degree'], x['out_degree'] = ni, no
        od = outdeg.get(x['ticker'], 0)
        if od > 0:
            assert x.get('isSource') is True, f"{x['ticker']}: edges but not isSource"
        if x.get('isSource') is False:
            assert od == 0, f"{x['ticker']}: isSource False but has edges"

    # 4. metadata from actuals
    net['nodes'] = nodes
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-04'
    net['metadata']['last_dq_repair'] = '2026-10-04'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
