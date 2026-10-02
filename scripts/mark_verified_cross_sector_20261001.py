#!/usr/bin/env python3
"""Mark verified-genuine cross-sector fingerprint edges in peer-network.json.

Background: the 2026-09-30 to 2026-10-01 extractor-fingerprint DQ series
(repair scripts peer_refresh_20260930.py, peer_thinedge_repair_20260930.py,
peer_batch2_refresh_20260930.py, peer_bank_garbage_repair_20260930.py,
peer_batch3_fingerprint_repair_20260930.py,
peer_batch4_gis_fingerprint_repair_20261001.py,
peer_batch5_thin_gis_cof_repair_20261001.py,
peer_batch6_thin_gis_cof_repair_20261001.py,
peer_batch7_fingerprint_repair_20261001.py) replaced 129 sources' FULL
outgoing edge sets with the compensation peer group transcribed verbatim
from each company's latest DEF 14A. Every repair script asserted the old
edge set and replaced it wholesale, so a repaired source's current edges
are filing-verbatim by construction.

The pre-commit guard's Section 19 flags edges where a source cites a
fingerprint target (GIS, COF, MSFT, PG, ...) outside the target's home
sectors. For repaired sources those flags are false positives: the filing
genuinely discloses the cross-sector peer (e.g. FE's 33-company general-
industry group, KVUE's GIS/HSY, CCI's BLK/STT/GIS). Until now that
distinction lived only in commit messages, so the queue kept flagging
already-verified edges and future batch runs risked re-repairing them.

This script moves the distinction into the data: it builds the repair map
(source -> (batch, filing)) by parsing the repair scripts' NEW dicts,
asserts the single-filing invariant for every repaired source (all current
outgoing edges carry the documented repair filing; violation = hard fail,
no write), and writes metadata["verified_cross_sector"] = the Section-19
queued edges from fully-verified sources, each with filing + batch
provenance. The guard's Section 19 then reports pending vs verified
separately and fails on stale marks or unmarked repaired-source edges.

Usage:
  python3 scripts/mark_verified_cross_sector_20261001.py   # applies + rewrites JSON
  python3 scripts/mark_verified_cross_sector_20261001.py --check  # dry run, no write

Exit 0 on success, non-zero on invariant violation (no write in either mode).
"""

import json
import os
import re
import shutil
import sys
from collections import OrderedDict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PEER_JSON = os.path.join(REPO, "data", "peer-network.json")

# batch label -> repair script, in chronological order (for "latest wins")
REPAIR_SCRIPTS = OrderedDict([
    ("peer-refresh-20260930", "scripts/peer_refresh_20260930.py"),
    ("peer-thinedge-20260930", "scripts/peer_thinedge_repair_20260930.py"),
    ("peer-batch2-20260930", "scripts/peer_batch2_refresh_20260930.py"),
    ("peer-bank-20260930", "scripts/peer_bank_garbage_repair_20260930.py"),
    ("peer-batch3-20260930", "scripts/peer_batch3_fingerprint_repair_20260930.py"),
    ("peer-batch4-20261001", "scripts/peer_batch4_gis_fingerprint_repair_20261001.py"),
    ("peer-batch5-20261001", "scripts/peer_batch5_thin_gis_cof_repair_20261001.py"),
    ("peer-batch6-20261001", "scripts/peer_batch6_thin_gis_cof_repair_20261001.py"),
    ("peer-batch7-20261001", "scripts/peer_batch7_fingerprint_repair_20261001.py"),
    ("peer-batch8a-20261001", "scripts/peer_batch8a_fingerprint_repair_20261001.py"),
    ("peer-batch8b-20261001", "scripts/peer_batch8b_fingerprint_repair_20261001.py"),
    ("peer-batch8c-20261001", "scripts/peer_batch8c_fingerprint_repair_20261001.py"),
    ("peer-batch8d-20261001", "scripts/peer_batch8d_fingerprint_repair_20261001.py"),
    ("peer-batch8e-20261001", "scripts/peer_batch8e_fingerprint_repair_20261001.py"),
    ("peer-batch8f-20261002", "scripts/peer_batch8f_fingerprint_repair_20261002.py"),
    ("peer-batch8g-20261002", "scripts/peer_batch8g_fingerprint_repair_20261002.py"),
    ("peer-batch8h-20261002", "scripts/peer_batch8h_fingerprint_repair_20261002.py"),
])

# Same table as check_metadata_consistency.py Section 19 (kept in sync here;
# the guard imports FINGERPRINT_TARGETS and REPAIR_MAP from this module).
FINGERPRINT_TARGETS = {
    "GIS": {"Consumer Staples"},
    "HSY": {"Consumer Staples"},
    "PG": {"Consumer Staples"},
    "TGT": {"Consumer Staples", "Consumer Discretionary"},
    "COF": {"Financials"},
    "BLK": {"Financials"},
    "STT": {"Financials"},
    "PFG": {"Financials"},
    "NDAQ": {"Financials"},
    "CHTR": {"Communication Services"},
    "PSA": {"Real Estate"},
    "FRT": {"Real Estate"},
    "WM": {"Industrials"},
    "KMI": {"Energy"},
    "CVX": {"Energy"},
    "IP": {"Materials"},
    "MSFT": {"Information Technology"},
}


def build_repair_map():
    """source ticker -> (batch label, documented repair filing)."""
    rep = {}
    for label, rel in REPAIR_SCRIPTS.items():
        src = open(os.path.join(REPO, rel), encoding="utf-8").read()
        m = re.search(r"^NEW = \{(.*?)\n\}", src, re.M | re.S)
        if not m:
            raise RuntimeError(f"{rel}: NEW dict not found")
        pairs = re.findall(
            r"^\s*'([A-Z][A-Z0-9.\-]{0,6})'\s*:\s*\('([^']+)'",
            m.group(1), re.M)
        if not pairs:
            raise RuntimeError(f"{rel}: no NEW entries parsed")
        for ticker, filing in pairs:
            # chronological order; latest batch wins on re-repair
            rep[ticker] = (label, filing)
    return rep


def queued_edges(peer):
    """Section-19 queue: (source, src_sector, target, tgt_sector) flagged edges."""
    sectors = {n.get("ticker"): n.get("sector") for n in peer.get("nodes", [])}
    out = []
    for e in peer.get("edges", []):
        tgt = e.get("target")
        home = FINGERPRINT_TARGETS.get(tgt)
        if not home:
            continue
        src = e.get("source")
        ssec = sectors.get(src)
        if ssec not in home:
            out.append((src, ssec, tgt, sectors.get(tgt)))
    return sorted(set(out))


def main():
    check_only = "--check" in sys.argv
    repair_map = build_repair_map()
    with open(PEER_JSON, encoding="utf-8") as f:
        peer = json.load(f)

    edges = peer.get("edges", [])
    by_source = {}
    for e in edges:
        by_source.setdefault(e.get("source"), []).append(e)

    # 1. Single-filing invariant: every repaired source's current outbound
    #    edge set must carry exactly the documented repair filing.
    violations = []
    for src, (batch, filing) in sorted(repair_map.items()):
        cur = by_source.get(src, [])
        filings = {e.get("filing") for e in cur}
        if filings != {filing}:
            violations.append(
                f"{src} ({batch}): current filings {sorted(filings)} != "
                f"documented {filing!r} ({len(cur)} edges)")
    if violations:
        print("INVARIANT VIOLATION - refusing to write:")
        for v in violations:
            print("  -", v)
        return 1

    # 2. Mark queued edges from fully-verified (repaired) sources.
    verified = []
    for src, ssec, tgt, tsec in queued_edges(peer):
        if src in repair_map:
            batch, filing = repair_map[src]
            verified.append({"source": src, "target": tgt,
                             "filing": filing, "batch": batch})
    verified.sort(key=lambda d: (d["source"], d["target"]))
    pending = len(queued_edges(peer)) - len(verified)

    per_batch = {}
    for v in verified:
        per_batch[v["batch"]] = per_batch.get(v["batch"], 0) + 1

    if check_only:
        print(f"dry run: {len(verified)} edges would be marked, "
              f"{pending} pending; invariant green "
              f"({len(repair_map)} repaired sources checked)")
        return 0

    bak = PEER_JSON.replace(".json", "_backup_20261001_1200_pre_verifiedmarks.json")
    shutil.copy2(PEER_JSON, bak)
    peer["metadata"]["verified_cross_sector"] = verified
    with open(PEER_JSON, "w", encoding="utf-8") as f:
        json.dump(peer, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"marked {len(verified)} verified-genuine cross-sector edges "
          f"({pending} remain pending); backup {os.path.basename(bak)}")
    for b in sorted(per_batch):
        print(f"  {b}: {per_batch[b]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
