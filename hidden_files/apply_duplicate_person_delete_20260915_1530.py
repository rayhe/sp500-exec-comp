#!/usr/bin/env python3
"""Name-ambiguity duplicate deletion batch - 2026-09-15 15:30 PT.

Deletes 5 stale same-person duplicate NEO rows proven via primary sources
(no EDGAR re-read needed; VM egress dead since 2026-09-12):

- OKE: 'Walter S. Hulse' 2023/2024/2025 (3 rows) are stale duplicates of
  'Walter S. Hulse, III'. ONEOK's own management page styles him
  "Walter S. Hulse III" (executive vice president, chief financial officer,
  treasurer, investor relations and corporate development); a 2019 SEC-filed
  ONEOK annual-report exhibit signs "/s/ Walter S. Hulse III". One person.
  The 2026-proxy (oke-20260331.htm, the company record's source) SCT rows
  are the 'III' rows with the full current title; the suffix-less rows are
  the phantom doubles (2025: both variants total identically $8,292,445 -
  one SCT has one row per NEO per year). Canonical 'III' rows kept.

- DRI: 'Raj Vennam' 2023/2024 (2 rows) are stale duplicates of
  'Rajesh Vennam'. Darden's own 2020 announcement names CFO
  "Rajesh (Raj) Vennam"; his SEC Form 4 prints "Vennam Rajesh"; the 10-K
  signature block reads "Rajesh Vennam". One person. The 2025-proxy
  (dri-20250804.htm, the company record's source) SCT rows are the
  'Rajesh Vennam' rows with the full title; the 2023 'Rajesh' row was
  independently re-verified verbatim against that exact filing on
  2026-09-11 (component_mismatch = genuine -$10 filer-side arithmetic).
  Canonical 'Rajesh' rows kept.

AJG adjudicated same run, no data change: 'Patrick Gallagher' 2025 COO is
a DISTINCT person - Patrick M. Gallagher, EVP and COO since 2024 per AJG's
own 2023 senior-leadership announcement and GlobalData bio; the CEO
'Pat Gallagher' is J. Patrick Gallagher, Jr. (Chairman/CEO since 1995).
STLD stays queued: one Barry T. Schneider proven (2025 DEF 14A bio via
sec.gov - President/COO since March 2023, previously SVP Flat Roll Steel
Group), but the stale 'Barry Schneider' SVP 2023/2024 rows' provenance
needs the EDGAR pass (a 2024 SVP title cannot come from the 2025 proxy).

Recomputes OKE/DRI FY2024 total_neo_compensation + neo_count, syncs all
headline copies (README / index.html / js/app.js static fallback /
metadata.description), and updates the name-ambiguity review queue.
Hard-asserts: only the 5 intended rows are removed, survivors intact,
aggregates recount-exact, 6759/6780 = 99.7%.
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
GOAL_HIDDEN = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files")
BACKUP = os.path.join(
    GOAL_HIDDEN, "compensation_backup_20260915_1530_pre_dupdel.json")

DELETE_TARGETS = [
    # (ticker, name, year, expected_total)
    ("OKE", "Walter S. Hulse", 2025, 8292445),
    ("OKE", "Walter S. Hulse", 2024, 5980593),
    ("OKE", "Walter S. Hulse", 2023, 4733303),
    ("DRI", "Raj Vennam", 2024, 3925173),
    ("DRI", "Raj Vennam", 2023, 3026160),
]
SURVIVORS = [
    ("OKE", "Walter S. Hulse, III", 2025, 8292445),
    ("OKE", "Walter S. Hulse, III", 2024, 6259278),
    ("OKE", "Walter S. Hulse, III", 2023, 4924117),
    ("DRI", "Rajesh Vennam", 2025, 4638289),
    ("DRI", "Rajesh Vennam", 2024, 3864631),
    ("DRI", "Rajesh Vennam", 2023, 3355329),
]

AUDIT_SENTENCE = (
    " 2026-09-15 15:30 PT name-ambiguity batch: OKE/DRI same-person "
    "duplicate rows deleted via primary-source identity proof - ONEOK's own "
    "management page styles the CFO 'Walter S. Hulse III' (2019 SEC-filed "
    "annual-report exhibit signed '/s/ Walter S. Hulse III'); Darden's 2020 "
    "announcement names CFO 'Rajesh (Raj) Vennam' (Form 4 'Vennam Rajesh', "
    "10-K signature 'Rajesh Vennam') - one person each; 3 stale 'Walter S. "
    "Hulse' rows (2023/2024/2025) and 2 stale 'Raj Vennam' rows (2023/2024) "
    "removed, canonical 2026-proxy 'III' / 2025-proxy 'Rajesh' rows kept "
    "(2025: both OKE variants totaled identically $8,292,445 - one SCT, one "
    "row per NEO per year); OKE FY2024 total_neo $33.7M->$27.7M, neo_count "
    "5->4; DRI FY2024 total_neo $23.6M->$19.7M, neo_count 4->3; AJG "
    "adjudicated distinct persons (Patrick M. Gallagher EVP/COO since 2024 "
    "per AJG announcement vs J. Patrick Gallagher Jr. Chairman/CEO) - no "
    "action; STLD stays queued (one Barry T. Schneider per 2025 DEF 14A "
    "bio, stale 'Barry Schneider' SVP rows need EDGAR pass); guard section "
    "14 added (deleted name forms must not reappear; AJG distinct pair "
    "allowlisted; new same-ticker same-year name-prefix pairs warn); "
    "headline buckets 99.7% (6,759/6,780).")


def main():
    os.makedirs(GOAL_HIDDEN, exist_ok=True)
    shutil.copy2(JSON_PATH, BACKUP)
    print("backup ->", BACKUP)

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    companies = {c["ticker"]: c for c in data["companies"]}

    before_keys = {(c["ticker"], e["name"], e["year"]): json.dumps(
        e, sort_keys=True)
        for c in data["companies"] for e in c.get("executives", [])}
    n_before = len(before_keys)
    assert n_before == 6785, f"expected 6785 rows, found {n_before}"

    # --- assert deletion targets exist exactly as expected ---
    for ticker, name, year, total in DELETE_TARGETS:
        rows = [e for e in companies[ticker]["executives"]
                if e["name"] == name and e["year"] == year]
        assert len(rows) == 1, f"expected 1 target row, found {len(rows)}: {ticker} {name} {year}"
        assert rows[0]["total"] == total, (
            f"total drift on {ticker} {name} {year}: {rows[0]['total']} != {total}")
        assert rows[0].get("_total_source") == "verified", (
            f"unexpected bucket on {ticker} {name} {year}: {rows[0].get('_total_source')}")

    # --- assert survivors exist exactly as expected ---
    for ticker, name, year, total in SURVIVORS:
        rows = [e for e in companies[ticker]["executives"]
                if e["name"] == name and e["year"] == year]
        assert len(rows) == 1, f"survivor missing: {ticker} {name} {year}"
        assert rows[0]["total"] == total, (
            f"survivor total drift: {ticker} {name} {year}")

    # --- delete ---
    for ticker, name, year, _ in DELETE_TARGETS:
        c = companies[ticker]
        c["executives"] = [e for e in c["executives"]
                           if not (e["name"] == name and e["year"] == year)]

    # --- recompute company aggregates (anchor fiscal year) ---
    for ticker in ("OKE", "DRI"):
        c = companies[ticker]
        fy = c["fiscal_year"]
        assert fy == 2024, f"{ticker} fiscal_year moved: {fy}"
        fy_rows = [e for e in c["executives"] if e["year"] == fy]
        c["total_neo_compensation"] = sum(e["total"] for e in fy_rows)
        c["neo_count"] = len(fy_rows)
        print(f"{ticker}: FY{fy} total_neo={c['total_neo_compensation']:,}"
              f" neo_count={c['neo_count']}")
    assert companies["OKE"]["total_neo_compensation"] == 27712439
    assert companies["OKE"]["neo_count"] == 4
    assert companies["DRI"]["total_neo_compensation"] == 19691383
    assert companies["DRI"]["neo_count"] == 3

    # --- metadata headline sync ---
    meta = data["metadata"]
    dq = meta["data_quality"]
    dqd = meta["data_quality_detailed"]
    assert meta["total_neo_records"] == 6785
    assert dq["verified"] == 6338 and dq["verified_total"] == 6764
    meta["total_neo_records"] = 6780
    meta["total_executives"] = 6780
    meta["title_coverage"] = "6780/6780"
    meta["description"] = meta["description"].replace(
        "6785 NEO records", "6780 NEO records")
    assert "6780 NEO records" in meta["description"]
    for block in (dq, dqd):
        block["verified"] = 6333
        block["verified_total"] = 6759

    # --- diff audit: only the 5 intended rows removed, nothing else touched ---
    after_keys = {(c["ticker"], e["name"], e["year"]): json.dumps(
        e, sort_keys=True)
        for c in data["companies"] for e in c.get("executives", [])}
    removed = set(before_keys) - set(after_keys)
    added = set(after_keys) - set(before_keys)
    changed = {k for k in before_keys if k in after_keys
               and before_keys[k] != after_keys[k]}
    assert removed == {(t, n, y) for t, n, y, _ in DELETE_TARGETS}, \
        f"unexpected removals: {removed}"
    assert not added, f"unexpected additions: {added}"
    assert not changed, f"unexpected modifications: {changed}"
    assert len(after_keys) == 6780
    # recount buckets
    from collections import Counter
    srcs = Counter(e.get("_total_source") for c in data["companies"]
                   for e in c.get("executives", []))
    assert srcs["verified"] == 6333, srcs
    print("diff audit clean: 5 rows removed, 0 added, 0 modified")

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("wrote", JSON_PATH)

    # --- static copy sync ---
    def sub(path, old, new, count=1):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert text.count(old) == count, \
            f"{path}: pattern {old!r} found {text.count(old)}x, expected {count}x"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new))

    readme = os.path.join(REPO, "README.md")
    # headline (appears once; audit-trail history sentences use slash form)
    sub(readme,
        "99.7% verified component-total consistency (6,764 of 6,785 records",
        "99.7% verified component-total consistency (6,759 of 6,780 records")
    # taxonomy table header date+count
    sub(readme, "(as of 2026-09-14: 6,785 rows):", "(as of 2026-09-15: 6,780 rows):")
    # taxonomy verified cell (verified_total)
    sub(readme, "| 6,764 (99.7%) |", "| 6,759 (99.7%) |")
    # methodology headline
    sub(readme,
        "Component-total consistency verified: 99.7% verified (6,764 of 6,785 total NEO records)",
        "Component-total consistency verified: 99.7% verified (6,759 of 6,780 total NEO records)")
    # audit-trail append: extend the line-11 paragraph (ends with the 14:00 batch sentence)
    with open(readme, encoding="utf-8") as f:
        text = f.read()
    tail_anchor = ("UHS FY2023 row count 3 vs 4 in FY2024/2025 - Edward H. Sim's "
                   "FY2023 row dropped by the parser, queued for the EDGAR pass; "
                   "headline buckets unchanged at 99.7% (6,764/6,785).")
    assert text.count(tail_anchor) == 1
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text.replace(tail_anchor, tail_anchor + AUDIT_SENTENCE))
    print("README synced + audit-trail appended")

    index = os.path.join(REPO, "index.html")
    sub(index, "6,785 Named Executive Officer records",
        "6,780 Named Executive Officer records")
    print("index.html synced")

    appjs = os.path.join(REPO, "js", "app.js")
    sub(appjs,
        "6,764 of 6,785 NEO rows verified (99.7%): 0 rounding, 0 recomputed, 21 component_mismatch",
        "6,759 of 6,780 NEO rows verified (99.7%): 0 rounding, 0 recomputed, 21 component_mismatch")
    print("js/app.js fallback synced")

    print("DONE: 6785 -> 6780 rows; verified_total 6764 -> 6759 (99.7%)")


if __name__ == "__main__":
    sys.exit(main())
