#!/usr/bin/env python3
"""Regression guard: iteration-log data claims must match the data files.

Every panel-eval iteration writes a "- Data:" bullet into the canonical
iteration log carrying the headline audit numbers (company count, NEO row
count, verified_total, the DEF 14A-verified percentage, peer-network
nodes/edges, PvP panel companies/company-years, enriched_count,
last_dq_repair), asserted as "Recomputed from data files this run (not
copied)". That assertion is only a hand convention (iteration-log standing
note #8: "recompute data stats from data files each run when writing log
prose, never copy-paste prior entries' numbers") - a typo or a stale
copy-paste makes the audit trail lie, and until this guard NOTHING
asserted the prose. check_metadata_consistency pins data-vs-own-metadata,
check_stub_home_capture and check_orphaned_stub_detail pin stub presence
and detail, but the prose NUMBERS in a backfilled entry were unverified -
the log-prose number-drift class.

This guard asserts the claim itself: when the latest full (non-[AUTO-STUB])
iteration entry's "- Data:" bullet says the numbers were recomputed from
the data files, every parseable claim in that bullet must equal the live
data files. A prior run's drifted prose fails loudly at the NEXT commit,
forcing correction before more entries pile on top of the lie - the same
fail-closed treatment check_stub_home_capture gives a voided stub.

Checks (all static - three small JSON reads + one log scan, <1s):
  S1 the canonical log exists and is readable at the hook's resolved path
     (missing/unreadable = exit 2 infra advisory, non-blocking; mirrors
     the sibling stub guards)
  S2 the three data files load (compensation.json, peer-network.json,
     pay_vs_performance.json) (unloadable = exit 2 infra advisory: the
     guard cannot verify, so it must not block)
  S3 the latest full "## ... - Iteration" entry (excluding [AUTO-STUB]
     headers) carries a "- Data:" bullet whose "Recomputed from data
     files" marker is present; each matched claim is compared to the
     data-file truth:
       - "<N> companies / <M> NEO rows" -> metadata total_companies /
         total_neo_records
       - "verified_total <N>" -> metadata verified_total
       - "<P>% DEF 14A-verified" -> round(verified/total*100, 2)
       - "peer network <N> nodes / <M> edges" -> peer node/edge counts
       - "PvP panel <N> companies / <M> company-years" -> pvp companies /
         company_years
       - "enriched_count <N>" -> metadata enriched_count
       - "last_dq_repair <date>" -> metadata last_dq_repair
     any mismatch = HARD FAIL naming the claim, the log's value, and the
     data file's value. A Data bullet without the recompute marker, or a
     marked bullet with no parseable claims (prose format evolved), prints
     a WARN advisory and passes - the guard verifies the assertion when it
     is made, it does not pin prose format.

Usage:
  scripts/check_log_prose_numbers.py              # same checks
  scripts/check_log_prose_numbers.py --static-only # same checks

Exit: 0 = prose matches (or no recompute assertion to verify);
      1 = drifted prose (loud); 2 = infra.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 15:30 - created (15:30 PT iteration). Closes the
    log-prose number-drift class: the per-run iteration-log entries
    hand-write the headline audit numbers with only the standing
    hand-convention ("recompute from data files each run, never
    copy-paste") as tripwire; a typo or stale copy-paste would make the
    audit trail lie with no verifier. Verified green on the true tree
    (latest full entry's 7 claim types all parse and match) and
    negative-tested in /tmp.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REL_LOG = os.path.join(
    "workspace", "goals", "s-p-500-executive-compensation-tracker",
    "hidden_files", "iteration-log.md")

DATA_FILES = {
    "comp": os.path.join(REPO, "data", "compensation.json"),
    "peer": os.path.join(REPO, "data", "peer-network.json"),
    "pvp": os.path.join(REPO, "data", "pay_vs_performance.json"),
}

ENTRY_RE = re.compile(
    r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} [A-Z]+ - Iteration (?!\[AUTO-STUB\])",
    re.M)
DATA_BULLET_RE = re.compile(r"^- Data: (.*)$", re.M)
RECOMPUTE_MARKER = "Recomputed from data files"


def resolve_log():
    override = os.environ.get("ITERATION_LOG")
    if override:
        return override
    return os.path.join(os.environ.get("HOME", ""), REL_LOG)


def num(s):
    return int(s.replace(",", ""))


results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


static_only = "--static-only" in sys.argv  # noqa: F841 (contract literal)

LOG = resolve_log()

# S1: canonical log exists and is readable
if not os.path.isfile(LOG):
    print("INFRA: canonical iteration log not found at %s" % LOG)
    sys.exit(2)
try:
    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        log_text = fh.read()
except OSError as exc:
    print("INFRA: cannot read canonical iteration log %s: %s" % (LOG, exc))
    sys.exit(2)
check("S1 canonical log readable", True, LOG)

# S2: data files load
truth = {}
for key, path in DATA_FILES.items():
    try:
        with open(path, "r", encoding="utf-8") as fh:
            truth[key] = json.load(fh)
    except (OSError, ValueError) as exc:
        print("INFRA: cannot load data file %s: %s" % (path, exc))
        print("  (the guard cannot verify prose without the data files; "
              "not a commit blocker)")
        sys.exit(2)
check("S2 data files load", True,
      "compensation.json, peer-network.json, pay_vs_performance.json")

comp_meta = truth["comp"].get("metadata", {})
peer_doc = truth["peer"]
peer_meta = peer_doc.get("metadata", {})
pvp_meta = truth["pvp"].get("metadata", {})

peer_nodes = peer_meta.get("node_count") or len(peer_doc.get("nodes", []))
peer_edges = peer_meta.get("edge_count") or len(peer_doc.get("edges", []))

# S3: latest full entry's Data bullet claims match the data files
starts = [m.start() for m in ENTRY_RE.finditer(log_text)]
if not starts:
    print("WARN: no full (non-stub) iteration entries found in the log; "
          "nothing to verify")
    sys.exit(0)

seg = log_text[starts[-1]:starts[-1] + 8000]
bullet_m = DATA_BULLET_RE.search(seg)
if not bullet_m:
    print("WARN: latest full iteration entry has no '- Data:' bullet; "
          "nothing to verify (prose format may have evolved)")
    sys.exit(0)
bullet = bullet_m.group(1)
if RECOMPUTE_MARKER not in bullet:
    print("WARN: latest '- Data:' bullet does not assert '%s'; no "
          "recompute claim to verify" % RECOMPUTE_MARKER)
    sys.exit(0)

claims = []  # (label, log_value_str, truth_value, equal)


def claim_comp_rows():
    m = re.search(r"(\d[\d,]*) companies / (\d[\d,]*) NEO rows", bullet)
    if m:
        claims.append((
            "companies / NEO rows",
            "%s / %s" % (m.group(1), m.group(2)),
            num(m.group(1)) == comp_meta.get("total_companies")
            and num(m.group(2)) == comp_meta.get("total_neo_records"),
            "log %s companies / %s NEO rows vs data %s / %s"
            % (m.group(1), m.group(2), comp_meta.get("total_companies"),
               comp_meta.get("total_neo_records"))))


def claim_verified_total():
    m = re.search(r"verified_total (\d[\d,]*)", bullet)
    if m:
        claims.append((
            "verified_total",
            m.group(1),
            num(m.group(1)) == comp_meta.get("verified_total"),
            "log verified_total %s vs data %s"
            % (m.group(1), comp_meta.get("verified_total"))))


def claim_pct():
    m = re.search(r"(\d+\.\d+)% DEF 14A-verified", bullet)
    if m:
        total = comp_meta.get("total_neo_records") or 0
        verified = comp_meta.get("verified_total") or 0
        truth_pct = round(verified / total * 100, 2) if total else None
        claims.append((
            "DEF 14A-verified %",
            m.group(1) + "%",
            truth_pct is not None and round(float(m.group(1)), 2) == truth_pct,
            "log %s%% vs data %s%%" % (m.group(1), truth_pct)))


def claim_peer():
    m = re.search(r"peer network (\d[\d,]*) nodes / (\d[\d,]*) edges", bullet)
    if m:
        claims.append((
            "peer network nodes / edges",
            "%s / %s" % (m.group(1), m.group(2)),
            num(m.group(1)) == peer_nodes and num(m.group(2)) == peer_edges,
            "log %s nodes / %s edges vs data %s / %s"
            % (m.group(1), m.group(2), peer_nodes, peer_edges)))


def claim_pvp():
    m = re.search(r"PvP panel (\d[\d,]*) companies / (\d[\d,]*) company-years",
                  bullet)
    if m:
        claims.append((
            "PvP panel companies / company-years",
            "%s / %s" % (m.group(1), m.group(2)),
            num(m.group(1)) == pvp_meta.get("companies")
            and num(m.group(2)) == pvp_meta.get("company_years"),
            "log %s companies / %s company-years vs data %s / %s"
            % (m.group(1), m.group(2), pvp_meta.get("companies"),
               pvp_meta.get("company_years"))))


def claim_enriched():
    m = re.search(r"enriched_count (\d+)", bullet)
    if m:
        claims.append((
            "enriched_count",
            m.group(1),
            int(m.group(1)) == comp_meta.get("enriched_count"),
            "log enriched_count %s vs data %s"
            % (m.group(1), comp_meta.get("enriched_count"))))


def claim_last_dq():
    m = re.search(r"last_dq_repair (\d{4}-\d{2}-\d{2})", bullet)
    if m:
        claims.append((
            "last_dq_repair",
            m.group(1),
            m.group(1) == comp_meta.get("last_dq_repair"),
            "log last_dq_repair %s vs data %s"
            % (m.group(1), comp_meta.get("last_dq_repair"))))


for fn in (claim_comp_rows, claim_verified_total, claim_pct, claim_peer,
           claim_pvp, claim_enriched, claim_last_dq):
    fn()

if not claims:
    print("WARN: recompute marker present but no parseable data claims in "
          "the latest '- Data:' bullet; nothing to verify (prose format "
          "may have evolved)")
    sys.exit(0)

failed = 0
for label, log_val, ok, detail in claims:
    check("S3 log prose '%s' matches data files" % label, ok,
          detail if not ok else "log %s == data files" % log_val)
    if not ok:
        failed += 1

if failed:
    print("FAIL: %d of %d data claims in the latest iteration-log entry "
          "contradict the data files (log-prose number drift)" % (failed,
                                                                  len(claims)))
    print("  Fix: correct the '- Data:' bullet numbers to the data-file "
          "values (recompute from the data files, never copy-paste), then "
          "re-run this guard.")
    sys.exit(1)

sys.exit(0)
