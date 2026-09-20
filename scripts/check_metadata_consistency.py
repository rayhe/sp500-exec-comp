#!/usr/bin/env python3
"""Metadata truthfulness guard for data/compensation.json.

Asserts that every metadata count field equals an independent recount of
the stored records, so stale-count drift can never be committed again.
History: 2026-09-07 (7c6a07b) synced 6700->6750, 2026-09-09 (a3be999)
synced 6759->6764, 2026-09-09 07:30 run synced buckets after 3f1a80c's
pension-repair run left data_quality at the old bucket values.

History: 2026-09-20 06:00 PT run added the last_dq_repair convention (section 3):
every DQ batch script sets BOTH top-level last_updated and
metadata.last_dq_repair to the run date; the footer's "Last repair" prefers
metadata.last_dq_repair, so it can never lag a DQ batch by a day again.
The guard asserts last_dq_repair is a valid ymd date and not later than
top-level last_updated.

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
History: 2026-09-14 14:00 PT run added section 12 (cross-company exec-name
collision tripwire) after a normalized (name, year) screen found 13
collisions across companies: 6 legit mid-year transitions, 2 same-name
coincidences, 1 suspicious (LULU/WSM Burgoyne, queued for DEF 14A
re-read). History: 2026-09-14 18:00 PT run added section 13
(title footnote-bleed/truncation tripwire) after a title-artifact screen
found bullet-bleed and mid-phrase-truncation classes section 7 missed:
repaired COR/ROST/SHW trailing markers mechanically (8 rows, base titles
verified via browser path), queued DOC/ALLE/APA/DPZ/VST (+UHS, STLD
already queued) for EDGAR re-reads.
History: 2026-09-15 07:30 PT run added section 4d (dataq-modal live-block
fallback truthfulness) after finding the pay-ratio, executive-transitions,
and title-artifacts static fallbacks were the last hand-typed headline
copies with no guard coverage: all three recount-exact today (pay ratio
343/499/33/10/113, 13 collision tuples, 27 rows at 8 companies), and any
future EDGAR batch that moves one of those numbers will now trip the
pre-commit hook until the fallback is re-synced. KNOWN_TITLE_ARTIFACTS
hoisted to module level for the 4d titles recount.
History: 2026-09-15 10:00 PT run repaired the DOC/APA bullet-bleed titles
(13 rows; base titles verified via the browser path) and removed their 5
tuples from KNOWN_TITLE_ARTIFACTS; the 4d titles fallback now recounts 14
rows at 6 companies (ALLE, DPZ, VST, TAP, UHS, STLD) and the js/app.js
fallback copy was re-synced to match.
History: 2026-09-15 12:00 PT run repaired the ALLE/DPZ/VST/STLD title
truncations (12 rows; exact SCT principal-position wording verified
verbatim in the 2026 proxy/DEF 14A filings via the browser path, all 36
stored totals matched) and removed their 4 tuples from
KNOWN_TITLE_ARTIFACTS; the 4d titles fallback now recounts 2 rows at 2
companies (TAP, UHS) and the js/app.js fallback copy was re-synced to
match. TAP stays queued (parenthetical tail not exposed verbatim in any
indexed primary source); UHS stays queued in the name-ambiguity queue
(org-label name row).
History: 2026-09-15 14:00 PT run repaired the last 2 org-label name rows via
the browser path - UHS 2023 'Behavioral Health' -> Matthew J. Peterson (SCT
name+title cell split; person verified via SEC Form 4 officer signature,
Becker's 2023-05-19, and the stored 2024/2025 rows) and STLD 2023 'Flat Roll
Steel' -> Christopher A. Graham (2026 STLD proxy CD&A NEO list names him
'Senior Vice President, Flat Roll Steel Group'; steeldynamics.com bio and
the stored 2025 row confirm); titles rejoined from the split fragments, all
numbers asserted unchanged. TAP Goyal 2025 'CEO of our Company (currently'
gained an in-record note documenting the truncation and the verified role
history (CSO 2019-Sep 30, 2025; President/CEO since Oct 1, 2025) - still
queued, no guessing. ORG_LABEL_UNRESOLVED emptied (tripwire kept), UHS tuple
removed from KNOWN_TITLE_ARTIFACTS (now 1 row at 1 company), section-4d
expected phrase made singular/plural-aware, js/app.js fallback re-synced
(33->34 repaired), side finding logged: UHS FY2023 has 3 rows vs 4 in
FY2024/2025 - Edward H. Sim's FY2023 row was dropped by the parser, queued
for the EDGAR re-read.
History: 2026-09-15 15:30 PT run added section 14 (name-ambiguity
resolution regression) after deleting 5 stale same-person duplicate rows
proven via primary sources: OKE 'Walter S. Hulse' 2023/2024/2025 (ONEOK's
own site: Walter S. Hulse III) and DRI 'Raj Vennam' 2023/2024 (Darden 2020
announcement "Rajesh (Raj) Vennam", Form 4 "Vennam Rajesh"); canonical
'III'/'Rajesh' rows kept, OKE/DRI FY2024 aggregates re-anchored
(total_neo $33.7M->$27.7M / $23.6M->$19.7M, neo_count 5->4 / 4->3). The
deleted name forms fail if reintroduced; AJG's adjudicated-distinct pair
(Patrick M. Gallagher EVP/COO since 2024 vs J. Patrick Gallagher Jr.
Chairman/CEO) fails if merged; new same-ticker same-year name-prefix pairs
warn for triage (STLD Barry/Barry T. known, queued for EDGAR pass).
History: 2026-09-15 18:00 PT run repaired 8 title-split/name-fragment rows
offline (MET Bill Pappas 2023-2025 heading-bleed '...GTO 2025 Total
Compensation:' -> 'EVP and Head of GTO'; LEN Sustana 2024 dangling comma ->
'Former Vice President'; MTD 'Richard Wong Head of Asia and Pacific'
2023-2025 -> name 'Richard Wong'; GNRC 'Raj Kanuru VP' 2025 -> name 'Raj
Kanuru'; all numeric fields asserted byte-identical) and queued 20 rows at
8 companies for the EDGAR title-column pass (COF Cooper 2024/2025 dangling
'President, ' clause; FFIV/JBHT name-title split fragments; PNC/EXPE/LEN
leading-'and' titles; MTD/GNRC full title wording). Section 7 gained
NAME_ROLE_FRAGMENT (hard fail on recurrence - zero remain) and
NAME_TITLE_GLUE (fail on new instances, warn on the 5 known FFIV/JBHT
tuples); section 13 gained dangling-punctuation, 'Total Compensation'
heading-bleed, and leading-'and' title screens with 8 queued tuples added
to KNOWN_TITLE_ARTIFACTS (now 9 tuples: 17 rows at 7 companies); the
dataq modal titles block and its live mirror were re-synced (34->41
repaired).
History: 2026-09-15 22:00 PT run repaired the 8 queued all-caps full-phrase
title rows via the EDGAR title-column re-read (egress recovered): AFL
Bradley E. Dyslin 2023-2025 'EXECUTIVE VICE PRESIDENT' -> 'Executive Vice
President, Global Chief Investment Officer; President, Aflac Global
Investments' (DEF 14A 2026-03-19 acc. 000162828026019621, filed Title Case
- caps were an extraction artifact); MHK Paul F. De Cock 2023-2025
'PRESIDENT AND CHIEF OPERATING OFFICER' -> 'President and Chief Operating
Officer; Former President - Flooring North America'; MHK Mauro Vandini
2024-2025 'PRESIDENT' -> 'President - Global Ceramic' (fn 4: appointed
President, Global Ceramic 2024-09-15) (DEF 14A 2026-04-03 acc.
000110465926039491); all numeric fields asserted byte-identical. Section 15
TITLE_ALLCAPS_FULLPHRASE_QUEUED drained to empty (n_full asserted 0), the
34 abbreviation rows stay locked as filing-conventional.
Headline buckets 99.7% (6,759/6,780).
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
    "def14a_verified_20260916": "def14a_verified_20260916",
    "def14a_verified_20260917": "def14a_verified_20260917",
    "def14a_verified_20260918": "def14a_verified_20260918",
    "def14a_verified_20260919": "def14a_verified_20260919",
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


# -- Section 4c: metadata.description self-consistency ----------------------------
# metadata.description is itself hand-typed headline copy living INSIDE the
# JSON ("500 companies, 6783 NEO records, 500 companies enriched"). It
# drifted to 6783 while the live count was 6785 — section 4 checks README,
# index.html, and js/app.js, but nobody checked the JSON's own headline.
# The description uses the raw integer (no thousands separator), unlike the
# comma-formatted copies elsewhere, so the pattern is f"{n} NEO records".
def check_json_description(n, meta, failures):
    desc = meta.get("description", "")
    want = f"{n} NEO records"
    if want not in desc:
        fail(
            f"metadata.description drift: expected {want!r} (live recount {n}) "
            f"in description {desc!r} -- sync the JSON's own headline copy",
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


# -- Section 4d: dataq-modal live-block fallback truthfulness ----------------
# The Data Verification methodology modal's pay-ratio, executive-
# transitions, and title-artifacts blocks are live-computed at modal-open
# time, but each ships a hand-typed static fallback ("As of the 2026-09-14
# screen: ...") shown before the data loads. Sections 4/4b/4c guard every
# other hand-typed headline on the site, but nothing asserted these three
# fallbacks: any EDGAR batch that legitimately moved the numbers (a title
# repair shrinking the 27-row queue, a new (name, year) tuple, a changed
# pay ratio) would leave the pre-load copy stale with no tripwire.
# This section recounts each block with the exact rule its live-computing
# function mirrors (pay ratio: guard section 11's 3%-tolerance rule;
# transitions: section 12's normalized (name, year) -> tickers screen;
# titles: rows whose (ticker, title) is in the section-13 allowlist) and
# fails the commit if the fallback phrases no longer carry those numbers.
# The triage breakdowns (6 transitions / 5 coincidences / 2 suspicious)
# are human judgment and are not recounted; only the tuple total is.
def check_dataq_modal_live_blocks(companies, failures):
    # pay-ratio distribution (mirrors _dataqPayRatioHtml and section 11)
    within = twox = half = other = 0
    for c in companies:
        pr = c.get("pay_ratio")
        mw = c.get("median_worker_pay")
        ct = c.get("total_compensation")
        if pr in (None, 0) or mw in (None, 0) or ct is None:
            continue
        r = (ct / mw) / pr
        if abs(r - 1) <= max(2 / pr, 0.03):
            within += 1
        elif 1.9 <= r <= 2.1:
            twox += 1
        elif 0.4 <= r <= 0.6:
            half += 1
        else:
            other += 1
    pr_n = within + twox + half + other

    # exec-name collision tuples (mirrors section 12's screen)
    def _coll_key(name):
        return re.sub(r"[^a-z ]", "", (name or "").lower()).strip()

    _person_year = {}
    for c in companies:
        for e in c.get("executives", []):
            nm = _coll_key(e.get("name"))
            yr = e.get("year")
            if nm and yr:
                _person_year.setdefault((nm, yr), set()).add(c.get("ticker"))
    n_coll = sum(1 for tickers in _person_year.values() if len(tickers) > 1)

    # title-artifact queue rows (rows whose (ticker, title) is allowlisted)
    n_art = 0
    art_cos = set()
    for c in companies:
        for e in c.get("executives", []):
            key = (c.get("ticker"), (e.get("title") or "").strip())
            if key in KNOWN_TITLE_ARTIFACTS:
                n_art += 1
                art_cos.add(c.get("ticker"))

    checks = [
        # pay-ratio fallback (JS-escaped apostrophe avoided in patterns)
        (f"{within} of {pr_n} screened companies",
         f"pay ratio within={within} of {pr_n}"),
        (f"{twox} cluster near 2x, {half} near 0.5x, {other} differ otherwise",
         f"pay ratio classes {twox}/{half}/{other}"),
        # transitions fallback
        (f"{n_coll} (name, fiscal year) tuples appear",
         f"transitions {n_coll} tuples"),
        (f"all {n_coll} triaged by tuple",
         f"transitions triage count {n_coll}"),
        # title-artifacts fallback (singular/plural-aware since 2026-09-15
        # 14:00 PT, when the queue fell to 1 row at 1 company)
        (f"leaving {n_art} row{'s' if n_art != 1 else ''} at "
         f"{len(art_cos)} compan{'ies' if len(art_cos) != 1 else 'y'} "
         f"shown exactly as parsed",
         f"title artifacts {n_art} rows at {len(art_cos)} companies"),
    ]
    path = os.path.join(os.path.join(HERE, ".."), "js", "app.js")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        fail(f"dataq-modal 4d: cannot read js/app.js: {e}", failures)
        return
    for pat, label in checks:
        if pat not in text:
            fail(
                f"dataq-modal 4d drift: expected {label} ({pat!r}) in "
                f"js/app.js static fallback: recount from live JSON "
                f"(pay ratio {within}/{pr_n}, {twox}/{half}/{other}; "
                f"transitions {n_coll} tuples; titles {n_art} rows at "
                f"{len(art_cos)} companies) disagrees with the hand-typed "
                f"fallback; sync the fallback before committing",
                failures,
            )


# Section-13 title-artifact allowlist, hoisted to module level so section 4d
# can recount the title-artifacts fallback's queued rows and companies.
# History: 2026-09-15 10:00 PT removed the 5 repaired tuples (DOC x4, APA x1;
# 13 rows) after base titles were verified via the browser path (Healthpeak
# IR for DOC, SEC Form 4 for APA) and the bullet-bleed stripped.
# History: 2026-09-15 12:00 PT removed the 4 repaired tuples (ALLE, DPZ, VST,
# STLD; 12 rows) after the exact SCT principal-position wording was verified
# verbatim in the 2026 proxy/DEF 14A filings via the browser path (all 36
# stored totals matched the filings). Remaining queue: TAP ("CEO of our
# Company (currently" -- parenthetical tail not exposed verbatim in any
# indexed primary source, do not guess) and UHS ("Executive Vice President
# and President of our" -- org-label name row, belongs to the
# name-ambiguity queue). 2 rows at 2 companies.
# History: 2026-09-15 22:00 PT drained all 9 queued tuples (19 rows at 7
# companies: TAP Goyal, COF Cooper x2, FFIV Werner/Maddison/Pelzer x5,
# JBHT Delco/Kuhlow x4, PNC Reilly x3, EXPE Dzielak x3, LEN Jaffe 2023)
# after every title cell was verified verbatim in the filed DEF 14A SCTs
# (VM egress recovered; User-Agent Kit/1.0). The same pass also repaired
# adjacent finds outside the queue: COF LaPrade 2023-2025 name/title glue
# (name 'Frank G. LaPrade, III', title restored as filed), LEN Jaffe
# 2024/2025 + Bessette 2023-2025 split-title rows, and the STLD
# 'Barry Schneider' 2023/2024 phantom rows (re-attributed to Glenn A.
# Pushis, Senior Vice President - see section 14). All 29 rows' numeric
# fields asserted byte-identical. 0 queued rows: the static fallback must
# now say "0 rows at 0 companies" and the guard fails on ANY title artifact
# match - the allowlist is empty by design, not by omission.
KNOWN_TITLE_ARTIFACTS = set()


# Section-14 name-ambiguity resolution guard (2026-09-15 15:30 PT).
# Two same-person duplicate families were proven via primary sources and
# deleted: OKE 'Walter S. Hulse' 2023/2024/2025 (stale doubles of
# 'Walter S. Hulse, III' - ONEOK's own management page styles him
# "Walter S. Hulse III", 2019 SEC-filed annual-report exhibit signed
# "/s/ Walter S. Hulse III") and DRI 'Raj Vennam' 2023/2024 (stale doubles
# of 'Rajesh Vennam' - Darden's 2020 announcement "Rajesh (Raj) Vennam",
# Form 4 "Vennam Rajesh"). The deleted name forms must never reappear for
# those tickers (fail). AJG's 'Pat Gallagher' vs 'Patrick Gallagher' pair
# was adjudicated DISTINCT persons (Patrick M. Gallagher EVP/COO since
# 2024 per AJG's own 2023 announcement; J. Patrick Gallagher Jr.
# Chairman/CEO) - both 2025 rows must survive; a future merge is a fail.
# The class screen is warning-only: same ticker + same year, one
# normalized name a strict prefix of the other, or same last name with a
# first-token prefix / middle-token difference (suffix, nickname, and
# dropped-middle-initial double-count signatures). The STLD pair was
# resolved 2026-09-15 22:00 PT: the stored 'Barry Schneider' 2023/2024
# 'SVP, Steel Operations' rows were Glenn A. Pushis's 2025-DEF-14A SCT rows
# (acc. 0001558370-25-002901, totals match to the dollar; 'SVP, Steel
# Operations' appears nowhere as a title in either filing; the 2026 filing
# bio: "Barry T. Schneider has been our President and Chief Operating
# Officer since March 2023" - one Barry Schneider exists). Both rows were
# re-attributed to 'Glenn A. Pushis', title 'Senior Vice President' as
# filed; numeric fields byte-identical. The pair is removed from the known
# set so any 'Barry Schneider' reappearance warns as NEW; anything NEW
# warns for triage, never auto-merges (section 12's rule: rows are never
# merged by a guard).
RESOLVED_DUPLICATE_NAMES = {
    ("OKE", "Walter S. Hulse"),
    ("DRI", "Raj Vennam"),
}
ADJUDICATED_DISTINCT_NAME_PAIRS = {
    ("AJG", "Pat Gallagher", "Patrick Gallagher"),
}
KNOWN_NAME_PREFIX_PAIRS = set()


def _norm_name(n):
    n = (n or "").lower()
    n = re.sub(r"[^a-z ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


# Section-15 title all-caps styling screen (2026-09-15 19:30 PT).
# A fresh offline screen found 41 NEO rows whose title is all-caps (every
# alpha character uppercase, >=4 alpha chars so plain 'CEO'/'CFO'/'COO' are
# out of scope). The pattern is stable across years per person (systematic,
# not random parse noise). Two sub-classes, locked separately:
#   (a) TITLE_ALLCAPS_ABBREV (14 tuples, 34 rows, 13 companies): standard
#       corporate title abbreviations ('SVP, COO', 'CEO, AWM', 'EVP & CFO',
#       'CHRO', 'CEO PMI U.S.', ...). Companies print these abbreviated forms
#       in their SCTs as a matter of convention; treated as as-disclosed,
#       no repair. Locked so a parser change cannot silently introduce
#       more.
#   (b) TITLE_ALLCAPS_FULLPHRASE_QUEUED (3 tuples, 8 rows, 2 companies):
#       full title phrases in all caps while sibling NEOs at the same
#       company extract in Title Case - AFL 'EXECUTIVE VICE PRESIDENT'
#       (Dyslin 2023-2025), MHK 'PRESIDENT AND CHIEF OPERATING OFFICER'
#       (De Cock 2023-2025), MHK 'PRESIDENT' (Vandini 2024-2025). The
#       company's own primary sources style Dyslin's title in Title Case
#       (SEC Form 4 "Executive Vice President"; 2026 proxy bio "Executive
#       Vice President, Global Chief Investment Officer, Aflac"), so the
#       caps are likely an extraction artifact - but the SCT title cell
#       itself is unverified (VM egress down since 2026-09-12 ~16:20 PT)
#       and the as-disclosed rule forbids re-casing on a hunch. Queued for
#       the EDGAR title-column re-read
#       (title_allcaps_queue_20260915_1930.md); warn, do not fail, do not
#       repair offline.
#   Update 2026-09-15 22:00 PT: EDGAR re-read complete (egress recovered).
#   Filed SCT title cells are Title Case, not all caps - the caps were an
#   extraction artifact. Repaired: AFL Dyslin 2023-2025 ->
#   "Executive Vice President, Global Chief Investment Officer; President,
#   Aflac Global Investments" (DEF 14A 2026-03-19 acc. 000162828026019621);
#   MHK De Cock 2023-2025 -> "President and Chief Operating Officer;
#   Former President - Flooring North America"; MHK Vandini 2024-2025 ->
#   "President - Global Ceramic" (fn 4: appointed President, Global Ceramic
#   2024-09-15) (DEF 14A 2026-04-03 acc. 000110465926039491). Queue EMPTY:
#   n_full asserted 0; any all-caps title outside the abbrev allowlist is
#   a new styling regression and fails hard.
# Any all-caps title outside both sets is a new styling regression and
# fails hard. Recounts are asserted exact so a future repair of any of
# these rows forces the allowlist update.
TITLE_ALLCAPS_ABBREV = {
    ("AAPL", "SVP, COO"),
    ("JPM", "CEO, AWM"),
    ("PEP", "CEO, EMEA"),
    ("CAT", "CHRO"),
    ("GD", "SVP, CFO"),
    ("PM", "CEO PMI U.S."),
    ("DOV", "SVP & CHRO"),
    ("DOW", "EVP, R&D"),
    ("CCI", "EVP & CTRO"),
    ("ECL", "CHAIRMAN"),
    ("AES", "EVP & CFO"),
    ("AES", "EVP & COO"),
    ("WAT", "SVP & CFO"),
    ("ESS", "CIO AND EVP"),
}
# Repaired 2026-09-15 22:00 PT via EDGAR re-read - empty. Kept as a named
# set so the section-15 screen still references the drained queue.
TITLE_ALLCAPS_FULLPHRASE_QUEUED = set()


def _is_allcaps_title(t):
    alpha = [ch for ch in t if ch.isalpha()]
    return len(alpha) >= 4 and all(ch.isupper() for ch in alpha)


def check_title_allcaps(companies, failures):
    n_abbrev = n_full = 0
    for c in companies:
        for e in c.get("executives", []):
            t = (e.get("title") or "").strip()
            if not t or not _is_allcaps_title(t):
                continue
            key = (c.get("ticker"), t)
            if key in TITLE_ALLCAPS_ABBREV:
                n_abbrev += 1
                continue
            if key in TITLE_ALLCAPS_FULLPHRASE_QUEUED:
                n_full += 1
                print(f"  warning: all-caps full-phrase title (queued, "
                      f"15): {c.get('ticker')} {e.get('name')} "
                      f"{e.get('year')} title={t!r} - the 2026-09-15 "
                      f"22:00 PT EDGAR repair drained this queue; "
                      f"unexpected recurrence")
                continue
            fail(f"new all-caps title not in the 2026-09-15 allowlists: "
                 f"{c.get('ticker')} {e.get('name')} {e.get('year')} "
                 f"title={t!r} (15)", failures)
    if n_abbrev != 34 or n_full != 0:
        fail(f"all-caps title recount drift: abbrev {n_abbrev} (want 34), "
             f"full-phrase {n_full} (want 0 - queue drained 2026-09-15 "
             f"22:00 PT) (15)", failures)


def check_name_ambiguity(companies, failures):
    # deleted stale forms must not reappear
    for ticker, dead_name in sorted(RESOLVED_DUPLICATE_NAMES):
        for c in companies:
            if c.get("ticker") != ticker:
                continue
            for e in c.get("executives", []):
                if e.get("name") == dead_name:
                    fail(
                        f"resolved duplicate name reappeared ({ticker} "
                        f"{dead_name!r} {e.get('year')}) - the 2026-09-15 "
                        f"15:30 PT batch deleted this stale same-person "
                        f"double; do not reintroduce (14)",
                        failures,
                    )
    # adjudicated-distinct pairs must keep both rows
    for ticker, na, nb in sorted(ADJUDICATED_DISTINCT_NAME_PAIRS):
        names = {e.get("name") for c in companies
                 if c.get("ticker") == ticker
                 for e in c.get("executives", [])}
        for want in (na, nb):
            if want not in names:
                fail(
                    f"adjudicated-distinct person row missing ({ticker} "
                    f"{want!r}) - AJG 'Pat Gallagher' (J. Patrick Gallagher "
                    f"Jr., Chairman/CEO) and 'Patrick Gallagher' (Patrick M. "
                    f"Gallagher, EVP/COO since 2024) are different people; "
                    f"do not merge (14)",
                    failures,
                )
    # warning-only class screen
    for c in companies:
        by_year = {}
        for e in c.get("executives", []):
            by_year.setdefault(e.get("year"), {})[_norm_name(
                e.get("name"))] = e.get("name")
        for yr in sorted(by_year):
            keys = sorted(k for k in by_year[yr] if k)
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    a, b = keys[i], keys[j]
                    if a == b:
                        continue
                    ta, tb = a.split(), b.split()
                    prefix = a.startswith(b) or b.startswith(a)
                    first_tok = (ta[-1] == tb[-1] and ta[0] != tb[0]
                                 and (ta[0].startswith(tb[0])
                                      or tb[0].startswith(ta[0]))
                                 and min(len(ta[0]), len(tb[0])) >= 3)
                    mid_tok = (len(ta) != len(tb) and ta[0] == tb[0]
                               and ta[-1] == tb[-1]
                               and abs(len(ta) - len(tb)) <= 2)
                    if not (prefix or first_tok or mid_tok):
                        continue
                    na, nb = by_year[yr][a], by_year[yr][b]
                    pair = (c.get("ticker"),) + tuple(sorted((na, nb)))
                    if pair in {(t,) + tuple(sorted((x, y)))
                                for t, x, y in ADJUDICATED_DISTINCT_NAME_PAIRS}:
                        continue
                    tag = "known" if pair in KNOWN_NAME_PREFIX_PAIRS else "NEW"
                    print(
                        f"  warning: same-ticker same-year name-prefix pair "
                        f"({tag}, 14): {c.get('ticker')} {yr} "
                        f"{na!r} vs {nb!r} - triage via primary sources; "
                        f"never auto-merge")


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

    # 3. DQ-repair freshness convention (2026-09-20 06:00 run): the footer
    # "Last repair" reads metadata.last_dq_repair; every DQ batch script must
    # set both top-level last_updated and metadata.last_dq_repair to the run
    # date, so the footer can never lag a batch by a day again.
    ymd = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    dqr = meta.get("last_dq_repair")
    if not (isinstance(dqr, str) and ymd.match(dqr)):
        fail(f"metadata.last_dq_repair={dqr!r} not a ymd date", failures)
    else:
        top = data.get("last_updated")
        if isinstance(top, str) and ymd.match(top) and dqr > top:
            fail(
                f"metadata.last_dq_repair={dqr} is later than top-level "
                f"last_updated={top}",
                failures,
            )

    # 3b. audit buckets vs record-level _total_source (count by canonical key so
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

    # 4d. dataq-modal live-block fallbacks: the pay-ratio, transitions, and
    #     title-artifacts static fallbacks must carry the live recounts
    check_dataq_modal_live_blocks(companies, failures)

    # 4c. metadata.description self-consistency: the JSON's own headline copy
    check_json_description(n, meta, failures)

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
    # warning-only (7d). The LHX class above stays a hard fail. Both known
    # members (UHS 2023 'Behavioral Health', STLD 2023 'Flat Roll Steel')
    # were resolved 2026-09-15 14:00 PT via the browser path (Peterson/Graham
    # verified against SEC Form 4, Becker's, the STLD proxy NEO list, and the
    # company bios); the tuple is kept as the tripwire for future classes.
    ORG_LABEL_UNRESOLVED = ()
    # History: 2026-09-15 18:00 PT added NAME_ROLE_FRAGMENT after repairing
    # the 3 MTD rows ('Richard Wong Head of Asia and Pacific' -> 'Richard
    # Wong'). Role language merged into the name field can never be part of
    # a genuine SCT name - hard fail on any recurrence.
    NAME_ROLE_FRAGMENT = re.compile(
        r"\b(Head of|President of|CEO of|CFO of|COO of|CTO of|"
        r"and (CEO|CFO|COO|CTO|CHRO|CLO|GC|VP))\b")
    # History: 2026-09-15 18:00 PT added NAME_TITLE_GLUE after repairing
    # GNRC 2025 ('Raj Kanuru VP' -> 'Raj Kanuru'). A name field ending in a
    # title token ('Cooper Werner VP', 'Frank PelzerFormer VP',
    # 'Brad DelcoCFO', 'John KuhlowCFO, CAO') means the title was split
    # across the name/title cell boundary.
    # History: 2026-09-15 22:00 PT drained the 5 known FFIV/JBHT tuples
    # after DEF 14A SCT re-reads pinned the exact split points (VM egress
    # recovered). Names and titles rejoined as filed ('Cooper Werner',
    # 'John Maddison', 'Frank Pelzer', 'Brad Delco', 'John Kuhlow'); all
    # numeric fields asserted byte-identical. The allowlist is empty by
    # design: any name/title-glue match now fails the commit.
    NAME_TITLE_GLUE = re.compile(
        r"\b(VP|CFO|CEO|COO|CTO|CAO|CIO|CHRO|GC|CLO|Former)\s*$|"
        r",\s*(?!(II|III|IV|V|Jr\.?|Sr\.?)$)[A-Z]{2,4}$")
    KNOWN_NAME_TITLE_GLUE = set()
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
            if NAME_ROLE_FRAGMENT.search(nm):
                fail(
                    f"{c.get('ticker')} {e.get('year')}: exec name={nm!r} "
                    f"carries a role fragment (section 7) - the 2026-09-15 "
                    f"18:00 PT batch repaired the MTD class offline; nothing "
                    f"genuine can match",
                    failures,
                )
            if NAME_TITLE_GLUE.search(nm):
                key = (c.get("ticker"), nm)
                tag = "known" if key in KNOWN_NAME_TITLE_GLUE else "NEW"
                print(f"  warning: name/title cell-boundary split ({tag}, "
                      f"7): {c.get('ticker')} {e.get('year')} name={nm!r} - "
                      f"see title_split_artifact_queue_20260915_1800.md")
                if key not in KNOWN_NAME_TITLE_GLUE:
                    fail(
                        f"new name/title-glue artifact: {c.get('ticker')} "
                        f"{nm!r} (section 7)",
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
        #     offline. 2026-09-15 14:00 PT: the queue is empty - UHS 2023
        #     'Behavioral Health' -> Matthew J. Peterson and STLD 2023
        #     'Flat Roll Steel' -> Christopher A. Graham, both verified via
        #     the browser path (no EDGAR re-read needed). The LHX class
        #     (repaired 2026-09-13 10:00) stays a hard fail in
        #     ORG_LABEL_ARTIFACTS.
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
    #    $1,000 with the EFFECTIVE pension (pension_nqdc or pension_change,
    #    see _eff_pension) in (0, None). Warning-only: the gap is
    #    arithmetic, the filing SCT must confirm the pension cell before
    #    repair.
    #    History: 2026-09-14 22:00 PT correction - the original 7-component
    #    rule preferred pension_nqdc alone and ignored pension_change, so it
    #    false-flagged 20 rows (SO 13, TFC 3, PPL 1, AME 3) whose pension
    #    lives in pension_change and had been repaired/re-verified
    #    2026-09-09/09-10 (all foot exactly; the $45,892,455 "missing
    #    pension" queue total was phantom). The pension-aware rule fires on
    #    ZERO rows; the old queue file is retired (kept for audit trail in
    #    the goal hidden_files). Genuine drops still trip: both pension keys
    #    0/None with gap > $1,000. 9b covers the residual footing anomalies
    #    on full rows (both directions, >$1,000, excluding adjudicated
    #    component_mismatch rows): none unadjudicated as of 2026-09-14
    #    22:00 PT.
    _COMP_KEYS = ("salary", "bonus", "stock_awards", "option_awards",
                  "non_equity_incentive", "pension_nqdc", "all_other")
    _NON_PEN_KEYS = ("salary", "bonus", "stock_awards", "option_awards",
                     "non_equity_incentive", "all_other")

    def _eff_pension(e):
        # Pension lives in either pension_nqdc or pension_change, never
        # both (see the section-4b recount note): Southern-style rows carry
        # 0 in pension_nqdc (the filing states no above-market NQDC
        # earnings) with the SCT column-(f) value in pension_change.
        pn, pc = e.get("pension_nqdc"), e.get("pension_change")
        if pn == 0 and (pc or 0) > 0:
            return pc
        return pn if pn is not None else pc

    for c in companies:
        for e in c.get("executives", []):
            if not all(k in e for k in _COMP_KEYS):
                continue
            if e.get("_total_source") == "component_mismatch":
                continue
            foot = sum(e.get(k) or 0 for k in _NON_PEN_KEYS) + (_eff_pension(e) or 0)
            gap = (e.get("total") or 0) - foot
            pen = _eff_pension(e)
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

    # 12. Cross-company same-year exec-name collision tripwire
    #     (2026-09-14 14:00 PT run). A normalized (name, fiscal year) tuple
    #     appearing as an NEO row at two different S&P 500 companies is
    #     either a genuine mid-year executive transition (both SCTs
    #     legitimately list the person), a same-name coincidence (two
    #     different people), or a parser misattribution to the wrong
    #     company. Screen found 13 collisions; each was triaged via the
    #     browser path against primary sources on 2026-09-14:
    #     LEGIT transitions (6): ashkenazi 2024 GOOGL/LLY (LLY->GOOGL CFO,
    #     GOOGL SCT title carries "as of July"), delorefice 2025 BDX/ULTA
    #     (BDX EVP&CFO -> ULTA CFO effective 2025-12-05, ULTA 8-K), knight
    #     2025 BAX/SOLV (BAX COO -> SOLV CCO effective 2025-11-10), woods
    #     2025 CFG/STT (Citizens Vice Chair&CFO -> STT CFO, joined late Aug
    #     2025), nudi 2025 GIS/MAS (GIS -> Masco President & CEO), sennesael
    #     2025 SWKS/WDC (SWKS -> WDC CFO; both SCTs carry "Former" at the
    #     old company). NAME COINCIDENCES (2, benign — rows live inside
    #     their own company, no cross-linking): hanson 2024/2025 CEG/SOLV
    #     (CEG's Bryan Hanson = 30yr nuclear veteran per Constellation's
    #     leadership page; SOLV's = ex-Zimmer Biomet medtech CEO), murphy
    #     2023-2025 KO/PGR (KO President & CFO vs PGR Claims President).
    #     SUSPICIOUS (1, queued for DEF 14A re-read, not repairable
    #     offline): burgoyne 2023/2024 LULU/WSM — the lululemon Burgoyne was
    #     LULU President Americas & Global Guest Innovation 2006-2025
    #     (joins Vail Resorts Jan 2026), so WSM's "EVP, Chief Talent
    #     Officer" rows cannot be the same person; WSM 2023 SCT parsed only
    #     4 rows (thin). See exec_collision_queue_20260914_1400.md (also
    #     queues the CFG 2025 woods title mismatch: stored "EVP and Head
    #     of Commercial Banking" vs his actual Citizens Vice Chair & CFO
    #     role). Any collision NOT in KNOWN_COLLISIONS fails as a
    #     regression signal; the guard never merges or reassigns rows.
    def _coll_key(name):
        return re.sub(r"[^a-z ]", "", (name or "").lower()).strip()

    KNOWN_COLLISIONS = {
        ("anat ashkenazi", 2024, "GOOGL", "LLY"),
        ("bryan c hanson", 2024, "CEG", "SOLV"),
        ("bryan c hanson", 2025, "CEG", "SOLV"),
        ("celeste burgoyne", 2023, "LULU", "WSM"),
        ("celeste burgoyne", 2024, "LULU", "WSM"),
        ("christopher j delorefice", 2025, "BDX", "ULTA"),
        ("heather knight", 2025, "BAX", "SOLV"),
        ("john f woods", 2025, "CFG", "STT"),
        ("john murphy", 2023, "KO", "PGR"),
        ("john murphy", 2024, "KO", "PGR"),
        ("john murphy", 2025, "KO", "PGR"),
        ("jonathon j nudi", 2025, "GIS", "MAS"),
        ("kris sennesael", 2025, "SWKS", "WDC"),
    }
    _person_year = {}
    for c in companies:
        for e in c.get("executives", []):
            nm = _coll_key(e.get("name"))
            yr = e.get("year")
            if nm and yr:
                _person_year.setdefault((nm, yr), set()).add(c.get("ticker"))
    for (nm, yr), tickers in sorted(_person_year.items()):
        if len(tickers) < 2:
            continue
        key = (nm, yr) + tuple(sorted(tickers))
        tag = "known" if key in KNOWN_COLLISIONS else "NEW"
        print(f"  warning: cross-company exec-name collision ({tag}, 12): "
              f"{nm!r} year {yr} at {sorted(tickers)} — see "
              f"exec_collision_queue_20260914_1400.md; do not merge rows")
        if key not in KNOWN_COLLISIONS:
            fail(f"new exec-name collision not in the 2026-09-14 allowlist: "
                 f"{nm!r} {yr} {sorted(tickers)} (12)", failures)

    # 13. Title footnote-bleed / truncation tripwire (2026-09-14 18:00 PT).
    #     A full-file title scan found two artifact classes section 7 did
    #     not cover: (a) footnote markers bled into the title cell
    #     (bullets like "●" plus the next NEO's name fragment, or trailing
    #     "*" footnote markers), and (b) mid-phrase truncation ("... of A",
    #     "... of D", "... of V", "Chair of the Board During"). The
    #     trailing-*/** subclass was repaired mechanically on 2026-09-14
    #     (COR Executive Chairman, ROST CFO, SHW SVP-Finance & CFO; base
    #     titles verified against primary sources via the browser path,
    #     8 rows). The bullet-bleed subclass was repaired 2026-09-15 10:00 PT
    #     (DOC x10 rows across 4 titles, APA x3 rows; base titles verified
    #     via the browser path -- Healthpeak IR for DOC, SEC Form 4 for APA;
    #     the bleed chain Brinker<-Moses<-Mabry<-Bohn<-Porter proved
    #     title-cell contamination only, no name-column row shift).
    #     The truncation subclass was repaired 2026-09-15 12:00 PT (ALLE x3
    #     rows "President and CEO", DPZ x3 "Chief Executive Officer", VST x3
    #     "President and Chief Executive Officer", STLD x3 "Chairman and
    #     Chief Executive Officer"; exact SCT principal-position wording
    #     verified verbatim in the 2026 proxy/DEF 14A filings via the browser
    #     path, all 36 stored totals matched the filings).
    #     The rest need DEF 14A SCT re-reads (VM egress dead since
    #     2026-09-12 ~18:00 PT) and are queued in
    #     title_bleed_truncation_queue_20260914_1800.md: TAP ("CEO of our
    #     Company (currently" -- unbalanced paren, mid-phrase truncation;
    #     Goyal became President and CEO effective 2025-10-01 per Molson
    #     Coors IR, so the parenthetical tail is likely a transition-date
    #     qualifier, but no indexed primary source exposes it verbatim --
    #     do not guess), UHS ("Executive Vice President and President of
    #     our" -- also in the name-ambiguity queue as an org-label name
    #     row). Any title NOT in KNOWN_TITLE_ARTIFACTS failing this screen
    #     is a new artifact class regression and fails hard.
    _TITLE_MARKER = re.compile(r"[●†‡#§]|\*{1,2}$")
    _TITLE_FRAG = re.compile(
        r"(?i)\b(of|the|and|or|to|in|during|for|our|a|an|&)$")
    _TITLE_OF_LETTER = re.compile(r"\bof [A-Z]$")
    # dangling punctuation: the title cell was truncated mid-clause leaving
    # a trailing comma/semicolon/colon (LEN 'Former Vice President,',
    # COF '...President, ', MET '...GTO 2025 Total Compensation:').
    _TITLE_DANGLING = re.compile(r"[,;:]\s*$")
    # document-heading bleed: a section heading captured into the title
    # cell (MET 'EVP and Head of GTO 2025 Total Compensation:').
    _TITLE_HEADING_BLEED = re.compile(r"(?i)total compensation")
    # leading-'and' fragment: the title's first clause was merged into the
    # name cell ('Cooper Werner VP' / 'and Executive Chief Financial
    # Officer'), or dropped entirely (PNC 'and CFO', EXPE 'and Secretary',
    # LEN 'and President'). No genuine SCT title starts with 'and'.
    _TITLE_LEADING_AND = re.compile(r"(?i)^and\b")
    for c in companies:
        for e in c.get("executives", []):
            t = (e.get("title") or "").strip()
            if not t:
                continue
            if not (_TITLE_MARKER.search(t) or _TITLE_FRAG.search(t)
                    or _TITLE_OF_LETTER.search(t)
                    or t.count("(") != t.count(")")
                    or _TITLE_DANGLING.search(t)
                    or _TITLE_HEADING_BLEED.search(t)
                    or _TITLE_LEADING_AND.search(t)):
                continue
            key = (c.get("ticker"), t)
            tag = "known" if key in KNOWN_TITLE_ARTIFACTS else "NEW"
            print(f"  warning: title footnote-bleed/truncation ({tag}, 13): "
                  f"{c.get('ticker')} {e.get('name')} {e.get('year')} "
                  f"title={t!r} — see "
                  f"title_bleed_truncation_queue_20260914_1800.md; do not "
                  f"repair offline")
            if key not in KNOWN_TITLE_ARTIFACTS:
                fail(f"new title artifact not in the 2026-09-14 allowlist: "
                     f"{c.get('ticker')} {t!r} (13)", failures)

    # 14. Name-ambiguity resolution regression (2026-09-15 15:30 PT):
    #     deleted stale same-person name forms must not reappear, the AJG
    #     adjudicated-distinct pair must keep both rows, and new
    #     same-ticker same-year name-prefix pairs warn for triage.
    check_name_ambiguity(companies, failures)

    # 15. Title all-caps styling screen (2026-09-15 19:30 PT; queue drained
    #     2026-09-15 22:00 PT): all-caps titles must be in
    #     TITLE_ALLCAPS_ABBREV (filing-conventional abbreviations, locked);
    #     the 8-row AFL/MHK full-phrase queue was repaired via the EDGAR
    #     title-column re-read (filed Title Case, not all caps) and now
    #     asserts 0. New instances fail, recounts asserted exact.
    check_title_allcaps(companies, failures)

    if failures:
        print("METADATA CONSISTENCY CHECK FAILED:")
        for m in failures:
            print("  -", m)
        return 1
    print(f"OK: {n} exec rows, buckets recount-exact, metadata truthful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
