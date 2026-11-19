#!/usr/bin/env python3
"""Regression guard: the peer-network section's peer-only ("orphan") clause
must report the live orphan count from the loaded peer-network.json + comp
lookup, not a hard-coded count.

Background (2026-10-07): the clause hard-coded "31 tracked companies
currently have peer-only nodes - cited as peers, but their own peer groups
have not yet been verified from their DEF 14As (extraction ongoing;
most-cited: HOLX, MA, SYK, C, FDX, GS)" - the batch-8r copy. Peer batches
8s+ verified every remaining peer group, so the live renderer now emits "All
tracked companies' peer groups have now been verified from their DEF 14As.",
and the static no-JS fallback was stale for the third time (it also went
stale after batch-8r and again after batch-8s). Same stale-count class as the
coverage clause (fixed the same run), the header company-count badge
(2026-09-24), the median-pay FY2025 sublabel (2026-10-07), and the
sector-comp / role-comp descs (2026-10-07). The fix carries today's live copy
in the static HTML; renderOrphanDesc() in js/network.js already renders the
clause live (textContent-only) from the node list x _compLookup.

This guard has two halves:
  A. Static: renderOrphanDesc() exists, classifies orphans as tracked
     tickers with out_degree 0 and isSource !== false, is textContent-only,
     and is called at load; index.html's #network-orphan-desc fallback
     carries today's live copy (0 orphans today) and no hard-coded
     "N tracked companies currently have peer-only nodes" remains outside
     the span.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     #network-orphan-desc reads the live orphan sentence on initial load;
     zero page errors.

Usage:
  scripts/check_network_orphan_desc.py              # static + render
  scripts/check_network_orphan_desc.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

519th review (2026-11-19): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of silently passing).
Pre-fix defects: this guard's class is the SILENT-PASS variant, not
the drift variant -- a missing d3 shim made render_checks() return
False, which main() ignored entirely (it never checked the return
value), so the guard exited 0 with "5/5 checks passed" although the
docstring promises exit 2 (infra) -- proved in-process before the
fix (~/workspace/sp500-519/pre519_proof.py: Test A rc=0, 0 R-checks);
and a transient render exception raised before any R-check was
uncaught (no retry wrapper) -- proved in-process before the fix
(Test B UNCATCHED RuntimeError on a simulated transient Chromium
launch stall, Popen calls=1). The playwright-missing branch keeps
its skip shape (rc=0 on passing statics) -- Test A2 control,
unchanged. Slowest remaining unadopted render guard by the
controlled readings this run: two-sample standalone averages
network_orphan_desc 9.99s vs sector_median_fy_key 8.92s vs
role_comp_desc 7.26s (sample 1: 10.54s / 7.55s / 6.22s; sample 2:
9.44s / 10.28s / 8.29s); freshest in-canary agrees on the order
(network 9.8s in the 2026-11-19T09:04Z shard-4 run vs sector 6.2s
and role 4.7s in the 06:31Z shard-3 run). The 518th load-inflated
order (role 65.70s > sector 61.30s > network 38.90s under load
average 7-14) was a load artifact -- the 518th note warned to
re-profile before picking, and the quiet-box re-profiles reverse
it; the pick follows the controlled readings, per the 516th note.
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


def live_orphans():
    # Same classification as renderOrphanDesc(): tracked = in the comp
    # lookup, out_degree 0, isSource !== false.
    comp = json.load(open(COMP_JSON, encoding="utf-8"))
    peer = json.load(open(PEER_JSON, encoding="utf-8"))
    tracked = set(c["ticker"] for c in comp["companies"])
    orphans = [n["ticker"] for n in peer["nodes"]
               if n["ticker"] in tracked
               and (n.get("out_degree") or 0) == 0
               and n.get("isSource") is not False]
    orphans.sort(key=lambda t: next(
        (n.get("in_degree") or 0 for n in peer["nodes"] if n["ticker"] == t), 0),
        reverse=True)
    return orphans


def live_copy(orphans):
    if not orphans:
        return "All tracked companies\u2019 peer groups have now been verified from their DEF 14As."
    top = ", ".join(orphans[:6])
    return ("%d tracked companies currently have peer-only nodes \u2014 cited as peers, "
            "but their own peer groups have not yet been verified from their DEF 14As "
            "(extraction ongoing; most-cited: %s).") % (len(orphans), top)


def static_checks():
    src = open(NETWORK_JS, encoding="utf-8").read()
    html = open(INDEX_HTML, encoding="utf-8").read()
    orphans = live_orphans()
    expected = live_copy(orphans)

    # S1: helper exists and classifies orphans from the node list + comp lookup.
    s1 = ("function renderOrphanDesc()" in src
          and "_compLookup" in src and "out_degree" in src
          and re.search(r"function renderOrphanDesc\(\)\s*\{.*?out_degree",
                        src, re.DOTALL) is not None)
    check("S1 renderOrphanDesc() classifies orphans from node list x _compLookup",
          s1, "" if s1 else "helper missing or does not classify from data")

    # S2: textContent-only - the helper never writes raw HTML into the desc.
    fn = src.split("function renderOrphanDesc()", 1)
    body = fn[1].split("\n    }\n", 1)[0] if len(fn) > 1 else ""
    s2 = "innerHTML" not in body
    check("S2 renderOrphanDesc() is textContent-only (no innerHTML)",
          s2, "" if s2 else "helper writes raw HTML")

    # S3: called at load next to renderNetworkCoverage().
    s3 = "renderOrphanDesc();" in src and "renderNetworkCoverage();" in src
    check("S3 renderOrphanDesc() is called at load next to renderNetworkCoverage()",
          s3, "" if s3 else "load call site missing")

    # S4: static HTML fallback carries today's live copy.
    m = re.search(r'<span id="network-orphan-desc">(.*?)</span>', html, re.DOTALL)
    fb = m.group(1) if m else ""
    # The HTML fallback uses &rsquo; where the JS live string has U+2019.
    fb_norm = fb.replace("&rsquo;", "\u2019")
    fallback_ok = fb_norm == expected
    check("S4 static #network-orphan-desc fallback carries today's live copy (%d orphans)"
          % len(orphans),
          fallback_ok, "" if fallback_ok else "fallback %r != live %r" % (fb[:80], expected[:80]))

    # S5: no hard-coded "N tracked companies currently have peer-only nodes"
    # remains outside the span.
    stripped = re.sub(r'<span id="network-orphan-desc">.*?</span>', '', html, flags=re.DOTALL)
    s5 = re.search(r"\d+ tracked companies currently have peer-only nodes", stripped) is None
    check("S5 no hard-coded 'N tracked companies currently have peer-only nodes' remains outside the span",
          s5, "" if s5 else "stale hard-coded orphan clause still present")


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
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

    expected = live_copy(live_orphans())

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
                "window.d3 && document.getElementById('network-orphan-desc')"
                " && document.getElementById('network-global-stats')"
                " && document.getElementById('network-global-stats').textContent.length > 0",
                timeout=90000)

            # R1: initial-load orphan desc == live-rendered sentence.
            text = pg.evaluate(
                "document.getElementById('network-orphan-desc').textContent")
            r1 = text == expected
            check("R1 initial-load network orphan desc == live sentence (%d orphans)"
                  % len(live_orphans()),
                  r1, "got %r" % text if not r1 else "")

            # R2: zero JS page errors across the lifecycle.
            check("R2 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if static_only:
        bad = [n for n, ok, _ in results if not ok]
        return 1 if bad else 0
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
    print("ALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
