#!/usr/bin/env python3
"""Regression guard: newly staged files must not be oversized (add-A-sweep class).

`git add -A` stages every new file in the working tree. .gitignore covers only
__pycache__/ and *.pyc (the 2026-09-18 __pycache__ sweep that shipped a .pyc
into the public repo), and the 86th guard (check_secret_leak.py) covers only
secrets in staged content - a scratch data dump, screenshot, editor backup, or
any other stray file written into the repo tree by a run would commit and push
to the PUBLIC repo with every other guard green and no tripwire at all. The
only tripwire was the run author's eyeball on `git status` before add -A, a
hand-convention, the same hand-convention pattern the 82nd guard closed for
log-prose numbers, the 86th for staged secrets, and the 87th for git identity.

This guard lists files NEWLY added to the index (git diff --cached
--diff-filter=A, exactly the population `git add -A` sweeps in) and HARD
FAILs the commit when any exceeds 1 MiB unless its path matches the
intentional-large-file allowlist (the DQ-batch backup convention
_backup_YYYYMMDD_HHMM_, e.g. data/compensation_backup_*.json and the
hidden_files/*_backup_*.json family, which are deliberately tracked).
Sizes come from the staged blob (`git cat-file -s :0:<path>`), so file
content is never read (binary-safe by construction). A future legitimate
large new file is fail-closed on purpose: extend the allowlist deliberately,
never silently sweep it.

Checks (all static - local git reads only, no network):
  S1 the staged new-file list is readable (git diff --cached works)
  S2 every newly staged file is <= 1 MiB or backup-allowlisted
     (oversize or unreadable staged blob -> HARD FAIL naming the path,
     the size, and the remediation)
  git itself failing (not a repo, git missing) -> exit 2 INFRA advisory,
  not a commit blocker, per the pre-commit contract.

Usage:
  scripts/check_staged_size.py
  scripts/check_staged_size.py --static-only
  scripts/check_staged_size.py --repo PATH   # fixture repos (negative tests)

Exit: 0 = no oversized unallowlisted new files; 1 = sweep risk (loud);
      2 = git failed (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-14 03:30 - created (03:30 PT iteration). Closes the add-A-sweep
    class: the eyeball on `git status` before `git add -A` had no
    fail-closed verifier, so a stray large scratch file would publish to
    the public repo with every guard green (the 86th guard covers secrets
    only; .gitignore covers only __pycache__/*.pyc; the 2026-09-18 .pyc
    sweep is the precedent).
"""
import re
import subprocess
import sys

THRESHOLD = 1048576  # 1 MiB
# Intentional-large-file convention: DQ-batch backups, deliberately tracked.
ALLOWLIST = re.compile(r"_backup_\d{8}_\d{4}")

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _git(repo, *args):
    """Return (rc, stdout_bytes, stderr_str) of a git invocation.

    rc None means git itself could not be invoked (infra), distinct from a
    git-level failure (nonzero rc with stderr explaining).
    """
    try:
        p = subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return (None, b"", "git invocation failed: %s" % e)
    return (p.returncode, p.stdout or b"",
            (p.stderr or b"").decode("utf-8", "replace").strip())


def _staged_new_files(repo):
    """Return (rc, [paths]) of files newly added to the index, NUL-split."""
    rc, out, err = _git(repo, "diff", "--cached", "--name-only", "-z",
                        "--diff-filter=A")
    if rc is None or rc != 0:
        return (rc, err)
    return (0, [f for f in out.split(b"\x00") if f])


def _staged_size(repo, raw_path):
    """Return the staged blob size in bytes, or None when unreadable.

    Uses the :0:<path> index rev so the size reflects exactly what would be
    committed, even if the worktree copy changed after staging. Content is
    never read, so binary files are safe.
    """
    path = raw_path.decode("utf-8", "replace")
    rc, out, _ = _git(repo, "cat-file", "-s", ":0:" + path)
    if rc is None or rc != 0:
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def main(argv):
    repo = "."
    args = list(argv)
    if "--repo" in args:
        i = args.index("--repo")
        if i + 1 < len(args):
            repo = args[i + 1]

    # S1: the staged new-file list must be readable; a git failure is INFRA,
    # not a verdict - the pre-commit contract says a broken git must not
    # wedge commits.
    rc, payload = _staged_new_files(repo)
    if rc is None or rc != 0:
        print("INFRA: staged-size: cannot list staged new files (%s) - no "
              "size verdict possible (advisory only)" % (payload or rc))
        return 2
    check("S1 staged new-file list readable", True,
          "%d new file(s) staged" % len(payload))

    # S2: every newly staged file is small or deliberately allowlisted.
    # Unreadable staged blobs are loud failures, never silent passes.
    bad = []
    for raw in payload:
        size = _staged_size(repo, raw)
        path = raw.decode("utf-8", "replace")
        if size is None:
            bad.append((path, "unreadable staged blob"))
        elif size > THRESHOLD and not ALLOWLIST.search(path):
            bad.append((path, "%d bytes (> %d byte threshold)" % (size, THRESHOLD)))
    for path, why in bad:
        print("FAIL: staged-size: newly staged file %r is oversized (%s) - "
              "add-A would sweep it into the public repo; remove it from "
              "the index (git rm --cached <path>) or extend the backup "
              "allowlist deliberately" % (path, why))
    if bad:
        return 1
    check("S2 no oversized new staged files", True,
          "%d new file(s) all <= 1 MiB or backup-allowlisted" % len(payload))
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main(sys.argv[1:]))
