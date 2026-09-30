#!/usr/bin/env python3
"""Peer-network thin-edge repair batch 2026-09-30 14:00 PT run.

Replaces garbage stub parses (n=1 outgoing edges from the automated extractor)
for GE, MRNA, COF, MS, EBAY, EMR, WDC, DOV with real CD&A peer groups
transcribed verbatim from each company's latest DEF 14A. Also deletes TSLA's
bogus TSLA->NVDA edge: Tesla's 2025-09-17 DEF 14A discloses NO named
compensation peer group (the special committee "expressly declined" peer
benchmarking; the only peer group in the filing is the SIC-3711 TSR group for
the 402(v) table), so the single NVDA edge is a false parse. TSLA isSource
flips to false.

Filing evidence (all downloaded to /tmp/peersweep/thinbatch/ this run):
- GE   DEF 14A 2026-03-12: 2025 comp peer group of 17 (verbatim company names)
- MRNA DEF 14A 2026-03-16: 2024-2025 group (adopted Oct 2024, used for the Feb
         2025 pay decisions reported in this proxy); the 2025-2026 group
         (adopted Oct 2025) applies to FY2026 - queued for the FY2026 cycle
- COF  DEF 14A 2026-03-25: 2025 peer comparator group of 18, tickers verbatim
         in the filing (DFS removed post-Discover acquisition; FITB/RF removed
         for smaller size; SCHW/FISV/INTU added)
- MS   DEF 14A 2026-04-02: "Comparison Group" (the comp-decisions group; the
         ROTCE Comparison Group is the separate relative-performance PSU
         metric group). Foreign ADRs BCS/DB/UBS skipped per ticker-node
         convention
- EBAY DEF 14A 2026-04-30: "2025 Peer Group" rendered as an image in the
         filing (OCR'd from i26002_069.jpg), 19 companies
- EMR  DEF 14A 2025-12-12: "Emerson vs. Compensation Comparator Group" table,
         18 companies
- WDC  DEF 14A 2025-10-06: "Pre-Separation Peer Group" graphic
         (wdc-20251006_g120.jpg): 16 continuing + 3 added in 2025 (Amkor,
         Marvell, Xerox); Cisco/NVIDIA/GlobalFoundries removed in 2025.
         Fiscal-2025 group used (comp record is FY2025); the post-separation
         FY2026 reassessment is queued for the FY2026 cycle
- DOV  DEF 14A 2026-03-24: "Executive Compensation Program Peer Group" table,
         15 companies (comp record is FY2024; group "remains unchanged from
         the prior year" per the filing)
- TSLA DEF 14A 2025-09-17 (re-downloaded this run): no named comp peer group

Old stub edges replaced: GE->PSX, MRNA->INCY, COF->GIS, MS->JPM, EBAY->COF,
EMR->KEY, WDC->TGT, DOV->PSA, TSLA->NVDA (deleted).
"""
import json, shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, edge year, [peer tickers in filing order])
NEW = {
    'GE':   ('DEF 14A 2026-03-12', 2026,
             ['MMM','AAL','BA','CAT','DAL','EMR','FDX','GD','HON','LHX','LMT',
              'NOC','PH','RTX','TXT','TDG','UAL']),
    'MRNA': ('DEF 14A 2026-03-16', 2026,
             ['ALNY','BMY','NBIX','ONC','INCY','REGN','BIIB','JAZZ','SRPT',
              'BMRN','MRK','VRTX']),
    'COF':  ('DEF 14A 2026-03-25', 2026,
             ['ALLY','GS','PNC','AXP','INTU','SYF','BAC','JPM','TFC','SCHW',
              'MA','USB','C','MS','V','FISV','PYPL','WFC']),
    'MS':   ('DEF 14A 2026-04-02', 2026,
             ['BAC','C','GS','JPM','WFC']),
    'EBAY': ('DEF 14A 2026-04-30', 2026,
             ['ADBE','ABNB','AMZN','XYZ','BKNG','DASH','EA','ETSY','EXPE',
              'GPN','INTU','NDAQ','PYPL','PINS','NOW','SNAP','WMT','W','ZM']),
    'EMR':  ('DEF 14A 2025-12-12', 2025,
             ['MMM','A','CARR','CMI','DHR','DD','ETN','FTV','GD','HON','ITW',
              'JCI','KEYS','NOC','PH','ROK','ROP','TEL']),
    'WDC':  ('DEF 14A 2025-10-06', 2025,
             ['AMD','ADI','AMAT','AVGO','HPE','KLAC','LRCX','MCHP','MU','MSI',
              'NTAP','NXPI','ON','QCOM','STX','TXN','AMKR','MRVL','XRX']),
    'DOV':  ('DEF 14A 2026-03-24', 2026,
             ['AME','CSL','GLW','ETN','FLS','FTV','ITW','IR','PH','ROK','ROP',
              'SNA','SWK','TXT','XYL']),
}

# ticker -> (name, sector) for peer-only nodes that do not exist yet
NEW_NODES = {
    'AAL':  ('American Airlines Group Inc', 'Industrials'),
    'ALLY': ('Ally Financial Inc', 'Financials'),
    'ALNY': ('Alnylam Pharmaceuticals Inc', 'Health Care'),
    'FLS':  ('Flowserve Corp', 'Industrials'),
    'NBIX': ('Neurocrine Biosciences Inc', 'Health Care'),
    'ONC':  ('BeOne Medicines Ltd', 'Health Care'),
    'SRPT': ('Sarepta Therapeutics Inc', 'Health Care'),
    'W':    ('Wayfair Inc', 'Consumer Discretionary'),
    'XRX':  ('Xerox Holdings Corp', 'Information Technology'),
}

def main():
    bak = SRC.replace('.json', '_backup_20260930_1400_pre_thinedge.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # sanity: every new target is either an existing node or in NEW_NODES
    for src, (filing, year, peers) in NEW.items():
        assert src in by_ticker, f'{src}: not a node'
        for t in peers:
            assert t in by_ticker or t in NEW_NODES, f'{src}: unknown target {t}'
    print('target mapping OK:', sum(len(p) for _, _, p in NEW.values()), 'targets')

    # add missing peer-only nodes (peer-only nodes omit isSource, per convention)
    added = 0
    for t, (name, sector) in NEW_NODES.items():
        if t in by_ticker:
            continue
        node = {'ticker': t, 'name': name, 'sector': sector,
                'in_degree': 0, 'out_degree': 0, 'market_cap_tier': 'large'}
        nodes.append(node)
        by_ticker[t] = node
        added += 1
    print('new peer-only nodes added:', added)

    # TSLA: assert and delete the single bogus edge, flip isSource off
    tsla_edges = [e for e in edges if e['source'] == 'TSLA']
    assert len(tsla_edges) == 1 and tsla_edges[0]['target'] == 'NVDA', \
        f'TSLA edge set unexpected: {tsla_edges}'
    print(f"TSLA: deleting bogus edge TSLA->NVDA filing={tsla_edges[0]['filing']}")
    edges = [e for e in edges if e['source'] != 'TSLA']
    by_ticker['TSLA']['isSource'] = False
    print('TSLA: isSource -> False')

    # replace edges per source, asserting before/after sets
    for src, (filing, year, peers) in NEW.items():
        old = [e for e in edges if e['source'] == src]
        old_targets = sorted(e['target'] for e in old)
        old_filings = sorted(set(e['filing'] for e in old))
        print(f'{src}: old {len(old)} edges {old_targets} filings={old_filings}')
        edges = [e for e in edges if e['source'] != src]
        for t in peers:
            edges.append({'source': src, 'target': t, 'year': year,
                          'group_type': 'primary', 'filing': filing})
        new_check = sorted(e['target'] for e in edges if e['source'] == src)
        assert new_check == sorted(peers), f'{src}: new edge set mismatch'
        assert len(set(new_check)) == len(new_check), f'{src}: duplicate targets'
        print(f'{src}: new {len(peers)} edges filing={filing} year={year}')

    # recompute degrees for all nodes (stored degrees must stay exact)
    from collections import Counter
    indeg = Counter(e['target'] for e in edges)
    outdeg = Counter(e['source'] for e in edges)
    for x in nodes:
        x['in_degree'] = indeg.get(x['ticker'], 0)
        x['out_degree'] = outdeg.get(x['ticker'], 0)

    net['edges'] = edges
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-09-30'
    # NOTE: metadata 'sources' string left as-is per 10:30 PT precedent. It is
    # already stale (says 472; 485 sources had edges before this batch, 484
    # after the TSLA removal). Queued: regenerate the sources string from
    # actuals instead of hand-editing.

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))

if __name__ == '__main__':
    main()
