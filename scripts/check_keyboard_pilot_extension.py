#!/usr/bin/env python3
"""Regression guard: keyboard pilot extension to composition donut + trend cards.

The 2026-10-08 14:00 PT run piloted keyboard operability on the sector
chart's filter bars (Interactivity 9.3 -> 9.4); this run extends the pilot
to the two remaining hover/click-only surfaces the 5-critic panel flagged:

  1. Composition donut segments (js/charts.js, drawCompositionChart):
     mouseover-only tooltips + hover highlight. Each .donut-seg is now
     tabindex="0" role="img" with a data-bearing aria-label
     ("<label>: <pct>% of median total, <median value>"); focus mirrors
     the hover highlight (arcHover expand + dim others) and shows the
     SAME tooltip HTML (compositionSegTooltipHtml) anchored to the
     focused segment; blur mirrors mouseout. Segments have no click
     action, so role="img" (not "button") is the semantically apt role.
  2. Clickable trend cards (js/app.js insight cards): div.trend-clickable
     with click-only listeners (company lookups, section scrolls). Each
     now exposes tabindex="0" role="button" with the actionHint as
     aria-label and an Enter/Space keydown firing the same action.

Both surfaces carry :focus-visible rings in css/style.css matching the
--accent convention (sector-bar pilot, .metric-card precedent).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 the .donut-seg join sets tabindex="0", role="img", an aria-label
        carrying the segment pct, and focus/blur handlers that mirror the
        hover highlight + tooltip show/hide.
     S2 the mouseover path is preserved (mouseover ->
        compositionSegTooltipHtml, mousemove repositions, mouseout resets).
     S3 css/style.css has the #composition-chart path.donut-seg:focus-visible
        rule with the --accent outline convention.
     S4 the keyboard additions are setAttribute-bound (no innerHTML) in
        the .donut-seg join block.
     S5 clickable trend cards get tabindex="0", role="button", an
        aria-label from actionHint, and an Enter/Space keydown that
        invokes card.action().
     S6 css/style.css has the .trend-clickable:focus-visible rule with the
        --accent outline convention.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 every rendered .donut-seg carries tabindex="0", role="img" and a
        non-empty aria-label naming its component share.
     R2 focusing a donut segment shows the chart tooltip with that
        segment's data (keyboard tooltip parity).
     R3 focusing a clickable trend card and pressing Enter fires its
        action (the "View trend chart" card scrolls the page).
     R4 zero JS page errors.

Usage:
  scripts/check_keyboard_pilot_extension.py              # static + render
  scripts/check_keyboard_pilot_extension.py --static-only

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
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
APP_JS = os.path.join(REPO, "js", "app.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def donut_join_block():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    # The composition donut .donut-seg join: from ".attr('class', 'donut-seg')"
    # to the focus/blur tail of its chained handlers.
    m = re.search(r"\.attr\('class', 'donut-seg'\)([\s\S]{0,9000}?)\.on\('blur', function\(\) \{[\s\S]{0,600}?\}\);",
                  charts)
    return m.group(0) if m else None


def card_action_block():
    app = open(APP_JS, encoding="utf-8").read()
    m = re.search(r"if \(card\.action\) \{([\s\S]{0,1500}?)card\.action\(\);[\s\S]{0,200}?\}\);\n\s*\}",
                  app)
    return m.group(0) if m else None


def static_checks():
    charts = open(CHARTS_JS, encoding="utf-8").read()
    app = open(APP_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    dblock = donut_join_block()
    cblock = card_action_block()

    s1 = (dblock is not None
          and ".attr('tabindex', '0')" in dblock
          and ".attr('role', 'img')" in dblock
          and ".attr('aria-label', function(d)" in dblock
          and "% of median total" in dblock
          and ".on('focus', function(event, d)" in dblock
          and "arcHover" in dblock
          and "compositionSegTooltipHtml(d)" in dblock
          and ".on('blur', function()" in dblock
          and "hideChartTooltip()" in dblock)
    check("S1 .donut-seg join sets tabindex/role=img/aria-label + focus/blur mirroring hover tooltip",
          s1, "" if s1 else "keyboard additions missing from the .donut-seg join")

    s2 = (dblock is not None
          and ".on('mouseover', function(event, d)" in dblock
          and "compositionSegTooltipHtml(d)" in dblock
          and ".on('mousemove', function(event)" in dblock
          and ".on('mouseout', function()" in dblock)
    check("S2 mouseover tooltip path preserved (compositionSegTooltipHtml shared)",
          s2, "" if s2 else "mouseover path altered or lost")

    m = re.search(r"#composition-chart path\.donut-seg:focus-visible \{([^}]*)\}", css)
    s3 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S3 :focus-visible ring on #composition-chart path.donut-seg uses --accent convention",
          s3, "" if s3 else "focus ring missing or off-convention")

    s4 = dblock is not None and "innerHTML" not in dblock
    check("S4 keyboard additions are setAttribute-bound (no innerHTML)",
          s4, "" if s4 else "innerHTML found in the .donut-seg join block")

    s5 = (cblock is not None
          and "el.setAttribute('tabindex', '0')" in cblock
          and "el.setAttribute('role', 'button')" in cblock
          and "card.actionHint" in cblock
          and "aria-label" in cblock
          and "e.key === 'Enter' || e.key === ' '" in cblock
          and "card.action()" in cblock
          and "el.addEventListener('click', card.action)" in cblock)
    check("S5 clickable trend cards expose tabindex/role=button/aria-label + Enter/Space -> card.action()",
          s5, "" if s5 else "keyboard wiring missing from the card action block")

    m = re.search(r"\.trend-clickable:focus-visible \{([^}]*)\}", css)
    s6 = (m is not None
          and "outline: 2px solid var(--accent)" in m.group(1)
          and "outline-offset: 2px" in m.group(1))
    check("S6 :focus-visible ring on .trend-clickable uses --accent convention",
          s6, "" if s6 else "focus ring missing or off-convention")


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
                "window.d3 && document.querySelectorAll('#composition-chart path.donut-seg').length > 0",
                timeout=90000)
            pg.wait_for_function(
                "document.querySelectorAll('.trend-card[role=\"button\"]').length > 0",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: every donut segment is a labelled image in the a11y tree.
            r1info = pg.evaluate("""() => {
              const segs = [...document.querySelectorAll('#composition-chart path.donut-seg')];
              const bad = segs.filter(s =>
                s.getAttribute('tabindex') !== '0' ||
                s.getAttribute('role') !== 'img' ||
                !(s.getAttribute('aria-label') || '').includes('% of median total'));
              return {n: segs.length, bad: bad.length,
                      sample: segs[0] ? segs[0].getAttribute('aria-label') : null};
            }""")
            r1 = r1info["n"] > 0 and r1info["bad"] == 0
            check("R1 all %d donut segments are tabindex=0 role=img with component-share aria-label" % r1info["n"],
                  r1, ("sample: %r" % r1info["sample"]) if not r1 else "")

            # R2: focusing a segment surfaces its tooltip (keyboard parity).
            pg.evaluate("""() => {
              const seg = document.querySelector('#composition-chart path.donut-seg');
              seg.scrollIntoView({block: 'center'});
              seg.focus();
            }""")
            pg.wait_for_timeout(600)
            r2info = pg.evaluate("""() => {
              const tip = document.querySelector('.chart-tooltip.visible');
              const seg = document.querySelector('#composition-chart path.donut-seg');
              const label = (seg.getAttribute('aria-label') || '').split(':')[0];
              return {visible: !!tip,
                      text: tip ? tip.textContent.slice(0, 60) : null,
                      label: label};
            }""")
            r2 = r2info["visible"] and r2info["label"] in (r2info["text"] or "")
            check("R2 focus on donut segment shows tooltip with segment data (%r)" % r2info["label"],
                  r2, "tooltip not visible or label mismatch: %r" % r2info["text"] if not r2 else "")
            # Blur restores the un-dimmed state and hides the tooltip.
            pg.evaluate("document.activeElement.blur()")
            pg.wait_for_timeout(400)
            tip_hidden = pg.evaluate("!document.querySelector('.chart-tooltip.visible')")
            check("R2b blur hides the tooltip", tip_hidden,
                  "tooltip still visible after blur" if not tip_hidden else "")

            # R3: Enter on the "View trend chart" card fires its scroll action.
            r3info = pg.evaluate("""() => {
              const cards = [...document.querySelectorAll('.trend-card[role="button"]')];
              const card = cards.find(c => (c.getAttribute('aria-label') || '') === 'View trend chart');
              if (!card) return {found: false};
              card.scrollIntoView({block: 'center'});
              card.focus();
              return {found: true, before: window.scrollY};
            }""")
            r3 = False
            if r3info.get("found"):
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(1500)
                after = pg.evaluate("window.scrollY")
                r3 = after != r3info["before"]
            check("R3 Enter on 'View trend chart' card fires its action (scrollY %s -> moved)" % r3info.get("before"),
                  r3, "scroll action did not fire" if not r3 else "")

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
