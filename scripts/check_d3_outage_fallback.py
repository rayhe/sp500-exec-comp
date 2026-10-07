#!/usr/bin/env python3
"""Regression guard: the d3-outage fallback replaces the network skeleton.

Background (2026-10-07 03:30 PT): the boot code injects a "Loading peer
network..." skeleton into #network-graph before the d3 availability check
runs. When the d3 CDN bundle fails to load, initNetwork is skipped and the
old markChartsUnavailable() only inserted a notice into the network
controls wrapper (.network-overflow-wrapper) - the skeleton spinner stayed
visible forever in the graph area, promising a load that would never happen
(see /tmp/sec_peer-network-section.png from the 2026-10-07 render review).

This guard has two halves:
  A. Static: markChartsUnavailable() replaces the #network-graph skeleton
     with a .network-unavailable-state empty state (no spinner), the old
     wrapper-insertion code is gone, exactly one "Network graph unavailable"
     string lives in js/app.js, and css/style.css styles the empty state.
  B. Render (headless Chromium, d3 requests aborted to simulate the outage):
     the skeleton spinner is gone, exactly one unavailable note renders in
     #network-graph, it carries the d3-failure text, zero page errors.

Usage:
  scripts/check_d3_outage_fallback.py              # static + render
  scripts/check_d3_outage_fallback.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""
import os
import re
import socket
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: markChartsUnavailable clears the #network-graph skeleton.
    m = re.search(r"function markChartsUnavailable\(\) \{.*?\n    \}\n", src, re.S)
    body = m.group(0) if m else ""
    check("S1 markChartsUnavailable replaces the network skeleton",
          "getElementById('network-graph')" in body
          and ".network-unavailable-state" in body
          and "netGraph.innerHTML = ''" in body,
          "" if body else "markChartsUnavailable not found")

    # S2: the old wrapper-insertion path is gone (it duplicated the notice
    # in the controls area while the spinner stayed in the graph area).
    check("S2 old network-overflow-wrapper insertion is gone",
          "querySelector('#peer-network-section .network-overflow-wrapper')" not in src)

    # S3: exactly one "Network graph unavailable" string (no duplicated note).
    n = src.count("Network graph unavailable")
    check("S3 exactly one 'Network graph unavailable' string", n == 1, "count=%d" % n)

    # S4: CSS styles the empty state.
    check("S4 .network-unavailable-state styled in css/style.css",
          re.search(r"\.network-unavailable-state\s*\{", css) is not None)


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
            # Deterministically simulate the d3 outage on all three fallback hosts.
            pg.route("**/d3*", lambda r: r.abort())
            pg.route("**/d3js.org/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port,
                    wait_until="networkidle", timeout=60000)
            time.sleep(4)
            state = pg.evaluate("""(() => {
                const g = document.getElementById('network-graph');
                const notes = [...g.querySelectorAll('.chart-unavailable-note')]
                    .map(n => n.textContent);
                return {
                    hasSpinner: !!g.querySelector('.skeleton-network-spinner'),
                    hasState: !!g.querySelector('.network-unavailable-state'),
                    notes,
                    sectionNotes: document.querySelectorAll(
                        '#peer-network-section .chart-unavailable-note').length,
                };
            })()""")
            r1 = state and not state["hasSpinner"] and state["hasState"]
            check("R1 skeleton spinner gone, unavailable state present", r1, str(state)[:160])
            r2 = state and any("d3 visualization library failed to load" in t for t in state["notes"])
            check("R2 note carries the d3-failure text", r2, str(state["notes"])[:160] if state else "")
            r3 = state and state["sectionNotes"] == 1
            check("R3 exactly one unavailable note in the network section", r3,
                  "count=%s" % (state["sectionNotes"] if state else "?"))
            r4 = len(errors) == 0
            check("R4 zero page errors", r4, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1 and r2 and r3 and r4
    finally:
        server.terminate()


def main():
    static_checks()
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = render_checks()
    if ok is None:
        print("render checks skipped")
        failed = [r for r in results if not r[1]]
        return 1 if failed else 0
    failed = [r for r in results if not r[1]]
    if failed or not ok:
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
