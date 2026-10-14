#!/usr/bin/env python3
"""Regression guard: no secrets in staged content (secret-leak class).

Every iteration run stages with `git add -A` and this repo is PUBLIC
(rayhe.github.io/sp500-exec-comp), so a pasted credential in a scratch
script, debug fixture, or data file would publish to GitHub with every
other guard green. Until now nothing asserted the staged delta was
secret-free: the only tripwire was the run author's eyeball on
`git status`, and a `git add -A` sweep does not show file CONTENTS.

This guard scans the ADDED lines of the staged diff (`git diff --cached`)
for high-signal credential patterns and HARD FAILs the commit on any hit,
naming the file, line number, and pattern - never the secret value itself
(redacted from all output; the operator re-inspects via `git diff --cached`
themselves).

Denylist design (2026-10-13): concrete credential prefixes and PEM private
key headers ONLY. Deliberately excluded:
  - bare `re_` (Resend prefix collides with `re_<identifier>` in code;
    verified false positives on this tree: re_peerrefresh,
    re_containers, re_titlemarke)
  - generic `key = "..."` / `token: ...` shapes (too FP-prone in JS/Python)
  - high-entropy-string heuristics (FP-prone on hashes in data files)
The PAT-in-URL literal is assembled by string concatenation below so this
guard's own source never contains the contiguous credential literal and
staging the guard file itself does not self-trip (verified in fixtures).

Checks (all static - one `git diff --cached`):
  S1 the staged diff's added lines contain no denylisted pattern
     (any hit -> HARD FAIL naming file:line + pattern, value redacted)
  Binary handling: the diff is decoded with errors="replace" so a binary
  file can never crash the scan into a traceback (which would exit 1
  without a FAIL verdict and trip the exit-consistency guard); added
  lines containing NUL are skipped as binary, and git's own "Binary
  files ... differ" hunks contribute no added lines.
  `git diff --cached` failing (not a repo, git missing) -> exit 2 INFRA
  advisory, not a commit blocker, per the pre-commit contract.

Usage:
  scripts/check_secret_leak.py              # scan staged diff
  scripts/check_secret_leak.py --static-only # same (the scan IS the static half)

Exit: 0 = staged delta secret-free; 1 = credential pattern in staged
      additions (loud); 2 = git diff itself failed (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 23:30 - created (23:30 PT iteration). Closes the
    secret-leak class; the last hand-eyeballed pair without a guard
    (`git add -A` content review on a public repo).
"""
import re
import subprocess
import sys

# (name, compiled pattern). Order is cosmetic; first match per line wins.
_PATTERNS = [
    ("github-classic-pat", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("github-fine-grained-pat", re.compile(r"github_pat_[A-Za-z0-9_]{16,}")),
    ("github-oauth-token", re.compile(r"gho_[A-Za-z0-9]{20,}")),
    ("github-app-token", re.compile(r"(?:ghu_|ghs_|ghr_)[A-Za-z0-9]{20,}")),
    # Split literal: this source must never contain the contiguous string,
    # or staging this file would trip the guard on itself.
    ("pat-embedded-url", re.compile("x-access-" + "token:")),
    ("aws-access-key-id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("pem-private-key", re.compile(
        r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("stripe-live-secret", re.compile(r"sk_live_[A-Za-z0-9]{16,}")),
    ("cloudflare-api-token", re.compile(r"cfat_[A-Za-z0-9_-]{20,}")),
    ("cloudflare-legacy-token", re.compile(r"cfut_[A-Za-z0-9_-]{20,}")),
    ("vercel-token", re.compile(r"vcp_[A-Za-z0-9]{20,}")),
    ("gitlab-pat", re.compile(r"glpat-[A-Za-z0-9_-]{16,}")),
]

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS" if ok else "FAIL") + ": " + name +
          ((" - " + detail) if detail else ""))


def _staged_diff():
    """Return (rc, decoded_text) of `git diff --cached -U0 --no-color`.

    Decoded with errors="replace": binary content must never raise
    UnicodeDecodeError into a traceback (traceback exits 1 with no FAIL
    verdict, which the exit-consistency guard would flag, and it would
    wrongly block commits staging binary assets).
    """
    try:
        p = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--no-color"],
            capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return None, "git diff failed to run: %s" % e
    text = (p.stdout.decode("utf-8", errors="replace") + "\n"
            + p.stderr.decode("utf-8", errors="replace"))
    return p.returncode, text


def _scan(diff_text):
    """Yield (path, new_lineno, pattern_name) for denylist hits in added lines."""
    path = None
    new_lineno = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            # `+++ b/<path>`; `/dev/null` for deletions (no added lines follow)
            path = p[2:] if p.startswith("b/") else p
            continue
        if line.startswith("@@ "):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            new_lineno = int(m.group(1)) if m else 0
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if path in (None, "/dev/null"):
            continue
        body = line[1:]
        if "\x00" in body:
            new_lineno += 1
            continue  # binary content: not scannable as text
        for name, rx in _PATTERNS:
            if rx.search(body):
                yield path, new_lineno, name
                break  # first pattern per line wins; line counted once
        new_lineno += 1


def main(argv):
    # The staged-diff scan IS the static half (no render half exists).
    if "--static-only" in sys.argv:
        pass

    rc, out = _staged_diff()
    if rc is None:
        print("INFRA: " + out + " - cannot scan staged content; "
              "not blocking the commit")
        return 2
    if rc != 0:
        print("INFRA: git diff --cached exited %d - cannot scan staged "
              "content; not blocking the commit" % rc)
        return 2

    hits = list(_scan(out))
    if hits:
        for path, lineno, name in hits:
            # Values are NEVER echoed: pattern name + location only.
            check("S1 no %s in staged %s:%d" % (name, path, lineno),
                  False, "credential pattern in staged additions "
                  "(value redacted) - remove it before committing")
        print("FAIL: secret-leak: %d staged addition(s) match credential "
              "patterns - unstage or scrub them, then re-run" % len(hits))
        return 1

    check("S1 staged additions secret-free", True,
          "scanned added lines of the staged diff against %d patterns"
          % len(_PATTERNS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
