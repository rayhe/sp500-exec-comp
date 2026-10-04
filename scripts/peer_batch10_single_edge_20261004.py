#!/usr/bin/env python3
"""Peer-network batch-10 single-edge adjudication (2026-10-04 06:00 PDT run).

Second batch of the 10-19 tier under the batch-8y tier rule: single-edge
adjudication against the latest DEF 14A (drop or mark verified, group
untouched). The next 13 heaviest pending one-edge sources (total_out 15-17),
each with exactly one queued cross-sector fingerprint edge, adjudicated
filing-verbatim via EDGAR (SEC Archives curl open this run; Kit/1.0 UA;
sequential ~3s pacing; CIKs from company_tickers_exchange.json cross-checked
against the submissions name field; no subagents per the task execution rule).
Evidence: goal hidden_files/peer-batch10-20261004/ (<TICKER>_def14a.htm +
<TICKER>_def14a.txt verbatim text + batch10_submissions.json accession/URL map
+ batch10_ciks.json + prescan.py/fetch_def14a.py).

Adjudications (all 13 DROPPED - none filing-genuine):
- CSCO->GIS: zero "General Mills" mentions full-text; FY2026 peer group is
  15 tech cos (ACN/ADBE/GOOG/AAPL/AVGO/DELL/HPQ/IBM/INTC/META/MSFT/ORCL/QCOM/
  CRM/V) (DEF 14A 2025-10-28).
- CSGP->BLK: 2 "BlackRock" hits are both 13G beneficial-ownership context;
  2025 Peer Group is real-estate/tech cos (AKAM/ADSK/ANSS/DOCU/EFX/FDS/FICO/
  IT/MSCI/PAYC/PTC/TU/TYL/VRSN/VRSK/WDAY/ZG) (DEF 14A 2026-04-30).
- DLR->IP: zero "International Paper" mentions; peer group is 10 REITs +
  8 tech cos (ARE/AMT/CCI/EQIX/EQR/PLD/O/SPG/VTR/WELL + ANET/ADSK/FTNT/NTAP/
  PANW/NOW/SNPS/WDAY) (DEF 14A 2026-04-17).
- NSC->IP: zero "International Paper" mentions; Class I Railroads Peer Group
  (5) + Industrials Peer Group (20: BNSF/CPKC/CSX/ETN/ITW/LHX/PH/TXT/WM/XPO/
  CNI/CARR/DOV/FTV/JCI/OTIS/RSG/TT/WAB/XYL) (DEF 14A 2026-03-27).
- CTVA->TGT: zero "Target Corporation"; 15 "Target" hits all target-comp
  language; July-2025 peer group (MMM/APD/ADM/BDX/BIIB/CE/DE/DD/EMN/ECL/HON/
  IFF/NTR/PPG/SHW/ZTS) (DEF 14A 2026-03-19).
- FTV->COF: zero "Capital One"/"COF"; 2025 peer group (AME/IDEX/ITW/ROK/
  MTD/STE/SYK/ECL/HON/ROP/TRMB/ZBRA/ADSK/NOW/SNPS) (DEF 14A 2026-04-29).
- MCO->GIS: zero "General Mills" mentions; 2025 peers (CME/IT/NDAQ/EFX/GPN/
  SPGI/FICO/ICE/TRI/FIS/MMC/VRSK/FISV/MSCI/WDAY) (DEF 14A 2026-03-04).
- PSX->FRT: zero "Federal Realty" mentions; 2025 Compensation Peer Group
  (MMM/ADM/COP/DE/DOW/F/GM/HAL/HON/LYB/MPC/OXY/WMB/VLO) (DEF 14A 2026-04-02).
- ROP->GIS: zero "General Mills" mentions full-text; 2025 self-selected
  peers (INTU/SNPS/CDNS/ADSK/ZM/BSX/SYK/NOW/PANW/CRWD/FTNT/BX/KKR + table;
  zero-mention search dispositive) (DEF 14A 2026-04-07).
- CBOE->GIS: 2 "General Mills" hits are both director Palmore's bio (ex-GC
  of GIS); 20-company custom peer group (AKAM/LSEG/BR/LPLA/CME/MKTX/DB1/
  MSCI/EFX/NDAQ/EUR/SEI/FDS/SF/FNT/TU/ICE/VRSK/JKHY/VIRT) (DEF 14A
  2026-04-02).
- CRWD->CHTR: zero "Charter Communications"/"CHTR"; 43 "Charter" hits all
  corporate-charter boilerplate; FY2026 peer group (APP/MDB/SNAP/ANET/OKTA/
  SNOW/TEAM/PLTR/TTD/SQ/PANW/WDAY/NET/PINS/ZM/DDOG/RBLX/ZS/FTNT/NOW/HUBS/
  SHOP) (DEF 14A 2026-05-05).
- EMN->TGT: zero "Target Corporation"; 83 "Target" hits all target-comp
  language; 2025 Proxy Peers (APD/ALB/ASH/AXTA/BALL/CE/CTVA/DOV/DD/ECL/FMC/
  HUN/IFF/PH/PPG/RPM/SEE/SHW/TT) (DEF 14A 2026-03-24).
- MDLZ->IP: zero "International Paper" mentions full-text; Compensation
  Survey Peer Group (MMM/KO/CL/EL/GIS/JNJ/KHC/KMB/MCD/NKE/PEP/PM/PG/SBUX) -
  GIS genuinely in group, IP absent (DEF 14A 2026-04-03).

Tier rule (batch-8y, for future runs): total_out >= 20 -> full verbatim re-read
+ wholesale replace; 10-19 -> single-edge adjudication (this batch and
following); <10 -> single-edge adjudication, lowest priority.

This is a DROP-ONLY batch: no new nodes, no REPAIR_SCRIPTS registration (the
mark_verified single-filing invariant requires a wholesale-replaced edge set;
dropped edges leave the queue naturally because queued_edges() scans live edges).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> (dropped target, adjudicating filing)
DROPS = {
    'CSCO': ('GIS', 'DEF 14A 2025-10-28'),
    'CSGP': ('BLK', 'DEF 14A 2026-04-30'),
    'DLR': ('IP', 'DEF 14A 2026-04-17'),
    'NSC': ('IP', 'DEF 14A 2026-03-27'),
    'CTVA': ('TGT', 'DEF 14A 2026-03-19'),
    'FTV': ('COF', 'DEF 14A 2026-04-29'),
    'MCO': ('GIS', 'DEF 14A 2026-03-04'),
    'PSX': ('FRT', 'DEF 14A 2026-04-02'),
    'ROP': ('GIS', 'DEF 14A 2026-04-07'),
    'CBOE': ('GIS', 'DEF 14A 2026-04-02'),
    'CRWD': ('CHTR', 'DEF 14A 2026-05-05'),
    'EMN': ('TGT', 'DEF 14A 2026-03-24'),
    'MDLZ': ('IP', 'DEF 14A 2026-04-03'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_0600_pre_batch10.json')
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

    # 2. recompute degrees exactly; report newly-zero-degree nodes
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

    # 3. metadata from actuals
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
