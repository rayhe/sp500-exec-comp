#!/usr/bin/env python3
"""Batch-15b: revert the COST->TGT verified_cross_sector mark (2026-10-04).

The batch-15 apply script marked COST->TGT verified after finding
"Target Corporation" verbatim in Costco's DEF 14A 2026-04-06 peer-companies
list (factually genuine). But the pre-commit guard hard-failed:
verified_cross_sector marks must match the cross-sector fingerprint
pattern, and COST (Consumer Staples) is INSIDE TGT's home-sector set
{FINGERPRINT_TARGETS["TGT"] = {"Consumer Staples", "Consumer
Discretionary"}} -- so COST->TGT was never a fingerprint-queue member and
the mark violates invariant (b) ("drift: marked edge no longer matches the
queue pattern").

Root cause: batch-15's scope was taken from the 2026-10-04 14:14 PT
iteration-log candidate list, which was computed with the strict
sector-inequality definition over the 6 batch-8y-era targets, NOT the
guard's FINGERPRINT_TARGETS table (17 targets, TGT home = Staples +
Discretionary). Two batch-15 adjudications fell outside the true queue:
COST->TGT (marked -- reverted here) and CL->TGT (dropped -- the drop
stands: the CL filing contains zero "Target Corporation" mentions, so the
edge was fabricated regardless of queue membership; the guard has no
invariant against the drop itself).

The COST->TGT edge itself is untouched (it is genuine per the filing);
only the queue-pattern mark is removed.
"""

import json

SRC = '/home/hatch/repos/sp500-exec-comp/data/peer-network.json'


def main():
    net = json.load(open(SRC))
    vc = net['metadata'].get('verified_cross_sector', [])
    before = len(vc)
    vc = [v for v in vc
          if not (v.get('source') == 'COST' and v.get('target') == 'TGT'
                  and v.get('batch') == 'batch-15')]
    assert len(vc) == before - 1, \
        f'expected to remove exactly 1 mark, removed {before - len(vc)}'
    # the edge itself must still exist
    assert any(e['source'] == 'COST' and e['target'] == 'TGT'
               for e in net['edges']), 'COST->TGT edge missing!'
    vc.sort(key=lambda v: (v['source'], v['target']))
    net['metadata']['verified_cross_sector'] = vc
    json.dump(net, open(SRC, 'w'), indent=1)
    print(f'verified_cross_sector: {before} -> {len(vc)} (COST->TGT mark removed, edge kept)')


if __name__ == '__main__':
    main()
