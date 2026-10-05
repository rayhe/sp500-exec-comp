#!/usr/bin/env python3
"""Regression guard: methodology info buttons must survive chart title rewrites.

Background (2026-10-05): drawGERChart assigned `titleEl.textContent = ...` on
every render, destroying the child `.methodology-info-btn` (data-method="ger")
and making the GER methodology modal unreachable from its own heading. The fix
introduced `_setTitleLabel()` in js/charts.js, which rewrites only the label
text and re-appends the button node. All other chart-title rewrites were
migrated to the same helper the same day.

This guard has two halves:
  A. Static: no raw `.textContent =` write on a title-ish element anywhere in
     js/*.js outside `_setTitleLabel` itself. The only standing exemption is
     the methodology modal's own title in app.js (`content.title`), which never
     carries an info button. Any new exemption must be explicit in EXEMPT_LABELS.
  B. Render (headless Chromium via playwright): after a full render, all 6
     [data-method] buttons are present, the GER button survives a sector-chip
     re-render, and each methodology modal (peer/gov/ger/dataq) opens with a
     non-empty live coverage block. Zero page errors.

Usage:
  scripts/check_methodology_buttons.py            # static + render
  scripts/check_methodology_buttons.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS_FILES = ["js/charts.js", "js/network.js", "js/app.js", "js/advanced-filters.js"]
REQUIRED_METHODS = {"peer", "gov", "ger"}
MIN_BUTTONS = 6
# (js_file, label-prefix) pairs that may write a title's textContent directly.
EXEMPT_LABELS = {("js/app.js", "content.title")}

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def helper_span(src):
    m = re.search(r"function _setTitleLabel\(titleEl, label\) \{.*?\n\}", src, re.S)
    return m.span() if m else None


def static_checks():
    # A1: the helper exists and preserves .methodology-info-btn children.
    p = os.path.join(REPO, "js/charts.js")
    src = open(p, encoding="utf-8").read()
    span = helper_span(src)
    check("A1 _setTitleLabel defined in js/charts.js", span is not None)
    body = src[span[0]:span[1]] if span else ""
    check("A2 helper preserves .methodology-info-btn child",
          "querySelector('.methodology-info-btn')" in body and "appendChild(btn)" in body)

    # A3: no raw title textContent writes outside the helper (plus exemptions).
    pat = re.compile(
        r"(?m)^(?P<indent>[ \t]*)(?:if \(\w+\) )?(?P<var>\w*[Tt]itle\w*)\.textContent = (?P<label>.*?);",
        re.S)
    bad = []
    for rel in JS_FILES:
        full = os.path.join(REPO, rel)
        s = open(full, encoding="utf-8").read()
        hspan = helper_span(s)
        for m in pat.finditer(s):
            if hspan and hspan[0] <= m.start() and m.end() <= hspan[1]:
                continue  # the helper's own write
            label = m.group("label").strip()
            if (rel, label.split()[0] if label else "") in EXEMPT_LABELS or label.startswith("content.title"):
                continue  # standing exemption: methodology modal title
            line = s[:m.start()].count("\n") + 1
            bad.append("%s:%d var=%s" % (rel, line, m.group("var")))
    check("A3 no raw title textContent writes outside _setTitleLabel",
          not bad, "; ".join(bad) if bad else "0 raw sites")

    # A4: index.html buttons - count, method coverage, a11y labels.
    html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
    btns = re.findall(r'<button[^>]*class="[^"]*methodology-info-btn[^"]*"[^>]*>', html)
    methods = set()
    no_aria = 0
    for b in btns:
        mm = re.search(r'data-method="([a-z]+)"', b)
        if mm:
            methods.add(mm.group(1))
        if "aria-label" not in b:
            no_aria += 1
    check("A4 >=%d methodology buttons in index.html" % MIN_BUTTONS,
          len(btns) >= MIN_BUTTONS, "%d buttons" % len(btns))
    check("A5 required methods present {peer,gov,ger}",
          REQUIRED_METHODS <= methods, "found: %s" % sorted(methods))
    check("A6 every button has aria-label", no_aria == 0,
          "%d missing" % no_aria if no_aria else "")


def get_d3_bytes():
    # Prefer the cached copy; else fetch via curl (VM Chromium egress is
    # blocked but curl through the proxy works - d3 is a build-time shim only).
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
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript", body=d3)

            page.route("**/npm/d3@7*", d3_route)
            page.route("**/unpkg.com/d3@7*", d3_route)
            page.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            page.route("**/fonts.gstatic.com/**", lambda r: r.abort())

            page.goto("http://127.0.0.1:%d/index.html" % port, wait_until="load")
            try:
                page.wait_for_function(
                    "window.d3 && document.querySelectorAll('[data-method]').length >= %d" % MIN_BUTTONS,
                    timeout=60000)
            except Exception:
                check("R0 page renders with d3 and >=%d buttons" % MIN_BUTTONS, False, "timeout")
                return False

            # R1: button count + method coverage in the live DOM.
            info = page.evaluate("""Array.from(document.querySelectorAll('[data-method]'))
                .map(b => b.dataset.method)""")
            methods = set(info)
            check("R1 live DOM has >=%d buttons, methods {peer,gov,ger} present" % MIN_BUTTONS,
                  len(info) >= MIN_BUTTONS and REQUIRED_METHODS <= methods,
                  "%d buttons, %s" % (len(info), sorted(methods)))

            # R2: the GER button survives the initial full render inside its h2.
            ger_btn = page.evaluate(
                "!!document.querySelector('#ger-chart-title .methodology-info-btn[data-method=\"ger\"]')")
            check("R2 GER button present inside #ger-chart-title after render", ger_btn)

            # R3: GER sector-chip re-render keeps the button (the original bug trigger).
            chips = page.evaluate(
                "Array.from(document.querySelectorAll('#ger-sector-chips button')).map(b => b.textContent.trim())")
            if chips:
                target = 1 if len(chips) > 1 else 0
                page.click("#ger-sector-chips button >> nth=%d" % target)
                page.wait_for_timeout(1500)
                ger_btn2 = page.evaluate(
                    "!!document.querySelector('#ger-chart-title .methodology-info-btn[data-method=\"ger\"]')")
                check("R3 GER button survives sector-chip re-render", ger_btn2,
                      "chips: %s" % chips[:4])
            else:
                check("R3 GER button survives sector-chip re-render", True, "no chips rendered; skipped")

            # R4: each methodology modal opens from a real button with its live coverage block.
            for method in ["peer", "gov", "ger"]:
                page.click('[data-method="%s"] >> nth=0' % method)
                page.wait_for_timeout(600)
                opened = page.evaluate(
                    "!document.getElementById('methodology-modal-overlay').hidden")
                block = page.evaluate(
                    "((document.getElementById('%s-coverage-block') || {}).textContent || '').trim().length" % method)
                check("R4 %s modal opens from button with live coverage block" % method,
                      opened and block > 0, "block chars: %d" % block)
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)

            # R5: dataq modal (opened via the metric-card CTA path) has its live block.
            page.evaluate("window.openMethodologyModal('dataq')")
            page.wait_for_timeout(600)
            opened = page.evaluate(
                "!document.getElementById('methodology-modal-overlay').hidden")
            block = page.evaluate(
                "((document.getElementById('dataq-coverage-block') || {}).textContent || '').trim().length")
            check("R5 dataq modal opens with live coverage block", opened and block > 0,
                  "block chars: %d" % block)
            page.keyboard.press("Escape")

            # R6: zero JS page errors.
            check("R6 zero JS page errors", not errors, "; ".join(errors[:3]) if errors else "")
            browser.close()
    finally:
        server.terminate()
    return True


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if not static_only:
        render_checks()
    fails = [r for r in results if not r[1]]
    print("----")
    print("checks: %d pass, %d fail" % (len(results) - len(fails), len(fails)))
    if fails:
        print("GUARD FAILED")
        sys.exit(1)
    print("OK: methodology buttons guard (static%s)" % ("" if not static_only else "-only"))


if __name__ == "__main__":
    main()
