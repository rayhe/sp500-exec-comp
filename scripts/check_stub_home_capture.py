#!/usr/bin/env python3
"""Regression guard: the canonical iteration log must contain the HEAD commit.

The post-commit hook (scripts/post-commit-iteration-log.sh, installed
2026-09-12) appends an [AUTO-STUB] to the canonical iteration log for EVERY
commit. But the hook resolves the log path as
${ITERATION_LOG:-$HOME/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/iteration-log.md}:
a commit made with HOME overridden (the IPv6-push recipe exports HOME=$TMPHOME
for its temp gitconfig, per the 2026-10-11 AGENTS.md entry) sends the stub
into the throwaway temp home - voided silently. The hook never fails, the
canonical log loses the commit entry, and nothing trips. AGENTS.md documents
the manual mitigation (write the iteration-log entry in the same run; do not
rely on the hook stub), but until this guard nothing VERIFIED the capture.
The commit-without-log-entry pattern the hook was installed to kill can recur
through the HOME-override path with no tripwire - the post-commit-stub
home-void class.

This guard asserts the capture itself: at commit time, the current HEAD
commit (the commit that just landed) must be present in the canonical log,
either by hash or by the hook's own subject-dedupe semantics (a "## " header
line containing the subject). A voided stub from a prior HOME-override
commit fails loudly at the NEXT commit, forcing backfill before more
unlogged work piles up - the same fail-closed treatment check_remote_branch_sync
gives a prior run's partial push.

Checks (all static - small file reads + two git calls, <0.5s):
  S1 the canonical log exists at the hook's resolved path
     (missing = exit 2 infra advisory, non-blocking; the hook itself skips
     silently when the log file is absent, and a broken checkout must not
     wedge every commit)
  S2 HEAD's hash is present in the log (stub or backfilled entry), OR a
     "## " header line contains HEAD's subject (the hook's dedupe semantics:
     an amend keeps the subject but changes the hash, and must not demand a
     second stub)
     (neither = HARD FAIL naming the void-stub cause and the backfill fix)

Usage:
  scripts/check_stub_home_capture.py              # same checks
  scripts/check_stub_home_capture.py --static-only # same checks

Exit: 0 = captured; 1 = voided/missing stub (loud); 2 = infra.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 10:00 - created (10:00 PT iteration). Closes the
    post-commit-stub home-void class; the pre-commit twin was closed
    2026-10-08 by check_hook_copy_sync and the installed-copy side
    2026-10-13 by check_postcommit_hook_sync, but neither asserted the stub
    actually landed in the canonical log.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REL_LOG = os.path.join(
    "workspace", "goals", "s-p-500-executive-compensation-tracker",
    "hidden_files", "iteration-log.md")


def resolve_log():
    override = os.environ.get("ITERATION_LOG")
    if override:
        return override
    return os.path.join(os.environ.get("HOME", ""), REL_LOG)


def git(args):
    return subprocess.run(["git"] + args, cwd=REPO, capture_output=True,
                          text=True, timeout=15)


results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


static_only = "--static-only" in sys.argv  # noqa: F841 (contract literal)

LOG = resolve_log()

# S1: canonical log exists (hook's own skip-semantics: missing log = advisory)
if not os.path.isfile(LOG):
    print("INFRA: canonical iteration log not found at %s" % LOG)
    print("  (the post-commit hook skips silently when the log file is absent; "
          "not a commit blocker)")
    sys.exit(2)

try:
    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        log_text = fh.read()
except OSError as exc:
    print("INFRA: cannot read canonical iteration log %s: %s" % (LOG, exc))
    sys.exit(2)
check("S1 canonical log readable", True, LOG)

# S2: HEAD captured by hash or by the hook's subject-dedupe semantics
head_hash = git(["rev-parse", "HEAD"]).stdout.strip()
subject = git(["log", "-1", "--format=%s"]).stdout.strip()
if not head_hash or not subject:
    print("INFRA: cannot resolve HEAD (not a git checkout?)")
    sys.exit(2)

if head_hash in log_text:
    check("S2 HEAD stub captured", True,
          "hash %s present in canonical log" % head_hash[:12])
    sys.exit(0)

subject_covered = False
for line in log_text.splitlines():
    if line.startswith("## ") and subject in line:
        subject_covered = True
        break
if subject_covered:
    check("S2 HEAD stub captured", True,
          "subject covered by a log header (hook dedupe semantics)")
    sys.exit(0)

print("FAIL: HEAD commit %s ('%s') has NO stub in the canonical log %s"
      % (head_hash[:12], subject, LOG))
print("  Likely cause: the commit was made with HOME overridden (the "
      "IPv6-push recipe exports HOME=$TMPHOME for its temp gitconfig), so "
      "the post-commit hook's auto-stub was written into the throwaway temp "
      "home and voided. The hook never fails, so this is silent without "
      "this guard.")
print("  Fix: backfill the iteration-log entry for this commit (full entry "
      "replacing the [AUTO-STUB] header), then re-run this guard.")
sys.exit(1)
