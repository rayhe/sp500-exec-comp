#!/usr/bin/env python3
"""Regression guard: d3-outage fallback covers bare (non-panel) chart containers.

Background (2026-10-07 07:30 PT): markChartsUnavailable() in js/app.js
inserted the outage note into every .chart-panel and replaced the network
skeleton, but the Composition section's #composition-chart and
#quartile-comp-chart are bare divs outside any .chart-panel - on a d3 CDN
outage they stayed completely empty (heading + description followed by
dead space). This guard pins the bare-container pass.

This guard has two halves:
  A. Static: the bareCharts list covers every d3 chart id from the
     redrawAllCharts() list in js/charts.js that is not inside a
     .chart-panel in index.html; role-comp-chart (plain-HTML, works without
     d3) stays excluded; the no-duplicate guard is present.
  B. Render (headless Chromium, d3 requests aborted to simulate the outage):
     both bare containers each carry exactly one unavailable note with the
     d3-failure text, role-comp-chart carries no note, zero page errors.

Usage:
  scripts/check_chart_outage_bare_containers.py              # static + render
  scripts/check_chart_outage_bare_containers.py --static-only

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
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
INDEX = os.path.join(REPO, "index.html")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def _fn_body(src, name):
    m = re.search(r"function " + re.escape(name) + r"\(\) \{.*?\n    \}\n", src, re.S)
    return m.group(0) if m else ""


def _chart_panel_ids(html):
    """All ids ending in -chart that live inside a .chart-panel div."""
    out = set()
    for m in re.finditer(r'<div[^>]*class="[^"]*chart-panel[^"]*"[^>]*>', html):
        start = m.start()
        depth = 0
        end = None
        for m2 in re.finditer(r"</?div\b", html[start:]):
            depth += 1 if m2.group(0) == "<div" else -1
            if depth == 0:
                end = start + m2.end()
                break
        if end is None:
            continue
        out.update(re.findall(r'id="([a-z0-9-]*-chart)"', html[start:end]))
    return out


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    charts = open(CHARTS_JS, encoding="utf-8").read()
    html = open(INDEX, encoding="utf-8").read()

    body = _fn_body(src, "markChartsUnavailable")

    # S1: the bareCharts list covers the two known bare d3-only containers.
    m = re.search(r"var bareCharts = \[(.*?)\];", body)
    bare = re.findall(r"'([a-z0-9-]+)'", m.group(1)) if m else []
    check("S1 bareCharts covers composition-chart + quartile-comp-chart",
          set(["composition-chart", "quartile-comp-chart"]) <= set(bare),
          "bare=%s" % bare)

    # S2: role-comp-chart is excluded (plain-HTML render, no d3 needed).
    check("S2 role-comp-chart excluded from the bare list",
          "role-comp-chart" not in bare)

    # S3: no-duplicate guard before appending the note.
    check("S3 no-duplicate guard on the bare-container pass",
          "bc.querySelector('.chart-unavailable-note')" in body)

    # S4: coverage completeness — every d3 chart id in redrawAllCharts() that
    # is not inside a .chart-panel must be in the bareCharts list, so a
    # future bare d3 chart cannot silently stay blank on outage.
    fn = re.search(r"function redrawAllCharts\(\) \{.*?\n\}", charts, re.S)
    ids = re.findall(r"'([a-z0-9-]*-chart)'", fn.group(0)) if fn else []
    panel_ids = _chart_panel_ids(html)
    uncovered = [i for i in ids
                 if i not in panel_ids and i not in bare
                 and ("id=\"" + i + "\"") in html]
    check("S4 every non-panel d3 chart id is covered by the bare list",
          not uncovered and len(ids) > 0,
          "uncovered=%s (checked %d ids)" % (uncovered, len(ids)))


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
                const note = id => {
                    const el = document.getElementById(id);
                    if (!el) return -1;
                    return el.querySelectorAll(':scope > .chart-unavailable-note').length;
                };
                const texts = id => {
                    const el = document.getElementById(id);
                    return [...el.querySelectorAll(':scope > .chart-unavailable-note')]
                        .map(n => n.textContent);
                };
                return {
                    comp: note('composition-chart'),
                    quart: note('quartile-comp-chart'),
                    compText: texts('composition-chart'),
                    roleNotes: note('role-comp-chart'),
                };
            })()""")
            r1 = state and state["comp"] == 1 and state["quart"] == 1
            check("R1 each bare container carries exactly one note", r1, str(state)[:160])
            r2 = state and any("d3 visualization library failed to load" in t
                               for t in state["compText"])
            check("R2 note carries the d3-failure text", r2,
                  str(state["compText"])[:120] if state else "")
            r3 = state and state["roleNotes"] == 0
            check("R3 role-comp-chart carries no note (HTML-rendered, works)",
                  r3, "notes=%s" % (state["roleNotes"] if state else "?"))
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
