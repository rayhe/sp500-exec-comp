#!/usr/bin/env python3
"""Peer-network batch-8x fingerprint-queue repair (2026-10-03 22:00 PDT run).

Final batch of the two-edge tier drain. The last 8 remaining 2-edge
sources (ALB/F at out=10; GRMN/REG/SPG at out=9-10; MAA/NCLH/TSCO at
out=10-11) re-extracted verbatim from latest DEF 14A via EDGAR (Kit/1.0
UA; primaryDocument from submissions; sequential ~3s pacing; no subagents
per the task execution rule). Peer sections transcribed verbatim.
Evidence in goal hidden_files/peer-batch8x-20261003/ <TICKER>_peer.txt
(verbatim transcriptions) + batch8x_submissions.json (accession/URL map) +
batch8x_docs.json + batch8x_ticker_map.json. 22 new peer-only nodes
(CC/HUN/OLN/STLA SEC-verified additions during build). Filing HTMLs persisted to
the goal dir AT download time (the batch-8h /tmp-peersweep-wipe lesson).

NOTE on filing access: SEC Archives www.sec.gov curl was UNBLOCKED this
run (200 on browse-edgar probe at 22:05 PDT) after the batch-8w 403
block - all 8 peer sections extracted directly from downloaded HTMLs,
no live-browser path needed.

Adjudications:
- F: dual-group pattern (HAL/KHC/ACGL precedents). The "December 2025
  peer group" (20 companies) is the compensation-decisions group and is
  STORED. The "2025 PSU TSR Peer Group" (auto makers incl. EVs) is the
  relative-TSR performance group - UNSTORED. F->MSFT is filing-genuine
  cross-sector (F Consumer Discretionary; MSFT home sector IT) - marked
  verified via mark_verified.
- REG: dual-column table ("Reviewed in 2024 for Setting 2025
  Compensation" vs "Reviewed in 2025 for Setting 2026 Compensation").
  Stored the 2025 column (18 companies, Kilroy in, AvalonBay out).
  The old set's AVB edge was a pre-emptive 2026-leak - fourth catch
  after DPZ/NCLH (batch-8w), CDW/BBY (batch-8v), TMUS/NKE.
- SPG: filing prints "The GAP (NYSE:GPS)"; stored as GAP (live ticker,
  CIK 39911, company node) per the batch-4 "Fiserv is FISV" rule.
  SPG->STT is filing-genuine cross-sector (SPG Real Estate; STT home
  sector Financials) - marked verified via mark_verified.
- ALB: the 2026-cycle changes (removed DOW/FCX, added CBT/FUL/AVNT/ASH)
  are forward-looking - stored the 2025 peer group (14 companies, DOW
  and FCX retained). ALB/TSCO PvP peer groups (S&P 1500 Specialty
  Chemicals Index / PvP index), GRMN's S&P 500 Consumer Discretionary
  Index, REG's FTSE Nareit Shopping Center Index - all PvP TSR indexes,
  UNSTORED per convention.
- NCLH: SAVE (Spirit Airlines, delisted) retained under last ticker per
  the PARA/QRVO/COMM/SMAR delisted-peer precedent.
"""

import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
# (all SEC company_tickers_exchange.json verified except SAVE (delisted)
# and GAP-liveticker; names filing-verbatim where the filing printed them)
NEW_NODES = {
    'ADC': ("Agree Realty Corp", 'Real Estate'),
    'BC': ("Brunswick Corporation", 'Consumer Discretionary'),
    'BRX': ("Brixmor Property Group Inc.", 'Real Estate'),
    'CASY': ("Casey's General Stores Inc", 'Consumer Staples'),
    'CC': ("Chemours Co", 'Materials'),
    'CWK': ("Cushman & Wakefield Ltd.", 'Real Estate'),
    'GOLF': ("Acushnet Holdings Corp.", 'Consumer Discretionary'),
    'HUN': ("Huntsman CORP", 'Materials'),
    'KRC': ("Kilroy Realty Corp", 'Real Estate'),
    'KRG': ("Kite Realty Group Trust", 'Real Estate'),
    'MAC': ("Macerich Co", 'Real Estate'),
    'MTN': ("Vail Resorts Inc", 'Consumer Discretionary'),
    'NNN': ("NNN REIT, Inc.", 'Real Estate'),
    'OLN': ("OLIN Corp", 'Materials'),
    'PII': ("Polaris Inc.", 'Consumer Discretionary'),
    'SAVE': ("Spirit Airlines, Inc.", 'Industrials'),
    'SKT': ("Tanger Inc.", 'Real Estate'),
    'STLA': ("Stellantis N.V.", 'Consumer Discretionary'),
    'TNL': ("Travel & Leisure Co.", 'Consumer Discretionary'),
    'VAC': ("Marriott Vacations Worldwide Corp", 'Consumer Discretionary'),
    'VC': ("Visteon Corporation", 'Consumer Discretionary'),
    'WGO': ("Winnebago Industries, Inc.", 'Consumer Discretionary'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'ALB': ('DEF 14A 2026-03-24',
            ['APD', 'FMC', 'CE', 'FCX', 'CC', 'HUN', 'CTVA', 'MOS',
             'DOW', 'NEM', 'DD', 'OLN', 'EMN', 'WLK']),
    'F': ('DEF 14A 2026-03-27',
          ['AAPL', 'GM', 'QCOM', 'CAT', 'HON', 'RIVN', 'CVX', 'HPQ',
           'RTX', 'CSCO', 'IBM', 'STLA', 'DE', 'INTC', 'TSLA', 'DELL',
           'LMT', 'BA', 'XOM', 'MSFT']),
    'GRMN': ('DEF 14A 2026-04-22',
             ['GOLF', 'TDY', 'BC', 'TXT', 'DECK', 'TRMB', 'DXCM',
              'VC', 'HEI', 'WGO', 'LOGI', 'YETI', 'NTAP', 'ZBRA',
              'PII']),
    'MAA': ('DEF 14A 2026-04-06',
            ['AMH', 'CPT', 'ESS', 'KIM', 'UDR', 'AVB', 'ELS', 'EXR',
             'PSA', 'BXP', 'EQR', 'INVH', 'SUI']),
    'NCLH': ('DEF 14A 2026-04-30',
             ['ALK', 'JBLU', 'RCL', 'BYD', 'LVS', 'SAVE', 'CZR',
              'VAC', 'TNL', 'CCL', 'MGM', 'MTN', 'H', 'PK', 'WYNN',
              'HST', 'PENN', 'YUM']),
    'REG': ('DEF 14A 2026-03-25',
            ['ADC', 'AMH', 'BXP', 'BRX', 'CPT', 'ELS', 'ESS', 'FRT',
             'HST', 'INVH', 'KRC', 'KIM', 'KRG', 'NNN', 'SUI', 'MAC',
             'UDR', 'VNO']),
    'SPG': ('DEF 14A 2026-04-01',
            ['AMT', 'CG', 'CBRE', 'CCI', 'CWK', 'EBAY', 'EQIX', 'FRT',
             'GPN', 'GAP', 'JLL', 'KIM', 'M', 'NTRS', 'PLD', 'O',
             'REG', 'STT', 'SKT', 'TPR', 'TJX']),
    'TSCO': ('DEF 14A 2026-03-26',
             ['AAP', 'BURL', 'ORLY', 'AZO', 'CASY', 'ROST', 'BBWI',
              'DKS', 'ULTA', 'BBY', 'DG', 'BJ', 'DLTR']),
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-03 22:00 PT from peer-network.json (980 nodes / 7,427 edges).
EXPECTED_OLD = {
    'ALB': ['APD', 'COF', 'CTVA', 'DD', 'DOW', 'FCX', 'GIS', 'JCI',
            'MOS', 'NEM'],
    'F': ['AXP', 'BA', 'CNC', 'CVX', 'GIS', 'HCA', 'LMT', 'MCK',
          'PEP', 'UNH'],
    'GRMN': ['CHTR', 'DECK', 'DXCM', 'IP', 'NTAP', 'TDY', 'TRMB',
             'TXT', 'ZBRA'],
    'MAA': ['AVB', 'EQR', 'ESS', 'EXR', 'GIS', 'INVH', 'KIM', 'PSA',
            'TGT', 'UDR'],
    'NCLH': ['CCL', 'CHTR', 'CZR', 'DRI', 'GIS', 'HST', 'LUV', 'LVS',
             'MAR', 'RCL'],
    'REG': ['AVB', 'CHTR', 'ESS', 'FRT', 'GIS', 'HST', 'INVH', 'KIM',
            'UDR'],
    'SPG': ['AWK', 'CBRE', 'ED', 'EQIX', 'IP', 'KIM', 'PFG', 'PLD',
            'REG'],
    'TSCO': ['AMD', 'AZO', 'BBY', 'COF', 'DG', 'DLR', 'DLTR', 'GIS',
             'ROST', 'TGT', 'ULTA'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261003_2200_pre_batch8x.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # 1. create new peer-only nodes (before edge validation)
    for t, (name, sector) in sorted(NEW_NODES.items()):
        assert t not in by_ticker, f'{t}: node already exists'
        n = {'ticker': t, 'name': name, 'sector': sector,
             'in_degree': 0, 'out_degree': 0, 'market_cap_tier': 'large'}
        nodes.append(n)
        by_ticker[t] = n
    print('new peer-only nodes:', len(NEW_NODES))

    # 2. assert + replace edges for the repaired sources
    for src, (filing, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker, f'{src}: unknown target {t}'
        assert src not in peers, f'{src}: self-edge'
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        assert old_targets == sorted(EXPECTED_OLD[src]), \
            f'{src}: old edge set changed: {old_targets}'
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

    # 3. recompute degrees exactly
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

    # 4. metadata from actuals
    net['nodes'] = nodes
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-03'
    net['metadata']['last_dq_repair'] = '2026-10-03'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
