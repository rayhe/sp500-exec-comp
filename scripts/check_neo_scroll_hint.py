#!/usr/bin/env python3
"""Regression guard: detail-panel table wraps (.neo-table-wrap, .pvp-table-wrap)
must show the same pulse-then-fade "Scroll ->" hint as the main table on narrow
viewports, with scroll-back replay.

Background (2026-10-07): the main #table-wrapper got a scroll-hint pill on
2026-10-06, but the company detail panel's NEO and Pay-vs-Performance tables
were left without one. On a 360px phone the NEO table shows NAME/TITLE/SALARY
and cuts off the remaining 6-7 columns (Stock Awards, Option Awards, ...,
Total) with no discoverability cue - the same glitch class the main-table fix
addressed. The fix reuses the shared .scroll-hint pill + pulse(3x)/fade CSS
contract via _wireScrollHint/_updateScrollHint helpers, wired at detail render
and re-checked when year tabs or the side-by-side toggle reveal hidden panels.

This guard has two halves:
  A. Static: the hint span is emitted inside both wrap producers; both wraps
     are position:relative (the pill is absolutely positioned); the scoped
     show rules come BEFORE the hide rules in source order (equal
     specificity - order wins, same lesson as the 2026-10-06 minimap fix);
     _wireScrollHint/_updateScrollHint exist and are wired at detail render;
     year-tab and SBS handlers re-check revealed panels.
  B. Render (headless Chromium via playwright, 360px mobile): expand TSLA's
     row; the visible .neo-table-wrap is scrollable and its hint pulses;
     the pulse fades; scrolling the wrap right hides the hint; scrolling back
     replays the pulse AND the replay fades; the .pvp-table-wrap hint pulses;
     zero page errors.

Usage:
  scripts/check_neo_scroll_hint.py              # static + render
  scripts/check_neo_scroll_hint.py --static-only

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
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    # S1: hint span emitted inside the NEO table wrap producer.
    s1 = '<div class="neo-table-wrap"><span class="scroll-hint"' in src
    check("S1 scroll-hint span emitted inside .neo-table-wrap", s1,
          "" if s1 else "neo wrap producer does not emit the hint")

    # S2: hint span emitted inside the PvP table wrap producer.
    s2 = '<div class="pvp-table-wrap"><span class="scroll-hint"' in src
    check("S2 scroll-hint span emitted inside .pvp-table-wrap", s2,
          "" if s2 else "pvp wrap producer does not emit the hint")

    # S3: both wraps are position:relative (the pill is absolutely positioned).
    neo_rel = bool(re.search(r"\.neo-table-wrap\s*\{[^}]*position:\s*relative;", css))
    pvp_rel = bool(re.search(r"\.pvp-table-wrap\s*\{[^}]*position:\s*relative;", css))
    check("S3 .neo-table-wrap and .pvp-table-wrap are position:relative",
          neo_rel and pvp_rel,
          ("neo wrap missing position:relative; " if not neo_rel else "")
          + ("pvp wrap missing position:relative" if not pvp_rel else ""))

    # S4: scoped show rules exist (display:block) and hide rules sort after them.
    show_neo = css.find(".neo-table-wrap.has-scroll-right .scroll-hint")
    show_pvp = css.find(".pvp-table-wrap.has-scroll-right .scroll-hint")
    s4a = show_neo != -1 and "display: block;" in css[show_neo:show_neo + 140]
    s4b = show_pvp != -1 and "display: block;" in css[show_pvp:show_pvp + 140]
    hide_m = re.search(
        r"\.neo-table-wrap\.scroll-end\s+\.scroll-hint,.*?"
        r"\.pvp-table-wrap\.scroll-started\s+\.scroll-hint\s*\{\s*display:\s*none;\s*\}",
        css, re.S)
    s4c = hide_m is not None and hide_m.start() > show_neo and hide_m.start() > show_pvp
    check("S4 show rules display:block and hide rules sort after them",
          s4a and s4b and s4c,
          ("show rule missing; " if not (s4a and s4b) else "")
          + ("hide rules missing or not after show rules" if not s4c else ""))

    # S5: shared helpers exist and are wired at detail render for both wraps.
    s5a = "function _updateScrollHint(el)" in src and "function _wireScrollHint(el)" in src
    s5b = ".neo-table-wrap, .pvp-table-wrap').forEach(_wireScrollHint)" in src
    check("S5 _wireScrollHint/_updateScrollHint wired at detail render for both wraps",
          s5a and s5b,
          ("helpers missing; " if not s5a else "")
          + ("detail-render wiring missing" if not s5b else ""))

    # S6: year-tab switch and SBS toggle re-check revealed panels.
    tab_recheck = src.count("section.querySelectorAll('.neo-table-wrap').forEach(_updateScrollHint)")
    check("S6 year-tab and SBS handlers re-check revealed panels",
          tab_recheck >= 2,
          "expected 2 re-check call sites, found %d" % tab_recheck if tab_recheck < 2 else "")


def get_d3_bytes():
    # Same cached copy as check_scroll_hint.py (build-time shim only).
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


HINT_OPACITY_JS = ("parseFloat(window.getComputedStyle("
                   "document.querySelector('.detail-panel %s .scroll-hint')"
                   ").opacity)")

WRAP_STATE_JS = """((cls) => {
    const w = document.querySelector('.detail-panel ' + cls + ' .scroll-hint')
        ? document.querySelector('.detail-panel ' + cls) : null;
    if (!w) return null;
    const h = w.querySelector('.scroll-hint');
    const cs = window.getComputedStyle(h);
    return {
        cls: w.className,
        scrollable: w.scrollWidth > w.clientWidth + 2,
        scrollLeft: w.scrollLeft,
        display: cs.display,
        opacity: parseFloat(cs.opacity)
    };
})('%s')"""


def wait_cond(pg, js_expr, timeout_ms):
    try:
        pg.wait_for_function(js_expr, timeout=timeout_ms)
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
            # Expand TSLA's row (DOM click; delegated tbody handler builds the panel).
            pg.evaluate(
                "[...document.querySelectorAll('#comp-table tbody tr')]"
                ".find(r => r.textContent.includes('Tesla')).click()")
            pg.wait_for_function(
                "document.querySelector('.detail-panel .neo-table-wrap') !== null",
                timeout=30000)
            pg.evaluate("document.querySelector('.detail-panel').scrollIntoView()")
            pg.wait_for_timeout(500)

            def state(cls):
                return pg.evaluate(WRAP_STATE_JS % cls)

            # R1: NEO wrap scrollable, hint pulses visibly.
            s = state(".neo-table-wrap")
            r1 = (s and s["scrollable"] and s["display"] == "block"
                  and wait_cond(pg, (HINT_OPACITY_JS % ".neo-table-wrap") + " > 0.3", 5000))
            s = state(".neo-table-wrap")
            check("R1 mobile: NEO wrap hint visible and pulsing on a scrollable table",
                  bool(r1), str(s) if not r1 else "")

            # R2: the initial pulse fades out.
            r2 = wait_cond(pg, (HINT_OPACITY_JS % ".neo-table-wrap") + " < 0.1", 12000)
            s = state(".neo-table-wrap")
            r2 = r2 and s and s["display"] == "block"
            check("R2 NEO hint pulse fades out (opacity ~0, still in DOM)",
                  bool(r2), str(s) if not r2 else "")

            # R3: scrolling the wrap right hides the hint via .scroll-started.
            pg.evaluate("document.querySelector('.detail-panel .neo-table-wrap')"
                        ".scrollTo({left: 120})")
            pg.wait_for_timeout(400)
            s = state(".neo-table-wrap")
            r3 = (s and "scroll-started" in s["cls"] and s["display"] == "none"
                  and s["scrollLeft"] > 10)
            check("R3 scrolling the NEO wrap right hides the hint (scroll-started)",
                  bool(r3), str(s) if not r3 else "")

            # R4: scrolling back replays the pulse, then the replay fades.
            pg.evaluate("document.querySelector('.detail-panel .neo-table-wrap')"
                        ".scrollTo({left: 0})")
            replayed = wait_cond(pg, (HINT_OPACITY_JS % ".neo-table-wrap") + " > 0.3", 5000)
            faded = wait_cond(pg, (HINT_OPACITY_JS % ".neo-table-wrap") + " < 0.1", 12000)
            s = state(".neo-table-wrap")
            r4 = bool(replayed and faded)
            check("R4 scroll-back replays the NEO hint pulse, then it fades again",
                  r4, str(s) if not r4 else "")

            # R5: the PvP wrap's hint exists and pulses. By this point its
            # load-time pulse has long faded (R1-R4 take tens of seconds), so
            # trigger the documented replay: scroll right (hides it) then back
            # to the start (replays the pulse from the first keyframe).
            pg.evaluate("document.querySelector('.detail-panel .pvp-table-wrap')"
                        ".scrollTo({left: 120})")
            pg.wait_for_timeout(400)
            s = state(".pvp-table-wrap")
            r5_hidden = (s and "scroll-started" in s["cls"] and s["display"] == "none")
            pg.evaluate("document.querySelector('.detail-panel .pvp-table-wrap')"
                        ".scrollTo({left: 0})")
            r5_pulse = wait_cond(pg, (HINT_OPACITY_JS % ".pvp-table-wrap") + " > 0.3", 5000)
            s = state(".pvp-table-wrap")
            r5 = bool(r5_hidden and r5_pulse and s and s["scrollable"]
                      and s["display"] == "block")
            check("R5 mobile: PvP wrap hint replays its pulse on scroll-back",
                  r5, str(s) if not r5 else "")

            # R6: zero JS page errors across the whole lifecycle.
            check("R6 zero JS page errors", len(errors) == 0,
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
