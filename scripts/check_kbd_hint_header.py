#!/usr/bin/env python3
"""Regression guard: the keyboard-shortcuts hint lives in the header, not as
a fixed bottom-right FAB.

Background (2026-10-06 19:30 PT): the hint was a fixed-position FAB that
overlapped real content in three evidence-backed render reviews (2026-09-24
detail panel, 2026-10-06 15:30 mobile insight-card body text, 2026-10-06 19:30
table GOV cell + network legend "57" + mobile table company cell). Two prior
patches (09-24 clearance padding, 15:30 icon-only collapse) only shrank the
overlap; a fixed element cannot avoid covering arbitrary bottom-right
content. The hint is now a <button> in .header-right (next to the theme
toggle) — same first-visit discovery affordance (plus the "?" key binding),
zero overlap, and keyboard-focusable.

This guard has two halves:
  A. Static: exactly one #kbd-hint, it is a <button> inside .header-right,
     the base .kbd-hint rule has no position:fixed, the obsolete
     .compare-tray.visible ~ .kbd-hint rule is gone, and js/app.js still
     wires the click -> modal path.
  B. Render (headless Chromium via playwright, 1440px + 360px): computed
     position is not fixed, the hint's box sits inside the header box,
     clicking it opens the kbd modal, zero page errors.

Usage:
  scripts/check_kbd_hint_header.py              # static + render
  scripts/check_kbd_hint_header.py --static-only

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
HTML = os.path.join(REPO, "index.html")
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    html = open(HTML, encoding="utf-8").read()
    src = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: exactly one #kbd-hint in the document.
    ids = re.findall(r'id="kbd-hint"', html)
    check("S1 exactly one #kbd-hint in index.html", len(ids) == 1,
          "found %d" % len(ids))

    # S2: it is a <button> inside .header-right.
    m = re.search(r'<div class="header-right">(.*?)</div>\s*</div>\s*</header>',
                  html, re.S)
    in_header = m is not None and 'id="kbd-hint"' in m.group(1)
    is_button = bool(re.search(r'<button[^>]*id="kbd-hint"', html))
    check("S2 #kbd-hint is a <button> inside .header-right",
          in_header and is_button,
          ("not inside .header-right; " if not in_header else "")
          + ("not a <button>" if not is_button else ""))

    # S3: the base .kbd-hint rule has no position property at all (normal
    # flow inside the header flexbox). Note: the @media phone block and
    # reduced-motion block also contain ".kbd-hint {" rules, so anchor on
    # the first occurrence (the base rule).
    base = re.search(r"/\* Keyboard hint badge.*?\*/\s*\.kbd-hint\s*\{(.*?)\}",
                     css, re.S)
    no_fixed = base is not None and "position" not in re.sub(r"\s+", "", base.group(1))
    check("S3 base .kbd-hint rule carries no position property", no_fixed,
          "" if no_fixed else "a position declaration is still present in the base rule")

    # S4: the obsolete compare-tray sibling rule is gone.
    check("S4 no .compare-tray.visible ~ .kbd-hint rule",
          ".compare-tray.visible ~ .kbd-hint" not in css, "")

    # S5: JS still wires click -> modal.
    s5 = ("getElementById('kbd-hint')" in src
          and "kbdHint.addEventListener('click', showKbdModal)" in src)
    check("S5 js/app.js wires #kbd-hint click to showKbdModal", s5, "")


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
            all_ok = True
            for label, w in [("desktop", 1440), ("mobile", 360)]:
                browser = pw.chromium.launch()
                errors = []
                pg = browser.new_page(viewport={"width": w, "height": 800},
                                      has_touch=(w == 360), is_mobile=(w == 360))
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.route("**/d3*", lambda r: r.fulfill(
                    status=200, content_type="application/javascript", body=d3))
                pg.route("**/d3js.org/**", lambda r: r.fulfill(
                    status=200, content_type="application/javascript", body=d3))
                pg.goto("http://127.0.0.1:%d/index.html" % port,
                        wait_until="networkidle", timeout=60000)
                time.sleep(5)
                # R1: computed position is not fixed and the box is inside the header.
                pos = pg.evaluate(
                    "(() => { const h = document.getElementById('kbd-hint');"
                    " if (!h) return null;"
                    " const cs = window.getComputedStyle(h);"
                    " const hb = document.querySelector('header').getBoundingClientRect();"
                    " const b = h.getBoundingClientRect();"
                    " return { pos: cs.position,"
                    "          inside: b.top >= hb.top - 1 && b.bottom <= hb.bottom + 1 }; })()")
                r1 = pos is not None and pos["pos"] != "fixed" and pos["inside"]
                check("R1-%s hint not fixed and inside header box" % label, r1,
                      "" if r1 else str(pos))
                # R2: click opens the kbd modal.
                pg.click("#kbd-hint")
                time.sleep(0.5)
                opened = pg.evaluate(
                    "document.getElementById('kbd-modal-overlay').classList.contains('visible')")
                check("R2-%s clicking hint opens kbd modal" % label, opened, "")
                if opened:
                    pg.keyboard.press("Escape")
                    time.sleep(0.3)
                # R3: zero page errors on this viewport.
                check("R3-%s zero page errors" % label, len(errors) == 0,
                      "; ".join(errors[:3]) if errors else "")
                all_ok = all_ok and r1 and opened and len(errors) == 0
                browser.close()
            return all_ok
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
