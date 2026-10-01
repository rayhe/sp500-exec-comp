#!/usr/bin/env python3
"""Peer-network batch-8a fingerprint-queue repair (2026-10-01 run).

Follow-up to the 2026-10-01 batch-7 run. The Section-19 fingerprint queue
listed 391 cross-sector fingerprint-target edges across 234 sources; the
heaviest remaining tier is 25 sources with exactly 3 queued edges each.
Batch-8a takes 6 of them (ADM/CRM/DIS/NOW/INTU/DAL) and re-extracts each
source's comp-decisions peer group VERBATIM from its latest DEF 14A,
keeping only edges that match the verbatim group. TSR/PSU comparator
groups and explicitly-excluded reference groups are unstored per the
batches 3-7 convention.

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession, filing HTML fetched
with User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)", peer sections
transcribed verbatim. Evidence in /tmp/peersweep/batch8a/<TICKER>_peer.txt
(copied to goal hidden_files/peer-batch8a-20261001/).

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  ADM  93 -> 0  (DEF 14A 2026-03-26; peer group IS the S&P 100 Index -
        no named company peer group disclosed; "we do not have a direct
        competitor... in the public markets". All 93 stored edges were
        S&P 100 constituents swallowed by the extractor. Index-only ->
        isSource False, per AMZN/CLX/CTAS/L/NRG/TSLA precedent.)
  CRM  23 -> 17 (DEF 14A 2026-04-16; fiscal-2026 peer group, refreshed
        Oct 2024; dropped: BLK, NDAQ, STT fingerprint appendages +
        AAPL, AMZN, GOOGL, META mega-caps the filing explicitly removed;
        added SAP)
  DIS  19 -> 18 (DEF 14A 2026-01-22; UNION of 8-co Media Industry Peers
        and 18-co General Industry Peers - both "help evaluate
        compensation levels for the NEOs" (FE precedent); S&P 500 Media
        & Entertainment Index performance group unstored; GENUINE KEEP:
        MSFT (filing-verbatim cross-sector); dropped: FRT, PSA
        fingerprint appendages + PARA stale ticker; added PSKY, WBD)
  NOW  21 -> 16 (DEF 14A 2026-04-06; 2025/2026 peer group; the filing
        EXPLICITLY excludes the Supplemental Reference Group (AAPL,
        AMZN, GOOGL, META, MSFT) - "did not include these companies in
        our peer group"; dropped: BLK, GIS, TGT fingerprint appendages
        + CSCO; added EBAY, SNOW, TEAM, CRM)
  INTU 40 -> 17 (DEF 14A 2025-11-26; fiscal-2025 compensation peer
        group; the extractor had swallowed the 43-co TSR PSU comparator
        group (CDNS, CRWD, DDOG, FTNT, PLTR, RBLX, SNPS, TTWO, SMCI, MA
        ...); dropped all 23 non-members incl. CHTR, GIS, PSA)
  DAL  24 -> 21 (DEF 14A 2026-04-24; 21-co peer group "three major U.S.
        airlines and 18 other companies"; GENUINE KEEPS: PG (filing-
        verbatim cross-sector, cf. batch-6 FE/KMB/KR), UNP, UPS, UAL;
        dropped: ADP, AWK, ECL, GIS, V, WM fabrications; added AAL, BA,
        MCD)
"""
import json
import shutil

REPO = '/home/hatch/repos/sp500-exec-comp'
SRC = REPO + '/data/peer-network.json'

# source -> (filing string, [peer tickers in filing order])
NEW = {
    'CRM': ('DEF 14A 2026-04-16',
            ['ACN', 'DELL', 'PYPL', 'ADBE', 'IBM', 'QCOM', 'AMD',
             'INTU', 'SAP', 'XYZ', 'MSFT', 'NOW', 'AVGO', 'ORCL',
             'WDAY', 'CSCO', 'PANW']),
    'DIS': ('DEF 14A 2026-01-22',
            ['GOOGL', 'AMZN', 'AAPL', 'CMCSA', 'META', 'NFLX', 'PSKY',
             'WBD', 'T', 'CHTR', 'IBM', 'MSFT', 'NKE', 'ORCL', 'CRM',
             'TMUS', 'UBER', 'VZ']),
    'NOW': ('DEF 14A 2026-04-06',
            ['ADBE', 'EBAY', 'ORCL', 'SNOW', 'ABNB', 'EA', 'PANW',
             'UBER', 'TEAM', 'INTU', 'PYPL', 'V', 'XYZ', 'NFLX',
             'CRM', 'WDAY']),
    'INTU': ('DEF 14A 2025-11-26',
             ['ADBE', 'DASH', 'CRM', 'ABNB', 'EA', 'NOW', 'ADSK',
              'NFLX', 'UBER', 'XYZ', 'PANW', 'V', 'AVGO', 'PYPL',
              'WDAY', 'CSCO', 'QCOM']),
    'DAL': ('DEF 14A 2026-04-24',
            ['AAL', 'AXP', 'BBY', 'BA', 'KO', 'DE', 'FDX', 'HD',
             'HON', 'MAR', 'MCD', 'NKE', 'PG', 'RTX', 'LUV', 'SBUX',
             'TGT', 'UBER', 'UNP', 'UAL', 'UPS']),
}

# index-only sources: remove all edges, flip isSource True -> False
# (precedent: AMZN, CLX, CTAS, L, NRG, TSLA)
INDEX_ONLY = {
    'ADM': 'DEF 14A 2026-03-26',
}

# expected old edge sets (assertion guard) -- captured at
# 2026-10-01 14:00 PT from peer-network.json (868 nodes / 7,327 edges)
EXPECTED_OLD = {
    'CRM': ['AAPL', 'ACN', 'ADBE', 'AMD', 'AMZN', 'AVGO', 'BLK', 'CSCO',
            'DELL', 'GOOGL', 'IBM', 'INTU', 'META', 'MSFT', 'NDAQ',
            'NOW', 'ORCL', 'PANW', 'PYPL', 'QCOM', 'STT', 'WDAY', 'XYZ'],
    'DIS': ['AAPL', 'AMZN', 'CHTR', 'CMCSA', 'CRM', 'FRT', 'GOOGL',
            'IBM', 'META', 'MSFT', 'NFLX', 'NKE', 'ORCL', 'PARA', 'PSA',
            'T', 'TMUS', 'UBER', 'VZ'],
    'NOW': ['AAPL', 'ABNB', 'ADBE', 'AMZN', 'BLK', 'CSCO', 'EA', 'GIS',
            'GOOGL', 'INTU', 'META', 'MSFT', 'NFLX', 'ORCL', 'PANW',
            'PYPL', 'TGT', 'UBER', 'V', 'WDAY', 'XYZ'],
    'INTU': ['AAPL', 'ABNB', 'ADBE', 'ADSK', 'AVGO', 'CDNS', 'CHTR',
             'CRM', 'CRWD', 'CSCO', 'DASH', 'DDOG', 'DELL', 'EA', 'FIS',
             'FISV', 'FTNT', 'GIS', 'GOOGL', 'HPQ', 'MA', 'META',
             'MSFT', 'NFLX', 'NOW', 'ORCL', 'PANW', 'PLTR', 'PSA',
             'PYPL', 'QCOM', 'RBLX', 'ROP', 'SMCI', 'SNPS', 'TTWO',
             'UBER', 'V', 'WDAY', 'XYZ'],
    'DAL': ['ADP', 'AWK', 'AXP', 'BBY', 'DE', 'ECL', 'FDX', 'GIS', 'HD',
            'HON', 'KO', 'LUV', 'MAR', 'NKE', 'PG', 'RTX', 'SBUX',
            'TGT', 'UAL', 'UBER', 'UNP', 'UPS', 'V', 'WM'],
}
EXPECTED_OLD_COUNT = {'ADM': 93}


def main():
    bak = SRC.replace('.json', '_backup_20261001_1400_pre_batch8a.json')
    shutil.copy2(SRC, bak)
    print('backup:', bak)

    net = json.load(open(SRC))
    nodes, edges = net['nodes'], net['edges']
    by_ticker = {x['ticker']: x for x in nodes}

    # 1. index-only sources: drop all edges, flip isSource
    for src, filing in INDEX_ONLY.items():
        assert src in by_ticker, f'{src}: not a node'
        old = [e for e in edges if e['source'] == src]
        assert len(old) == EXPECTED_OLD_COUNT[src], \
            f'{src}: old edge count changed: {len(old)}'
        assert by_ticker[src].get('isSource') is True, f'{src}: not isSource'
        edges = [e for e in edges if e['source'] != src]
        by_ticker[src]['isSource'] = False
        print(f'{src}: {len(old)} old -> 0 new (index-only, {filing})')

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
    net['edges'] = edges
    nsrc = sum(1 for x in nodes if x.get('isSource') is True)
    net['metadata']['node_count'] = len(nodes)
    net['metadata']['edge_count'] = len(edges)
    net['metadata']['last_updated'] = '2026-10-01'
    net['metadata']['last_dq_repair'] = '2026-10-01'
    net['metadata']['sources'] = \
        f'{nsrc} DEF 14A proxy statements from S&P 500 companies'
    print('sources:', nsrc)

    with open(SRC, 'w') as f:
        json.dump(net, f, indent=1)
    print('wrote', SRC, '| nodes:', len(nodes), '| edges:', len(edges))


if __name__ == '__main__':
    main()
