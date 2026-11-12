#!/usr/bin/env python3
"""DEF 14A enrichment batch 2026-11-12 (433rd review).

Closes the queued 432nd-run directive: enrich the 9 non-DEF-14A companies
from their latest DEF 14A. Primary-source findings (all verified live
this run via EDGAR data.sec.gov + www.sec.gov Archives):
  * TSLA: 2026-10-19 DEF 14A (acc. 0001104659-26-116700) bears the FY2025
    SCT; all 9 stored FY2025/2024/2023 rows match byte-identically,
    incl. Musk 2025 $158,359,009,867 and pay ratio 2,522,203:1 / median
    $62,786 (also restated verbatim in the proxy's pay-ratio disclosure).
    Company-level source STAYS 10-K/A per the 276th review's deliberate
    decision (REALIZED_COMP_NOTES cites the 10-K/A; the proxy SCT is
    identical, so re-sourcing adds no data).
  * EA: 2025-06-24 DEF 14A (acc. 0001308179-25-000556) bears FY2025 SCT;
    all 13 stored FY2025/2024/2023 rows match on values; Miele title is
    the fuller SCT-verbatim form (see TITLE_FIXES).
  * TECH: 2025-09-19 DEF 14A (acc. 0001308179-25-000599) bears FY2025 SCT;
    14/15 rows match on values (McManus 2023 is an all-dash filing row,
    no stored record, correctly skipped). Kelderman 2025 keeps its
    component_mismatch label: its +$1 gap is filing-side (the proxy's
    own components sum to total-1) and the 307th review adjudicated
    $1-gap rows as label-retained.
  * K: 2024-03-04 DEF 14A (acc. 0000055067-24-000010) bears FY2023 SCT;
    11/15 rows match; Lawlor 2022 is a column-shift misallocation
    (see VALUE_FIXES); Pilnick titles are the SCT-verbatim +Former form.
  * BX: no DEF 14A exists (efts full-text search: 0 hits; submissions
    window back to 2017: 0) - corroborates the company `notes` field.
  * KKR: 2026-02-27 DEF 14A is a special-meeting proxy (Apr 21, 2026),
    no comp tables - corroborates the company `notes` field.
  * SKYD / FDXF: still no DEF 14A (efts: 0 hits each; SKYD CIK
    0002041610 has never filed one; FDXF CIK 0002082247 none yet).
  * VMRK: still no post-merger DEF 14A (latest on CIK 906107 remains
    the pre-merger EQR 2026-04-14 proxy).
  * ERIE (DEF 14C filer, not in the note's 9): out of scope - its rows
    are already verified from its information statement.

Changes applied here (44 rows gain the def14a_verified_20261112 label):
  * 43 rows currently "verified" and confirmed exact vs the proxy SCT
    (TSLA 9, EA 13, TECH 13, K 8) -> def14a_verified_20261112.
  * K Lawlor 2022: values reallocated filing-verbatim (total unchanged)
    and label moved def14a_verified_20260910 -> def14a_verified_20261112
    (its old label certified the misallocated values).
  * EA Miele titles (2023/2024/2025) and K Pilnick titles (2021/2022/2023)
    set to SCT-verbatim wording. Title-only repairs do not move buckets
    (PNW Baum 2025 precedent), so Pilnick's rows keep
    def14a_verified_20260910; Miele's rows move verified -> 20261112
    with the verification itself.
  * No company-level source/filing_url changes. Row count, verified_total
    (7,274), component_mismatch (44) all unchanged.

Metadata: data_quality + data_quality_detailed are recomputed from the
row labels (never hand-typed); last_dq_repair + top-level last_updated
set to 2026-11-12. Guard LABEL_TO_KEY gains the new label in the same
commit (check_metadata_consistency.py, dated 433rd-review note).

Usage: python3 hidden_files/apply_def14a_enrichment_20261112.py
Writes a backup first; asserts pre/post invariants; exits non-zero
without writing if any assert fails.
"""
import collections
import json
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP = os.path.join(REPO, "data", "compensation.json")
BACKUP = os.path.join(
    REPO, "hidden_files",
    "compensation_backup_20261112_0240_pre_def14aenrich.json")
EXTRACTED = os.path.join(
    os.path.expanduser("~"), "workspace", "goals",
    "s-p-500-executive-compensation-tracker", "hidden_files",
    "def14a_20261112", "sct_extracted_20261112.json")

NEW_LABEL = "def14a_verified_20261112"
FIELDS = ["salary", "bonus", "stock_awards", "option_awards",
          "non_equity_incentive", "pension_nqdc", "all_other", "total"]

# (ticker, name, year) -> SCT-verbatim title (filing wording wins).
TITLE_FIXES = {
    ("EA", "Laura Miele", 2025): "President, EA Entertainment & Central Development",
    ("EA", "Laura Miele", 2024): "President, EA Entertainment & Central Development",
    ("EA", "Laura Miele", 2023): "President, EA Entertainment & Central Development",
    ("K", "Gary Pilnick", 2023): "Former Vice Chairman and Chief Legal Officer",
    ("K", "Gary Pilnick", 2022): "Former Vice Chairman and Chief Legal Officer",
    ("K", "Gary Pilnick", 2021): "Former Vice Chairman and Chief Legal Officer",
}

# (ticker, name, year) -> filing-verbatim component values (total unchanged).
VALUE_FIXES = {
    ("K", "David Lawlor", 2022): {
        "bonus": 0, "stock_awards": 1700642,
        "option_awards": 0, "non_equity_incentive": 688213,
    },
}

# Rows to relabel, keyed (ticker, name, year). Built from the verified
# compare: exact-match rows + title-fix rows + the Lawlor value fix.
# TECH Kelderman 2025 is deliberately absent (component_mismatch retained).
# K rows already on def14a_verified_20260910 with no content change are
# deliberately absent (no bucket churn on pure re-verification).
RELABEL = {
    ("TSLA", "Elon Musk", 2025), ("TSLA", "Elon Musk", 2024),
    ("TSLA", "Elon Musk", 2023), ("TSLA", "Vaibhav Taneja", 2025),
    ("TSLA", "Vaibhav Taneja", 2024), ("TSLA", "Vaibhav Taneja", 2023),
    ("TSLA", "Tom Zhu", 2025), ("TSLA", "Tom Zhu", 2024),
    ("TSLA", "Tom Zhu", 2023),
    ("EA", "Andrew Wilson", 2025), ("EA", "Andrew Wilson", 2024),
    ("EA", "Andrew Wilson", 2023), ("EA", "Stuart Canfield", 2025),
    ("EA", "Stuart Canfield", 2024), ("EA", "Laura Miele", 2025),
    ("EA", "Laura Miele", 2024), ("EA", "Laura Miele", 2023),
    ("EA", "Mala Singh", 2025), ("EA", "Mala Singh", 2024),
    ("EA", "Mala Singh", 2023), ("EA", "Jacob Schatz", 2025),
    ("EA", "Jacob Schatz", 2024),
    ("TECH", "Kim Kelderman", 2024), ("TECH", "Kim Kelderman", 2023),
    ("TECH", "James Hippel", 2025), ("TECH", "James Hippel", 2024),
    ("TECH", "James Hippel", 2023), ("TECH", "William Geist", 2025),
    ("TECH", "William Geist", 2024), ("TECH", "William Geist", 2023),
    ("TECH", "Matthew McManus", 2025), ("TECH", "Matthew McManus", 2024),
    ("TECH", "Shane Bohnen", 2025), ("TECH", "Shane Bohnen", 2024),
    ("TECH", "Shane Bohnen", 2023),
    ("K", "Steve Cahillane", 2023), ("K", "Steve Cahillane", 2021),
    ("K", "Amit Banati", 2023), ("K", "Amit Banati", 2021),
    ("K", "Chris Hood", 2023), ("K", "Chris Hood", 2021),
    ("K", "David Lawlor", 2023), ("K", "Shumit Kapoor", 2023),
    ("K", "David Lawlor", 2022),
}


def buckets(companies):
    c = collections.Counter()
    for comp in companies:
        for e in comp.get("executives", []):
            c[e.get("_total_source", "?")] += 1
    return dict(c)


def main():
    data = json.load(open(COMP, encoding="utf-8"))
    companies = data["companies"]
    meta = data["metadata"]

    # ---- pre-invariants (from the live file, not memory) ----
    n_rows = sum(len(c.get("executives", [])) for c in companies)
    assert n_rows == 7318, f"row count {n_rows} != 7318"
    assert meta["verified_total"] == 7274, "verified_total drifted"
    assert meta["data_quality"]["component_mismatch"] == 44, "mismatch drifted"
    pre_buckets = buckets(companies)
    assert pre_buckets.get("verified") == 5859, "verified bucket drifted"
    assert pre_buckets.get("def14a_verified_20260910") == 105, "20260910 drifted"

    # ---- cross-check the relabel set against the extraction ----
    ext = json.load(open(EXTRACTED, encoding="utf-8"))
    extracted_keys = set()
    for ticker, payload in ext.items():
        for r in payload.get("rows", []):
            # NOTE: all-zero rows are NOT skipped here - TSLA Musk 2023/2024
            # are genuine $0 rows (salary 0, no awards), not dash rows.
            # The TECH McManus 2023 all-dash row is simply absent from
            # RELABEL, so it needs no special-casing in this check.
            extracted_keys.add((ticker, r["name"], r["year"]))
    missing = RELABEL - extracted_keys
    assert not missing, f"relabel rows not in extraction: {missing}"

    by_key = {}
    for comp in companies:
        for e in comp.get("executives", []):
            by_key[(comp["ticker"], e["name"], e["year"])] = e

    changed = []
    # value fixes first (Lawlor 2022): total must not move.
    for key, vals in VALUE_FIXES.items():
        row = by_key.get(key)
        assert row is not None, f"missing row for value fix {key}"
        old_total = row["total"]
        for f, v in vals.items():
            row[f] = v
        assert row["total"] == old_total, f"{key} total moved!"
        comps = sum(row[f] for f in FIELDS if f != "total")
        assert comps == row["total"], (
            f"{key} does not foot after fix: comps {comps} vs total {row['total']}")
        changed.append(("value", key))
    # title fixes (SCT-verbatim wording).
    for key, title in TITLE_FIXES.items():
        row = by_key.get(key)
        assert row is not None, f"missing row for title fix {key}"
        assert row.get("title") != title, f"{key} title already {title!r}?"
        row["title"] = title
        changed.append(("title", key))
    # relabels.
    for key in sorted(RELABEL):
        row = by_key.get(key)
        assert row is not None, f"missing row for relabel {key}"
        old = row.get("_total_source")
        assert old in ("verified", "def14a_verified_20260910"), (
            f"{key} unexpected pre-label {old!r}")
        row["_total_source"] = NEW_LABEL
        changed.append(("relabel", key, old))

    # ---- post-invariants ----
    n_rows2 = sum(len(c.get("executives", [])) for c in companies)
    assert n_rows2 == 7318, "row count moved!"
    post = buckets(companies)
    assert post.get("verified") == 5859 - 43, post.get("verified")
    assert post.get("def14a_verified_20260910") == 104, post
    assert post.get(NEW_LABEL) == 44, post
    assert post.get("component_mismatch") == 44, post
    vt = sum(v for k, v in post.items()
             if k == "verified" or k.startswith("def14a_verified_"))
    assert vt == 7274, f"verified_total recomputed {vt} != 7274"

    # ---- metadata sync (recomputed, never hand-typed) ----
    for bucket_key in ("data_quality", "data_quality_detailed"):
        b = meta[bucket_key]
        for k in list(b.keys()):
            if k in ("verified_total", "last_audit"):
                continue
            b[k] = post.get(k, 0)
        # the new bucket did not exist before this batch; add it.
        b[NEW_LABEL] = post[NEW_LABEL]
        b["verified_total"] = vt
    assert meta["data_quality"]["verified_total"] == 7274
    assert meta["data_quality_detailed"]["verified_total"] == 7274
    meta["last_dq_repair"] = "2026-11-12"
    data["last_updated"] = "2026-11-12"

    # ---- write (backup first) ----
    shutil.copyfile(COMP, BACKUP)
    with open(COMP, "w", encoding="utf-8") as f:
        # ensure_ascii=False: the file carries raw UTF-8 (em-dashes etc.);
        # ensure_ascii=True would rewrite 871 lines as \uXXXX escapes.
        # Verified byte-identical round-trip with these settings before
        # running (2026-11-12).
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"backup: {BACKUP}")
    print(f"changed rows: {len(changed)} "
          f"({sum(1 for c in changed if c[0]=='value')} value, "
          f"{sum(1 for c in changed if c[0]=='title')} title, "
          f"{sum(1 for c in changed if c[0]=='relabel')} relabel)")
    print(f"buckets: verified {post['verified']}, "
          f"def14a_verified_20260910 {post['def14a_verified_20260910']}, "
          f"{NEW_LABEL} {post[NEW_LABEL]}, "
          f"component_mismatch {post['component_mismatch']}, "
          f"verified_total {vt}")
    print("OK: compensation.json updated")


if __name__ == "__main__":
    main()
