#!/usr/bin/env python3
"""Regression guard: every landed commit must carry proof the pre-commit guard suite ran for it.

Closes the hook-bypass / guard-run-proof class (2026-10-14 10:00 PT iteration,
91st guard): the pre-commit hook can be skipped entirely with
`git commit --no-verify`, and a fresh clone where the hook was never installed
runs zero guards (check_hook_copy_sync S1 treats a missing installed hook as a
mere exit-2 advisory, not a blocker). Until now the only tripwire was the run
author's hand-convention - the commit recipe never passes --no-verify - so a
bypassed commit would land with all 90 guards silently unrun and every guard
green by definition.

Mechanism (see the GUARD-RUN PROOF tail section of scripts/pre-commit-guards.sh):
on every green pre-commit run the hook appends one JSON line to
hidden_files/guard_runs.jsonl recording the staged tree it approved
(parent HEAD sha + `git write-tree` output + guard count + hook sha256 + UTC
timestamp). This guard audits the landed history: every commit newer than the
ledger's first (epoch) marker must have a matching (parent, tree) marker. A
commit with no marker landed without the suite -> HARD FAIL naming it. The
(parent, tree) key is sound: a marker for (P, T) proves the hook approved tree
T on top of parent P, so any commit sharing the key is content-identical to
what the suite approved (message/timestamp/author metadata is not
guard-scanned and is out of scope).

Checks (all static - git reads and one small file read, no network):
  S1 the proof ledger is readable (working-tree copy first, then HEAD's
     committed copy); missing or empty -> exit 2 infra advisory (the system
     is not bootstrapped yet; this must not wedge the seeding commit's own
     pre-commit run)
  S2 the ledger's first line identifies the epoch commit (the commit whose
     pre-commit run created the ledger); every commit in (epoch, HEAD] has a
     matching (parent, tree) marker, else HARD FAIL naming each unproven
     commit with its subject

Exit: 0 = every audited commit proven; 1 = unproven commit(s) in the window,
      corrupt ledger line, or epoch marker not found in history (history
      rewrite - fail closed); 2 = infra (no ledger yet, git failure).

Remediation for a HARD FAIL: do NOT just re-commit. Inspect the named
commit's diff, run the full guard suite against its tree by hand (every
scripts/check_*.py in full mode), and only then backfill a marker line with
an extra {"backfilled": true, ...} field - or revert the commit. After a
history rewrite, delete the ledger and let the next green pre-commit run
re-seed a new epoch.

Usage:
  scripts/check_hook_run_proof.py              # same checks
  scripts/check_hook_run_proof.py --static-only # same checks
  scripts/check_hook_run_proof.py --repo PATH  # fixture repo

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-14 10:00 - created (10:00 PT iteration). Closes the hook-bypass
    class; the 91st guard script.
"""
import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_REL = os.path.join("hidden_files", "guard_runs.jsonl")

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _git(repo, *args):
    """Return (rc, stdout_str, stderr_str) of a git invocation; (None,...) on exception."""
    try:
        p = subprocess.run(["git", "-C", repo] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=30)
    except Exception as e:
        return None, "", "exception: %s" % e
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace").strip())


def _read_ledger(repo):
    """Return (lines, source) or (None, reason). Working tree first, then HEAD's committed copy."""
    wt = os.path.join(repo, LEDGER_REL)
    if os.path.isfile(wt):
        try:
            with open(wt, "r", encoding="utf-8") as f:
                return f.read().splitlines(), "working tree"
        except OSError as e:
            return None, "working-tree ledger unreadable: %s" % e
    rc, out, err = _git(repo, "show", "HEAD:" + LEDGER_REL)
    if rc == 0:
        return out.splitlines(), "HEAD committed copy"
    return None, "no ledger in working tree nor at HEAD"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--repo", default=REPO)
    args = ap.parse_args()
    repo = args.repo

    # S1: ledger readable
    raw, source = _read_ledger(repo)
    if raw is None:
        print("INFRA: hook-run-proof: %s" % source)
        print("INFRA: proof ledger not bootstrapped yet (the seeding commit's own")
        print("INFRA: pre-commit run creates it) - advisory only, not blocking")
        return 2
    lines = [l for l in raw if l.strip()]
    if not lines:
        print("INFRA: hook-run-proof: ledger (%s) is empty - not bootstrapped" % source)
        return 2
    markers = []
    for i, line in enumerate(lines):
        try:
            m = json.loads(line)
        except json.JSONDecodeError as e:
            print("FAIL: hook-run-proof: ledger line %d is corrupt (%s): %.80r"
                  % (i + 1, e, line))
            print("FAIL: hook-run-proof: the proof store is damaged - failing closed;")
            print("FAIL: hook-run-proof: inspect %s before committing" % LEDGER_REL)
            return 1
        if not isinstance(m, dict) or "parent" not in m or "tree" not in m:
            print("FAIL: hook-run-proof: ledger line %d lacks parent/tree fields: %.80r"
                  % (i + 1, line))
            return 1
        markers.append(m)
    check("ledger-readable", True, "%d marker(s) from %s" % (len(markers), source))

    # S2: locate the epoch commit (first marker's (parent, tree)) in history
    ep, et = markers[0]["parent"], markers[0]["tree"]
    rc, out, err = _git(repo, "log", "--format=%H%x00%P%x00%T%x00", "HEAD")
    if rc != 0:
        print("INFRA: hook-run-proof: git log failed: %s" % err)
        return 2
    fields = out.split("\x00")
    if fields and fields[-1] == "":
        fields.pop()
    recs = []  # newest-first: (sha, parent, tree)
    for i in range(0, len(fields), 3):
        triple = fields[i:i + 3]
        if len(triple) != 3:
            break
        recs.append(tuple(triple))
    epoch_idx = None
    for i, (sha, par, tree) in enumerate(recs):
        if (par if par else "root") == ep and tree == et:
            epoch_idx = i
            break
    if epoch_idx is None:
        print("FAIL: hook-run-proof: epoch marker (parent=%.12s tree=%.12s) matches no commit"
              % (ep, et))
        print("FAIL: hook-run-proof: in HEAD's history - history was rewritten or the ledger")
        print("FAIL: hook-run-proof: is from another lineage; failing closed. Remediation: delete")
        print("FAIL: hook-run-proof: %s and let the next green pre-commit run re-seed a new epoch"
              % LEDGER_REL)
        return 1
    audited = recs[:epoch_idx]  # commits strictly newer than the epoch
    proof_keys = set((m["parent"], m["tree"]) for m in markers)
    missing = []
    for sha, par, tree in audited:
        if ((par if par else "root"), tree) not in proof_keys:
            missing.append(sha)
    if missing:
        print("FAIL: hook-run-proof: %d commit(s) landed with no guard-run proof "
              "(bypassed via --no-verify or committed where the hook was not installed):"
              % len(missing))
        for sha in missing:
            rc2, subj, _ = _git(repo, "log", "-1", "--format=%h %s", sha)
            print("FAIL: hook-run-proof:   unproven commit %s"
                  % (subj.strip() if rc2 == 0 else sha))
        print("FAIL: hook-run-proof: remediation: inspect each diff, run the full guard suite")
        print("FAIL: hook-run-proof: against its tree by hand, then backfill a marker with")
        print("FAIL: hook-run-proof: {\"backfilled\": true} - or revert the commit. Blocking.")
        check("all-audited-commits-proven", False, "%d unproven" % len(missing))
        return 1
    check("all-audited-commits-proven", True,
          "%d commit(s) newer than epoch all carry proof" % len(audited))
    return 0


if __name__ == "__main__":
    sys.exit(main())
