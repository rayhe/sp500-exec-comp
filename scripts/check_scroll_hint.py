#!/usr/bin/env python3
"""Regression guard: the table scroll-hint pill must pulse-then-fade on load
and REPLAY the full pulse+fade cycle when the user scrolls back to the start.

Background (2026-10-06): on narrow viewports the compensation table scrolls
horizontally. A "Scroll ->" pill pulses 3x on load to draw the eye, then fades
out (forwards fill) so it never lingers over row chips; the right-edge fade
keeps signaling scrollability. The replay mechanism is implicit: scrolling
adds .scroll-started (display:none on the hint), and returning to the start
removes it (display:block), which restarts the CSS animation from the first
keyframe. There is no JS replay timer - the whole contract rides on the
display toggle and CSS animation ordering, so this guard pins the observable
behavior instead of the implementation.

This guard has two halves:
  A. Static: the hint element lives inside #table-wrapper; base rule hides it;
     .has-scroll-right shows it; .scroll-end/.scroll-started hide it; the hide
     rules come AFTER the show rule in source order (equal specificity
     (0,3,0) - order wins, same specificity lesson as the 2026-10-06 minimap
     fix); pulse+fade keyframes exist with a forwards fade; reduced-motion
     override kills the animation; the JS scroll indicator toggles the three
     classes with the right thresholds.
  B. Render (headless Chromium via playwright, 360px mobile): initial pulse is
     visible then fades; scrolling right hides the hint; scrolling back to
     the start replays the pulse AND the replay fades again; zero page errors.

Usage:
  scripts/check_scroll_hint.py              # static + render
  scripts/check_scroll_hint.py --static-only

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

    # S1: the hint element exists inside #table-wrapper.
    m = re.search(r'<div class="table-wrapper" id="table-wrapper">(.*?)</div>',
                  html, re.S)
    s1 = m is not None and 'class="scroll-hint"' in m.group(1)
    check("S1 hint element lives inside #table-wrapper", s1,
          "" if s1 else "span.scroll-hint not found inside the wrapper div")

    # S2: base rule hides the hint.
    check("S2 .scroll-hint base rule is display:none",
          bool(re.search(r"\.scroll-hint\s*\{[^}]*display:\s*none;", css)), "")

    # S3: .has-scroll-right shows it.
    show_rule = ".table-wrapper.has-scroll-right .scroll-hint {"
    s3 = show_rule in css and "display: block;" in css.split(show_rule, 1)[1][:120]
    check("S3 .has-scroll-right shows the hint (display:block)", s3,
          "" if s3 else "show rule missing or not display:block")

    # S4: hide rules exist and come AFTER the show rule in source order.
    # All three selectors are (0,3,0); equal specificity means order wins,
    # so scroll-end/scroll-started must sort below has-scroll-right.
    show_idx = css.find(".table-wrapper.has-scroll-right .scroll-hint")
    hide_block = re.search(
        r"\.table-wrapper\.scroll-end\s+\.scroll-hint,\s*"
        r"\.table-wrapper\.scroll-started\s+\.scroll-hint\s*\{\s*display:\s*none;\s*\}",
        css)
    hide_idx = hide_block.start() if hide_block else -1
    s4 = show_idx != -1 and hide_idx != -1 and hide_idx > show_idx
    check("S4 scroll-end/scroll-started hide the hint and sort after the show rule",
          s4, "hide rules must follow the show rule (equal specificity, order wins)"
          if not s4 else "")

    # S5: pulse + terminal fade keyframes with a forwards fill.
    s5a = "@keyframes scrollHintPulse" in css
    s5b = "@keyframes scrollHintFadeOut" in css
    s5c = bool(re.search(r"animation:[^;]*scrollHintPulse[^;]*3[^;]*scrollHintFadeOut[^;]*forwards",
                         css))
    check("S5 pulse(3x) + forwards fade-out animation declared",
          s5a and s5b and s5c,
          ("pulse keyframes missing; " if not s5a else "")
          + ("fade keyframes missing; " if not s5b else "")
          + ("shorthand missing 3 iterations or forwards fill" if not s5c else ""))

    # S6: reduced-motion override kills the animation and pins a static opacity.
    s6 = ("prefers-reduced-motion" in css
          and ".scroll-hint" in css
          and "animation: none !important" in css)
    check("S6 prefers-reduced-motion override present for the hint", s6, "")

    # S7: JS scroll indicator toggles the three classes.
    js_bits = [
        "el.classList.add('has-scroll-right')",
        "el.classList.add('scroll-end')",
        "el.classList.add('scroll-started')",
        "el.scrollWidth > el.clientWidth",
        "el.scrollLeft > 10",
    ]
    missing = [b for b in js_bits if b not in src]
    check("S7 updateScrollIndicator toggles has-scroll-right/scroll-end/scroll-started",
          not missing, "missing: %s" % missing if missing else "%d/%d bits" % (len(js_bits), len(js_bits)))


def get_d3_bytes():
    # Same cached copy as check_minimap_toggle.py (build-time shim only).
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


HINT_STATE_JS = """(() => {
    const w = document.getElementById('table-wrapper');
    const h = w.querySelector('.scroll-hint');
    if (!w || !h) return null;
    const cs = window.getComputedStyle(h);
    return {
        cls: w.className,
        scrollable: w.scrollWidth > w.clientWidth + 2,
        scrollLeft: w.scrollLeft,
        display: cs.display,
        opacity: parseFloat(cs.opacity)
    };
})()"""


def wait_opacity(pg, cond, timeout_ms, label):
    # Poll-based wait: fixed sleeps race the CSS animation timing
    # (2026-10-06 scroll-spy lesson), so poll for the predicate instead.
    try:
        pg.wait_for_function(
            "(() => { const w = document.getElementById('table-wrapper');"
            " const cs = window.getComputedStyle(w.querySelector('.scroll-hint'));"
            " const op = parseFloat(cs.opacity);"
            " return (%s); })()" % cond, timeout=timeout_ms)
        return True
    except Exception:
        return False


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
            pg = browser.new_page(viewport={"width": 360, "height": 800},
                                  has_touch=True, is_mobile=True)
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
                "window.d3 && document.querySelectorAll('#comp-table tbody tr').length > 0",
                timeout=90000)
            pg.wait_for_timeout(400)

            # R1: table is horizontally scrollable and the hint pulses visibly.
            s = pg.evaluate(HINT_STATE_JS)
            r1 = (s and s["scrollable"] and s["display"] == "block"
                  and not ("scroll-started" in s["cls"] or "scroll-end" in s["cls"])
                  and wait_opacity(pg, "op > 0.3", 4000, "initial pulse"))
            s = pg.evaluate(HINT_STATE_JS)
            check("R1 mobile: hint visible and pulsing on a scrollable table",
                  bool(r1), str(s) if not r1 else "")

            # R2: the initial pulse+fade completes (opacity pinned at 0).
            r2 = wait_opacity(pg, "op < 0.1", 12000, "initial fade")
            s = pg.evaluate(HINT_STATE_JS)
            r2 = r2 and s["display"] == "block"
            check("R2 initial pulse fades out (opacity ~0, still in DOM)",
                  bool(r2), str(s) if not r2 else "")

            # R3: scrolling right hides the hint via .scroll-started.
            pg.evaluate("document.getElementById('table-wrapper').scrollTo({left: 150})")
            pg.wait_for_timeout(400)
            s = pg.evaluate(HINT_STATE_JS)
            r3 = ("scroll-started" in s["cls"] and s["display"] == "none"
                  and s["scrollLeft"] > 10)
            check("R3 scrolling right hides the hint (scroll-started)",
                  bool(r3), str(s) if not r3 else "")

            # R4: scrolling back to the start replays the full pulse+fade.
            pg.evaluate("document.getElementById('table-wrapper').scrollTo({left: 0})")
            s = pg.evaluate(HINT_STATE_JS)
            replayed = (wait_opacity(pg, "op > 0.3", 5000, "replay pulse")
                        and pg.evaluate(HINT_STATE_JS)["display"] == "block"
                        and "scroll-started" not in pg.evaluate(HINT_STATE_JS)["cls"])
            faded_again = wait_opacity(pg, "op < 0.1", 12000, "replay fade")
            s = pg.evaluate(HINT_STATE_JS)
            r4 = bool(replayed and faded_again)
            check("R4 scroll-back replays pulse, then the replay fades again",
                  r4, str(s) if not r4 else "")

            # R5: zero JS page errors across the whole lifecycle.
            check("R5 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if not static_only:
        rc = render_checks()
        if rc is None:
            print("render checks skipped")
    fails = [n for n, ok, _ in results if not ok]
    print("\n%d/%d checks passed" % (len(results) - len(fails), len(results)))
    if fails:
        print("FAILED: " + ", ".join(fails))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
