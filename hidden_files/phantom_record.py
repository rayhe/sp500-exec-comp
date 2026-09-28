#!/usr/bin/env python3
"""Increment the metadata.phantom_removed campaign counter after a DQ batch.

Convention (established 2026-09-27 23:30 PT run): every DQ data-repair batch
script calls record_batch() with its pre-repair and post-repair
compensation.json states. The batch's phantom delta is

    delta = sum(pre exec `total`) - sum(post exec `total`)

positive when parser-invented compensation was removed, negative when genuine
missing-NEO rows were restored filing-verbatim.

Usage from a DQ batch script (repo root as cwd):

    import sys
    sys.path.insert(0, "hidden_files")
    import phantom_record
    delta = phantom_record.record_batch(
        pre_path="hidden_files/compensation_backup_<stamp>_pre_dqbatch.json",
        data_path="data/compensation.json",
        stamp="2026-09-27 23:30 PT",
    )
    print(f"phantom delta: ${delta:,}")

record_batch() rewrites data/compensation.json with the counters incremented
(cumulative += delta; gross_removed += max(delta,0); restored += -min(delta,0);
batches += 1; last_updated = stamp) and PRESERVES the canonical serialization
(indent=1, ensure_ascii=True) byte-identically outside the counter block.

After calling it, the batch script must also re-sync the dataq modal's static
fallback in js/app.js (the "dataq-phantom-block" div): the guard's section 4f
fails the commit if the fallback numbers drift from metadata.phantom_removed.
The live renderer (_dataqPhantomHtml) needs no changes.

Seed note: the counters were seeded 2026-09-27 23:30 PT by an exact git-blob
computation over the 63 DQ-labeled data-repair commits (2026-09-12 onward).
Per-batch table: goal hidden_files/phantom-counter/cumulative.json.
Script: goal hidden_files/phantom-counter/compute_cumulative.py.
Do NOT seed from the iteration log's rounded prose figures.
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _exec_total(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    total = 0
    for c in d.get("companies", []):
        for e in c.get("executives", []):
            v = e.get("total")
            if isinstance(v, (int, float)):
                total += v
    return total


def record_batch(pre_path, data_path=None, stamp=None):
    data_path = data_path or os.path.join(REPO_ROOT, "data", "compensation.json")
    pre_path = pre_path if os.path.isabs(pre_path) else os.path.join(REPO_ROOT, pre_path)

    delta = _exec_total(pre_path) - _exec_total(data_path)
    delta = int(round(delta))

    with open(data_path, encoding="utf-8") as f:
        raw = f.read()
    d = json.loads(raw)
    pr = d["metadata"].get("phantom_removed")
    if not isinstance(pr, dict):
        raise RuntimeError("metadata.phantom_removed missing — seed it first (see module docstring)")

    pr["cumulative"] = int(pr["cumulative"]) + delta
    pr["gross_removed"] = int(pr["gross_removed"]) + max(delta, 0)
    pr["restored"] = int(pr["restored"]) + max(-delta, 0)
    pr["batches"] = int(pr["batches"]) + 1
    if stamp:
        pr["last_updated"] = stamp

    out = json.dumps(d, indent=1, ensure_ascii=True)
    with open(data_path, "w", encoding="utf-8") as f:
        f.write(out)
    return delta


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Increment phantom_removed counters after a DQ batch")
    ap.add_argument("pre_path", help="pre-repair backup of data/compensation.json")
    ap.add_argument("--data-path", default=None)
    ap.add_argument("--stamp", default=None, help='e.g. "2026-09-28 02:00 PT"')
    args = ap.parse_args()
    delta = record_batch(args.pre_path, args.data_path, args.stamp)
    print(f"phantom delta: ${delta:,}")
