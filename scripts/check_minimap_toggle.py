#!/usr/bin/env python3
"""Regression guard: mobile minimap collapse toggle must hide the dead zone
and expand/collapse reliably.

Background (2026-10-06, commit 6b603a0): on small screens the opaque 96x66
minimap painted over the top-right graph nodes at default zoom, drew no
viewport rect until zoomed in, and was camouflaged against the dark theme -
a dead zone occluding labels and swallowing taps. The fix starts the mobile
minimap collapsed behind a 34px toggle button (aria-expanded + label flip),
restoring the graph on tap. This guard pins that behavior.

This guard has two halves:
  A. Static: the toggle wiring in js/network.js is intact (button, class,
     aria attributes, click handler toggling .expanded), the CSS keeps the
     toggle hidden on desktop / shown on mobile, the mobile minimap defaults
     to display:none with #network-graph scoping (the 2026-10-06 specificity
     lesson: "#network-graph canvas { display: block }" (1,0,1) outranks a
     bare ".network-minimap { display:none }" (0,1,0)), and the cluster-stats
     mirror rules hide both minimap and toggle when the stats panel is up.
  B. Render (headless Chromium via playwright): on a 360px viewport the
     toggle is visible while the minimap is display:none with
     aria-expanded=false; tapping it expands (display:block, .expanded,
     aria-expanded=true, label flips to "Hide network overview map", .active,
     canvas has painted pixels); tapping again collapses; on a 1440px
     viewport the toggle is display:none and the minimap stays visible.
     Zero page errors.

Usage:
  scripts/check_minimap_toggle.py              # static + render
  scripts/check_minimap_toggle.py --static-only

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
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    src = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # A1: toggle creation wiring in network.js.
    a1_bits = [
        "mmToggle.className = 'network-minimap-toggle'",
        "mmToggle.setAttribute('aria-label', 'Show network overview map')",
        "mmToggle.setAttribute('aria-expanded', 'false')",
        "mmCanvas.classList.toggle('expanded')",
        "mmToggle.classList.toggle('active', expanded)",
        "mmToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false')",
        "'Hide network overview map' : 'Show network overview map'",
    ]
    missing = [b for b in a1_bits if b not in src]
    check("A1 toggle wiring intact in js/network.js",
          not missing, "missing: %s" % missing if missing else "%d/%d bits" % (len(a1_bits), len(a1_bits)))

    # A2: desktop base rule hides the toggle.
    check("A2 desktop base rule hides toggle",
          bool(re.search(r"\.network-minimap-toggle\s*\{[^}]*display:\s*none;", css)),
          "")

    # A3: mobile query shows the toggle.
    check("A3 mobile query shows toggle (display:flex)",
          ".network-minimap-toggle { display: flex; }" in css,
          "")

    # A4: mobile minimap defaults to display:none, scoped under #network-graph
    # so the base "#network-graph canvas { display: block }" rule (1,0,1)
    # cannot outrank it.
    check("A4 mobile minimap collapsed by default, #network-graph scoped",
          "#network-graph .network-minimap { display: none; }" in css,
          "specificity lesson 2026-10-06" if "#network-graph .network-minimap { display: none; }" not in css else "")

    # A5: expanded state restores the minimap.
    check("A5 .expanded restores minimap display",
          "#network-graph .network-minimap.expanded { display: block; }" in css,
          "")

    # A6: cluster-stats mirror rules hide both minimap and toggle when the
    # stats panel is visible (same DOM parent: #network-graph).
    a6a = ".network-cluster-stats.visible ~ .network-minimap { display: none !important; }" in css
    a6b = ".network-cluster-stats.visible ~ .network-minimap-toggle { display: none !important; }" in css
    check("A6 cluster-stats hides minimap AND toggle",
          a6a and a6b,
          ("minimap rule missing; " if not a6a else "") + ("toggle rule missing" if not a6b else ""))

    # A7: canvas bitmap is hooked into the main draw cycle, so expanding the
    # minimap shows a painted frame (no blank-canvas on expand).
    check("A7 drawMiniMap hooked into main draw cycle",
          "drawMiniMap();" in src and "draw = function()" in src,
          "")


def get_d3_bytes():
    # Same cached copy as check_scrollspy_nav.py / check_methodology_buttons.py
    # (build-time shim only).
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


TOGGLE_STATE_JS = """(() => {
    const t = document.querySelector('.network-minimap-toggle');
    const mm = document.querySelector('#network-graph .network-minimap');
    if (!t || !mm) return null;
    const cs = window.getComputedStyle(t), mcs = window.getComputedStyle(mm);
    return {
        toggleDisplay: cs.display,
        mmDisplay: mcs.display,
        expanded: mm.classList.contains('expanded'),
        aria: t.getAttribute('aria-expanded'),
        label: t.getAttribute('aria-label'),
        active: t.classList.contains('active')
    };
})()"""


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

            def new_page(width, height):
                pg = browser.new_page(viewport={"width": width, "height": height},
                                      has_touch=(width <= 600), is_mobile=(width <= 600))
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
                    "window.d3 && !!document.querySelector('.network-minimap-toggle')",
                    timeout=90000)
                pg.evaluate(
                    "document.getElementById('peer-network-section').scrollIntoView({block:'start'})")
                pg.wait_for_timeout(1200)
                return pg

            # R1: mobile starts collapsed behind the toggle (the dead zone is gone).
            m = new_page(360, 800)
            s0 = m.evaluate(TOGGLE_STATE_JS)
            check("R1 mobile: toggle visible, minimap collapsed, aria-expanded=false",
                  s0 and s0["toggleDisplay"] == "flex"
                  and s0["mmDisplay"] == "none"
                  and s0["expanded"] is False
                  and s0["aria"] == "false"
                  and s0["label"] == "Show network overview map",
                  str(s0) if not (s0 and s0["toggleDisplay"] == "flex" and s0["mmDisplay"] == "none") else "")

            # R2: tap expands - full state flip plus a painted canvas.
            m.evaluate("document.querySelector('.network-minimap-toggle').click()")
            m.wait_for_timeout(600)
            s1 = m.evaluate(TOGGLE_STATE_JS)
            painted = m.evaluate("""(() => {
                const mm = document.querySelector('#network-graph .network-minimap');
                const px = mm.getContext('2d').getImageData(0,0,mm.width,mm.height).data;
                for (let i = 3; i < px.length; i += 40) if (px[i] > 0) return true;
                return false;
            })()""")
            check("R2 mobile: tap expands (display, .expanded, aria, label, .active, painted)",
                  s1 and s1["mmDisplay"] == "block"
                  and s1["expanded"] is True
                  and s1["aria"] == "true"
                  and s1["label"] == "Hide network overview map"
                  and s1["active"] is True
                  and painted,
                  ("state=" + str(s1) + " " if not (s1 and s1["mmDisplay"] == "block") else "")
                  + ("" if painted else "canvas blank"))

            # R3: tap again collapses back to the R1 state.
            m.evaluate("document.querySelector('.network-minimap-toggle').click()")
            m.wait_for_timeout(400)
            s2 = m.evaluate(TOGGLE_STATE_JS)
            check("R3 mobile: second tap collapses (aria/label reset)",
                  s2 and s2["mmDisplay"] == "none"
                  and s2["expanded"] is False
                  and s2["aria"] == "false"
                  and s2["label"] == "Show network overview map"
                  and s2["active"] is False,
                  str(s2) if not (s2 and s2["mmDisplay"] == "none") else "")
            m.close()

            # R4: desktop keeps the always-visible minimap; toggle hidden.
            d = new_page(1440, 900)
            s3 = d.evaluate(TOGGLE_STATE_JS)
            check("R4 desktop: toggle hidden, minimap visible",
                  s3 and s3["toggleDisplay"] == "none"
                  and s3["mmDisplay"] != "none",
                  str(s3) if not (s3 and s3["toggleDisplay"] == "none") else "")
            d.close()

            # R5: zero JS page errors across both viewports.
            check("R5 zero JS page errors", not errors, "; ".join(errors[:3]) if errors else "")
            browser.close()
    finally:
        server.terminate()
    return True


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if not static_only:
        render_checks()
    failed = [r for r in results if not r[1]]
    if failed:
        print("\n%d/%d checks FAILED" % (len(failed), len(results)))
        sys.exit(1)
    print("\n%d/%d checks passed" % (len(results), len(results)))
    sys.exit(0)


if __name__ == "__main__":
    main()
