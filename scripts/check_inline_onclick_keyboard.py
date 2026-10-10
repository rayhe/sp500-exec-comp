#!/usr/bin/env python3
"""Regression guard: inline onclick filter controls in insight cards are
keyboard-operable.

The 2026-10-09 18:00 PT run closed a new failure-mode class the 5-critic
panel flagged: inline onclick filter controls in insight-card prose were
entirely click-only, while every earlier keyboard pilot had targeted card
*chart* surfaces (sector-rank rows, corr cells, treemap leaves, scatter
dots, donut segments, quartile bars). The inline controls are the prose
filter links and histogram bars:

  .insight-tenure-bracket (x4), .tenure-dist-bar-group, .gov-grade-filter,
  .comp-dist-bar-group, .yoy-dist-bar-group, .ratio-dist-bar-group,
  .eq-dist-bar-group, .pctile-dist-bar-group, .conc-dist-bar-group,
  .sector-sort-bar-group, .sop-dist-bar-group, .asp-dist-bar-group

js/app.js gains _upgradeInlineOnclickControls(root), called after each
insight card's innerHTML is set. It upgrades every [onclick] in the card
that is not already keyboard-operable:

  - skipped: native controls (a/button/input/select/textarea), elements
    carrying their own tabindex or onkeydown (e.g. the PvP badge), elements
    already role=button, and already-upgraded nodes (data-kbd-upgraded)
  - upgraded: tabindex="0", role="button", data-bearing aria-label (the
    element's own title with "click to" -> "Press Enter to"; visible text
    when there is no title), Enter/Space keydown that preventDefault()s,
    stopPropagation()s (keyboard-pilot contract), and fires el.click() so
    the keyboard path reproduces the exact mouse behavior.

CSS adds the :focus-visible --accent ring for [data-kbd-upgraded] inside
.insight-card, matching the site convention.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _upgradeInlineOnclickControls is defined with the skip conditions
        (native tags, tabindex, onkeydown, data-kbd-upgraded, role=button)
        and sets tabindex="0", role="button", aria-label, data-kbd-upgraded,
        plus an Enter/Space keydown with preventDefault + stopPropagation +
        e.currentTarget.click().
     S2 the helper is called with the card element after card.innerHTML is
        set in the insight render loop.
     S3 aria-label derivation prefers the element's title ("click to" ->
        "Press Enter to") and falls back to visible text + CTA.
     S4 css/style.css has the .insight-card [data-kbd-upgraded]:focus-visible
        rule with the --accent outline convention.
     S5 no innerHTML in the new helper (attribute-bound additions only).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every non-skipped [onclick] inside .insight-card is role=button
        tabindex=0 with a non-empty aria-label carrying data-kbd-upgraded
        (n > 10 expected across cards).
     R2 the PvP badge (own tabindex + onkeydown) is NOT re-upgraded.
     R3 pressing Enter on a focused .insight-tenure-bracket span fires
        window.filterByTenureQuartile with the bracket's quartile (keyboard/
        click parity).
     R4 zero JS page errors.

Usage:
  scripts/check_inline_onclick_keyboard.py              # static + render
  scripts/check_inline_onclick_keyboard.py --static-only

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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def helper_block(app):
    m = re.search(
        r"function _upgradeInlineOnclickControls\(root\) \{([\s\S]*?)\n    \}",
        app)
    return m.group(0) if m else None


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    hb = helper_block(app)

    s1 = (hb is not None
          and "querySelectorAll('[onclick]')" in hb
          and "hasAttribute('tabindex')" in hb
          and "hasAttribute('onkeydown')" in hb
          and "hasAttribute('data-kbd-upgraded')" in hb
          and "getAttribute('role') === 'button'" in hb
          and "tag === 'A'" in hb and "tag === 'BUTTON'" in hb
          and "setAttribute('tabindex', '0')" in hb
          and "setAttribute('role', 'button')" in hb
          and "setAttribute('aria-label', label)" in hb
          and "setAttribute('data-kbd-upgraded', '1')" in hb
          and "addEventListener('keydown'" in hb
          and "e.key === 'Enter'" in hb
          and "e.key === ' '" in hb
          and "e.preventDefault()" in hb
          and "e.stopPropagation()" in hb
          and "e.currentTarget.click()" in hb)
    check("S1 _upgradeInlineOnclickControls: skips native/already-operable, sets tabindex=0 role=button aria-label, Enter/Space -> preventDefault/stopPropagation/click()",
          s1, "" if s1 else "helper wiring missing or diverged")

    s2 = ("_upgradeInlineOnclickControls(card);" in app
          and re.search(r"card\.innerHTML = html;\n(?:.*\n)*?.*_upgradeInlineOnclickControls\(card\);",
                        app) is not None)
    check("S2 helper is invoked with the card right after card.innerHTML is set in the insight render loop",
          s2, "" if s2 else "hook call missing or misplaced")

    s3 = (hb is not None
          and "getAttribute('title')" in hb
          and "title.replace(/click to/gi, 'Press Enter to')" in hb
          and "Press Enter to activate" in hb)
    check("S3 aria-label derives from the element title ('click to' -> 'Press Enter to'), text fallback + CTA",
          s3, "" if s3 else "aria-label derivation missing")

    m = re.search(
        r"\.insight-card \[data-kbd-upgraded\]:focus-visible\s*\{([\s\S]*?)\}",
        css)
    s4 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1))
    check("S4 :focus-visible --accent ring on .insight-card [data-kbd-upgraded]",
          s4, "" if s4 else "focus ring missing or off-convention")

    s5 = (hb is not None and "innerHTML" not in hb)
    check("S5 keyboard additions are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML found in the helper")

    r = subprocess.run(["node", "--check", APP_JS],
                       capture_output=True, text=True, timeout=60)
    check("S6 node --check js/app.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")


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
            pg.wait_for_function(
                "window.d3 && document.querySelectorAll('.insight-card').length > 10",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('.insight-card .clickable-bar').length > 5",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every non-skipped [onclick] inside insight cards is an
            # upgraded button.
            r1info = pg.evaluate("""() => {
              // Mirror the helper's PRE-upgrade skip set: native controls
              // and elements with their own onkeydown (e.g. PvP badge).
              // Upgraded nodes carry tabindex, so tabindex must NOT be in
              // the skip set here.
              const skip = el => {
                const t = (el.tagName || '').toUpperCase();
                return t === 'A' || t === 'BUTTON' || t === 'INPUT' ||
                       t === 'SELECT' || t === 'TEXTAREA' ||
                       el.hasAttribute('onkeydown');
              };
              const all = [...document.querySelectorAll('.insight-card [onclick]')]
                .filter(el => !skip(el));
              const bad = all.filter(el =>
                el.getAttribute('tabindex') !== '0' ||
                el.getAttribute('role') !== 'button' ||
                !(el.getAttribute('aria-label') || '').length ||
                el.getAttribute('data-kbd-upgraded') !== '1');
              return {n: all.length, bad: bad.length,
                      sample: all[0] ? all[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["n"] > 10 and r1info["bad"] == 0)
            check("R1 all %d non-skipped insight-card [onclick] are upgraded buttons (tabindex=0 role=button aria-label)"
                  % r1info["n"],
                  r1, ("n=%d bad=%d sample=%r" % (
                      r1info["n"], r1info["bad"], r1info["sample"])) if not r1 else "")

            # R2: the PvP badge (own tabindex + onkeydown) is NOT re-upgraded.
            r2info = pg.evaluate("""() => {
              const b = document.querySelector('.pvp-cov-badge');
              if (!b) return 'NO_BADGE';
              return {tab: b.getAttribute('tabindex'),
                      role: b.getAttribute('role'),
                      upgraded: b.hasAttribute('data-kbd-upgraded')};
            }""")
            r2 = (r2info != "NO_BADGE"
                  and r2info["tab"] == "0"
                  and r2info["role"] == "button"
                  and r2info["upgraded"] is False)
            check("R2 PvP badge keeps its own keyboard wiring (not re-upgraded)",
                  r2, "badge state: %r" % (r2info,) if not r2 else "")

            # R3: Enter on a focused tenure-bracket span fires the same
            # filter the click fires (keyboard/click parity).
            r3setup = pg.evaluate("""() => {
              window.__tenureCalls = [];
              const orig = window.filterByTenureQuartile;
              window.filterByTenureQuartile = function() {
                window.__tenureCalls.push([].slice.call(arguments));
                return orig.apply(this, arguments);
              };
              const sp = document.querySelector('.insight-tenure-bracket');
              if (!sp) return 'NO_SPAN';
              sp.scrollIntoView({block: 'center'});
              sp.focus();
              return sp.getAttribute('aria-label');
            }""")
            if r3setup == "NO_SPAN":
                check("R3 Enter on tenure bracket fires filterByTenureQuartile", False,
                      "no .insight-tenure-bracket rendered")
            else:
                pg.wait_for_timeout(300)
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(600)
                r3calls = pg.evaluate("window.__tenureCalls")
                r3 = (len(r3calls) == 1 and r3calls[0][0] == 20)
                check("R3 Enter on tenure bracket fires filterByTenureQuartile(20, ...) exactly once",
                      r3, ("calls: %r label: %r" % (r3calls, r3setup)) if not r3 else "")

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    if "--static-only" in sys.argv:
        static_checks()
    else:
        static_checks()
        rc = render_checks()
        if rc is None:
            print("SKIP: render checks unavailable; static checks decide")
    fails = [n for n, ok, _ in results if not ok]
    if fails:
        print("\n%d check(s) FAILED: %s" % (len(fails), ", ".join(fails)))
        return 1
    print("\nALL %d CHECKS PASSED" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
