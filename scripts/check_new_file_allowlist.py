#!/usr/bin/env python3
"""Regression guard: newly staged files must match the intentional-new-file allowlist.

`git add -A` stages every new file in the working tree; .gitignore covers
only __pycache__/ and *.pyc (the 2026-09-18 .pyc sweep that shipped a
compiled file into the public repo is the precedent). The 88th guard
(check_staged_size.py) closed the LARGE-file variant of the sweep - HARD
FAIL on newly staged files > 1 MiB - but a SMALL scratch file (a fixture
leftover, a /tmp-style data dump, an editor backup, a stray CSV or a 2KB
scratch JSON) passes the size guard and would be swept into the PUBLIC
repo with the run's unrelated commit message. The only tripwire was the
run author's eyeball on `git status` before add -A: the same hand-convention
pattern the 82nd/86th/87th/88th guards closed. The add-A
small-scratch-sweep class.

This guard asserts the sweep population itself, statically: every file
newly added to the index (git diff --cached --diff-filter=A, exactly the
population `git add -A` sweeps in) must match the intentional-new-file
allowlist below. A future legitimate new-file class is fail-closed on
purpose: extend the allowlist deliberately, never silently sweep it.

Allowlist (intentional new-file classes observed in this repo's history):
  1. scripts/<name>.py - deliberate placement: every scripts/*.py addition
     in the repo's history is a pipeline tool or guard (check_* guards,
     peer_batch* extractors, dq_tripwire, drift_canary, ...). A file placed
     in scripts/ is an intentional tool by construction; scratch work
     belongs elsewhere.
  2. the DQ-batch backup convention _backup_YYYYMMDD_HHMM (same regex as
     the 88th guard): data/*_backup_*.json and hidden_files/*_backup_*.json
     are deliberately tracked pre-repair snapshots.
  3. hidden_files/ repair/batch utility scripts (apply_*, sync_*,
     repair_*, phantom_*, fix_*, ceo_*, mark_verified_*, peer_*) -
     one-off utilities deliberately tracked as provenance.
  4. hidden_files/drift_canary_full_YYYYMMDD_HHMM.log - canary full logs
     teed to hidden_files/ per the iteration-log convention.
  5. site-root robots.txt + sitemap.xml (220th review) - crawler files
     for the Pages site, named individually like the og-image precedent.

Checks (all static - one git call, <0.5s):
  S1 enumerate newly staged files
     (git diff --cached --name-only -z --diff-filter=A; git itself
     failing -> exit 2 INFRA advisory, non-blocking)
  S2 HARD FAIL naming every non-allowlisted new file and the fix
     (git rm --cached <path>, or extend the allowlist deliberately)

Usage:
  scripts/check_new_file_allowlist.py              # same checks
  scripts/check_new_file_allowlist.py --static-only # same checks
  scripts/check_new_file_allowlist.py --repo PATH  # fixture repo

Exit: 0 = sweep population clean; 1 = sweep risk (loud); 2 = infra.

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-14 07:30 - created (07:30 PT iteration). Closes the add-A
    small-scratch-sweep class; the 88th guard (check_staged_size.py)
    closed only the >1MiB variant, leaving small scratch files sweepable
    with no tripwire but the run author's eyeball.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWLIST = [
    # 1. deliberate placement: new pipeline tools and guards in scripts/
    re.compile(r"^scripts/[a-z][a-z0-9_]*\.py$"),
    # 2. DQ-batch backup convention (same regex as the 88th guard, verbatim)
    re.compile(r"_backup_\d{8}_\d{4}"),
    # 3. repair/batch utility scripts tracked as provenance
    re.compile(r"^hidden_files/(apply|sync|repair|phantom|fix|ceo|mark_verified|peer)_[a-z0-9_]+\.py$"),
    # 4. canary full logs teed to hidden_files/ (iteration-log convention)
    re.compile(r"^hidden_files/drift_canary_full_\d{8}_\d{4}\.log$"),
    # 5. guard-run proof ledger (91st guard: appended by the pre-commit hook
    #    on every green run; tracked as provenance)
    re.compile(r"^hidden_files/guard_runs\.jsonl$"),
    # 6. site-root social preview image (217th review, 2026-10-25): the
    #    deliberate 1200x630 PNG referenced by og:image + twitter:image in
    #    index.html. A single named asset, not a new file class.
    re.compile(r"^og-image\.png$"),
    # 7. site-root crawler files (220th review, 2026-10-25): robots.txt +
    #    sitemap.xml for the Pages site, completing the search surface
    #    (canonical + description + OG set came in the 212th-219th reviews).
    #    Two single named files, not a new file class.
    re.compile(r"^robots\.txt$"),
    re.compile(r"^sitemap\.xml$"),
]

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _git(repo, *args):
    """Return (rc, stdout_bytes, stderr_str) of a git invocation."""
    try:
        p = subprocess.run(
            ["git", "-C", repo] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, b"", "git invocation failed: %s" % e
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")


def main(argv):
    if "--static-only" in sys.argv:  # noqa: F841 - contract marker, same checks
        pass
    repo = REPO
    if "--repo" in argv:
        repo = argv[argv.index("--repo") + 1]

    # S1: enumerate newly staged files (exactly the add-A sweep population).
    rc, out, err = _git(repo, "diff", "--cached", "--name-only", "-z",
                        "--diff-filter=A")
    if rc != 0:
        print("INFRA: new-file-allowlist: git diff --cached failed (rc=%d): %s"
              % (rc, err.strip()[:200]))
        return 2
    staged = [p for p in out.decode("utf-8", "replace").split("\0") if p]

    # S2: every newly staged file must be allowlisted.
    bad = [p for p in staged
           if not any(pat.search(p) for pat in ALLOWLIST)]
    for p in bad:
        print("FAIL: new-file-allowlist: newly staged file %r matches no "
              "intentional-new-file allowlist entry - add-A would sweep it "
              "into the public repo; remove it from the index "
              "(git rm --cached <path>) or extend the allowlist "
              "deliberately" % p)
    if bad:
        check("sweep-population-allowlisted", False,
              "%d non-allowlisted new file(s)" % len(bad))
        return 1
    check("sweep-population-allowlisted", True,
          "%d new file(s) all allowlisted" % len(staged))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
