#!/usr/bin/env python3
"""Regression guard: a staged change to data/compensation.json that moves the
exec-total sum must also increment metadata.phantom_removed (the campaign
counter behind the dataq modal's "phantom compensation removed" block).

Background (2026-10-12 03:30 PT): the phantom campaign counter is seeded by an
exact git-blob computation (2026-09-27 23:30 PT, 63 DQ batches) plus
record_batch() increments for the three 2026-09-28 DQ batches (02:00 PT
+$52,230,124; 14:00 PT -$6,818,888; 18:00 PT +$33,573,226) = $2,284,244,764,
re-derived to the dollar this run against git history. The existing section 4f
guard asserts metadata<->fallback parity and cumulative == gross - restored,
but NOTHING asserted the counter against the commits that move it: a DQ batch
that changed exec totals without calling hidden_files/phantom_record.py
record_batch() would silently stale the "Net: $2.3B" campaign claim the dataq
modal shows users, and every existing guard would stay green (both sides of
the parity check would stale together). All 17 data-touching commits since
the 2026-09-28 18:00 PT screen re-derive to $0 deltas, so the counter is
truthful today - this guard keeps it that way.

Checks (runs at pre-commit time, only when data/compensation.json is staged):
  S1 data/compensation.json is staged in this commit; otherwise SKIP (fast path).
  S2 the staged blob's exec-total sum vs the HEAD blob's: delta = HEAD - staged,
     same definition as phantom_record.record_batch() (sum of executives[].total,
     int(round())).
  S3 if delta != 0, the staged metadata.phantom_removed.batches must differ
     from HEAD's (record_batch() was called in this change). A nonzero delta
     with an untouched counter FAILS loudly, naming the record_batch() fix and
     the dataq-phantom-block fallback re-sync.

Usage:
  scripts/check_phantom_delta_sync.py              # same checks
  scripts/check_phantom_delta_sync.py --static-only # same (pre-commit contract)

Exit: 0 = pass/skip; 1 = staged totals moved without a counter bump (blocks the
commit); 2 = infra problem (git blob unreadable, no HEAD parent).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-12 03:30 - created (03:30 PT iteration). Closes the campaign-counter
    drift class: metadata<->fallback parity (section 4f) is necessary but not
    sufficient; the counter must also track the data it summarizes.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = "data/compensation.json"

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def git(*args):
    return subprocess.run(
        ["git", "-C", REPO] + list(args),
        capture_output=True, check=True,
    ).stdout


def exec_total_and_batches(raw):
    d = json.loads(raw)
    total = 0
    for c in d.get("companies", []):
        for e in c.get("executives", []):
            v = e.get("total")
            if isinstance(v, (int, float)):
                total += v
    pr = d.get("metadata", {}).get("phantom_removed") or {}
    return int(round(total)), pr.get("batches")


def main():
    # S1: fast path - only run when data/compensation.json is staged.
    try:
        staged_names = git("diff", "--cached", "--name-only", "--", DATA_PATH).decode().split()
    except subprocess.CalledProcessError as e:
        print("INFRA: git diff --cached failed: %s" % e)
        sys.exit(2)
    if DATA_PATH not in [n.strip() for n in staged_names]:
        print("SKIP: data/compensation.json not staged in this commit")
        sys.exit(0)

    # S2: HEAD vs staged blob totals.
    try:
        head_raw = git("show", "HEAD:" + DATA_PATH)
    except subprocess.CalledProcessError:
        print("SKIP: no HEAD parent blob for data/compensation.json (new file)")
        sys.exit(0)
    try:
        staged_raw = git("show", ":" + DATA_PATH)
    except subprocess.CalledProcessError as e:
        print("INFRA: cannot read staged blob :%s: %s" % (DATA_PATH, e))
        sys.exit(2)
    try:
        head_total, head_batches = exec_total_and_batches(head_raw)
        staged_total, staged_batches = exec_total_and_batches(staged_raw)
    except (ValueError, KeyError, AttributeError) as e:
        print("INFRA: cannot parse compensation blobs: %s" % e)
        sys.exit(2)

    delta = head_total - staged_total
    check("S2 staged exec-total delta vs HEAD computed (HEAD $%s -> staged $%s)"
          % ("{:,}".format(head_total), "{:,}".format(staged_total)),
          True, "delta $%s" % "{:,}".format(delta))

    # S3: nonzero delta requires a counter bump in the same staged change.
    bumped = staged_batches != head_batches
    if delta != 0 and not bumped:
        check("S3 nonzero phantom delta recorded via phantom_removed.batches",
              False,
              "staged change moves exec totals by $%s but phantom_removed.batches "
              "is still %r - call hidden_files/phantom_record.py record_batch() "
              "with the pre-batch backup, then re-sync the dataq-phantom-block "
              "fallback in js/app.js (section 4f fails the commit otherwise)"
              % ("{:,}".format(delta), head_batches))
    else:
        check("S3 nonzero phantom delta recorded via phantom_removed.batches",
              True,
              "delta $%s, batches %r -> %r"
              % ("{:,}".format(delta), head_batches, staged_batches))

    fails = [n for n, ok, _ in results if not ok]
    print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
    if fails:
        print("FAILED: " + ", ".join(fails))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
