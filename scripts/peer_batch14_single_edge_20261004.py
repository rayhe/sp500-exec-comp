#!/usr/bin/env python3
"""Peer-network batch-14 single-edge adjudication (2026-10-04 14:00 PDT run).

Fifth batch of the 10-19 tier under the batch-8y tier rule: single-edge
adjudication against the latest DEF 14A (drop or mark verified, group
untouched). The next 13 heaviest pending one-edge sources (all 6 remaining
at total_out=12, all 6 at total_out=11, plus the heaviest at total_out=10),
each with exactly one queued cross-sector fingerprint edge, adjudicated
filing-verbatim via EDGAR (SEC Archives curl open all run; Kit/1.0 UA;
sequential ~3s pacing; CIKs from company_tickers_exchange.json cross-checked
against the submissions name field; no subagents per the task execution
rule). Evidence: goal hidden_files/peer-batch14-20261004/
(<TICKER>_def14a.htm + <TICKER>_def14a.txt verbatim text +
batch14_submissions.json accession/URL map + fetch_def14a.py + prescan.py).

Adjudications (all 10 DROPPED - none filing-genuine):
- TFC->CHTR: zero "Charter Communications" mentions; 14 bare "Charter"
  hits are all corporate-charter / committee-charter boilerplate -
  charter-boilerplate vector, ninth catch (CRWD/CPB/APA/HSY/XEL + 3 more).
  2025 peer group is 10 banks (JPM/BAC/WFC/USB/PNC/...). (DEF 14A 2026-03-16).
- TECH->GIS: zero "General Mills" mentions in the full filing (DEF 14A
  2025-09-19).
- SNA->GIS: zero "General Mills" mentions in the full filing (DEF 14A
  2026-03-12).
- PM->PSA: zero "Public Storage" mentions in the full filing (DEF 14A
  2026-03-26).
- PKG->GIS: zero "General Mills" mentions in the full filing (DEF 14A
  2026-03-27).
- JBL->GIS: zero "General Mills" mentions in the full filing (DEF 14A
  2025-12-12).
- FITB->CHTR: zero "Charter Communications" mentions; 16 bare "Charter"
  hits are all corporate-charter / committee-charter boilerplate -
  charter-boilerplate vector, tenth catch. 2025 Compensation Peer Group
  is 12 banks (CFG/MTB/CMA/PNC/FHN/RF/FCNCA/TFC/HBAN/USB/KEY/ZION).
  (DEF 14A 2026-03-09).
- DGX->PSA: zero "Public Storage" mentions in the full filing (DEF 14A
  2026-04-06).
- CMI->GIS: the 5 "General Mills" hits are all director-bio text for
  Kimberly A. Nelson (retired SVP External Relations, General Mills) -
  not a peer-group listing (director-bio vector, third catch after
  IP->GIS batch-9 / AIZ batch-13 pattern). (DEF 14A 2026-04-02).
- BRO->GIS: zero "General Mills" mentions in the full filing (DEF 14A
  2026-03-24).

No marks this batch: none of the 10 adjudicated edges is filing-genuine.
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
    'BRO':  ('GIS',  'DEF 14A 2026-03-24'),
    'CMI':  ('GIS',  'DEF 14A 2026-04-02'),
    'DGX':  ('PSA',  'DEF 14A 2026-04-06'),
    'FITB': ('CHTR', 'DEF 14A 2026-03-09'),
    'JBL':  ('GIS',  'DEF 14A 2025-12-12'),
    'PKG':  ('GIS',  'DEF 14A 2026-03-27'),
    'PM':   ('PSA',  'DEF 14A 2026-03-26'),
    'SNA':  ('GIS',  'DEF 14A 2026-03-12'),
    'TECH': ('GIS',  'DEF 14A 2025-09-19'),
    'TFC':  ('CHTR', 'DEF 14A 2026-03-16'),
}

MARKS = {}


def main():
    bak = SRC.replace('.json', '_backup_20261004_1130_pre_batch14.json')
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
        # adjudicating filing must match the stored edge filing for a drop too
        assert matches[0].get('filing') == filing, \
            f'{src}->{tgt}: stored filing {matches[0].get("filing")} != {filing}'
        edges = [e for e in edges if not (e['source'] == src and e['target'] == tgt)]
        print(f'dropped {src}->{tgt} ({filing})')

    assert n_before - len(edges) == len(DROPS), 'drop count mismatch'
    print(f'edges: {n_before} -> {len(edges)}')

    # 2. mark filing-genuine edges (edge stays; verified list grows)
    vc = net['metadata'].get('verified_cross_sector', [])
    for src, (tgt, filing, batch) in sorted(MARKS.items()):
        matches = [e for e in edges if e['source'] == src and e['target'] == tgt]
        assert len(matches) == 1, f'{src}->{tgt}: expected 1 live edge for marking'
        assert matches[0].get('filing') == filing, \
            f'{src}->{tgt}: stored filing {matches[0].get("filing")} != {filing}'
        assert not any(v['source'] == src and v['target'] == tgt for v in vc), \
            f'{src}->{tgt}: already marked'
        vc.append({'source': src, 'target': tgt, 'filing': filing, 'batch': batch})
        print(f'marked verified {src}->{tgt} ({filing})')
    vc.sort(key=lambda v: (v['source'], v['target']))
    net['metadata']['verified_cross_sector'] = vc
    print(f'verified_cross_sector: {len(vc)} entries')

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
