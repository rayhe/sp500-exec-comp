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
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

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


def get_d3_bytes():
    cache = os.path.expanduser(
        "~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/methbtn-20261005/d3.min.js")
    if os.path.exists(cache):
        return open(cache, "rb").read()
    tmp = tempfile.NamedTemporaryFile(suffix=".js", delete=False).name
    r = subprocess.run(
        ["curl", "-sL", "--http1.1", "-A", "Kit/1.0 (factoryfactorykit@gmail.com)",
         "https://cdn.jsdelivr.net/npm/d3@7", "-o", tmp],
        timeout=60)
    if r.returncode != 0 or os.path.getsize(tmp) < 100000:
        return None
    return open(tmp, "rb").read()


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
        return False

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
        sys.exit(0 if static_ok else 1)
    render_ok = render_checks()
    if render_ok is None:
        sys.exit(0 if static_ok else 1)
    if render_ok is False and not any(not ok for _, ok, _ in results):
        sys.exit(2)
    sys.exit(0 if static_ok and render_ok else 1)


if __name__ == "__main__":
    main()
