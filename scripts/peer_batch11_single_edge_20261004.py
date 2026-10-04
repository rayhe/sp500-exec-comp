#!/usr/bin/env python3
"""Peer-network batch-11 single-edge adjudication (2026-10-04 07:30 PDT run).

Third batch of the 10-19 tier under the batch-8y tier rule: single-edge
adjudication against the latest DEF 14A (drop or mark verified, group
untouched). The 13 heaviest remaining pending one-edge sources (total_out
14-15 at out=15/14, plus the two heaviest at out=13), each with exactly one
queued cross-sector fingerprint edge, adjudicated filing-verbatim via EDGAR
(SEC Archives curl open all run; Kit/1.0 UA; sequential ~3s pacing; CIKs from
company_tickers_exchange.json cross-checked against the submissions name
field; no subagents per the task execution rule). Evidence: goal
hidden_files/peer-batch11-20261004/ (<TICKER>_def14a.htm + <TICKER>_def14a.txt
verbatim text + batch11_submissions.json accession/URL map + prescan.py).

Adjudications (12 DROPPED, 1 MARKED VERIFIED):
- XEL->CHTR: zero "Charter Communications" mentions; 12 "Charter" hits are
  all corporate-charter/committee-charter boilerplate. 2025 Peer Group is 18
  utilities (AEE/AEP/CNP/ED/D/DTE/DUK/EIX/ETR/ES/EXC/FE/NEE/PPL/PSEG/SRE/SO/
  WEC) (DEF 14A 2026-04-07).
- WY->PSA: FILING-GENUINE -> marked verified. "Peer Group for 2025
  Compensation Opportunities" comparator table lists Public Storage (PSA)
  verbatim among 18 cos; the filing states the group aims at a ~50/50 REIT /
  basic-materials mix (DEF 14A 2026-04-01).
- OTIS->IP: zero "International Paper" mentions. 2025 Peer Group is 17
  industrials (CARR/ITW/SWK/CMI/JCI/TEL/DOV/LEA/TT/ETN/MSI/WAB/FLR/PH/WDC/
  FTV/ROK); FTV replaced by IR for 2026 (DEF 14A 2026-04-17).
- WTW->GIS: zero "General Mills" mentions. 2025 peer group is 16 cos
  (Aon/Arch/AJG/ADP/Booz Allen/Brown & Brown/Cognizant/FNF/FIS/FAF/Fiserv/
  MMC/PFG/RHI/SPGI/UNM); added Arch + Brown & Brown, removed Conduent +
  Hartford (DEF 14A 2026-03-27).
- URI->IP: zero "International Paper" mentions. 2025 Peer Group is 18 cos
  (CARR/RSG/CTAS/ROK/DOV/SWK/FTV/TT/ITW/WM/JBHT/WCN/MAS/WCC/OTIS/GWW/PH/XYL)
  - Waste Management IS genuinely in the group (stored, unflagged); only
  the IP edge is fabricated. Removed C.H. Robinson, added ITW + OTIS
  (DEF 14A 2026-03-25).
- MSCI->GIS: zero "General Mills" mentions. Fiscal-2025 peer group is 18
  cos (CBOE/CME/CSGP/DNB/EFX/FDS/FICO/IT/ICE/MKTX/MCO/MORN/NDAQ/SEIC/SPGI +
  3 more incl. MSCI itself; fintech/exchanges/data/research) (DEF 14A
  2026-03-11).
- IRM->WM: 3 "Waste Management" hits are all Stericycle-acquisition
  footnotes ("acquired by Waste Management in November 2024"), never a peer
  group. 2025 Peer Group is 18 cos (BR/FTNT/SBAC/CTAS/GPN/STX/CCI/NTAP/
  SRCL/DLR/PAYX/WY/EFX/PLD/WDAY/EQIX/PSA) (DEF 14A 2026-03-24).
- EVRG->GIS: zero "General Mills" mentions. 2025 peer group is 16 utilities
  (Alliant/CNP/Eversource/Portland General/Ameren/CMS/NiSource/PPL/Atmos/
  DTE/OGE/TXNM/Black Hills/Entergy/Pinnacle West/WEC) (DEF 14A 2026-03-26).
- EQT->GIS: zero "General Mills" mentions. 2025 Compensation Benchmarking
  Peer Group is 14 E&P/midstream cos (Antero/APA/Coterra/Devon/Diamondback/
  EOG/Expand/OXY/ONEOK/Ovintiv/Permian/Range/Targa/Williams) (DEF 14A
  2026-02-26).
- EOG->GIS: zero "General Mills" mentions. 2025 Peer Group (comp) is 14
  cos (APA/Cheniere/COP/Coterra/Devon/Diamondback/EQT/Expand/HAL/OXY/
  Ovintiv/PSX/SLB/Williams); September 2025 Performance Peer Group is a
  separate 14-co set - GIS in neither; removed Marathon Oil (acquired by
  COP) (DEF 14A 2026-03-27).
- BXP->COF: zero "Capital One" mentions full-text. Filing discloses no
  named compensation peer-group list (benchmarking via survey data; TSR
  measured vs a 6-office-REIT Custom Index: DEI/KRC/ESRT/SLG/HPP/VNO)
  (DEF 14A 2026-04-10).
- WRB->GIS: zero "General Mills" mentions. Comp peer group "should be
  comprised primarily of property casualty insurance underwriters"
  (DEF 14A 2026-04-22).
- MSI->GIS: zero "General Mills" mentions. 2025 Peer Group is 12 cos
  (Adobe/ITW/Rockwell/Autodesk/Intuit/Roper/Dover/L3Harris/ServiceNow/
  Fortive/Parker-Hannifin/Trimble); removed Agilent (DEF 14A 2026-04-02).

This batch is NOT drop-only (one genuine mark): WY->PSA is appended to
metadata.verified_cross_sector, which the network tab reads live
(js/network.js "Cross-Sector Verified" stat) to split verified vs pending.
No REPAIR_SCRIPTS registration: the mark_verified single-filing invariant
requires a wholesale-replaced edge set, which single-edge adjudication does
not produce (batch-9 process note (d) class). Consequence: mark_verified
--check still counts WY->PSA in its live queue recompute (pending 59 vs
effective 58); the log records the asymmetry.

Tier rule (batch-8y): total_out >= 20 -> full verbatim re-read + wholesale
replace; 10-19 -> single-edge adjudication (this batch and following);
<10 -> single-edge adjudication, lowest priority.
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> (dropped target, adjudicating filing)
DROPS = {
    'XEL':  ('CHTR', 'DEF 14A 2026-04-07'),
    'OTIS': ('IP',   'DEF 14A 2026-04-17'),
    'WTW':  ('GIS',  'DEF 14A 2026-03-27'),
    'URI':  ('IP',   'DEF 14A 2026-03-25'),
    'MSCI': ('GIS',  'DEF 14A 2026-03-11'),
    'IRM':  ('WM',   'DEF 14A 2026-03-24'),
    'EVRG': ('GIS',  'DEF 14A 2026-03-26'),
    'EQT':  ('GIS',  'DEF 14A 2026-02-26'),
    'EOG':  ('GIS',  'DEF 14A 2026-03-27'),
    'BXP':  ('COF',  'DEF 14A 2026-04-10'),
    'WRB':  ('GIS',  'DEF 14A 2026-04-22'),
    'MSI':  ('GIS',  'DEF 14A 2026-04-02'),
}

# source -> (verified target, filing) appended to metadata.verified_cross_sector
MARKS = {
    'WY': ('PSA', 'DEF 14A 2026-04-01'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_0730_pre_batch11.json')
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

    # 2. mark filing-genuine edges (edge stays; verified list grows)
    vlist = net['metadata'].get('verified_cross_sector', [])
    have = {(v['source'], v['target']) for v in vlist}
    for src, (tgt, filing) in sorted(MARKS.items()):
        assert src in by_ticker, f'{src}: not a node'
        assert tgt in by_ticker, f'{tgt}: not a node'
        assert (src, tgt) not in have, f'{src}->{tgt}: already marked'
        matches = [e for e in edges if e['source'] == src and e['target'] == tgt]
        assert len(matches) == 1, f'{src}->{tgt}: expected 1 edge, found {len(matches)}'
        vlist.append({'source': src, 'target': tgt,
                      'filing': filing, 'batch': 'peer-batch11-20261004'})
        print(f'marked verified {src}->{tgt} ({filing})')
    vlist.sort(key=lambda v: (v['source'], v['target']))
    net['metadata']['verified_cross_sector'] = vlist
    print(f'verified_cross_sector: {len(vlist)} entries')

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
