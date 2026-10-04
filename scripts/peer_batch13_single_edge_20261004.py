#!/usr/bin/env python3
"""Peer-network batch-13 single-edge adjudication (2026-10-04 11:30 PDT run).

Fifth batch of the 10-19 tier under the batch-8y tier rule: single-edge
adjudication against the latest DEF 14A (drop or mark verified, group
untouched). The next 13 heaviest pending one-edge sources (all 6 remaining
at total_out=12, all 6 at total_out=11, plus the heaviest at total_out=10),
each with exactly one queued cross-sector fingerprint edge, adjudicated
filing-verbatim via EDGAR (SEC Archives curl open all run; Kit/1.0 UA;
sequential ~3s pacing; CIKs from company_tickers_exchange.json cross-checked
against the submissions name field; no subagents per the task execution
rule). Evidence: goal hidden_files/peer-batch13-20261004/
(<TICKER>_def14a.htm + <TICKER>_def14a.txt verbatim text +
batch13_submissions.json accession/URL map + fetch_def14a.py + prescan.py).

Adjudications (11 DROPPED, 2 MARKED VERIFIED):
- KMX->GIS: zero "General Mills" mentions full-text (DEF 14A 2026-05-12).
- MHK->IP: zero "International Paper" mentions. 2025 peer group is 15 cos
  (Builders FirstSource/Carrier/Eastman/Fortune Brands/Leggett & Platt/
  Lennox*/Masco/Newell/Owens Corning/PPG/RPM/Sherwin-Williams/Stanley
  Black & Decker/Trane/Whirlpool; JELD-WEN removed) (DEF 14A 2026-04-03).
- MOS->TGT: zero "Target Corporation" mentions; 101 bare "Target" hits are
  all compensation jargon ("Target incentive", "target opportunity", etc.;
  the regex-collision "Target inc" class is "Target incentive" mid-word).
  2025 Mosaic Peer Group is 15 cos (Air Products/DuPont/Newmont/Alcoa/
  Eastman/Nutrien/Barrick/Ecolab/PPG/Celanese/FMC/Teck/CF Industries/
  Freeport-McMoRan/Westlake/Corteva) (DEF 14A 2026-04-16).
- SPGI->TGT: zero "Target Corporation" mentions; 132 bare "Target" hits are
  all compensation jargon. Named peer group is the 10-K performance group
  (Moody's/CME/MSCI/FactSet/Verisk/ICE) (DEF 14A 2026-03-31).
- TXT->GIS: single "General Mills" hit is a director bio ("served as a
  director of General Mills from 2009 until September 2024") - director-bio
  vector, second catch after CBOE/IP. (DEF 14A 2026-03-05).
- VLO->GIS: zero "General Mills" mentions. Performance Peer Group for
  relative TSR is 10 cos (ConocoPhillips*/Marathon Petroleum*/CVR/OXY*/Delek/
  PBF/EOG*/Phillips 66*/HF Sinclair/XLE) + LyondellBasell; * = also in the
  Compensation Comparator Peer Group (DEF 14A 2026-03-19).
- BALL->GIS: FILING-GENUINE -> marked verified. "General Mills Inc."
  verbatim in "The 2025 Peer Group, which was used to inform decisions in
  setting 2025 target pay for NEOs" (16 cos incl. Avery Dennison/Molson
  Coors/Campbell Soup/ConAgra/Kimberly-Clark; food-&-beverage inclusion is
  deliberate per the stated criteria - aluminum-packaged shelf-space peers).
  The MDLZ/WY-class observation again: the fingerprint fires on genuinely
  cross-sector-adjacent companies. (DEF 14A 2026-03-17).
- GOOGL->MSFT: FILING-GENUINE -> marked verified. "Microsoft Corporation"
  verbatim in "the Compensation Committee selected the following peer
  companies for 2025" (11 cos: Amazon/Meta/Oracle/Apple/Microsoft/
  Salesforce/Cisco/Netflix/Disney/IBM/Nvidia), "used to obtain compensation
  benchmarks for our named executive officers". (DEF 14A 2026-04-24).
- HII->GIS: zero "General Mills" mentions. 2025 NEO compensation analysis
  peer group is 16 cos (Booz Allen/Leidos/Cognizant/Northrop/Dover/Oshkosh/
  GD/Parker/Howmet/Spirit Aero/Jacobs/Teledyne/KBR/Textron/L3Harris/
  TransDigm; Spirit out / Amentum in for 2026) (DEF 14A 2026-03-20).
- MLM->GIS: zero "General Mills" mentions. 2025 Compensation Peer Group is
  17 cos (Albemarle/Carlisle/Celanese/CF Industries/...); separate S&P 500
  TSR Peer Group for PSUs (DEF 14A 2026-04-15).
- MNST->IP: zero "International Paper" mentions; no named compensation
  peer list (FW Cook benchmarking reference point only) (DEF 14A
  2026-03-27).
- REGN->CHTR: zero "Charter Communications" mentions; 12 bare "Charter"
  hits are all corporate-charter / Lead Independent Director Charter /
  committee-charter boilerplate - charter-boilerplate vector, eighth catch
  (CRWD/CPB/APA/HSY/XEL + 2 more). (DEF 14A 2026-04-24).
- AIZ->IP: zero "International Paper" mentions full-text (DEF 14A
  2026-04-06).

Marks: BALL->GIS and GOOGL->MSFT appended to
metadata.verified_cross_sector (77 entries, sorted). Both stored edges
claim group_type="primary" and the adjudicating filings match the stored
edge filing dates exactly (2026-03-17 / 2026-04-24), so the invariant
(single filing per edge set) is consistent with marking.
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
    'KMX':  ('GIS',  'DEF 14A 2026-05-12'),
    'MHK':  ('IP',   'DEF 14A 2026-04-03'),
    'MOS':  ('TGT',  'DEF 14A 2026-04-16'),
    'SPGI': ('TGT',  'DEF 14A 2026-03-31'),
    'TXT':  ('GIS',  'DEF 14A 2026-03-05'),
    'VLO':  ('GIS',  'DEF 14A 2026-03-19'),
    'HII':  ('GIS',  'DEF 14A 2026-03-20'),
    'MLM':  ('GIS',  'DEF 14A 2026-04-15'),
    'MNST': ('IP',   'DEF 14A 2026-03-27'),
    'REGN': ('CHTR', 'DEF 14A 2026-04-24'),
    'AIZ':  ('IP',   'DEF 14A 2026-04-06'),
}

# source -> (verified target, filing, batch) - edge stays; list grows
MARKS = {
    'BALL':  ('GIS',  'DEF 14A 2026-03-17', 'peer-batch13-20261004'),
    'GOOGL': ('MSFT', 'DEF 14A 2026-04-24', 'peer-batch13-20261004'),
}


def main():
    bak = SRC.replace('.json', '_backup_20261004_1130_pre_batch13.json')
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
