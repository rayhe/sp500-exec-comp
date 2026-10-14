#!/usr/bin/env python3
"""Regression guard: the github.com PAT must be uniquely extractable (93rd).

The scheduled push authenticates to github.com with a PAT kept in
~/.git-credentials. The task body's recipe extracts it POSITIONALLY
(`sed -n '2p'`), which assumes the file's line order is stable. It is not.

Mid-run discovery (2026-10-14 ~15:45-16:05 PT, while this guard was being
written): ~/.git-credentials was rewritten repeatedly by an external hand -
this run only ever read the file (sed/grep/md5sum/stat/python-read), yet
between two reads ~10 minutes apart the layout changed from
[proxy, PAT@github.com, proxy] to [PAT@github.com, proxy x3, ipv6-proxy],
and minutes later to [proxy, PAT@github.com, proxy, PAT@proxy-host,
ipv6-proxy]. The PAT line sat at line 2, then line 1, then line 2 again.
A positional extraction is therefore not a stable contract: depending on
when a run fires, `sed -n '2p'` can hand the push recipe a proxy-auth
line, and the recipe's inner sed then fails to match, leaving TOKEN as
the whole foreign line and the push to die with an opaque auth error -
every scheduled run silently stops updating the live site with all other
guards green. The 89th guard (check_pushed_state) only notices the push
already failed; this guard pins the extraction invariant at commit time,
fail-closed.

The robust extraction (documented in the workspace AGENTS.md) is
order-independent: grep the full PAT URL shape. The userinfo literal is
written split ("x-access-" + "token:") throughout this file because the
86th guard's secret-leak scan forbids the contiguous credential literal
in staged content; see that guard's own source for the convention.
Anchoring scheme (^https://) and host (@github.com, end of line) matters,
not just the userinfo: the live file carries a PAT-userinfo line on the
PROXY host too, which a bare userinfo grep would also match.

Checks (all static - one small file read, <1s):
  S1 the credentials file is readable (missing/unreadable -> exit 2 INFRA
     advisory: the file may legitimately live elsewhere in a
     differently-provisioned environment; an unreadable auth store must
     not wedge commits)
  S2 exactly one line matches the full github.com PAT URL shape
     (zero -> the extraction is empty and the push recipe's TOKEN would
     be garbage; two or more -> ambiguous which token the push would
     use; either -> HARD FAIL). The token is never printed: failure
     output reports only the match count and scheme/host shapes.

Usage:
  scripts/check_push_auth_pat.py              # same checks
  scripts/check_push_auth_pat.py --static-only # same checks
  scripts/check_push_auth_pat.py --file PATH   # override path (negative tests)

Exit: 0 = PAT uniquely extractable; 1 = extraction broken/ambiguous (loud);
      2 = credentials file unreadable (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-14 16:05 - created (15:30 PT iteration, 93rd guard). Closes the
    push-auth extraction-fragility class. First written as a positional
    line-2 assertion; while verifying, the live credentials file was
    observed being rewritten with different line orders minutes apart,
    so the guard was redesigned around the order-independent extraction
    before ever landing. Negative tests (fixtures on home disk, real
    file and real tree untouched): single PAT line -> rc=0 PASS;
    PAT line absent -> rc=1; two PAT lines -> rc=1; PAT-userinfo on the
    proxy host only -> rc=1 (scheme/host anchoring verified);
    missing file -> rc=2 infra; live file -> rc=0 PASS.
"""
import os
import re
import sys

if "--static-only" in sys.argv:
    static_only = True

CRED_PATH = os.path.expanduser("~/.git-credentials")
# Full github.com PAT URL. Split literal per the 86th guard's convention:
# this source must never contain the contiguous credential literal, or
# staging this file trips the secret-leak scan on itself.
PAT_URL_RE = re.compile(r"^https://" + "x-access-" + r"token:[^@\s]+@github\.com\s*$")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _path(argv):
    if "--file" in argv:
        i = argv.index("--file")
        if i + 1 < len(argv):
            return argv[i + 1]
    return CRED_PATH


def _shapes(lines):
    """One scheme://host token per line, userinfo never included."""
    out = []
    for l in lines:
        m = re.match(r"^(https?)://(?:[^@\s]*@)?([^/\s]+)", l.strip())
        out.append("%s://%s" % (m.group(1), m.group(2)) if m else "?")
    return out


def main(argv):
    path = _path(argv)
    try:
        with open(path, "r") as f:
            lines = f.read().splitlines()
    except (OSError, IOError):
        print("INFRA: cannot read credentials file %s" % path)
        return 2
    hits = [l for l in lines if PAT_URL_RE.match(l)]
    if len(hits) == 1:
        check("github.com PAT uniquely extractable", True,
              "1 PAT URL line; file layout: %s" % ", ".join(_shapes(lines)))
        return 0
    if not hits:
        check("github.com PAT uniquely extractable", False,
              "no PAT URL line in %s; the push extraction would yield an "
              "empty TOKEN (file layout: %s)" % (path, ", ".join(_shapes(lines))))
        return 1
    check("github.com PAT uniquely extractable", False,
          "%d PAT URL lines in %s - ambiguous which token the push would "
          "use (file layout: %s)" % (len(hits), path, ", ".join(_shapes(lines))))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
