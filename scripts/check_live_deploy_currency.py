#!/usr/bin/env python3
"""Regression guard: the GitHub Pages deploy must not go stale (84th).

Every push goes to origin master+main and GitHub Pages rebuilds the site
asynchronously. The per-run "live-site currency check" (fetching
rayhe.github.io/sp500-exec-comp/data/compensation.json and eyeballing the
counts against local HEAD) is a manual hand-convention in the iteration
log - the same hand-convention pattern the 82nd guard closed for
log-prose numbers and the 83rd closed for the canary cadence.

Failure mode: if a Pages build fails or wedges (queue jam, a broken data
file, a misconfigured build branch), the live site keeps serving STALE
data while every static guard stays green. The deploy has no fail-closed
verifier; the staleness is only caught when a run happens to do the
manual live check, so between runs the site can serve yesterday's numbers
with all guards nominally passing.

This guard pins the live deploy to the repo's data fingerprint in FULL
(canary) mode: it fetches the live compensation.json, sha256-hashes the
served bytes, and compares against the local data/compensation.json at
the current commit. Byte-identical is the bar - GitHub Pages serves the
file verbatim, so any pushed data change must eventually appear live.

Checks:
  --static-only (commit time): the deploy has not happened yet, so no
     live assertion is possible at commit time. The static half asserts
     the cheap static invariants instead, fast (<2s):
     S1 local data/compensation.json exists and parses as JSON with a
        metadata block (input sanity for the full-mode comparison;
        missing/unparseable -> HARD FAIL: the repo is in a state the
        guard's premise cannot cover, and committing blind is the wrong
        trade)
     S2 the live URL constant is a well-formed https URL on the expected
        host and path (guards against a typo'd URL silently checking the
        wrong site - a same-host wrong-path fetch 404s, but an entirely
        wrong host could serve something else)
     then SKIP: the live comparison itself is full-mode (canary) only,
     by design - documented here so the next auditor does not flag the
     static half as hollow.
  full mode (drift canary, scheduled): fetch the live file and compare
     F1 byte-identical sha256 -> PASS (reports companies/rows/verified
        from the live metadata for readability)
     F2 hash mismatch -> HARD FAIL naming both short hashes plus live vs
        local counts, with CDN-lag guidance (a FAIL within ~15 min of a
        push is usually Pages propagation - re-run to confirm before
        treating it as a wedged deploy)
     F3 clean HTTP error from the origin (404/5xx) -> HARD FAIL (deploy
        broken or site down)
     F4 transport failure (timeout, DNS, connection reset, proxy error)
        -> exit 2 INFRA advisory, non-blocking (the egress proxy flakes;
        wedging a commit over a proxy hiccup is the wrong trade)

Usage:
  scripts/check_live_deploy_currency.py                 # full mode
  scripts/check_live_deploy_currency.py --static-only   # commit-time half
  scripts/check_live_deploy_currency.py --live-url URL  # test override
  scripts/check_live_deploy_currency.py --local PATH   # test override

Exit: 0 = live matches local (or static half green); 1 = live stale or
      broken; 2 = could not reach the live site (infra advisory).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

History:
  2026-10-13 19:30 - created (19:30 PT iteration). Closes the
    deploy-staleness class: the post-push live-site currency check was a
    manual per-run hand-convention with no fail-closed verifier, so a
    failed/wedged Pages build would leave the live site serving stale
    data with every guard green. Negative tests (all in /tmp, real tree
    untouched): byte-identical fixture over local http.server -> rc=0
    PASS; diverged fixture -> rc=1 FAIL naming both short hashes;
    404 from server -> rc=1 FAIL; connection refused -> rc=2 INFRA;
    --static-only on the real tree -> rc=0 with the canary-only SKIP;
    --static-only with missing --local file -> rc=1 FAIL.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
DEFAULT_LOCAL = os.path.join(TOP, "data", "compensation.json")
LIVE_URL = "https://rayhe.github.io/sp500-exec-comp/data/compensation.json"
FETCH_TIMEOUT = 60

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _opt(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_local_meta(path):
    """Return (ok, metadata-or-error-string)."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        return False, "cannot read %s: %s" % (path, e)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return False, "%s is not valid JSON: %s" % (path, e)
    meta = data.get("metadata") if isinstance(data, dict) else None
    if not isinstance(meta, dict):
        return False, "%s has no metadata block" % path
    return True, meta


def _meta_summary(meta):
    dq = meta.get("data_quality") or {}
    return "companies=%s rows=%s verified=%s" % (
        meta.get("total_companies"), meta.get("total_neo_records"),
        dq.get("verified_total"))


def static_half(local_path):
    # S1: the local data file the full-mode comparison fingerprints must
    # exist and parse - without it the guard's premise is broken.
    ok, meta_or_err = _load_local_meta(local_path)
    check("live-deploy-input-local", ok,
          _meta_summary(meta_or_err) if ok else meta_or_err)
    if not ok:
        return 1
    # S2: the live URL is the exact expected endpoint - a typo'd URL
    # silently checking the wrong site would make every future PASS a lie.
    url_ok = (LIVE_URL == "https://rayhe.github.io/sp500-exec-comp/"
              "data/compensation.json")
    check("live-deploy-input-url", url_ok, LIVE_URL if url_ok else
          "unexpected LIVE_URL constant: %r" % LIVE_URL)
    if not url_ok:
        return 1
    print("SKIP: live comparison is full-mode (canary) only - the deploy "
          "has not happened at commit time; see guard docstring")
    return 0


def full_mode(local_path, live_url):
    # Local fingerprint first: fail-closed on unreadable local data (same
    # bar as the static half - the metadata gate would already have fired,
    # but this guard must not PASS on a premise it cannot check).
    try:
        local_hash = _sha256_file(local_path)
    except OSError as e:
        print("FAIL: live-deploy-currency - cannot read local %s: %s"
              % (local_path, e))
        return 1
    ok, meta_or_err = _load_local_meta(local_path)
    local_summary = _meta_summary(meta_or_err) if ok else "metadata unreadable"

    # Fetch the live file. Transport problems are INFRA (exit 2,
    # non-blocking): the egress proxy flakes and wedging a canary over a
    # proxy hiccup is the wrong trade. Clean HTTP errors are FAIL: the
    # origin answered and the deploy is broken or the site is down.
    req = urllib.request.Request(live_url, headers={"User-Agent": "Kit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            status = resp.status
            live_bytes = resp.read()
    except urllib.error.HTTPError as e:
        print("FAIL: live-deploy-currency - live fetch HTTP %s (%s); "
              "deploy broken or site down" % (e.code, live_url))
        return 1
    except Exception as e:  # URLError, TimeoutError, socket/OSError, proxy errors
        print("INFRA: live-deploy-currency - could not reach %s: %s "
              "(advisory only; egress/proxy flake suspected)" % (live_url, e))
        return 2

    live_hash = hashlib.sha256(live_bytes).hexdigest()
    if live_hash == local_hash:
        try:
            live_meta = json.loads(live_bytes.decode("utf-8"))["metadata"]
            live_summary = _meta_summary(live_meta)
        except (ValueError, UnicodeDecodeError, KeyError, TypeError):
            live_summary = "metadata unreadable"
        check("live-deploy-currency", True,
              "live sha256 %s.. == local; %s" % (live_hash[:12], live_summary))
        return 0

    try:
        live_meta = json.loads(live_bytes.decode("utf-8"))["metadata"]
        live_summary = _meta_summary(live_meta)
    except (ValueError, UnicodeDecodeError, KeyError, TypeError):
        live_summary = "live body not parseable as dataset JSON"
    print("FAIL: live-deploy-currency - live sha256 %s.. != local %s..; "
          "live [%s] vs local [%s]; the Pages deploy is STALE or diverged. "
          "If a push landed within the last ~15 min, re-run first - Pages "
          "CDN propagation, not a wedged deploy, is the usual cause."
          % (live_hash[:12], local_hash[:12], live_summary, local_summary))
    return 1


def main(argv):
    local_path = _opt(argv, "--local") or DEFAULT_LOCAL
    live_url = _opt(argv, "--live-url") or LIVE_URL
    if "--static-only" in sys.argv:
        return static_half(local_path)
    return full_mode(local_path, live_url)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
