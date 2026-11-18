#!/usr/bin/env python3
"""Regression guard: the peer-network section description's coverage clause
("Covers 516 of the 518 tracked companies: ...") must report the live
tracked-with-node count from the loaded peer-network.json + comp lookup, not
a hard-coded count.

Background (2026-10-07): the clause hard-coded "Covers 516 of the 518
tracked companies: CPRT has no network node (...), and VMRK has no node yet
(...)" - true today, but the same stale-count class the header company-count
badge (2026-09-24), median-pay FY2025 sublabel (2026-10-07), sector-comp desc
and role-comp desc (2026-10-07) fixes addressed. A peer batch that adds nodes
(or a future post-merger VMRK DEF 14A, which the standing VMRK watch tracks)
would silently stale both the counts and the enumerated tickers. The fix
renders the clause live via renderNetworkCoverage() in js/network.js (counts
computed from node tickers x comp lookup, uncovered tickers enumerated with
a ticker-keyed reason map and a generic fallback for unknown tickers), with
the static HTML keeping today's copy as the no-JS fallback.

This guard has two halves:
  A. Static: renderNetworkCoverage() exists, derives covered/total from the
     node list and _compLookup, is textContent-only, and is called at load;
     index.html's #network-coverage-desc fallback carries today's live copy
     and no hard-coded "Covers N of the M" remains outside the span.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     #network-coverage-desc reads the live coverage sentence on initial
     load; zero page errors.

Usage:
  scripts/check_network_coverage_desc.py              # static + render
  scripts/check_network_coverage_desc.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

505th review (2026-11-18): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of exiting 0 with no
R-checks at all). static_checks() gains the OSError-to-return-2
path (488th template), covering the network.js / index.html reads
and the live_coverage() data reads. Pre-fix defects, both
429th-review classes in one guard: a missing d3 shim made
render_checks() return False, which main() ignored entirely, so it
exited 0 (the silent-pass variant, 430th shape, although the
docstring promises exit 2 for a missing shim) -- and printed
"5/5 checks passed" while the render half never ran; a missing
playwright install exited 0 the same way (the silent-pass variant,
although the docstring promises exit 2 for playwright missing);
and the INFRA sentinel itself is truthy, so a render half
returning INFRA would have exited 0 the same way (latent silent
pass, S4 form); and a transient render exception raised before
any R-check was uncaught (no retry wrapper) -- proved in-process
before the fix (~/workspace/sp500-505/pre505_proof.py: Test A-live
rc=0, 0 R-checks; Test A2 rc=0, 0 R-checks; Test A3 rc=0, 0
R-checks; Test B UNCATCHED RuntimeError on a simulated transient
Chromium launch stall). The proof monkeypatches get_d3_bytes to
None and stubs sys.modules['playwright.sync_api'] to None
(ImportError) rather than moving the d3 cache aside (the shard-1
canary is live concurrently; the monkeypatch touches no shared
state). The playwright-missing branch keeps its skip shape (rc=0
on passing statics) and the docstring's exit-2 promise for that
branch is unchanged from the pre-fix guard, per the 486th/487th
precedent. render_checks() already returns an explicit bool on
success (458th note (27) checked). Sole unadopted shard-1 render
guard by the canary's exact shard function, so no slowest-guard
comparison applies; the multi-run history plus the standalone
re-profile this run (500th note (152) rule): network_coverage
median 7.7s / mean 9.8s / max 26.0s over the last 20 shard-1 runs,
freshest 4.7s, 18.73s standalone under the live canary's load
(inflated; used only as a relative check, per the 485th
precedent). Shard verified with drift_canary._guard_shard (432nd
note): network_coverage_desc in shard 1 (with the full check_
name). The shard-1 canary for this review was re-launched after
the first attempt was killed by a runtime restart at ~3m45s with
no state written; the re-baseline is the completed re-run against
d7592fc. 17 check_*.py files still match the source-only grep
after this adoption (16 unadopted guards + the contract guard's
S1e string literal, which occurs twice in that file, so 18
matching lines); the recursive scripts/ grep adds the shared
module's own definition (19 lines over 18 .py files) plus one
stale __pycache__ .pyc (the 472nd note (76) trap -- quote the
source-only count going forward).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_JS = os.path.join(REPO, "js", "network.js")
INDEX_HTML = os.path.join(REPO, "index.html")
COMP_JSON = os.path.join(REPO, "data", "compensation.json")
PEER_JSON = os.path.join(REPO, "data", "peer-network.json")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def live_coverage():
    comp = json.load(open(COMP_JSON, encoding="utf-8"))
    peer = json.load(open(PEER_JSON, encoding="utf-8"))
    tracked = set(c["ticker"] for c in comp["companies"])
    node_t = set(n["ticker"] for n in peer["nodes"])
    uncovered = sorted(tracked - node_t)
    return len(tracked), len(tracked) - len(uncovered), uncovered


def static_checks():
    try:
        src = open(NETWORK_JS, encoding="utf-8").read()
        html = open(INDEX_HTML, encoding="utf-8").read()
        total, covered, uncovered = live_coverage()
    except OSError as exc:
        print("INFRA: cannot read guard inputs: %s" % exc)
        return 2

    # S1: helper exists and derives covered/total from the node list + comp lookup.
    s1 = ("function renderNetworkCoverage()" in src
          and "nodeTickers" in src and "_compLookup" in src
          and re.search(r"function renderNetworkCoverage\(\)\s*\{.*?uncovered",
                        src, re.DOTALL) is not None)
    check("S1 renderNetworkCoverage() derives covered/total from node tickers x _compLookup",
          s1, "" if s1 else "helper missing or does not compute coverage from data")

    # S2: textContent-only - the helper never writes raw HTML into the desc.
    fn = src.split("function renderNetworkCoverage()", 1)
    body = fn[1].split("\n    }\n", 1)[0] if len(fn) > 1 else ""
    s2 = "innerHTML" not in body
    check("S2 renderNetworkCoverage() is textContent-only (no innerHTML)",
          s2, "" if s2 else "helper writes raw HTML")

    # S3: called at load next to renderOrphanDesc().
    s3 = "renderOrphanDesc();\n    // Same for the network coverage clause" in src \
        and "renderNetworkCoverage();" in src
    check("S3 renderNetworkCoverage() is called at load next to renderOrphanDesc()",
          s3, "" if s3 else "load call site missing")

    # S4: static HTML fallback carries today's live copy.
    m = re.search(r'<span id="network-coverage-desc">(.*?)</span>', html, re.DOTALL)
    fallback_ok = m is not None \
        and ("Covers %d of the %d tracked companies" % (covered, total)) in m.group(1) \
        and all(t in m.group(1) for t in uncovered)
    check("S4 static #network-coverage-desc fallback carries today's live copy (%d/%d, %s)"
          % (covered, total, ",".join(uncovered)),
          fallback_ok, "" if fallback_ok else "fallback missing id or wrong copy")

    # S5: no hard-coded "Covers N of the M" outside the span.
    # (2026-10-08: also exclude the PvP coverage paragraph -- it is a
    # guarded live-rendered fallback of its own, kept current by
    # check_pvp_coverage_desc.py S5, not a stale hard-coded clause.)
    stripped = re.sub(r'<span id="network-coverage-desc">.*?</span>', '', html, flags=re.DOTALL)
    stripped = re.sub(r'<p class="section-desc" id="pvp-coverage-desc">.*?</p>', '', stripped, flags=re.DOTALL)
    s5 = re.search(r"Covers \d+ of the \d+ tracked companies", stripped) is None
    check("S5 no hard-coded 'Covers N of the M tracked companies' remains outside the span",
          s5, "" if s5 else "stale hard-coded coverage clause still present")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def render_checks():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: render checks need playwright (pip install playwright)")
        return None
    d3 = get_d3_bytes()
    if d3 is None:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

    total, covered, uncovered = live_coverage()
    # Mirror the JS join contract: "a, b, and c" for 3+, "a and b" for 2.
    reason = {"CPRT": "has no network node (no extractable peer-group disclosure in its DEF 14A filing)",
              "VMRK": "has no node yet (no post-merger DEF 14A filed)"}
    parts = ["%s %s" % (t, reason.get(t, "has no network node (peer group not yet verified from its DEF 14A)"))
             for t in uncovered]
    if len(parts) == 1:
        lst = parts[0]
    else:
        lst = ", ".join(parts[:-1]) + ", and " + parts[-1]
    expected = "Covers %d of the %d tracked companies: %s." % (covered, total, lst)

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-proxy-server"])
            errors = []
            pg = browser.new_page(viewport={"width": 1440, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript", body=d3)

            pg.route("**/npm/d3@7*", d3_route)
            pg.route("**/unpkg.com/d3@7*", d3_route)
            pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, wait_until="load")
            pg.wait_for_function(
                "window.d3 && document.getElementById('network-coverage-desc')"
                " && document.getElementById('network-global-stats')"
                " && document.getElementById('network-global-stats').textContent.length > 0",
                timeout=90000)

            # R1: initial-load coverage desc == live-rendered sentence.
            text = pg.evaluate(
                "document.getElementById('network-coverage-desc').textContent")
            r1 = text == expected
            check("R1 initial-load network coverage desc == live sentence (%d/%d)" % (covered, total),
                  r1, "got %r" % text if not r1 else "")

            # R2: zero JS page errors across the lifecycle.
            check("R2 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
    fails = [n for n, ok, _ in results if not ok]
    if fails or ok is False:
        if fails:
            print("FAILED: " + ", ".join(fails))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
