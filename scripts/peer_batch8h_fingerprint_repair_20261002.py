#!/usr/bin/env python3
"""Peer-network batch-8h fingerprint-queue repair (2026-10-02 run).

Follow-up to the batch-8a/8b/8c/8d/8e/8f/8g runs (2026-10-01/02). After 8g, the
Section-19 fingerprint queue holds 274 cross-sector fingerprint-target edges
across 192 sources; the 3-edge tier is fully drained. Batch-8h takes the 6
heaviest remaining 2-queue sources by total outbound edge count
(DTE 26 / BKNG 24 / NOC 24 / SRE 24 / BKR 23 / CEG 23) and re-extracts each
source's comp-decisions peer group VERBATIM from its latest DEF 14A, keeping
only edges that match the verbatim group. TSR/performance comparator groups,
2026-variant groups, and unnamed survey databases are documented but unstored
per the batches 3-8g convention (V Block->Uber / HPQ FY2026 / GDDY 2026 /
KMB 2026 / CNP 2026 / IFF 2026 / KDP 2026 / GEV 2026 / DVN Jan-2026 /
CRL 2026 / ADM index-only / CTAS+ETN TSR-only precedents).

Extraction (this run, no subagents per the task execution rule): EDGAR
submissions JSON for the latest DEF 14A accession (all six accessions
re-verified against data.sec.gov this run), filing HTML fetched with
User-Agent "Kit/1.0 (factoryfactorykit@gmail.com)" (sequential, 2-3s pacing;
non-padded CIK in Archive URLs + curl -L per the batch-8d note). Peer
sections transcribed verbatim. Evidence in goal
hidden_files/peer-batch8h-20261002/ <TICKER>_peer.txt (verbatim
transcriptions) + batch8h_filings.json (accession/URL map). /tmp/peersweep/
was wiped mid-run by a VM /tmp recycle; filings were re-downloaded with
identical byte sizes and re-anchored before transcription.

Repairs (6 sources; all from latest DEF 14A, comp-decisions groups):

  DTE   26 -> 23 (DEF 14A 2026-03-12; peer group approved by O&C Committee
        June 2024, 23 utilities/energy cos verbatim; queued GIS/IP
        fabrications dropped; also AWK/GE/KEY dropped)
  BKNG  24 -> 16 (DEF 14A 2026-04-21; 2025-compensation-decisions
        "Compensation Peer Group", 16 travel/e-commerce/tech cos verbatim
        (determined 2024); queued IP fabrication dropped; MSFT SURVIVES -
        genuine verbatim cross-sector edge, marked verified; Alphabet stored
        as GOOGL per the 17-edge network precedent; IAC/InterActiveCorp
        stored as IAC - the company renamed to People Incorporated on
        2026-06-04 (ticker IAC->PPLI, EDGAR + PR Newswire verified),
        delisted-peer precedent keeps the filing-era ticker; 2025 PSU
        relative-TSR travel/tourism group documented unstored per
        TSR-group precedent)
  NOC   24 -> 22 (DEF 14A 2026-04-03; Target Industry Peer Group (TIPG) used
        for 2025 compensation decisions, 22 cos verbatim (incl. the six
        (1)-marked direct peers); queued COF/IP fabrications dropped; also
        HII/KEY/LDOS dropped; Performance Peer Group (BA/GD/LHX/LMT/RTX)
        and 2023 TSR Peer Group documented unstored per precedent)
  SRE   24 -> 28 (DEF 14A 2026-03-27; 28-co Compensation Peer Group used in
        the late-2024 labor market review for 2025 target pay, verbatim
        with filing GICS sectors; Marsh & McLennan stored as MRSH - SEC
        submissions JSON shows the live NYSE ticker is MRSH (changed from
        MMC in 2025), the old edge set's MRSH was correct; Interpublic
        stored as IPG verbatim (filing footnote: Omnicom subsidiary since
        2025-11-26, data excluded from Table 8 but still named in the
        group); queued IP/TGT fabrications dropped; also AWK/OMC dropped)
  BKR   23 -> 27 (DEF 14A 2026-03-30; 27-co Compensation "Reference Group"
        (blend of general industry, capital intensive, global oil & gas),
        verbatim; International Paper Company SURVIVES - genuine verbatim
        cross-sector edge (BKR Energy -> IP Materials), marked verified;
        queued COF fabrication dropped; Performance "Peer Group" (OSX index
        + TechnipFMC + S&P 500 Industrials median) documented unstored per
        TSR-group precedent)
  CEG   23 -> 18 (DEF 14A 2026-03-19; 2025 blended peer group (8 energy
        services/IPPs + 10 general industry), 18 cos verbatim with filing
        tickers; International Paper SURVIVES - genuine verbatim
        cross-sector edge (CEG Utilities -> IP Materials), marked verified;
        WestRock stored as WRK verbatim - Smurfit Westrock merger 2024,
        ticker dead, delisted-peer precedent; queued CHTR/GIS fabrications
        dropped; also AWK/CAT/DE/DOW/GE/NOC/STZ/WEC dropped; the disclosed
        2026-variant group (+CAT/+COP/+DE/+DOW/+GEV/+GD/+GE/+NOC/+SLB/+UNP;
        -AES/-CSX/-D/-DINO/-IP/-PPG/-WRK) documented but NOT stored per the
        2026-variant precedent chain; rTSR custom group unnamed in filing)

Three new verified_cross_sector marks this batch (all filing-verbatim,
surviving the repair): BKNG->MSFT, BKR->IP, CEG->IP. Queue 274->262 pending;
verified 44->47.

No ticker-slot collisions: DINO/IAC/MPLX/TRIP/WRK are all free (IAC absent
from live SEC company_tickers.json - renamed PPLI; WRK delisted 2024;
DINO/MPLX/TRIP SEC-verified 2026-10-02).
"""
import json
import shutil

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'

# new peer-only nodes: ticker -> (name, sector)
NEW_NODES = {
    'DINO': ('HF Sinclair Corp', 'Energy'),
    'IAC': ('IAC/InterActiveCorp', 'Communication Services'),
    'MPLX': ('MPLX LP', 'Energy'),
    'TRIP': ('TripAdvisor, Inc.', 'Consumer Discretionary'),
    'WRK': ('WestRock Company', 'Materials'),
}

# ticker -> (filing string, verbatim peer ticker list)
NEW = {
    'DTE': ('DEF 14A 2026-03-12',
            ['LNT', 'EXC', 'AEE', 'FE', 'AEP', 'NI', 'CNP', 'PCG',
             'CMS', 'PNW', 'ED', 'PPL', 'D', 'PEG', 'DUK', 'SRE',
             'EIX', 'SO', 'ETR', 'WEC', 'EVRG', 'XEL', 'ES']),
    'BKNG': ('DEF 14A 2026-04-21',
             ['ADBE', 'EXPE', 'PYPL', 'ABNB', 'IAC', 'TRIP', 'GOOGL',
              'MAR', 'UBER', 'AMZN', 'META', 'W', 'EBAY', 'MSFT',
              'EA', 'NFLX']),
    'NOC': ('DEF 14A 2026-04-03',
            ['MMM', 'HON', 'ABT', 'ITW', 'AMAT', 'JCI', 'BA', 'LHX',
             'CAT', 'LRCX', 'CSCO', 'LMT', 'CMI', 'MDT', 'DE',
             'PCAR', 'ETN', 'PH', 'EMR', 'QCOM', 'GD', 'RTX']),
    'SRE': ('DEF 14A 2026-03-27',
            ['APD', 'AEP', 'AMT', 'ADI', 'CNP', 'LNG', 'GLW', 'D',
             'DUK', 'EIX', 'ETR', 'HLT', 'ITW', 'IFF', 'IPG', 'IQV',
             'J', 'KMB', 'LHX', 'MRSH', 'MPLX', 'NEE', 'PCG',
             'PEG', 'SLB', 'SO', 'TXT', 'WMB']),
    'BKR': ('DEF 14A 2026-03-30',
            ['MMM', 'CAT', 'COP', 'CMI', 'DHR', 'DE', 'DVN', 'ETN',
             'EMR', 'EOG', 'GD', 'GEV', 'HAL', 'HON', 'ITW', 'IP',
             'JCI', 'LHX', 'NOC', 'NOV', 'OXY', 'PCAR', 'PH',
             'PWR', 'SLB', 'FTI', 'TXT']),
    'CEG': ('DEF 14A 2026-03-19',
            ['AEP', 'D', 'DUK', 'NEE', 'NRG', 'AES', 'VST', 'SO',
             'LNG', 'CSX', 'IP', 'DINO', 'LYB', 'NUE', 'OXY',
             'PPG', 'SHW', 'WRK']),
}

# no-named-group sources: none this batch (all six name comp groups)

# expected old edge sets (assertion guard) -- captured at
# 2026-10-02 06:10 PT from peer-network.json (909 nodes / 7,071 edges)
EXPECTED_OLD = {
    'DTE': ['AEE', 'AEP', 'AWK', 'CMS', 'CNP', 'D', 'DUK', 'ED',
            'ES', 'ETR', 'EVRG', 'EXC', 'FE', 'GE', 'GIS', 'IP',
            'KEY', 'LNT', 'NI', 'PCG', 'PEG', 'PNW', 'PPL', 'SO',
            'WEC', 'XEL'],
    'BKNG': ['ABNB', 'ADBE', 'AMZN', 'AWK', 'CCL', 'DAL', 'EA',
             'ED', 'EXPE', 'GOOGL', 'HLT', 'ICE', 'IP', 'LUV',
             'MAR', 'META', 'MSFT', 'NCLH', 'NFLX', 'PYPL', 'RCL',
             'SPGI', 'UAL', 'UBER'],
    'NOC': ['ABT', 'AMAT', 'BA', 'CAT', 'CMI', 'COF', 'CSCO', 'DE',
            'EMR', 'ETN', 'GD', 'HII', 'IP', 'ITW', 'JCI', 'KEY',
            'LDOS', 'LMT', 'LRCX', 'MDT', 'PCAR', 'PH', 'QCOM',
            'RTX'],
    'SRE': ['ADI', 'AMT', 'AWK', 'CNP', 'D', 'DUK', 'ETR', 'HLT',
            'IFF', 'IP', 'IPG', 'IQV', 'ITW', 'J', 'KMB', 'MRSH',
            'NEE', 'OMC', 'PCG', 'PEG', 'SO', 'TGT', 'TXT', 'WMB'],
    'BKR': ['CAT', 'CMI', 'COF', 'COP', 'DE', 'DHR', 'DVN', 'EMR',
            'EOG', 'ETN', 'GD', 'GEV', 'HAL', 'HON', 'IP', 'ITW',
            'JCI', 'NOC', 'OXY', 'PCAR', 'PH', 'SLB', 'TXT'],
    'CEG': ['AWK', 'CAT', 'CHTR', 'CSX', 'D', 'DE', 'DOW', 'DUK',
            'GE', 'GIS', 'LYB', 'NEE', 'NOC', 'NRG', 'NUE', 'OXY',
            'PPG', 'SHW', 'SO', 'STZ', 'VST', 'WEC', 'WMB'],
}


def main():
    bak = SRC.replace('.json', '_backup_20261002_0610_pre_batch8h.json')
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
