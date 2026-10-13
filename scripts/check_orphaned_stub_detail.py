#!/usr/bin/env python3
"""Regression guard: no iteration-log AUTO-STUB may stay bare past its backfill window.

The post-commit hook (scripts/post-commit-iteration-log.sh, installed
2026-09-12) appends a bare [AUTO-STUB] block for EVERY commit, and the
owning run is supposed to backfill it with full detail (a "### AUTO-STUB
backfill" subsection naming the stub's hash, or a full "## ... - Iteration
(...)" entry covering the same commit). If the owning run dies between
commit and backfill (VM reboot, crash, timeout - observed 2026-10-13
06:27 PT when the drift-canary reboot orphaned mid-pass work), the stub
stays bare forever: the commit is present in the log but its detail is
lost, and nothing trips. check_stub_home_capture (79th) only asserts the
commit is PRESENT (hash or subject) - a bare stub satisfies it - so the
commit-without-log-DETAIL pattern recurs with no tripwire. The
orphaned-stub-detail class.

A stub counts as COVERED when any of these hold:
  - its 40-char commit hash appears anywhere else in the log (a backfill
    subsection or a full entry naming it), or
  - its subject appears in a full (non-[AUTO-STUB]) "## ... - Iteration
    (...)" header (the hook's own subject-dedupe semantics), or
  - its block already carries detail beyond the hook's bare 4-line
    template (some runs wrote the full entry inline but kept the
    [AUTO-STUB] header text - covered in spirit).

A bare, uncovered stub is ACTIONABLE while its detail is still
reconstructible (the owning run is recent): older than --fail-after-hours
(default 6 - the owning run backfills within minutes of its commit, so a
bare stub older than 6h means the run is gone) and within
--actionable-days (default 7). Actionable orphans HARD FAIL, mirroring
check_stub_home_capture's fail-closed treatment: the next commit is
blocked until the orphan is backfilled. Bare stubs older than the
actionable window are historical (detail no longer reconstructible);
they print as WARN advisories and are inventoried separately, never
blockers - failing on them would wedge the repo with no remediation path.

Checks (all static - one log scan, <1s on the 1.4MB log):
  S1 the canonical log exists and is readable at the hook's resolved path
     (${ITERATION_LOG:-$HOME/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/iteration-log.md})
     (missing/unreadable = exit 2 INFRA advisory, non-blocking; the hook
     itself skips silently when the log file is absent)
  S2 every "## <ts> - Iteration [AUTO-STUB] (<subject>)" header parses to
     a valid America/Los_Angeles timestamp in the hook's
     "+%Y-%m-%d %H:%M %Z" shape
     (unparseable = HARD FAIL: the aging contract depends on the hook's
     date format; a corrupted date in the logging backbone is loud)
  S3 no ACTIONABLE bare orphan exists (bare template shape + uncovered +
     6h < age <= 7d)
     (each = HARD FAIL naming timestamp, hash, subject, and the backfill
     remediation; historical orphans print as WARN advisories)

Usage:
  scripts/check_orphaned_stub_detail.py              # same checks
  scripts/check_orphaned_stub_detail.py --static-only # same checks

Exit: 0 = no actionable orphans; 1 = actionable orphan(s) (loud);
      2 = infra.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 11:30 - created (11:30 PT iteration). Closes the
    orphaned-stub-detail class: the stub mechanism (2026-09-12) plus the
    presence guard (79th, 2026-10-13 10:00) still allowed a commit whose
    log presence was ONLY the bare auto-stub forever. Six actionable
    orphans found and backfilled same run (2026-10-06/07/09); 39
    historical orphans inventoried advisory-only.
"""
import os
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REL_LOG = os.path.join(
    "workspace", "goals", "s-p-500-executive-compensation-tracker",
    "hidden_files", "iteration-log.md")

FAIL_AFTER_HOURS = 6
ACTIONABLE_DAYS = 7
LA = ZoneInfo("America/Los_Angeles")

STUB_HEADER_RE = re.compile(
    r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ([A-Z]{3,4})"
    r" - Iteration \[AUTO-STUB\] \((.*)\)$")
FULL_HEADER_RE = re.compile(
    r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} [A-Z]{3,4} - Iteration \((.*)\)$")
AUTO_COMMIT_RE = re.compile(
    r"^- Commit: `([0-9a-f]{40})` - auto-appended by the repo post-commit hook")
DETAIL_LINE = "Detail to be backfilled by the next scheduled run"


def resolve_log():
    override = os.environ.get("ITERATION_LOG")
    if override:
        return override
    return os.path.join(os.environ.get("HOME", ""), REL_LOG)


results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


static_only = "--static-only" in sys.argv  # noqa: F841 (contract literal)

LOG = resolve_log()

# S1: canonical log exists and is readable (hook's own skip-semantics)
if not os.path.isfile(LOG):
    print("INFRA: canonical iteration log not found at %s" % LOG)
    print("  (the post-commit hook skips silently when the log file is "
          "absent; not a commit blocker)")
    sys.exit(2)
try:
    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        log_lines = fh.read().splitlines()
except OSError as exc:
    print("INFRA: cannot read canonical iteration log %s: %s" % (LOG, exc))
    sys.exit(2)
check("S1 canonical log readable", True, LOG)

now = datetime.now(LA)
full_subjects = [m.group(1) for ln in log_lines
                 for m in [FULL_HEADER_RE.match(ln)] if m]

actionable = []
historical = []
unparseable = []

for i, ln in enumerate(log_lines):
    m = STUB_HEADER_RE.match(ln)
    if not m:
        continue
    ts_s, _abbr, subject = m.groups()

    # S2: timestamp must parse in the hook's date shape
    try:
        ts = datetime.strptime(ts_s, "%Y-%m-%d %H:%M").replace(tzinfo=LA)
    except ValueError:
        unparseable.append((ts_s, subject))
        continue

    # zone: lines until the next dated "## " header ("### " does not end it)
    zone = []
    for k in range(i + 1, len(log_lines)):
        if log_lines[k].startswith("## "):
            break
        zone.append(log_lines[k])

    # bare-template shape: the Detail-backfill line present, exactly the
    # two auto-appended bullets, no "### " subsection carrying detail
    has_detail_line = any(DETAIL_LINE in l for l in zone)
    bullets = sum(1 for l in zone if l.startswith("- "))
    subsect = any(l.startswith("### ") for l in zone)
    stub_hash = None
    stub_commit_line = None
    for off, l in enumerate(zone[:8]):
        hm = AUTO_COMMIT_RE.match(l)
        if hm:
            stub_hash = hm.group(1)
            stub_commit_line = i + 1 + off
            break
    if not (has_detail_line and bullets == 2 and not subsect):
        continue  # detailed inline or backfilled in-zone: covered

    # coverage: hash anywhere else in the log (excluding ONLY the stub's
    # own auto-appended Commit line - a tight exclusion, not a line
    # window, so an era-style detail section immediately after the stub
    # still counts), or subject in a full header
    if stub_hash:
        elsewhere = [l for k, l in enumerate(log_lines)
                     if k != stub_commit_line]
        if stub_hash in "\n".join(elsewhere):
            continue
    if any(subject in fs for fs in full_subjects):
        continue

    age = now - ts
    entry = (ts_s, subject, stub_hash)
    if age <= timedelta(hours=FAIL_AFTER_HOURS):
        continue  # owning run may still backfill
    elif age <= timedelta(days=ACTIONABLE_DAYS):
        actionable.append((entry, age))
    else:
        historical.append((entry, age))

if unparseable:
    for ts_s, subject in unparseable:
        print("FAIL: stub header has an unparseable timestamp %r "
              "(subject: %s...)" % (ts_s, subject[:60]))
    print("  The orphan-aging contract depends on the hook's "
          "'+%%Y-%%m-%%d %%H:%%M %%Z' date shape; fix the header date.")
    sys.exit(1)
check("S2 all stub timestamps parse", True,
      "%d stub headers" % sum(1 for ln in log_lines
                              if STUB_HEADER_RE.match(ln)))

for (ts_s, subject, stub_hash), age in historical:
    print("WARN: historical bare stub (age %.1fd, advisory only): %s %s %s..."
          % (age.total_seconds() / 86400, ts_s,
             (stub_hash[:12] if stub_hash else "?"), subject[:50]))

if actionable:
    check("S3 no actionable orphaned stub", False,
          "%d bare stub(s) past the %dh backfill window"
          % (len(actionable), FAIL_AFTER_HOURS))
    for (ts_s, subject, stub_hash), age in actionable:
        print("  ORPHAN: %s (age %.1fh) commit %s" %
              (ts_s, age.total_seconds() / 3600,
               stub_hash if stub_hash else "?"))
        print("    subject: %s" % subject[:100])
    print("  Fix: backfill each orphan (a '### AUTO-STUB backfill' subsection "
          "naming 'Stub <ts> / commit `<hash>`' with the run's detail - "
          "reconstructible from 'git show <hash>'), then re-run this guard.")
    sys.exit(1)

check("S3 no actionable orphaned stub", True,
      "0 bare stubs older than %dh within the %d-day actionable window"
      % (FAIL_AFTER_HOURS, ACTIONABLE_DAYS)
      + ("; %d historical inventoried advisory-only" % len(historical)
         if historical else ""))
sys.exit(0)
