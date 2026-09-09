#!/usr/bin/env python3
"""Metadata truthfulness guard for data/compensation.json.

Asserts that every metadata count field equals an independent recount of
the stored records, so stale-count drift can never be committed again.
History: 2026-09-07 (7c6a07b) synced 6700->6750, 2026-09-09 (a3be999)
synced 6759->6764, 2026-09-09 07:30 run synced buckets after 3f1a80c's
pension-repair run left data_quality at the old bucket values.

Usage:
  python3 scripts/check_metadata_consistency.py          # manual run
  cp scripts/check_metadata_consistency.py .git/hooks/pre-commit  # install hook

Exit 0 when all asserts pass, non-zero with a failure list otherwise.
The check is read-only: it never modifies the JSON.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")

# record-level _total_source label -> metadata data_quality key
LABEL_TO_KEY = {
    "verified": "verified",
    "DEF14A-verified 2026-09-07": "def14a_verified_20260907",
    "DEF14A-verified 2026-09-08": "def14a_verified_20260908",
    "recomputed": "recomputed",
    "rounding": "rounding",
    "incomplete_components": "incomplete_components",
    "bloated_component": "bloated_component",
    "recomputed_implausible_total": "recomputed_implausible_total",
    "component_mismatch": "component_mismatch",
}
# keys that must NOT appear in the bucket-sum (derived / non-bucket)
SUM_EXCLUDED = {"verified_total"}


def fail(msg, failures):
    failures.append(msg)


def main():
    failures = []
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    companies = data["companies"]
    n = sum(len(c.get("executives", [])) for c in companies)
    meta = data.get("metadata", {})

    # 1. headline counts
    if meta.get("total_neo_records") != n:
        fail(f"total_neo_records={meta.get('total_neo_records')} != recount {n}", failures)
    if meta.get("total_executives") != n:
        fail(f"total_executives={meta.get('total_executives')} != recount {n}", failures)

    # 2. title coverage
    title_gaps = sum(
        1 for c in companies for e in c.get("executives", []) if not e.get("title")
    )
    expect_tc = f"{n - title_gaps}/{n}"
    if meta.get("title_coverage") != expect_tc:
        fail(f"title_coverage={meta.get('title_coverage')!r} != {expect_tc!r}", failures)

    # 3. audit buckets vs record-level _total_source
    src_counts = Counter()
    unlabeled = 0
    for c in companies:
        for e in c.get("executives", []):
            src = e.get("_total_source")
            if src is None:
                unlabeled += 1
            else:
                src_counts[src] += 1
    if unlabeled:
        fail(f"{unlabeled} exec rows missing _total_source", failures)
    unknown = [s for s in src_counts if s not in LABEL_TO_KEY]
    if unknown:
        fail(f"unknown _total_source labels not in LABEL_TO_KEY: {unknown}", failures)

    for block_name in ("data_quality", "data_quality_detailed"):
        block = meta.get(block_name)
        if not isinstance(block, dict):
            fail(f"metadata.{block_name} missing or not a dict", failures)
            continue
        for label, key in LABEL_TO_KEY.items():
            if key in block and block[key] != src_counts.get(label, 0):
                fail(
                    f"{block_name}.{key}={block[key]} != recount "
                    f"({label})={src_counts.get(label, 0)}",
                    failures,
                )
        # verified_total convention: verified + both DEF14A buckets
        want_vt = (
            src_counts.get("verified", 0)
            + src_counts.get("DEF14A-verified 2026-09-07", 0)
            + src_counts.get("DEF14A-verified 2026-09-08", 0)
        )
        if block.get("verified_total") != want_vt:
            fail(
                f"{block_name}.verified_total={block.get('verified_total')} "
                f"!= {want_vt}",
                failures,
            )
        bucket_sum = sum(
            v for k, v in block.items() if isinstance(v, int) and k not in SUM_EXCLUDED
        )
        if bucket_sum != n:
            fail(f"{block_name} bucket sum={bucket_sum} != {n}", failures)

    if failures:
        print("METADATA CONSISTENCY CHECK FAILED:")
        for m in failures:
            print("  -", m)
        return 1
    print(f"OK: {n} exec rows, buckets recount-exact, metadata truthful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
