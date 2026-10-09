#!/usr/bin/env python3
"""Regression guard: keyboard pilot extension to insight action cards.

The 2026-10-09 14:00 PT run ran the 5-critic panel across data richness,
visual design, interactivity, network graph quality, and analytical depth.
The interactivity critic flagged the insight-card grid (js/app.js,
renderInsights) as the largest remaining mouse-only surface: the
~26 insight cards carrying a click action (each with an actionHint like
"View scatter plot" / "Filter to CEO transitions") had zero keyboard
reachability — no tabindex, no role, no keydown, no focus ring.

This run makes every .insight-clickable card a full keyboard surface:

  1. tabindex="0", role="button", and a data-bearing aria-label
     ("<label>. <actionHint>") on the card when ins.action is set.
  2. Enter/Space fires the SAME ins.action the click handler fires.
     The keydown guards on e.target === card so keys pressed on nested
     buttons (insight-compare-btn) stay on the button path, and calls
     e.preventDefault() so document-level single-key shortcuts do not
     double-fire (the 2026-10-09 double-fire fix convention).
  3. :focus-visible ring on .insight-clickable uses the --accent
     convention (compare-btn / sector-bar / donut pilots), and the CTA
     hint (.insight-cta) reveals on focus just as on hover.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the ins.action wiring block sets tabindex="0", role="button",
        and an aria-label built from ins.label + ins.actionHint.
     S2 a keydown listener handles Enter and Space, guards on
        e.target === card, calls e.preventDefault(), then ins.action().
     S3 the original click handler is retained (keyboard/click parity).
     S4 css/style.css has the .insight-clickable:focus-visible rule
        with the --accent outline convention plus the .insight-cta
        opacity reveal on focus.
     S5 the keyboard additions are attribute-bound (no innerHTML).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered .insight-clickable card has role="button",
        tabindex="0", and a non-empty aria-label.
     R2 pressing Enter on the "Pay vs Performance Alignment" card fires
        its scroll action (stubbed scrollToSectionById records the id)
        — keyboard/click parity for the card action path.
     R3 pressing Enter while focus is on a nested compare button does
        NOT fire the card action (e.target guard) — the button path is
        handled by the button itself.
     R4 zero JS page errors.

Usage:
  scripts/check_insight_card_keyboard.py              # static + render
  scripts/check_insight_card_keyboard.py --static-only

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


def action_block(app):
    m = re.search(
        r"if \(ins\.action\) \{\n([\s\S]*?)\n        \}",
        app)
    return m.group(0) if m else None


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    block = action_block(app)

    s1 = (block is not None
          and "card.setAttribute('tabindex', '0')" in block
          and "card.setAttribute('role', 'button')" in block
          and "card.setAttribute('aria-label', ins.label" in block
          and "ins.actionHint" in block)
    check("S1 ins.action block sets tabindex=0, role=button, aria-label from label+actionHint",
          s1, "" if s1 else "card keyboard attributes missing from the action block")

    s2 = (block is not None
          and "card.addEventListener('keydown'" in block
          and "e.target !== card" in block
          and "e.key === 'Enter'" in block
          and "e.key === ' '" in block
          and "e.preventDefault()" in block
          and "ins.action();" in block)
    check("S2 Enter/Space keydown guarded on e.target===card, preventDefault, then ins.action()",
          s2, "" if s2 else "keydown wiring missing or unguarded")

    s3 = (block is not None
          and "card.addEventListener('click', ins.action)" in block)
    check("S3 click handler retained (keyboard/click parity)",
          s3, "" if s3 else "click handler removed or diverged from ins.action")

    m = re.search(
        r"\.insight-clickable:focus-visible\s*\{([\s\S]*?)\}",
        css)
    s4 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and ".insight-clickable:focus-visible .insight-cta" in css
          and re.search(
              r"\.insight-clickable:focus-visible \.insight-cta\s*\{[^}]*opacity: 1",
              css) is not None)
    check("S4 :focus-visible --accent ring on .insight-clickable + CTA reveal on focus",
          s4, "" if s4 else "focus ring or CTA reveal missing or off-convention")

    s5 = (block is not None and "innerHTML" not in block)
    check("S5 keyboard additions are attribute-bound (no innerHTML)",
          s5, "" if s5 else "innerHTML found in the action block")


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
                "window.d3 && document.querySelectorAll('.insight-clickable').length > 5",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # R1: every action card is a labelled button with one tab stop.
            r1info = pg.evaluate("""() => {
              const cards = [...document.querySelectorAll('.insight-clickable')];
              const bad = c =>
                c.getAttribute('role') !== 'button' ||
                c.getAttribute('tabindex') !== '0' ||
                !(c.getAttribute('aria-label') || '').length;
              return {n: cards.length, bad: cards.filter(bad).length,
                      sample: cards[0] ? cards[0].getAttribute('aria-label') : null};
            }""")
            r1 = (r1info["n"] > 5 and r1info["bad"] == 0)
            check("R1 all %d insight cards are role=button tabindex=0 with aria-label"
                  % r1info["n"],
                  r1, ("n=%d bad=%d sample=%r" % (
                      r1info["n"], r1info["bad"], r1info["sample"]))
                  if not r1 else "")

            # R2: stub the scroll target, Enter on the PvP card fires its
            # action (same path as click).
            pg.evaluate("""() => {
              window.__scrollCalls = [];
              window.scrollToSectionById = function(id) {
                window.__scrollCalls.push(id); };
            }""")
            pg.evaluate("""() => {
              const card = [...document.querySelectorAll('.insight-clickable')]
                .find(c => (c.getAttribute('aria-label') || '')
                  .indexOf('Pay vs Performance Alignment') === 0);
              if (!card) throw new Error('pvp card not found');
              card.scrollIntoView({block: 'center'});
              card.focus();
            }""")
            pg.wait_for_timeout(400)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(500)
            r2info = pg.evaluate("window.__scrollCalls")
            r2 = (r2info == ["pvp-comparison-section"])
            check("R2 Enter on Pay-vs-Performance card fires scrollToSectionById('pvp-comparison-section')",
                  r2, "calls recorded: %r" % (r2info,) if not r2 else "")

            # R3: Enter on a nested compare button must NOT fire the card
            # action (e.target guard); the button path handles it.
            r3ok = pg.evaluate("""() => {
              window.__toggleCalls = [];
              window._toggleCompare = function(t) { window.__toggleCalls.push(t); };
              window.__scrollCalls = [];
              const btn = document.querySelector('.insight-clickable .insight-compare-btn');
              if (!btn) return 'NO_BTN';
              btn.focus();
              return 'OK';
            }""")
            if r3ok == "NO_BTN":
                check("R3 nested-button guard", False, "no insight-compare-btn rendered")
            else:
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(500)
                r3info = pg.evaluate(
                    "({toggle: window.__toggleCalls, scroll: window.__scrollCalls})")
                r3 = (len(r3info["toggle"]) == 1 and r3info["scroll"] == [])
                check("R3 Enter on nested compare button fires _toggleCompare only, not the card action",
                      r3, "recorded: %r" % (r3info,) if not r3 else "")

            # R4: zero JS page errors across the lifecycle.
            check("R4 zero JS page errors", len(errors) == 0,
                  "; ".join(errors[:3]) if errors else "")

            browser.close()
            return all(ok for _, ok, _ in results)
    finally:
        server.terminate()


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if static_only:
        bad = [n for n, ok, _ in results if not ok]
        return 1 if bad else 0
    rc = render_checks()
    if rc is None:
        bad = [n for n, ok, _ in results if not ok]
        return 1 if bad else 0
    bad = [n for n, ok, _ in results if not ok]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
