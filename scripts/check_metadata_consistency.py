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
History: 2026-09-12 11:30 PT run added the def14a_verified_20260912 label
(rounding-bucket collapse: 24 rows re-verified vs primary DEF 14A SCTs).
History: 2026-09-12 18:00 PT run added section 5 (company-aggregate recount)
after finding DQ row repairs (PNC Parsley, LULU Frank) left company-level
total_neo_compensation stale by +3.57M / -4.41M.
History: 2026-09-12 22:00 PT run added section 6 (CEO name/total pairing)
after finding MAA paired successor-CEO A. Bradley Hill's name with
predecessor H. E. Bolton Jr.'s FY2024 SCT total $8,445,660 (no such SCT row
exists); repaired to Hill's verified 2025 SCT total $5,453,480.
History: 2026-09-13 02:00 PT run added section 7 (NEO name/title hygiene)
after repairing 12 name rows + REGN ceo_name + 151 title rows carrying
parser artifacts (" Board co-Chair" footnote suffix, " East/West Region"
labels, title stray-comma class " and, "/"Vice, President"/"Senior, Vice").
History: 2026-09-13 06:00 PT run added section 6b (CEO title-awareness) after
re-pairing 4 CEO anchors whose section-6 name/total pairing was satisfied by
the wrong person's SCT row (NKE Friend/CFO, GE Stokes/segment "Former CEO",
HOLX Oberton/CFO, PSA Boyle/COO); extended section 7 with the trailing
footnote-digit name class (MLM x9), the residual "Executive Vice, " comma
class (22 rows), missing-space title joins (46 + 31 rows), the general
',[A-Z]' missing-space-after-comma rule (caught PNW 'Guldner,Former' and AIZ
'Luthi,Former'), and the split-name reassembly class (PNW 'Andrew D'/Cooper,
COF 'Matthew W'/Cooper).
History: 2026-09-13 15:30 PT run added section 4b (dataq-modal truthfulness)
after finding the Data Verification methodology modal's hand-typed $1-$2
taxonomy count (246, two recounts stale vs README's 273) and the Coverage
static fallback's audit date (2026-09-10 vs metadata 2026-09-12) had drifted
past the section-4 headline checks. The section-4b recount uses the
8-component set (pension_change included — 21 rows store pension there); a
History: 2026-09-14 03:30 PT run extended section 4 (taxonomy-header row
count) after finding the README Data Verification Taxonomy header said
"(as of the 2026-09-12 audit: 6,781 rows)" while the JSON had 6,785 rows
(+1 CBRE 2026-09-13 06:00, +1 LHX Rambeau 2023 restore 10:00, +2 ABNB Mertz
2026-09-13 18:00); the table's bucket cells were current, only the
header count was stale — a blind spot the headline-pattern checks did
not cover. The header now asserts the live count.
History: 2026-09-14 07:30 PT run added section 10 (peer-network <-> company
coverage) after the first-ever cross-check of data/peer-network.json against
the 500 companies: 0 dangling edges, degrees recount-exact, 0 self-loops, 0
duplicate edges — but AOS and CPRT have no network node (no extractable DEF
14A peer-group disclosure in the 2026-07-19 network build) and 8 nodes are
non-S&P companies cited as benchmarking peers (DDOG, MRVL, PINS, RBLX, SNAP,
SNOW, SPOT, XYZ; all out_degree 0). Index-membership drift also confirmed:
DDOG joined the S&P 500 in July 2025 yet is absent from the 500-company
list — a company-list refresh vs current index membership is queued (needs
EDGAR), not attempted here.
History: 2026-09-14 10:00 PT run added section 11 (CEO-anchor transition
tripwire + pay-ratio methodology screen) after a normalized CEO-anchor
screen found 493/500 anchors clean but 7 companies where ceo_name is the
current post-2024-transition CEO while fiscal_year=2024 rows cover the
prior CEO and total_compensation matches no 2024 row (TMUS, NKE, SWKS, CCI,
PSA, MAA — queued for DEF 14A re-read), plus a pay-ratio recompute screen
showing 156/499 deviations as a methodology class (transition-year CEO-pay
figures and pension-swing years, spot-verified CMG/MO), not a parse class.
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "data", "compensation.json")
PEER_JSON_PATH = os.path.join(HERE, "..", "data", "peer-network.json")

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
    "def14a_verified_20260912": "def14a_verified_20260912",
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
            # taxonomy table header carries the live row count, not a date-frozen
            # one (2026-09-14: header said 6,781 rows while JSON had 6,785;
            # the audit-trail sentences above legitimately keep old counts as
            # history, but the header must track the current row count).
            f"{fmt(n)} rows):",
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


# -- Section 4b: dataq-modal truthfulness ------------------------------------
# The Data Verification methodology modal (js/app.js) hand-types two values
# the section-4 headline checks do not cover: the taxonomy-decision count of
# verified-family rows whose components foot within $1-$2, and the "last
# audit" date in the Coverage static fallback / live-render default. Both
# drifted undetected (2026-09-13 15:30 run: modal said 246 rows, README said
# 273 — two recounts stale; static fallback said "last audit 2026-09-10"
# while metadata said 2026-09-12).
#
# The $1-$2 recount MUST use the 8-component set: pension values live in
# either pension_nqdc or pension_change (never both; 21 rows use
# pension_change). A 7-component recount silently returns 272 instead of 273
# — the exact trap the 15:30 run fell into before checking the key set.
COMP_FIELDS_8 = [
    "salary", "bonus", "stock_awards", "option_awards",
    "non_equity_incentive", "pension_nqdc", "pension_change", "all_other",
]


def _int_or_zero(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def recount_small_delta_rows(companies):
    n12 = 0
    for c in companies:
        for r in c.get("executives", []):
            src = r.get("_total_source", "")
            if src != "verified" and not src.startswith("def14a_verified"):
                continue
            s = sum(_int_or_zero(r.get(k)) for k in COMP_FIELDS_8)
            if abs(s - _int_or_zero(r.get("total"))) in (1, 2):
                n12 += 1
    return n12


def check_dataq_modal_truthfulness(companies, meta, failures):
    n12 = recount_small_delta_rows(companies)
    last_audit = meta.get("data_quality", {}).get("last_audit")
    if not last_audit:
        fail("dataq-modal truthfulness: metadata.data_quality.last_audit missing", failures)
        return
    checks = {
        # README taxonomy-decision line (en dash U+2013 between $1 and $2)
        "README.md": [f"{n12} `verified` rows carry $1\u2013$2 deltas"],
        "js/app.js": [
            # modal taxonomy copy (HTML-escaped en dash)
            f"{n12} <em>verified</em> rows carry $1&ndash;$2 deltas",
            # static fallback header shown before data loads
            f"Coverage (last audit {last_audit})",
            # live-render default used when dq.last_audit is absent
            f"|| '{last_audit}'",
        ],
    }
    repo_root = os.path.join(HERE, "..")
    for fname, patterns in checks.items():
        path = os.path.join(repo_root, fname)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            fail(f"dataq-modal truthfulness: cannot read {fname}: {e}", failures)
            continue
        for pat in patterns:
            if pat not in text:
                fail(
                    f"dataq-modal drift in {fname}: expected {pat!r} "
                    f"(from live JSON: {n12} $1-$2 verified rows, "
                    f"last_audit {last_audit}) not found — sync the modal "
                    f"copy to the JSON values before committing",
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

    # 4b. dataq-modal truthfulness: the methodology modal's hand-typed
    #     taxonomy-decision count and audit date must match the live JSON
    check_dataq_modal_truthfulness(companies, meta, failures)

    # 5. company-level aggregate recount: total_neo_compensation must equal
    #    the sum of exec totals for the company's primary fiscal_year, and
    #    neo_count must equal the number of exec records for that year.
    #    History: the 2026-09-12 10:00 DQ batch repaired exec rows
    #    (PNC Parsley 5,311,019 -> 8,881,019; LULU Frank 8,814,478 ->
    #    4,407,239) without refreshing these aggregates, leaving stale
    #    company totals on the live site until this section was added.
    for c in companies:
        fy = c.get("fiscal_year")
        if not fy:
            continue
        rows = [e for e in c.get("executives", []) if e.get("year") == fy]
        want_total = sum((e.get("total") or 0) for e in rows)
        stored_total = c.get("total_neo_compensation")
        if stored_total is not None and stored_total != want_total:
            fail(
                f"{c.get('ticker')}: total_neo_compensation={stored_total:,} != "
                f"sum of FY{fy} exec totals {want_total:,} — refresh the "
                f"company aggregate after any exec-row repair",
                failures,
            )
        stored_count = c.get("neo_count")
        if stored_count is not None and stored_count != len(rows):
            fail(
                f"{c.get('ticker')}: neo_count={stored_count} != "
                f"{len(rows)} exec records for FY{fy}",
                failures,
            )

    # 6. CEO name/total pairing: the displayed (ceo_name, total_compensation)
    #    pair must correspond to a real SCT row for the named person (any
    #    available year — CEO transitions legitimately pair the current CEO
    #    with their latest SCT total, e.g. TMUS/SWKS/CCI FY2025 rows).
    #    Last-name fuzzy match tolerates middle-initial variants
    #    ("David Gitlin" vs "David L. Gitlin", CARR).
    def _last(n):
        n = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", (n or "").lower()).strip()
        parts = re.findall(r"[a-z]+", n)
        return parts[-1] if parts else ""

    for c in companies:
        cname = c.get("ceo_name")
        stored = c.get("total_compensation")
        if not cname or stored is None:
            continue
        cl = _last(cname)
        paired = [
            e for e in c.get("executives", [])
            if e.get("total") == stored
            and cl
            and (cl in _last(e.get("name")) or _last(e.get("name")) in cl)
        ]
        if not paired:
            fail(
                f"{c.get('ticker')}: no SCT row pairs ceo_name={cname!r} "
                f"with total_compensation={stored:,} — the displayed CEO pay "
                f"must be a real SCT row for the named person",
                failures,
            )

    # 6b. CEO title-awareness: the paired SCT row's title must not indicate a
    #     non-CEO role. History: 2026-09-13 06:00 PT batch found four anchors
    #     paired with the wrong person's SCT total that section 6 could not catch:
    #     NKE Matthew Friend ("Executive Vice President and Chief Financial
    #     Officer"), GE Russell Stokes ("SVP, Former CEO Engines & Services" - a
    #     segment title), HOLX Karleen Oberton ("Chief Financial Officer"), PSA
    #     Thomas S. Boyle ("Chief Operating Officer"). A C-suite title that is not
    #     CEO, or a "Former CEO <segment>" title, fails the commit. A paired title
    #     with no CEO token at all (e.g. "President", "Chairman" - legitimate at
    #     some companies) is printed as a warning for human review but does not
    #     fail, since the top job is not always titled CEO.
    NON_CEO_CX = re.compile(
        r"chief (financial|operating|legal|accounting|investment|commercial|people|"
        r"technology|marketing|administrative|strategy|risk|information|"
        r"human resources) officer",
        re.I,
    )
    SEGMENT_FORMER_CEO = re.compile(r"\bformer ceo [a-z]", re.I)
    CEO_TOKEN = re.compile(r"chief executive officer|\bceo\b", re.I)
    for c in companies:
        cname = c.get("ceo_name")
        stored = c.get("total_compensation")
        if not cname or stored is None:
            continue
        cl = _last(cname)
        paired = [
            e for e in c.get("executives", [])
            if e.get("total") == stored
            and cl
            and (cl in _last(e.get("name")) or _last(e.get("name")) in cl)
        ]
        for e in paired:
            t = e.get("title") or ""
            if NON_CEO_CX.search(t):
                fail(
                    f"{c.get('ticker')}: CEO-paired row {e.get('name')!r} "
                    f"({e.get('year')}) has non-CEO C-suite title {t!r} — the "
                    f"headline CEO pay must belong to the company CEO (6b)",
                    failures,
                )
            elif SEGMENT_FORMER_CEO.search(t):
                fail(
                    f"{c.get('ticker')}: CEO-paired row {e.get('name')!r} "
                    f"({e.get('year')}) has segment-qualified title {t!r} — "
                    f"\"Former CEO <segment>\" is not the company CEO (6b)",
                    failures,
                )
            elif not CEO_TOKEN.search(t):
                print(
                    f"  warning: {c.get('ticker')}: CEO-paired row "
                    f"{e.get('name')!r} ({e.get('year')}) title {t!r} carries no "
                    f"CEO token — human review advised (6b)"
                )
    # 7. NEO name/title hygiene: the 2026-09-13 02:00 PT batch repaired three
    #    parser-artifact classes (REGN " Board co-Chair" footnote suffix in
    #    names + ceo_name, REG " East/West Region" labels in names, and the
    #    title stray-comma class " and, " / "Vice, President" / "Senior,
    #    Vice"). None of these strings can occur in a genuine SCT name or
    #    title, so any recurrence is a parser regression - fail the commit.
    #    History: 2026-09-13 02:00 PT run added section 7 after repairing
    #    12 name rows + 1 ceo_name + 151 title rows across the full file.
    #    History: 2026-09-13 06:00 PT run extended section 7 with the trailing
    #    footnote-digit name class (MLM "Petro 7"), the residual "Executive
    #    Vice, " stray-comma class (22 rows), and the missing-space title joins
    #    ("FinancialOfficer", "andPresident", ...) after repairing 9 + 22 + 46 rows.
    #    History: 2026-09-13 10:00 PT run extended section 7 with the org-label
    #    name class (LHX "Missile Solutions" / "Mission Systems" / "Spectrum
    #    Dominance" were division labels parsed as NEO names; repaired to the
    #    real NEOs) plus a warning-class tripwire for All Other Compensation
    #    subtables masquerading as SCT rows (APH 2025/2023: salary collapsed to
    #    benefits-scale dollars while the same person's adjacent-year SCT total
    #    is >10x larger). The tripwire is a warning, not a failure: genuine
    #    stubs (EG Andrade 2025 partial-year) and genuine $0-comp years (TSLA
    #    Musk 2022-2024) share the salary/total shape but are confirmed in
    #    their filings, so a hard fail would reject truth.
    NAME_SUFFIX_ARTIFACTS = (" Board co-Chair", " East Region", " West Region")
    ORG_LABEL_ARTIFACTS = ("Missile Solutions", "Mission Systems",
                           "Spectrum Dominance")
    TITLE_COMMA_ARTIFACTS = (" and, ", "Vice, President", "Senior, Vice",
                             "Executive Vice, ", "Chief, Executive")
    # comma directly followed by an uppercase letter with no space: no genuine
    # SCT name/title is typeset this way. Catches 'Guldner,Former' (PNW) and
    # the ',Alphabet'/ ',Google' / ',Chief' joins.
    MISSING_SPACE_AFTER_COMMA = re.compile(r",[A-Z]")
    NAME_FOOTNOTE_DIGITS = re.compile(r" \d+(, \d+)*$")
    TITLE_MISSING_SPACE = (
        "FinancialOfficer", "ExecutiveOfficer", "VicePresident", "andPresident",
        "Presidentand", "CommercialOfficer", "Presidentof", "andAdministrative",
        "Officerand", "andCEO", "andTechnology", "andGeneral", "andBest",
        "ChiefRevenue", "ChiefInvestment", "MedicalEssentials", "BioPharmaSystems",
        "InterventionalSegment", "PresidentInternational", "andSupply",
        "ChainSolutions", "asof July",
    )
    # percentage bleed: a pct figure followed by a name fragment can never be
    # a genuine SCT title (ORLY 'Chief Executive Officer 100 % Brent G').
    TITLE_PERCENT_BLEED = re.compile(r"\d+\s*%\s+[A-Za-z]")
    # committee-code bleed: 'EC (Chair)'-style codes come from the
    # board-committee table, never an SCT title cell (PPL 2023-2025).
    TITLE_COMMITTEE_BLEED = re.compile(r"\b[A-Z]{2,5}\s*\(Chair\)")
    # division labels parsed as NEO names that cannot be resolved offline;
    # warning-only (7d). The LHX class above stays a hard fail.
    ORG_LABEL_UNRESOLVED = ("Behavioral Health", "Flat Roll Steel")
    for c in companies:
        cn = c.get("ceo_name") or ""
        # distinct person-name set for the 7c embedded-name bleed check
        company_person_names = {
            e.get("name") for e in c.get("executives", []) if e.get("name")
        }
        for suf in NAME_SUFFIX_ARTIFACTS:
            if cn.endswith(suf):
                fail(
                    f"{c.get('ticker')}: ceo_name={cn!r} carries parser "
                    f"artifact suffix {suf!r} (section 7)",
                    failures,
                )
        if NAME_FOOTNOTE_DIGITS.search(cn):
            fail(
                f"{c.get('ticker')}: ceo_name={cn!r} carries trailing SCT "
                f"footnote digit(s) (section 7)",
                failures,
            )
        if MISSING_SPACE_AFTER_COMMA.search(cn):
            fail(
                f"{c.get('ticker')}: ceo_name={cn!r} carries missing-space-"
                f"after-comma artifact (section 7)",
                failures,
            )
        if cn in ORG_LABEL_ARTIFACTS:
            fail(
                f"{c.get('ticker')}: ceo_name={cn!r} is a division/org label, "
                f"not a person (section 7)",
                failures,
            )
        for e in c.get("executives", []):
            nm = e.get("name") or ""
            for suf in NAME_SUFFIX_ARTIFACTS:
                if nm.endswith(suf):
                    fail(
                        f"{c.get('ticker')} {e.get('year')}: exec name={nm!r} "
                        f"carries parser artifact suffix {suf!r} (section 7)",
                        failures,
                    )
            if nm in ORG_LABEL_ARTIFACTS:
                fail(
                    f"{c.get('ticker')} {e.get('year')}: exec name={nm!r} is a "
                    f"division/org label, not a person (section 7)",
                    failures,
                )
            if NAME_FOOTNOTE_DIGITS.search(nm):
                fail(
                    f"{c.get('ticker')} {e.get('year')}: exec name={nm!r} "
                    f"carries trailing SCT footnote digit(s) (section 7)",
                    failures,
                )
            ti = e.get("title") or ""
            for pat in TITLE_COMMA_ARTIFACTS:
                if pat in ti:
                    fail(
                        f"{c.get('ticker')} {e.get('year')} "
                        f"{nm!r}: title={ti!r} carries stray-comma artifact "
                        f"{pat!r} (section 7)",
                        failures,
                    )
            for pat in TITLE_MISSING_SPACE:
                if pat in ti:
                    fail(
                        f"{c.get('ticker')} {e.get('year')} "
                        f"{nm!r}: title={ti!r} carries missing-space artifact "
                        f"{pat!r} (section 7)",
                        failures,
                    )
            if MISSING_SPACE_AFTER_COMMA.search(nm) or MISSING_SPACE_AFTER_COMMA.search(ti):
                fail(
                    f"{c.get('ticker')} {e.get('year')} "
                    f"{nm!r}: name/title carries missing-space-after-comma "
                    f"artifact: title={ti!r} (section 7)",
                    failures,
                )
            # unbalanced parens in a NAME can never be genuine SCT text -
            # the 2026-09-13 22:00 PT batch repaired the INVH dangling-paren
            # split class (16 rows: name="Dallas B. Tanner (",
            # "Charles D. Young (Former"). Fail the commit on recurrence.
            if nm.count("(") != nm.count(")"):
                fail(
                    f"{c.get('ticker')} {e.get('year')}: exec name={nm!r} "
                    f"has unbalanced parentheses - dangling-paren split "
                    f"artifact (section 7)",
                    failures,
                )
            # unbalanced parens in a TITLE are warning-only: TAP 2025
            # "CEO of our Company (currently" is a genuine truncation whose
            # full wording needs the filing to repair, so a hard fail would
            # block the commit on an unrepaired-but-known row.
            if ti.count("(") != ti.count(")"):
                print(
                    f"  warning: {c.get('ticker')} {e.get('year')} "
                    f"{nm!r}: title={ti!r} has unbalanced parentheses - "
                    f"truncation artifact, verify wording vs DEF 14A (7)"
                )
            # 7c. title-bleed artifacts (fail): the 2026-09-14 02:00 PT batch
            #     repaired three title-cell bleed classes. None can occur in a
            #     genuine SCT title cell, so any recurrence is a parser
            #     regression - fail the commit.
            #     (a) honorific suffix ': Mr' (UHS 10 rows, footnote artifact);
            #     (b) percentage + name-fragment bleed, e.g. 'Chief Executive
            #         Officer 100 % Brent G' (ORLY);
            #     (c) another NEO's name embedded in the title, e.g. BG 2025
            #         'Chief Executive Officer, and John Neppl, Chief
            #         Financial Officer' (GPC 2025 same class).
            if ti.endswith((": Mr", ": Ms", ": Mrs", ": Dr")):
                fail(
                    f"{c.get('ticker')} {e.get('year')} "
                    f"{nm!r}: title={ti!r} carries honorific-suffix bleed "
                    f"artifact (section 7c)",
                    failures,
                )
            if TITLE_PERCENT_BLEED.search(ti):
                fail(
                    f"{c.get('ticker')} {e.get('year')} "
                    f"{nm!r}: title={ti!r} carries percentage/name-fragment "
                    f"bleed artifact (section 7c)",
                    failures,
                )
            # committee-membership bleed: board-committee codes like
            # 'EC (Chair), PCC, SC (Chair)' (PPL Sorgi 2023-2025, repaired
            # 2026-09-14 02:00) come from the committee table, never an SCT
            # title cell.
            if TITLE_COMMITTEE_BLEED.search(ti):
                fail(
                    f"{c.get('ticker')} {e.get('year')} "
                    f"{nm!r}: title={ti!r} carries board-committee "
                    f"membership bleed artifact (section 7c)",
                    failures,
                )
            for other in company_person_names:
                if (not other or other == nm
                        or other in ORG_LABEL_ARTIFACTS
                        or other in ORG_LABEL_UNRESOLVED):
                    continue
                if re.search(r"(?<![A-Za-z.])" + re.escape(other)
                             + r"(?![A-Za-z.])", ti, re.I):
                    fail(
                        f"{c.get('ticker')} {e.get('year')} "
                        f"{nm!r}: title={ti!r} embeds another NEO's name "
                        f"{other!r} - title-bleed artifact (section 7c)",
                        failures,
                    )
                    break
        # 7d. unresolved org-label names (warning only): division labels
        #     parsed as NEO names whose real person cannot be recovered
        #     offline. UHS 2023 'Behavioral Health' and STLD 2023 'Flat Roll
        #     Steel' are queued for the next EDGAR run; the LHX class
        #     (repaired 2026-09-13 10:00) stays a hard fail in ORG_LABEL_ARTIFACTS.
        for e in c.get("executives", []):
            if (e.get("name") or "") in ORG_LABEL_UNRESOLVED:
                print(
                    f"  warning: {c.get('ticker')} {e.get('year')}: exec "
                    f"name={e.get('name')!r} is a division label, not a "
                    f"person - real NEO name needs DEF 14A re-read (7d)"
                )
        if cn.count("(") != cn.count(")"):
            fail(
                f"{c.get('ticker')}: ceo_name={cn!r} has unbalanced "
                f"parentheses (section 7)",
                failures,
            )

    # 7b. All-Other-Compensation-subtable tripwire (warning only): an SCT row
    #     whose salary and total are both stub-scale while the same person has
    #     another year at the same company with a >10x larger SCT total is the
    #     signature of the 2026-09-13 APH corruption (footnote subtable parsed
    #     as SCT rows). Genuine partial-year stubs (EG Andrade 2025) have no
    #     adjacent full year to trip the >10x clause, and genuine $0-comp
    #     years (TSLA Musk 2022-2024) are the expected residual hits — both
    #     confirmed in their filings, so this stays a warning, not a failure.
    person_totals = {}
    for c in companies:
        for e in c.get("executives", []):
            person_totals.setdefault((c.get("ticker"), e.get("name")), []).append(
                e.get("total") or 0
            )
    for c in companies:
        for e in c.get("executives", []):
            sal = e.get("salary") or 0
            tot = e.get("total") or 0
            if sal < 25000 and tot < 250000:
                others = [
                    t for t in person_totals[(c.get("ticker"), e.get("name"))]
                    if t > 10 * tot and t > 0
                ]
                if others:
                    print(
                        f"  warning: {c.get('ticker')} {e.get('year')} "
                        f"{e.get('name')!r}: stub-scale salary ${sal:,} / "
                        f"total ${tot:,} with a >10x larger SCT total "
                        f"(${max(others):,}) in another year — possible All "
                        f"Other Compensation subtable parsed as SCT row (7b)"
                    )

    # 8. Salary-drop column-shift tripwire (warning only): the 2026-09-13
    #    18:00 PT ABNB repair exposed a systematic parse error — the salary
    #    cell of an older-year SCT row is dropped, every component shifts one
    #    column left (bonus<-stock, stock<-options, options<-non-equity,
    #    non-equity<-all-other), the filing's printed total lands in
    #    all_other, and the stored total is recomputed at ~2x the filing
    #    total. Signature: salary == 0, bonus > 0, all_other > 0, and the
    #    doubling gap |total - 2*all_other| is salary-plausible (<10% of
    #    total). A 2026-09-13 scan found 161 rows / 41 tickers / ~$1.237B
    #    phantom compensation sharing the exact signature (CMI Rumsey 2024:
    #    stored $42.2M vs inferred filing total $21.9M = stored all_other;
    #    inferred salaries plausible for all 161, zero always-zero-salary
    #    persons). Warning-only, not a failure: each hit needs its DEF 14A
    #    SCT re-read before repair — the inferred values are arithmetic, not
    #    filing-verbatim. Full row list + inferred values + per-ticker
    #    inflation in the goal hidden_files review queue
    #    (column_shift_review_queue_20260913_1800.md). Company-level
    #    total_neo_compensation for affected tickers is inflated wherever
    #    the corrupted year is the anchor fiscal year; section 5 cannot see
    #    it because the aggregate faithfully sums the corrupted rows.
    for c in companies:
        for e in c.get("executives", []):
            sal = e.get("salary") or 0
            bonus = e.get("bonus") or 0
            ao = e.get("all_other") or 0
            tot = e.get("total") or 0
            if (
                sal == 0
                and bonus > 0
                and ao > 0
                and tot > 0
                and abs(tot - 2 * ao) <= 0.10 * tot
            ):
                print(
                    f"  warning: {c.get('ticker')} {e.get('year')} "
                    f"{e.get('name')!r}: salary $0 with bonus "
                    f"${bonus:,} and total ${tot:,} ~= 2x all_other "
                    f"${ao:,} — salary-drop column-shift signature (8); "
                    f"verify vs DEF 14A SCT before repair"
                )

    # 9. Pension-drop tripwire (warning only): the 2026-09-13 22:00 PT
    #    batch found a second systematic parse-error class - the "Change in
    #    Pension Value and NQDC Earnings" column is dropped (0/None) while
    #    the stored total is the filing's printed total, so the total
    #    exceeds the captured components by exactly the pension value.
    #    Signature on full 7-component rows: gap = total - sum(components) >
    #    $1,000 with pension_nqdc in (0, None). 20 rows / 4 tickers /
    #    $45.9M missing pension (SO 13, TFC 3, PPL 1, AME 3); the SO rows
    #    carry def14a_verified_20260909 totals so the gap is definitively
    #    the pension column. Warning-only: the gap is arithmetic, the
    #    filing SCT must confirm the pension cell before repair. Row list
    #    + filing URLs in the goal hidden_files review queue
    #    (pension_drop_review_queue_20260913_2200.md). TFC/PPL rows also
    #    have bonus=None, so the verifier must confirm pension-vs-bonus.
    #    9b covers the residual footing anomalies on full rows (both
    #    directions, >$1,000, excluding adjudicated component_mismatch
    #    rows): none unadjudicated as of 2026-09-13 22:00 PT.
    _COMP_KEYS = ("salary", "bonus", "stock_awards", "option_awards",
                  "non_equity_incentive", "pension_nqdc", "all_other")
    for c in companies:
        for e in c.get("executives", []):
            if not all(k in e for k in _COMP_KEYS):
                continue
            if e.get("_total_source") == "component_mismatch":
                continue
            foot = sum(e.get(k) or 0 for k in _COMP_KEYS)
            gap = (e.get("total") or 0) - foot
            pen = e.get("pension_nqdc")
            if gap > 1000 and pen in (0, None):
                print(
                    f"  warning: {c.get('ticker')} {e.get('year')} "
                    f"{e.get('name')!r}: total ${e.get('total'):,} exceeds "
                    f"components by ${gap:,} with pension "
                    f"{pen} - dropped pension-column signature (9); verify "
                    f"vs DEF 14A SCT before repair"
                )
            elif abs(gap) > 1000:
                print(
                    f"  warning: {c.get('ticker')} {e.get('year')} "
                    f"{e.get('name')!r}: total ${e.get('total'):,} does not "
                    f"foot to components (gap ${gap:,}) - anomaly for "
                    f"filing review (9b)"
                )

    # 10. Peer-network <-> company-list coverage (2026-09-14 07:30 PT run):
    #     first-ever cross-check of data/peer-network.json against the 500
    #     companies. Hard invariants (fail): metadata node_count/edge_count
    #     == actual counts; every edge source/target resolves to a node
    #     ticker; per-node in_degree/out_degree recount-exact. Warning-only
    #     hygiene: no self-loops, no duplicate (source,target,year,
    #     group_type) edges. Coverage: every company should have a network
    #     node. KNOWN_COVERAGE_GAPS are warning-tracked (no extractable DEF
    #     14A peer-group disclosure in the 2026-07-19 network build; both
    #     still render their company pages, the network search just finds
    #     no node — no crash). Any NEW missing company fails (regression).
    #     Nodes not matching any company must be in PEER_ONLY_NODES
    #     (non-S&P companies cited as benchmarking peers, all out_degree
    #     0); unknown non-company nodes fail. Index-membership drift
    #     (DDOG in S&P 500 since Jul 2025, absent from the 500-company
    #     list) is a queued company-list refresh, not a section-10
    #     failure — do not "fix" it by hand-editing either list.
    KNOWN_COVERAGE_GAPS = {"AOS", "CPRT"}
    PEER_ONLY_NODES = {"DDOG", "MRVL", "PINS", "RBLX", "SNAP", "SNOW",
                       "SPOT", "XYZ"}
    with open(PEER_JSON_PATH, encoding="utf-8") as f:
        peer = json.load(f)
    pnodes = peer.get("nodes", [])
    pedges = peer.get("edges", [])
    pmeta = peer.get("metadata", {})
    if pmeta.get("node_count") != len(pnodes):
        fail(f"peer node_count={pmeta.get('node_count')} != {len(pnodes)}",
             failures)
    if pmeta.get("edge_count") != len(pedges):
        fail(f"peer edge_count={pmeta.get('edge_count')} != {len(pedges)}",
             failures)
    ptickers = set(n.get("ticker") for n in pnodes)
    if len(ptickers) != len(pnodes):
        fail("peer nodes contain duplicate tickers", failures)
    dangling = [e for e in pedges
                if e.get("source") not in ptickers
                or e.get("target") not in ptickers]
    if dangling:
        fail(f"{len(dangling)} peer edges reference missing nodes "
             f"(e.g. {dangling[0].get('source')}->{dangling[0].get('target')})",
             failures)
    indeg = Counter(e.get("target") for e in pedges)
    outdeg = Counter(e.get("source") for e in pedges)
    for pnode in pnodes:
        t = pnode.get("ticker")
        if pnode.get("in_degree") != indeg.get(t, 0):
            fail(f"peer node {t} in_degree={n.get('in_degree')} != recount "
                 f"{indeg.get(t, 0)}", failures)
        if pnode.get("out_degree") != outdeg.get(t, 0):
            fail(f"peer node {t} out_degree={n.get('out_degree')} != recount "
                 f"{outdeg.get(t, 0)}", failures)
    selfloops = [e for e in pedges if e.get("source") == e.get("target")]
    if selfloops:
        print(f"  warning: {len(selfloops)} peer self-loop edges "
              f"(e.g. {selfloops[0].get('source')}) - (10)")
    seen_edges = set()
    dup_edges = 0
    for e in pedges:
        k = (e.get("source"), e.get("target"), e.get("year"),
             e.get("group_type"))
        if k in seen_edges:
            dup_edges += 1
        seen_edges.add(k)
    if dup_edges:
        print(f"  warning: {dup_edges} duplicate peer edges "
              f"(same source/target/year/group_type) - (10)")
    ctickers = set(c.get("ticker") for c in companies)
    missing_nodes = sorted(ctickers - ptickers)
    for t in missing_nodes:
        if t in KNOWN_COVERAGE_GAPS:
            print(f"  warning: {t} is an S&P 500 company with no peer-network "
                  f"node (known coverage gap, 10); network search finds no "
                  f"node — do not fabricate edges without a DEF 14A peer "
                  f"group re-read")
        else:
            fail(f"company {t} has no peer-network node (new coverage gap, "
                 f"10)", failures)
    unknown_extra = sorted(ptickers - ctickers - PEER_ONLY_NODES)
    if unknown_extra:
        fail(f"peer nodes not matching any company and not in PEER_ONLY "
             f"allowlist: {unknown_extra} (10)", failures)

    # 11. CEO-anchor transition tripwire + pay-ratio methodology screen
    #     (2026-09-14 10:00 PT run, warning-only). company.ceo_name is
    #     AFL-CIO's CURRENT-CEO name while fiscal_year/total_compensation
    #     come from the anchor-year DEF 14A: at CEO transitions the anchor
    #     fields describe two different people. Match rule: strip
    #     punctuation, drop middle initials and suffixes (jr/sr/ii/iii/
    #     iv/v), then require same last name AND (same first name OR same
    #     first initial) — this absorbs the AMZN 'Andy Jassy' vs 'Andrew R.
    #     Jassy' nickname variant (totals byte-identical, no action).
    #     A company trips when NO anchor-year exec row matches ceo_name by
    #     that rule AND no anchor-year row's total equals
    #     company.total_compensation. KNOWN_ANCHOR_TRANSITIONS are the six
    #     adjudicated 2026-09-14 cases (TMUS, NKE, SWKS, CCI, PSA, MAA) with
    #     per-company questions in the goal hidden_files review queue
    #     (ceo_anchor_transition_queue_20260914_1000.md); any NEW trip is a
    #     regression signal for the next EDGAR-connected run. The
    #     pay-ratio half of section 11 is a summary-only screen: recompute
    #     total_compensation/median_worker_pay vs company.pay_ratio (3%
    #     tolerance). Deviations are a METHODOLOGY class, not a parse
    #     class — disclosed ratios use the pay-ratio table's CEO-pay figure
    #     (transition-year year-end CEO, annualized comp, pension-swing
    #     years), spot-verified CMG (disclosed ratio uses Boatwright's
    #     ~$19.1M, not Niccol's $37.5M SCT total) and MO (2026 DEF 14A:
    #     annualized $24.58M -> 147:1; stored ct $53.6M is the 2024 SCT
    #     total). 33 companies cluster at implied/reported ~1.9-2.0x, 10
    #     at ~0.4-0.6x. Do NOT "repair" by overwriting disclosed ratios;
    #     the UI renders pay_ratio as-disclosed (never recomputes), which
    #     is the correct behavior. Emits one summary warning, not one per
    #     company, so the actionable tripwires stay readable.
    def _anchor_key(name):
        parts = [p for p in re.sub(r"[^a-z ]", " ", (name or "").lower())
                 .split()
                 if p not in ("jr", "sr", "ii", "iii", "iv", "v")
                 and len(p) > 1]
        if not parts:
            return ("", "")
        return (parts[0], parts[-1])

    def _anchor_match(row_name, ceo_name):
        rf, rl = _anchor_key(row_name)
        cf, cl = _anchor_key(ceo_name)
        return bool(rl and rl == cl and rf and (rf == cf or rf[0] == cf[0]))

    KNOWN_ANCHOR_TRANSITIONS = {"TMUS", "NKE", "SWKS", "CCI", "PSA", "MAA"}
    anchor_trips = []
    for c in companies:
        ceo = c.get("ceo_name")
        fy = c.get("fiscal_year")
        ct = c.get("total_compensation")
        if not ceo or fy is None or ct is None:
            continue
        rows = [e for e in c.get("executives", [])
                if e.get("year") == fy]
        name_hit = any(_anchor_match(e.get("name"), ceo) for e in rows)
        total_hit = any(e.get("total") == ct for e in rows)
        if not name_hit and not total_hit:
            anchor_trips.append(c.get("ticker"))
    for t in sorted(anchor_trips):
        known = "known" if t in KNOWN_ANCHOR_TRANSITIONS else "NEW"
        print(f"  warning: {t} CEO-anchor transition ({known}, 11): "
              f"ceo_name has no anchor-year SCT row and "
              f"total_compensation matches no anchor-year row — see "
              f"ceo_anchor_transition_queue_20260914_1000.md; do not "
              f"repair offline")
    new_trips = sorted(set(anchor_trips) - KNOWN_ANCHOR_TRANSITIONS)
    if new_trips:
        fail(f"new CEO-anchor transitions not in the 2026-09-14 allowlist: "
             f"{new_trips} (11)", failures)

    pr_within = pr_2x = pr_half = pr_other = 0
    for c in companies:
        pr = c.get("pay_ratio")
        mw = c.get("median_worker_pay")
        ct = c.get("total_compensation")
        if pr in (None, 0) or mw in (None, 0) or ct is None:
            continue
        implied = ct / mw
        r = implied / pr
        if abs(r - 1) <= max(2 / pr, 0.03):
            pr_within += 1
        elif 1.9 <= r <= 2.1:
            pr_2x += 1
        elif 0.4 <= r <= 0.6:
            pr_half += 1
        else:
            pr_other += 1
    if pr_2x + pr_half + pr_other:
        print(f"  warning: pay-ratio methodology screen (11): "
              f"{pr_within}/{pr_within + pr_2x + pr_half + pr_other} screened foot within tolerance; {pr_2x} cluster "
              f"~2x, {pr_half} ~0.5x, {pr_other} other — methodology "
              f"class (transition-year CEO-pay figures, pension-swing "
              f"years; spot-verified CMG/MO), not a parse class; UI "
              f"renders disclosed ratios as-is (correct); do not overwrite")

    if failures:
        print("METADATA CONSISTENCY CHECK FAILED:")
        for m in failures:
            print("  -", m)
        return 1
    print(f"OK: {n} exec rows, buckets recount-exact, metadata truthful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
