#!/usr/bin/env python3
"""Regression guard: the default network view draws the same-sector edge web
ON TOP of the nodes (edge-web overlay).

Background (2026-10-06 23:30 PT): the default "All Peers" view drew all 7,739
edges underneath the nodes. The packed default layout (collision radius =
node radius + 2) leaves almost no gaps between the opaque node fills, so the
edge web was invisible and the flagship view read as a bubble chart with no
visible peer relationships — contradicting the section copy ("Arrows show
which companies benchmark against which peers") and the 2026-10-03 code
comment stating the edge web is the structure-carrying channel of the default
view. Fix: the same-sector pass was extracted into strokeSameSectorEdges()
and is now stroked after the Nodes loop (overlay), gated on the pure default
state (default edge branch, no active path). Cross-sector edges stay
underneath as dim context; hover/sector/tier/community/flow/quartile/trend
branches keep their existing behavior.

This guard has two halves:
  A. Static: the helper exists; the default else branch sets
     defaultEdgeBranch = true exactly once; the overlay call is gated on
     defaultEdgeBranch with the activePath exclusion; the old under-node
     same-sector block is gone.
  B. Render (headless Chromium via playwright): in the default view with no
     hover, a wheel-zoom (which triggers draw() via the d3 zoom handler)
     strokes >= 5000 quadratic curves (one per same-sector edge, ~5,547
     expected) — proving the overlay pass runs on top of the nodes — with
     zero page errors.

Usage:
  scripts/check_network_edge_overlay.py              # static + render
  scripts/check_network_edge_overlay.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

481st review (2026-11-16): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (and the
now-unused tempfile import), the render half returns the INFRA
sentinel when the shim is unavailable, and main() is restructured
around run_render_with_retry with the INFRA-to-exit-2 mapping (its
sys.exit calls become returns, and the all-pass path gains the uniform
"ALL N CHECKS PASSED" summary line this guard never printed). Pre-fix
defects: (#1, no retry wrapper) a transient render exception raised
before any R-check was uncaught -- traceback, exit 1, 0 R-checks, no
FAIL verdict; (#2, latent silent pass, S4 form) main() already mapped
a False render return to exit 2 (the 432nd-note crosstab exception
class -- the live missing-shim exit was correct, code 2), but the
INFRA sentinel itself is truthy, so a render half returning INFRA
would have fallen through the False check into "0 if static_ok and
render_ok" and exited 0 with 0 R-checks while the render half never
ran -- proved in-process before the fix
(~/workspace/sp500-481/pre481_proof.py: Test A-live code=2, "INFRA:
could not obtain d3.min.js shim", 0 R-checks; Test A2 code=0, 0
R-checks; Test B UNCATCHED RuntimeError on a simulated transient
Chromium launch stall). Slowest adoptable shard-4 render guard by the
multi-run history plus the re-profile: median 16.9s over the last 6
shard-4 runs (16.3s freshest state) and 19.13s standalone (this run)
vs inline-onclick 17.2s median / 14.31s standalone and crosstab 16.4s
median / 14.82s standalone -- network-edge leads the freshest state
by a hair and the re-profile by a wide margin, trailing inline by
0.3s on the 6-run median only, and takes the shard-4 slot in the
1-2-3 rotation (478th shard 1, 479th shard 2, 480th shard 3), per the
469th note (68) rule that the evidence base is the multi-run history
plus the re-profile, not one state reading.

530th review (2026-11-20): late-raise silent pass closed -- main()
ignored a False return from run_render_with_retry, so a render half
that raised after an R-check was recorded (or returned False with no
FAIL recorded) exited 0 with "ALL N CHECKS PASSED" while the render
half never completed. main() now checks ok is False after the fails
list and returns 1 with "render half failed (see INFRA lines above)"
when no FAIL was recorded, keeping the guard's existing summary
format and the playwright-missing skip shape. Third of the four full
adopters in this class by the freshest in-canary reading at pick time
(17.8s in the 2026-11-20T10:36:09Z shard-4 run, pre-fix form) vs
check_scrollspy_nav.py 81.0s (pinned 528th), check_sort_aria_sort.py
77.9s (pinned 529th) and check_pathfinder_toggle_aria 17.2s
remaining. Pinned in the LATE_RAISE_PINNED contract list
(check_render_guard_common.py S4f variants). Pre-fix defects proved
in-process before the fix (~/workspace/sp500-530/pre530_proof.py):
Test A late raise after R1 rc=0 with "ALL 6 CHECKS PASSED"; Test B
render False rc=0 with "ALL 5 CHECKS PASSED"; Test A0 transient
raise already rc=1 via the synthetic FAIL; Test A2
playwright-missing rc=0 skip unchanged. render_checks() already
returns an explicit bool on success, so no None-on-success fix was
needed (458th note (27) checked).
"""
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

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    src = open(NETWORK_JS, encoding="utf-8").read()

    # S1: the extracted helper exists.
    check("S1 strokeSameSectorEdges helper defined",
          "function strokeSameSectorEdges()" in src, "")

    # S2: the default edge else-branch sets defaultEdgeBranch = true exactly once.
    sets = len(re.findall(r"defaultEdgeBranch\s*=\s*true", src))
    check("S2 defaultEdgeBranch = true set exactly once in default branch",
          sets == 1, "found %d" % sets)

    # S3: the overlay invocation is gated on defaultEdgeBranch with the
    # activePath exclusion.
    m = re.search(
        r"if\s*\(defaultEdgeBranch\s*&&\s*!"
        r"\(activePath\s*&&\s*activePath\.nodes\.length\s*>=\s*2\)\)\s*\{\s*\n"
        r"\s*strokeSameSectorEdges\(\);", src)
    check("S3 overlay gated on defaultEdgeBranch && !activePath",
          m is not None, "")

    # S4: the old under-node same-sector block is gone (its distinctive
    # comment only survives if the block does).
    check("S4 old under-node same-sector pass removed",
          "accent-tinted, curved to reduce overlap" not in src, "")

    # S5: the helper still applies the GER-threshold edge filter (no behavior
    # regression for GER heatmap mode).
    helper = re.search(r"function strokeSameSectorEdges\(\)\s*\{(.*?)\n        \}",
                       src, re.S)
    has_ger = helper is not None and "gerHeatmapMode && gerThreshold > 0" in helper.group(1)
    check("S5 helper keeps GER-threshold edge filter", has_ger, "")


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

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            errors = []
            pg = browser.new_page(viewport={"width": 1440, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.route("**/d3*", lambda r: r.fulfill(
                status=200, content_type="application/javascript", body=d3))
            pg.goto("http://127.0.0.1:%d/index.html" % port,
                    wait_until="networkidle", timeout=60000)
            time.sleep(7)
            pg.evaluate(
                "document.getElementById('peer-network-section')"
                ".scrollIntoView({block:'start'})")
            time.sleep(4)  # let the force layout cool so ticks stop
            # Install a quadraticCurveTo counter, then wheel-zoom over the
            # canvas center: d3 zoom -> draw() -> overlay pass strokes one
            # curve per same-sector edge (~5,547). No hover: the mouse never
            # enters the canvas before the wheel event.
            pg.evaluate("""(() => {
                window.__qct = 0;
                const proto = CanvasRenderingContext2D.prototype;
                const orig = proto.quadraticCurveTo;
                proto.quadraticCurveTo = function() {
                    window.__qct++;
                    return orig.apply(this, arguments);
                };
            })()""")
            box = pg.evaluate("""(() => {
                const c = document.querySelector('#network-graph canvas');
                const b = c.getBoundingClientRect();
                return {x: b.x + b.width / 2, y: b.y + b.height / 2};
            })()""")
            pg.mouse.move(box["x"], box["y"])
            time.sleep(0.3)
            pg.mouse.wheel(0, 120)
            time.sleep(1.5)
            n = pg.evaluate("window.__qct || 0")
            # In the default branch with no hover, the ONLY quadraticCurveTo
            # source is the overlay pass (the old under-node pass was removed;
            # hover connected-edges need hoveredNode). ~5,547 same-sector
            # edges; assert a generous lower bound for one full pass.
            check("R1 wheel-zoom draw() strokes >= 5000 same-sector curves (overlay on top)",
                  n >= 5000, "counted %d" % n)
            check("R2 zero page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")
            ok = n >= 5000 and len(errors) == 0
            browser.close()
            return ok
    finally:
        server.terminate()


def main():
    static_checks()
    static_ok = all(ok for _, ok, _ in results)
    if "--static-only" in sys.argv:
        return 0 if static_ok else 1
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
    failed = [r for r in results if not r[1]]
    if failed or (ok is False):
        if failed:
            print("\n%d check(s) FAILED" % len(failed))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("\nALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
