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

Section 4 additionally asserts that the hand-typed headline numbers in
README.md, index.html, and the js/app.js dataq static fallback match the
live JSON buckets. The pre-commit guard cannot re-verify data, but it CAN
kill the recurring stale-copy class (2026-09-11 18:11 batch left README at
99.1%/6,718 for ~80 min; 22:00 batch left the README audit trail missing)
by refusing commits whose static copy contradicts the JSON it commits.
History: 2026-09-12 (this run) added section 4.
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
    "DEF14A-verified 2026-09-09": "def14a_verified_20260909",
    "DEF14A-verified 2026-09-10": "def14a_verified_20260910",
    "recomputed": "recomputed",
    "rounding": "rounding",
    "incomplete_components": "incomplete_components",
    "bloated_component": "bloated_component",
    "recomputed_implausible_total": "recomputed_implausible_total",
    "def14a_verified_20260907": "def14a_verified_20260907",
    "def14a_verified_20260908": "def14a_verified_20260908",
    "def14a_verified_20260909": "def14a_verified_20260909",
    "def14a_verified_20260910": "def14a_verified_20260910",
    "component_mismatch": "component_mismatch",
}
# Canonicalize a record-level _total_source label to its metadata bucket key.
# DEF14A labels exist in two spellings (raw "DEF14A-verified 2026-09-09" and
# normalized "def14a_verified_20260909"); both must bucket to the same key so
# the guard stays green regardless of which spelling a writer emits.
def canon(label):
    return LABEL_TO_KEY.get(label, label)


# keys that must NOT appear in the bucket-sum (derived / non-bucket)
SUM_EXCLUDED = {"verified_total"}

# metadata keys counted as "verified" for the verified_total derived field
VERIFIED_KEYS = {"verified"} | {
    key for key in LABEL_TO_KEY.values() if key.startswith("def14a_verified_")
}


def fail(msg, failures):
    failures.append(msg)


# -- Section 4: static-copy truthfulness -------------------------------------
# Hand-typed headline numbers in README.md, index.html, and the js/app.js
# dataq static fallback must match the live JSON buckets. Each pattern is
# built from the JSON-derived values (not hardcoded), so the guard stays
# correct as buckets legitimately move; it only fires when static copy was
# hand-edited to a value the JSON no longer supports (the 2026-09-11 DQ
# batches each shipped exactly this drift within hours of writing the copy).
# Patterns are exact substrings chosen to be stable copy phrasing: the
# audit-trail sentences they live in may grow new batches, but the headline
# clause itself must keep these numbers or be deleted entirely (deletion
# also fails the guard — the copy is required, not optional).
def check_static_copy(n, vt, rounding, recomputed, mismatch, failures):
    pct = f"{vt / n * 100:.1f}%"
    fmt = lambda x: f"{x:,}"

    # file -> expected substrings, all derived from live JSON values
    checks = {
        "README.md": [
            f"{pct} verified component-total consistency ({fmt(vt)} of {fmt(n)} records",
            f"{fmt(vt)} ({pct})",
            f"Component-total consistency verified: {pct} verified "
            f"({fmt(vt)} of {fmt(n)} total NEO records), {rounding} rounding-gap rows, "
            f"{recomputed} recomputed",
            f"{mismatch} filing-side component mismatches",
        ],
        "index.html": [
            f"{fmt(n)} Named Executive Officer records",
        ],
        "js/app.js": [
            f"{fmt(vt)} of {fmt(n)} NEO rows verified ({pct}): "
            f"{rounding} rounding, {recomputed} recomputed, {mismatch} component_mismatch",
        ],
    }
    repo_root = os.path.join(HERE, "..")
    for fname, patterns in checks.items():
        path = os.path.join(repo_root, fname)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            fail(f"static-copy check: cannot read {fname}: {e}", failures)
            continue
        for pat in patterns:
            if pat not in text:
                fail(
                    f"static-copy drift in {fname}: expected headline "
                    f"{pat!r} (from live JSON: {n} rows, {vt} verified, "
                    f"{rounding}/{recomputed}/{mismatch} buckets) not found — "
                    f"sync the static copy to the JSON values before committing",
                    failures,
                )


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

    # 3. audit buckets vs record-level _total_source (count by canonical key so
    # raw and normalized spellings of the same label bucket together)
    src_counts = Counter()
    unlabeled = 0
    for c in companies:
        for e in c.get("executives", []):
            src = e.get("_total_source")
            if src is None:
                unlabeled += 1
            else:
                src_counts[canon(src)] += 1
    if unlabeled:
        fail(f"{unlabeled} exec rows missing _total_source", failures)
    unknown = [s for s in src_counts if s not in set(LABEL_TO_KEY.values())]
    if unknown:
        fail(f"unknown _total_source labels not in LABEL_TO_KEY: {unknown}", failures)

    for block_name in ("data_quality", "data_quality_detailed"):
        block = meta.get(block_name)
        if not isinstance(block, dict):
            fail(f"metadata.{block_name} missing or not a dict", failures)
            continue
        for key in set(LABEL_TO_KEY.values()):
            if key in block and block[key] != src_counts.get(key, 0):
                fail(
                    f"{block_name}.{key}={block[key]} != recount {src_counts.get(key, 0)}",
                    failures,
                )
        # verified_total convention: verified + all DEF14A buckets
        want_vt = sum(src_counts.get(key, 0) for key in VERIFIED_KEYS)
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

    # 4. static-copy truthfulness: README.md / index.html / js/app.js static
    #    fallbacks must carry the live headline numbers from data_quality
    dq = meta.get("data_quality", {})
    check_static_copy(
        n,
        dq.get("verified_total"),
        dq.get("rounding"),
        # recomputed key is dropped from data_quality when the bucket hits 0
        # (Sep 10 2026) — absence means 0, same convention as the dataq modal
        dq.get("recomputed", 0),
        dq.get("component_mismatch"),
        failures,
    )

    if failures:
        print("METADATA CONSISTENCY CHECK FAILED:")
        for m in failures:
            print("  -", m)
        return 1
    print(f"OK: {n} exec rows, buckets recount-exact, metadata truthful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
