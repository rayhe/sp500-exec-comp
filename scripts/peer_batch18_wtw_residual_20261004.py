#!/usr/bin/env python3
"""Peer-network batch-18: WTW consultant-contamination residual adjudication
(2026-10-04 22:00 PDT run).

Trigger: the batch-17 screen for consultant-contamination found WTW
(Willis Towers Watson PLC) still cited as a peer by 15 sources (in_degree
15). Every one of the 15 stored edges was re-adjudicated filing-verbatim
against its latest DEF 14A (EDGAR, Kit/1.0 UA, sequential ~2.5s pacing;
CIKs from compensation.json; no subagents per the task execution rule).

Adjudications:
- 7 DROPPED (consultant/vendor contamination, not named peers):
  - BA->WTW: "survey data provided by Willis Towers Watson and obtained
    through its Executive Compensation Survey" - data vendor only
    (DEF 14A 2026-03-06).
  - CSGP->WTW: WTW is the retained independent compensation consultant;
    the 2025 Peer Group is 17 named cos (Akamai/ANSYS/Autodesk/DocuSign/
    Equifax/FactSet/Fair Isaac/Gartner/MSCI/Paycom/PTC/TransUnion/Tyler/
    VeriSign/Verisk/Workday/Zillow), no WTW (DEF 14A 2026-04-30).
  - CTSH->WTW: zero "Willis Towers Watson" full-text mentions in the
    filing (DEF 14A 2026-04-17).
  - EVRG->WTW: WTW retained for a competitive market assessment via its
    2024 Energy Services Executive Compensation Database; unnamed survey
    sample UNSTORED per precedent (DEF 14A 2026-03-26).
  - HWM->WTW: WTW appears only in the "WILLIS TOWERS WATSON CUSTOM SURVEY
    COMPARATOR GROUP" (unnamed survey participants - UNSTORED) and as
    survey data provider; the operative Proxy Peer Group is Attachment B
    (DEF 14A 2026-04-06).
  - MOS->WTW: "data from general industry surveys prepared by Willis
    Towers Watson PLC"; peer group is a separate named comparator set
    (DEF 14A 2026-04-16).
  - SPGI->WTW: WTW survey data only; the 2025/2026 Proxy Peer Group is
    16 named cos (AXP/ADP/BLK/CME/FIS/FISV/ICE/MMC/MA/MCO/PYPL/STT/TROW/
    SCHW/TRI/V), no WTW (DEF 14A 2026-03-31).
- 7 KEPT (WTW filing-genuine named peer-group member; no change, edge
  asserted present): ACGL (Compensation Peer Group), AIZ (compensation
  peer group), AJG (Insurance Brokers peer list), AON (2025/2026 Peer
  Group), BRO (peer table, "Insurance Intermediary"), CBRE (Benchmarking
  Compensation Comparator Group), MRSH (2025 Peer Group for Executive
  Compensation).
- 1 WHOLESALE: STT 3->19. The stored set (BNY/NTRS/WTW) was fragmentary:
  the filing's 2025 Compensation Peer Group is 19 firms, printed as an
  image (ny20058931x1_peers-1.jpg) - verbatim transcription: AMP/GS/PRU/
  BK/ICE/SPGI/BLK/IVZ/SSNC/COF/JPM/TFC/SCHW/MCO/USB/FIS/NTRS/BEN/PNC.
  BK stored as BNY per the BK->BNY 2026-05-21 live-holder rule (batch-8c).
  WTW dropped (filing names Meridian as consultant; WTW is a data
  vendor here). Restored 16 genuine peers; BNY + NTRS retained.
  No cross-sector verified marks: FIS/SSNC are not FINGERPRINT_TARGETS,
  and STT->BLK / STT->COF are same-sector (Financials).

Evidence: goal hidden_files/wtw-residual-20261004/ (<T>_def14a.htm x15,
wtw_submissions.json, ny20058931x1_peers-1.jpg (STT peer-group image),
adjudication notes in this docstring).
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# source -> (dropped target, adjudicating filing); filing must match the
# stored edge's filing string.
DROPS = {
    'BA': ('WTW', 'DEF 14A 2026-03-06'),
    'CSGP': ('WTW', 'DEF 14A 2026-04-30'),
    'CTSH': ('WTW', 'DEF 14A 2026-04-17'),
    'EVRG': ('WTW', 'DEF 14A 2026-03-26'),
    'HWM': ('WTW', 'DEF 14A 2026-04-06'),
    'MOS': ('WTW', 'DEF 14A 2026-04-16'),
    'SPGI': ('WTW', 'DEF 14A 2026-03-31'),
}

# source -> filing; WTW edge asserted present and filing-verbatim, no change.
KEEPS = {
    'ACGL': 'DEF 14A 2026-03-24',
    'AIZ': 'DEF 14A 2026-04-06',
    'AJG': 'DEF 14A 2026-03-23',
    'AON': 'DEF 14A 2026-04-28',
    'BRO': 'DEF 14A 2026-03-24',
    'CBRE': 'DEF 14A 2026-04-03',
    'MRSH': 'DEF 14A 2026-03-31',
}

# wholesale re-reads: source -> (filing, verbatim peer tickers)
NEW = {
    'STT': ('DEF 14A 2026-04-08',
            ['AMP', 'GS', 'PRU', 'BNY', 'ICE', 'SPGI', 'BLK', 'IVZ',
             'SSNC', 'COF', 'JPM', 'TFC', 'SCHW', 'MCO', 'USB', 'FIS',
             'NTRS', 'BEN', 'PNC']),
}

# expected old edge sets for wholesale sources (assertion guard)
EXPECTED_OLD = {
    'STT': ['BNY', 'NTRS', 'WTW'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_2200_pre_batch18.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}
    n_before = len(edges)

    # 1. assert + drop each adjudicated contamination edge
    for src, (tgt, filing) in sorted(DROPS.items()):
        hits = [e for e in edges if e['source'] == src and e['target'] == tgt]
        assert len(hits) == 1, f'{src}->{tgt}: expected 1 edge, got {len(hits)}'
        assert hits[0]['filing'] == filing, \
            f'{src}->{tgt}: filing drift {hits[0]["filing"]} != {filing}'
        edges = [e for e in edges if not (e['source'] == src and e['target'] == tgt)]
        print(f'dropped {src}->{tgt} ({filing})')

    # 2. assert keeps are present and filing-verbatim
    for src, filing in sorted(KEEPS.items()):
        hits = [e for e in edges if e['source'] == src and e['target'] == 'WTW']
        assert len(hits) == 1, f'{src}->WTW: expected 1 edge, got {len(hits)}'
        assert hits[0]['filing'] == filing, \
            f'{src}->WTW: filing drift {hits[0]["filing"]} != {filing}'
        print(f'kept {src}->WTW ({filing})')

    # 3. assert + wholesale replace
    for src, (filing, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'
        assert src not in peers, f'{src}: self-edge'
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
        assert all(e['filing'] == filing for e in old), \
            f'{src}: old edges carry mixed filings'
        edges = [e for e in edges if e['source'] != src]
        year = int(filing.rsplit(' ', 1)[1].split('-')[0])
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicates'
        assert by_ticker[src].get('isSource') is True, f'{src}: not isSource'
        print(f'{src}: {len(old)} old -> {len(peers)} new ({filing})')

    # 4. no new nodes expected; recompute degrees exactly
    from collections import Counter
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    for e in edges:
        assert e['source'] in by_ticker and e['target'] in by_ticker, \
            f"dangling edge {e['source']}->{e['target']}"
    mism = 0
    for x in nodes:
        ni, no = indeg.get(x['ticker'], 0), outdeg.get(x['ticker'], 0)
        if x.get('in_degree') != ni or x.get('out_degree') != no:
            mism += 1
        x['in_degree'], x['out_degree'] = ni, no
    print('nodes with changed degrees:', mism)
    for x in nodes:
        od = outdeg.get(x['ticker'], 0)
        if od > 0:
            assert x.get('isSource') is True, \
                f"{x['ticker']}: edges but not isSource"
        if x.get('isSource') is False:
            assert od == 0, f"{x['ticker']}: isSource False but has edges"

    # 5. metadata from actuals
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
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges',
          f'({n_before} -> {len(edges)})')


if __name__ == '__main__':
    main()
