#!/usr/bin/env python3
"""Regression guard: path-finder toggle reports its state to assistive tech.

The 422nd review found the "Find Path" toggle (#path-finder-toggle) was a
disclosure control with no disclosure state: it showed/hid
#path-finder-bar, but the button carried neither aria-expanded nor
aria-controls, and none of the three sites that open or close the bar
(click toggle, pfPrefill, findNetworkPath) ever set aria-expanded. A
screen-reader user got no feedback about whether the bar was open --
unlike its siblings #network-overflow-toggle (aria-expanded +
aria-controls in the markup, flipped in js) and the minimap toggle
(aria-expanded + label flip in js/network.js). The fix adds both
attributes to the button in index.html and routes all three bar
open/close sites through one pfSetBarOpen(open) helper in
js/network.js, so the attribute cannot drift from the .visible class
again.

Checks:
  S1 index.html: #path-finder-toggle carries aria-expanded="false" and
     aria-controls="path-finder-bar", and the controlled element exists.
  S2 js/network.js: pfSetBarOpen(open) toggles .visible on the bar,
     .active on the toggle, and sets aria-expanded true/false.
  S3 all three bar open/close sites (pfPrefill, click handler,
     findNetworkPath) call pfSetBarOpen; no raw pfBar.classList
     add/remove('visible') or pfToggle.classList add/remove('active')
     survives outside the helper.
  R1-R4 render (headless Chromium via playwright, 1440px desktop, d3
     shim): initial aria-expanded=false with the bar hidden; click
     opens (aria=true, .visible, .active); second click closes
     (aria=false, hidden, no .active); findNetworkPath('AAPL','MSFT')
     opens the bar programmatically with aria=true.
  R5 zero JS page errors.

Usage:
  scripts/check_pathfinder_toggle_aria.py
  scripts/check_pathfinder_toggle_aria.py --static-only

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
INDEX_HTML = os.path.join(REPO, "index.html")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    html = open(INDEX_HTML, encoding="utf-8").read()
    src = open(NETWORK_JS, encoding="utf-8").read()

    # S1: the toggle declares its disclosure state and target in markup.
    m = re.search(r'<button[^>]*id="path-finder-toggle"[^>]*>', html)
    s1 = bool(m) and 'aria-expanded="false"' in m.group(0) \
        and 'aria-controls="path-finder-bar"' in m.group(0) \
        and 'id="path-finder-bar"' in html
    check("S1 toggle carries aria-expanded=false + aria-controls=path-finder-bar",
          s1, "button tag: %s" % (m.group(0) if m else "NOT FOUND"))

    # S2: the helper sets class and attribute together.
    s2_bits = [
        "function pfSetBarOpen(open) {",
        "pfBar.classList.toggle('visible', open)",
        "pfToggle.classList.toggle('active', open)",
        "pfToggle.setAttribute('aria-expanded', open ? 'true' : 'false')",
    ]
    missing = [b for b in s2_bits if b not in src]
    check("S2 pfSetBarOpen sets .visible + .active + aria-expanded together",
          not missing, "missing: %s" % missing if missing else "%d/%d bits" % (len(s2_bits), len(s2_bits)))

    # S3: every bar open/close site routes through the helper; no raw
    # class mutation survives outside it.
    helper = src[src.index("function pfSetBarOpen(open) {"):]
    helper = helper[:helper.index("\n    }\n") + len("\n    }\n")]
    stripped = src.replace(helper, "", 1)
    raw = [p for p in ("pfBar.classList.add('visible')",
                       "pfBar.classList.remove('visible')",
                       "pfToggle.classList.add('active')",
                       "pfToggle.classList.remove('active')")
           if p in stripped]
    callers = src.count("pfSetBarOpen(")
    check("S3 all open/close sites use pfSetBarOpen, no raw class mutation left",
          not raw and callers >= 4,  # 1 def + 3 call sites
          ("raw mutation left: %s" % raw) if raw else ("pfSetBarOpen occurrences: %d" % callers))


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
    const t = document.getElementById('path-finder-toggle');
    const b = document.getElementById('path-finder-bar');
    if (!t || !b) return null;
    return {
        aria: t.getAttribute('aria-expanded'),
        controls: t.getAttribute('aria-controls'),
        visible: b.classList.contains('visible'),
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
            pg.click('a[data-section="peer-network-section"]')
            pg.wait_for_selector("#network-graph canvas", timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: initial state -- collapsed, aria-expanded=false.
            s0 = pg.evaluate(TOGGLE_STATE_JS)
            check("R1 initial: aria-expanded=false, bar hidden, toggle inactive",
                  s0 and s0["aria"] == "false" and s0["controls"] == "path-finder-bar"
                  and s0["visible"] is False and s0["active"] is False,
                  str(s0) if not (s0 and s0["aria"] == "false" and s0["visible"] is False) else "")

            # R2: click opens -- full state flip.
            pg.click("#path-finder-toggle")
            pg.wait_for_timeout(400)
            s1 = pg.evaluate(TOGGLE_STATE_JS)
            check("R2 click opens (aria=true, .visible, .active)",
                  s1 and s1["aria"] == "true" and s1["visible"] is True and s1["active"] is True,
                  str(s1) if not (s1 and s1["aria"] == "true" and s1["visible"] is True) else "")

            # R3: second click closes -- back to the R1 state.
            pg.click("#path-finder-toggle")
            pg.wait_for_timeout(400)
            s2 = pg.evaluate(TOGGLE_STATE_JS)
            check("R3 second click closes (aria=false, hidden, inactive)",
                  s2 and s2["aria"] == "false" and s2["visible"] is False and s2["active"] is False,
                  str(s2) if not (s2 and s2["aria"] == "false" and s2["visible"] is False) else "")

            # R4: programmatic open via findNetworkPath flips aria too
            # (the pfPrefill / findNetworkPath open path, not the click).
            pg.evaluate("window.findNetworkPath('AAPL', 'MSFT')")
            pg.wait_for_timeout(800)
            s3 = pg.evaluate(TOGGLE_STATE_JS)
            check("R4 findNetworkPath opens bar with aria-expanded=true",
                  s3 and s3["aria"] == "true" and s3["visible"] is True and s3["active"] is True,
                  str(s3) if not (s3 and s3["aria"] == "true" and s3["visible"] is True) else "")

            # R5: zero JS page errors across the run.
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
