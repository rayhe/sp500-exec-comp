#!/usr/bin/env python3
"""Peer-network batch-8g fingerprint-queue repair (2026-10-02 run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f runs (2026-10-01/02). After 8f, the
Section-19 fingerprint queue holds 286 cross-sector fingerprint-target edges
across 198 sources; the 3-edge tier is fully drained. Batch-8g takes the 6
heaviest remaining 2-queue sources by total outbound edge count
(CARR 31 / ETN 30 / ITW 28 / LNT 28 / MMM 27 / CRL 26) and re-extracts each
source's comp-decisions peer group VERBATIM from its latest DEF 14A, keeping
only edges that match the verbatim group. TSR/performance comparator groups,
index peer groups, unnamed survey databases, and 2026-variant groups are
documented but unstored per the batches 3-8f convention (V Block->Uber /
HPQ FY2026 / GDDY 2026 / KMB 2026 / CNP 2026 / IFF 2026 / KDP 2026 /
GEV 2026 / DVN Jan-2026 / ADM index-only precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, 3s pacing;
non-padded CIK in Archive URLs + curl -L per the batch-8d note). Peer
sections transcribed verbatim. Evidence in /tmp/peersweep/batch8g/
<TICKER>_peer.txt (copied to goal hidden_files/peer-batch8g-20261002/) with
batch8g_filings.json (accession/URL map).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  CARR  31 -> 15 (DEF 14A 2026-03-03; 2025 Compensation Peer Group, 15 cos
        verbatim ("8 of 16" incl. Carrier itself); queued IP/PSA fabrications
        all dropped)
  ETN   30 -> 0  (DEF 14A 2026-03-13; filing names NO compensation peer group
        - the only named group is the 16-co TSR Peer Group (ESIP/PSU
        performance hurdle), documented but unstored per the CTAS batch-8a
        precedent; isSource flipped True->False; queued GIS/IP fabrications
        dropped)
  ITW   28 -> 17 (DEF 14A 2026-03-27; 2025 Peer Group, 17 cos verbatim,
        unchanged from 2024; queued COF/IP fabrications dropped)
  LNT   28 -> 20 (DEF 14A 2026-03-31; defined executive compensation peer
        group of 20 utilities (Pay Governance), verbatim; the EEI Stock
        Index (performance-share TSR group) and the ~1,000-co WTW General
        Industry survey database documented but unstored per the ADM
        index-only / unnamed-survey precedents; new nodes AVA/IDA/BKH/MDU/
        SWX/TXNM; queued COF/IP fabrications dropped)
  MMM   27 -> 21 (DEF 14A 2026-03-25; 2025 Peer Group, 21 cos verbatim
        (approved Aug 2024 post-Solventum, unchanged May 2025); Abbott
        Laboratories correctly excluded (removed for 2025 per filing);
        queued IP/PG fabrications dropped)
  CRL   26 -> 37 (DEF 14A 2026-03-31; 2025 proxy peer group, 37 cos with
        tickers given verbatim in the filing - the old 26-edge set had
        picked up COO/INCY/MRNA/PODD from the survey footnote while missing
        11 real peers; Vertex stored as VRTX (live Nasdaq ticker; filing
        prints "(VERX)", same ticker-slot discipline as batch-5 "Avent,
        Inc." -> AVT); Catalent CTLT stored verbatim per delisted-peer
        precedent; 2026 expected variant (-Catalent/+Cooper Companies)
        documented but NOT stored; new nodes FTRE/MYGN/MEDP; queued
        CHTR/IP fabrications dropped)

No ticker-slot collisions: AVA/IDA/BKH/MDU/SWX/TXNM/FTRE/MYGN/MEDP are all
free (SEC company_tickers.json 2026-10-02: AVISTA CORP/IDACORP INC/BLACK
HILLS CORP/MDU RESOURCES GROUP/Southwest Gas Holdings/TXNM ENERGY/Fortrea/
MYRIAD GENETICS/Medpace). No surviving cross-sector fingerprint edges in
any repaired source, so no new verified_cross_sector marks this batch.
"""
import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'AVA': ('Avista Corp', 'Utilities'),
    'IDA': ('IDACORP, Inc.', 'Utilities'),
    'BKH': ('Black Hills Corp.', 'Utilities'),
    'MDU': ('MDU Resources Group, Inc.', 'Utilities'),
    'SWX': ('Southwest Gas Holdings, Inc.', 'Utilities'),
    'TXNM': ('TXNM Energy, Inc.', 'Utilities'),
    'FTRE': ('Fortrea Holdings Inc.', 'Health Care'),
    'MYGN': ('Myriad Genetics, Inc.', 'Health Care'),
    'MEDP': ('Medpace Holdings, Inc.', 'Health Care'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'CARR': ('DEF 14A 2026-03-03',
             ['MMM', 'CAT', 'CMI', 'DE', 'ETN', 'EMR', 'HON',
              'ITW', 'JCI', 'OTIS', 'PH', 'SWK', 'TEL', 'TT',
              'WHR']),
    'ITW': ('DEF 14A 2026-03-27',
            ['MMM', 'CAT', 'CMI', 'DE', 'DOV', 'ETN', 'ECL',
             'EMR', 'FTV', 'GD', 'HON', 'JCI', 'PH', 'PPG',
             'ROK', 'SWK', 'TT']),
    'LNT': ('DEF 14A 2026-03-31',
            ['ATO', 'ES', 'POR', 'AEE', 'HE', 'PPL', 'AVA',
             'IDA', 'PEG', 'BKH', 'MDU', 'SWX', 'CNP', 'NI',
             'TXNM', 'CMS', 'OGE', 'WEC', 'EVRG', 'PNW']),
    'MMM': ('DEF 14A 2026-03-25',
            ['CARR', 'CAT', 'CL', 'GLW', 'CMI', 'DE', 'DOW',
             'DD', 'ETN', 'ECL', 'EMR', 'GD', 'GE', 'HON',
             'ITW', 'JCI', 'KMB', 'NOC', 'PH', 'TEL', 'TT']),
    'CRL': ('DEF 14A 2026-03-31',
            ['ABT', 'FTRE', 'MYGN', 'A', 'GILD', 'RVTY', 'AMGN',
             'HOLX', 'PFE', 'AVTR', 'ICLR', 'DGX', 'BAX', 'IDXX',
             'REGN', 'BDX', 'ILMN', 'STE', 'BIO', 'IQV', 'TFX',
             'BIIB', 'JAZZ', 'TMO', 'BSX', 'LH', 'VRTX', 'BMY',
             'MEDP', 'WAT', 'BRKR', 'MDT', 'WST', 'CTLT', 'MRK',
             'LLY', 'MTD']),
}

# no-named-group sources: remove all edges, flip isSource True -> False
# (precedent: AMZN, CLX, CTAS, L, NRG, TSLA, ADM)
INDEX_ONLY = {
    'ETN': 'DEF 14A 2026-03-13',
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 03:30 PT from peer-network.json (900 nodes / 7,131 edges)
EXPECTED_OLD = {
    'CARR': ['ALLE', 'AME', 'CAT', 'CMI', 'DE', 'DOV', 'EMR', 'ETN',
             'FTV', 'GE', 'GNRC', 'HON', 'IEX', 'IP', 'IR', 'ITW',
             'JCI', 'MAS', 'NDSN', 'OTIS', 'PCAR', 'PH', 'PNR',
             'POOL', 'PSA', 'ROK', 'SNA', 'SWK', 'TEL', 'TT', 'XYL'],
    'ITW': ['AMCR', 'AME', 'AON', 'APTV', 'BALL', 'CAT', 'CMI', 'COF',
            'DD', 'DE', 'DOV', 'DOW', 'ECL', 'EMR', 'ETN', 'FTV',
            'GD', 'HON', 'IP', 'JCI', 'LNT', 'MAS', 'MTD', 'PH',
            'PPG', 'ROK', 'SWK', 'TT'],
    'LNT': ['AEE', 'AEP', 'ATO', 'AWK', 'CMS', 'CNP', 'COF', 'D',
            'DTE', 'DUK', 'ED', 'ETR', 'EVRG', 'EXC', 'FE', 'GE',
            'IP', 'LUV', 'NEE', 'NI', 'PCG', 'PEG', 'PNW', 'PPL',
            'SO', 'WDC', 'WEC', 'XEL'],
    'MMM': ['AON', 'BA', 'CARR', 'CAT', 'CL', 'CMI', 'DD', 'DE',
            'DOW', 'ECL', 'EMR', 'ETN', 'GD', 'GLW', 'HON', 'IP',
            'ITW', 'JCI', 'JNJ', 'KMB', 'NOC', 'PG', 'PH', 'SOLV',
            'TEL', 'TT', 'WTW'],
    'CRL': ['A', 'AMGN', 'BAX', 'BIIB', 'BMY', 'BSX', 'CHTR', 'COO',
            'DGX', 'GILD', 'HOLX', 'IDXX', 'INCY', 'IP', 'IQV',
            'LLY', 'MDT', 'MRK', 'MRNA', 'PFE', 'PODD', 'REGN',
            'STE', 'TMO', 'VRTX', 'WAT'],
}
EXPECTED_OLD_COUNT = {'ETN': 30}


def main():
    bak = SRC.replace('.json', '_backup_20261002_0330_pre_batch8g.json')
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

    # 2. index-only sources: drop all edges, flip isSource
    for src, filing in INDEX_ONLY.items():
        assert src in by_ticker, f'{src}: not a node'
        old = [e for e in edges if e['source'] == src]
        assert len(old) == EXPECTED_OLD_COUNT[src], \
            f'{src}: old edge count changed: {len(old)}'
        assert by_ticker[src].get('isSource') is True, f'{src}: not isSource'
        edges = [e for e in edges if e['source'] != src]
        by_ticker[src]['isSource'] = False
        print(f'{src}: {len(old)} old -> 0 new (no named comp group, {filing})')

    # 3. assert + replace edges for the repaired sources
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

    # 4. recompute degrees exactly
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
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-02'
    net['metadata']['last_dq_repair'] = '2026-10-02'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'

    json.dump(net, open(SRC, 'w'), indent=1)
    print('wrote', SRC, len(nodes), 'nodes', len(edges), 'edges')


if __name__ == '__main__':
    main()
