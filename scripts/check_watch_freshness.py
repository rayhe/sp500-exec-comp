#!/usr/bin/env python3
"""Regression guard: EDGAR deferral-watch re-verification must not go stale (85th).

The dataset's completeness claim rests on three open deferrals: VMRK's
post-merger DEF 14A (CIK 906107 - the one roster company whose filing_url is
empty), PSKY/FDXF's first-ever DEF 14A (CIK 2041610 / 2082247 - no proxy ever
filed), and the FY2025 granular-detail study watch (AP/Equilar publish
headline medians only). Each iteration re-verifies them via EDGAR
data.sec.gov and records "(last checked ... PT)" / "(last search ... PT)"
timestamps in the iteration log's next-run candidates - but "re-check
periodically" is a hand-written convention, the same hand-convention pattern
the 82nd guard closed for log-prose numbers, the 83rd closed for the canary
cadence, and the 84th closed for the deploy currency check.

Failure mode: if the loop stops re-verifying the watches (a run skips them,
the cadence slips from hours to days), a newly filed DEF 14A sits
un-ingested while every guard stays green. The "99.53% DEF 14A-verified /
517 enriched" headline slowly rots with no fail-closed tripwire - the
watches' watchdog is missing, and nothing notices.

This guard pins the re-verification cadence itself, fail-closed at commit
time: every watch recheck asserted in the latest full iteration-log entry
must be within WATCH_STALE_HOURS of the commit. The guard pins cadence
only - the actual EDGAR re-verification stays the iteration run's job,
mirroring check_canary_freshness.py (83rd).

Checks (all static - one local file read, no network):
  S1 canonical iteration log exists and is readable
     (missing/unreadable -> exit 2 INFRA advisory, non-blocking, per the
     pre-commit contract; a deleted log must not wedge commits)
  S2 the latest full "## ... - Iteration" entry is found (excluding
     [AUTO-STUB] headers, so a trailing bare stub never becomes the audit
     target - same convention as check_log_prose_numbers.py)
     (no full entry -> exit 2 INFRA advisory)
  S3 every line in that entry carrying a "last checked" / "last search"
     recheck assertion carries a parseable PT timestamp within
     WATCH_STALE_HOURS (fresh -> PASS; stale -> HARD FAIL naming the
     watch line, the hours-since, and the remediation: re-verify via
     EDGAR data.sec.gov and refresh the timestamp). The candidates list
     packs several watches onto ONE line, so each marker occurrence is
     audited separately against the text up to the next marker - a stale
     second watch on a line whose first watch is fresh still fails. A
     recheck marker with no parseable timestamp, or an entry with no
     recheck markers at all, prints a WARN advisory and passes - the
     guard verifies the assertion when made and does not pin prose format
     (same deliberate tradeoff as check_log_prose_numbers.py's no-marker
     WARN). A timestamp more than 1h in the future prints a WARN
     (probable typo; it would otherwise silently extend the freshness
     window).

Timestamp formats accepted: "last checked 2026-10-13 ~18:05 PT",
"last checked ~18:05 PT" (date falls back to the entry header's date;
if the resulting PT datetime is in the future, one day is subtracted -
the midnight-crossover disambiguation), "last search rejected
2026-10-13 ~15:36 PT". PT is interpreted as America/Los_Angeles.

Usage:
  scripts/check_watch_freshness.py              # same checks
  scripts/check_watch_freshness.py --static-only # same checks
  (ITERATION_LOG env var overrides the canonical log path - used by
  negative tests)

Exit: 0 = all asserted watches fresh (or no assertions to audit);
      1 = a watch assertion is stale (loud);
      2 = log/entry unreadable (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 22:00 - created (22:00 PT iteration). Closes the
    watch-staleness class: the VMRK post-merger DEF 14A watch, the
    PSKY/FDXF first-proxy watches, and the FY2025 granular-detail search
    watch were re-verified "periodically" by hand-convention only; a
    slipped cadence would let a newly filed DEF 14A sit un-ingested with
    every guard green. Negative tests (all in /tmp, real tree untouched):
    fresh fixture (2h) -> rc=0; stale fixture (30h) -> rc=1 naming hours
    + remediation; time-only stamp on entry date -> rc=0; missing log ->
    rc=2 infra; unparseable marker timestamp -> rc=0 WARN; entry with no
    markers -> rc=0 WARN; future timestamp -> rc=0 with future-WARN; shared-line
    fixture with the SECOND watch stale -> rc=1 (per-marker segmentation);
    stub-tailed log audits the full entry before the stub.
"""
import datetime
import os
import re
import sys

try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except Exception:  # pragma: no cover - ancient interpreters only
    PT = datetime.timezone(datetime.timedelta(hours=-7))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REL_LOG = os.path.join(
    "workspace", "goals", "s-p-500-executive-compensation-tracker",
    "hidden_files", "iteration-log.md")

WATCH_STALE_HOURS = 24  # the loop runs 5+ iterations/day; October is
# proxy off-season, so a full day without a re-verification means the
# cadence slipped and the next commit must not land silently.

ENTRY_RE = re.compile(
    r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} [A-Z]+ - Iteration (?!\[AUTO-STUB\])",
    re.M)
ENTRY_DATE_RE = re.compile(
    r"^## (\d{4}-\d{2}-\d{2}) \d{2}:\d{2} [A-Z]+ - Iteration", re.M)
MARKER_RE = re.compile(r"last\s+(?:checked|search)", re.I)
TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})?\s*~?\s*(\d{1,2}):(\d{2})\s*PT")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def warn(msg):
    print("WARN: " + msg)


static_only = "--static-only" in sys.argv  # noqa: F841 (contract literal)


def resolve_log():
    override = os.environ.get("ITERATION_LOG")
    if override:
        return override
    return os.path.join(os.environ.get("HOME", ""), REL_LOG)


def parse_watch_ts(line, entry_date):
    """Parse the first PT timestamp on a recheck-marker line.

    Returns an aware datetime, or None when the line's timestamp does
    not parse. A date-less stamp falls back to the entry header's date;
    a result in the future is disambiguated back one day (midnight
    crossover between the recheck and the log write).
    """
    m = TS_RE.search(line)
    if not m:
        return None
    date_s, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
    if hh > 23 or mm > 59:
        return None
    dateless = date_s is None
    if dateless:
        date_s = entry_date
    if date_s is None:
        return None
    try:
        naive = datetime.datetime.strptime(
            "%s %02d:%02d" % (date_s, hh, mm), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    ts = naive.replace(tzinfo=PT)
    now = datetime.datetime.now(PT)
    if dateless and ts > now:
        # midnight crossover: a dateless stamp later than now belongs to
        # the previous day (the recheck preceded the log write). An
        # explicitly dated future stamp is left alone so the future-WARN
        # in main() can flag the probable typo instead of masking it.
        ts = ts - datetime.timedelta(days=1)
    return ts


def main(argv):
    log_path = resolve_log()

    # S1: canonical log readable (INFRA on any read failure - fail-open so
    # a missing log cannot wedge commits)
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            log_text = fh.read()
    except (OSError, FileNotFoundError) as exc:
        print("INFRA: cannot read canonical iteration log %s: %s "
              "(advisory only)" % (log_path, exc))
        return 2
    check("S1 canonical log readable", True, log_path)

    # S2: latest full entry found (stub headers excluded)
    entries = list(ENTRY_RE.finditer(log_text))
    if not entries:
        print("INFRA: no full iteration entry found in %s "
              "(advisory only)" % log_path)
        return 2
    last = entries[-1]
    end = log_text.find("\n## ", last.start() + 1)
    entry_text = log_text[last.start():] if end == -1 else log_text[last.start():end]
    date_m = ENTRY_DATE_RE.match(entry_text)
    entry_date = date_m.group(1) if date_m else None
    check("S2 latest full entry found", True,
          "entry dated %s" % (entry_date or "unknown"))

    # S3: every asserted recheck is fresh. The candidates list packs several
    # watches onto one line, so each "last checked"/"last search" marker
    # is audited separately against the text up to the next marker - a
    # stale second watch on a line whose first watch is fresh still fails.
    now = datetime.datetime.now(PT)
    stale = []
    warned = 0
    asserted = 0
    for line in entry_text.splitlines():
        spans = list(MARKER_RE.finditer(line))
        for i, sp in enumerate(spans):
            seg_end = spans[i + 1].start() if i + 1 < len(spans) else len(line)
            segment = line[sp.start():seg_end]
            asserted += 1
            ts = parse_watch_ts(segment, entry_date)
            if ts is None:
                warn("recheck marker with unparseable timestamp is not "
                     "freshness-auditable (advisory): %s" % segment.strip()[:100])
                warned += 1
                continue
            if ts > now + datetime.timedelta(hours=1):
                warn("recheck timestamp more than 1h in the future (probable "
                     "typo; advisory): %s" % segment.strip()[:100])
                warned += 1
            age_h = (now - ts).total_seconds() / 3600.0
            if age_h > WATCH_STALE_HOURS:
                stale.append((segment.strip()[:110], age_h))
    if asserted == 0:
        warn("latest full entry asserts no watch re-verifications; "
             "nothing to freshness-audit (advisory)")
        check("S3 watch assertions fresh", True, "no assertions made")
        return 0
    if stale:
        for line_text, age_h in stale:
            check("watch-freshness", False,
                  "STALE %.1fh ago (threshold %dh): %s - re-verify via "
                  "EDGAR data.sec.gov and refresh the 'last checked' "
                  "timestamp" % (age_h, WATCH_STALE_HOURS, line_text))
        return 1
    check("S3 watch assertions fresh", True,
          "%d asserted recheck(s) within %dh%s" %
          (asserted, WATCH_STALE_HOURS,
           "; %d warning(s)" % warned if warned else ""))
    return 0


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
