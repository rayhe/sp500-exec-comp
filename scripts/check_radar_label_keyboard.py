#!/usr/bin/env python3
"""Regression guard: the compare radar dimension labels (.cmp-radar-dim-label)
are keyboard-operable (roving-tabindex group with bespoke SVG treatment).

The 2026-10-09 22:00 PT panel audit found these as the last click-only
control class in the compare view: SVG <text> axis labels with
cursor:pointer + a <title> child ("... click to sort table by this
dimension"), D3-wired .on('click') -> insightResetAndSort(sortInfo.key,
sortInfo.dir). Before this fix they had no tabindex, no role, no keydown:
entirely mouse-only (the 22:00 PT run repaired the dead click handler by
exposing window.insightResetAndSort, so the mouse path works; this guard
pins the keyboard path).

Bespoke SVG treatment (js/app.js, file-scope _kbdUpgradeSvgRoving) rather
than _kbdUpgradeRoving() because:
  (1) the labels' "title" is an SVG <title> CHILD element, not a title
      attribute, so getAttribute('title') returns null; the helper reads
      el.querySelector('title').textContent for the aria-label source;
  (2) SVG elements have no .click() method, so Enter/Space dispatches a
      synthetic bubbled MouseEvent('click') instead (D3 .on('click') uses
      addEventListener, so the synthetic event hits the real listener for
      exact keyboard/click parity).

Upgrade semantics (treemap-roving convention): first label tabindex="0",
rest "-1"; role="button"; data-bearing aria-label from the <title> child
("click to" -> "Press Enter to"); data-kbd-upgraded="1" (so the generic
[data-kbd-upgraded]:focus-visible --accent ring in css/style.css applies);
Enter/Space -> preventDefault/stopPropagation + synthetic click (keyboard-
pilot contract); arrows move the holder linearly with preventDefault/
stopPropagation so the global ArrowLeft/Right table-page shortcut cannot
double-fire.

Call site: renderComparisonRadar() -> _kbdUpgradeSvgRoving(svg.node(),
'.cmp-radar-dim-label') right after the label-creation forEach (theme
toggle and other redraws rebuild the svg, so the upgrade re-applies on
every render). Labels for dims without sortInfo never get
.cmp-radar-dim-label and carry no click action: excluded by construction
(click/no-op parity, same as the heatmap hm-zero precedent).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _kbdUpgradeSvgRoving defined at file scope with the two SVG
        adaptations (querySelector('title') for the aria source; synthetic
        MouseEvent click dispatch instead of el.click()).
     S2 call site _kbdUpgradeSvgRoving(svg.node(), '.cmp-radar-dim-label')
        exists AND sits after the .cmp-radar-dim-label label creation.
     S3 parity target intact: the D3 .on('click') still calls
        insightResetAndSort(sortInfo.key, sortInfo.dir).
     S4 aria-label source intact: .append('title') with the "click to sort
        table by this dimension" text.
     S5 node --check js/app.js is green.
     S6 window.insightResetAndSort exposure present (the 2026-10-09 22:00 PT
        dead-click repair the synthetic keyboard click resolves through).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 compare view (META + AAPL via _toggleCompare + #compare-go-btn):
        - >=1 .cmp-radar-dim-label, exactly one tabindex="0" holder, rest
          "-1", all role=button with data-bearing aria-labels containing
          "Press Enter to sort table by" and data-kbd-upgraded="1".
        - Enter on the holder fires exactly one click event on that label
          (recorded by a capture listener on the svg) -- the same event a
          mouse click produces, which the D3 .on('click') listener handles.
        - ArrowRight moves the holder (when >=2 labels).
     R2 zero JS page errors.

Usage:
  scripts/check_radar_label_keyboard.py              # static + render
  scripts/check_radar_label_keyboard.py --static-only

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

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()

    # S1: bespoke SVG helper with the two adaptations.
    has_helper = "function _kbdUpgradeSvgRoving(svgNode, selector)" in app
    has_title_child = ("el.querySelector('title')" in app
                       and "titleEl ? (titleEl.textContent || '')" in app)
    has_synth_click = ("new MouseEvent('click', { bubbles: true" in app
                       and "dispatchEvent(ev)" in app)
    s1 = has_helper and has_title_child and has_synth_click
    check("S1 _kbdUpgradeSvgRoving file-scope helper with SVG adaptations (title child; synthetic click)",
          s1, "" if s1 else "helper missing or lost an SVG adaptation")

    # S2: call site ordered after the label creation.
    i_create = app.find(".attr('class', 'cmp-radar-dim-label')")
    i_call = app.find("_kbdUpgradeSvgRoving(svg.node(), '.cmp-radar-dim-label')")
    s2 = i_create > 0 and i_call > i_create
    check("S2 _kbdUpgradeSvgRoving(svg.node(), '.cmp-radar-dim-label') after label creation",
          s2, "" if s2 else "call site missing or misordered")

    # S3: parity target intact (D3 click -> insightResetAndSort).
    s3 = ("labelEl.on('click', function()" in app
          and "insightResetAndSort(sortInfo.key, sortInfo.dir)" in app)
    check("S3 parity target intact (D3 .on('click') -> insightResetAndSort(sortInfo.key, dir))",
          s3, "" if s3 else "the click handler the keyboard path reproduces diverged")

    # S4: aria-label source title intact.
    s4 = ("click to sort table by this dimension" in app
          and ".append('title').text(d.label" in app)
    check("S4 data-bearing <title> child source intact",
          s4, "" if s4 else "the <title> feeding the keyboard aria-labels is gone")

    r = subprocess.run(["node", "--check", APP_JS],
                       capture_output=True, text=True, timeout=60)
    check("S5 node --check js/app.js is green",
          r.returncode == 0, r.stderr.strip()[:300] if r.returncode else "")

    s6 = "window.insightResetAndSort = insightResetAndSort" in app
    check("S6 window.insightResetAndSort exposure present (dead-click repair the synthetic click resolves through)",
          s6, "" if s6 else "exposure missing: compare sort clicks would throw")


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
            pg.wait_for_timeout(1200)

            # ---------- R1: radar dimension labels ----------
            pg.evaluate("""() => {
              window._toggleCompare('META');
              window._toggleCompare('AAPL');
              document.getElementById('compare-go-btn').click();
            }""")
            pg.wait_for_selector(".cmp-radar-dim-label", timeout=60000)
            pg.wait_for_timeout(800)
            r1shape = pg.evaluate("""() => {
              const labels = [...document.querySelectorAll('.cmp-radar-dim-label')];
              const holders = labels.filter(
                l => l.getAttribute('tabindex') === '0');
              const neg = labels.filter(
                l => l.getAttribute('tabindex') === '-1');
              const bad = labels.filter(l =>
                l.getAttribute('role') !== 'button' ||
                !(l.getAttribute('aria-label') || '')
                  .includes('Press Enter to sort table by') ||
                l.getAttribute('data-kbd-upgraded') !== '1');
              const label0 = holders[0] ?
                holders[0].getAttribute('aria-label') : null;
              const tag0 = holders[0] ?
                (holders[0].tagName || '').toLowerCase() : null;
              return {n: labels.length, holders: holders.length,
                      neg: neg.length, bad: bad.length,
                      label0: label0, tag0: tag0};
            }""")
            r1shape_ok = (r1shape["n"] >= 1
                          and r1shape["holders"] == 1
                          and r1shape["neg"] == r1shape["n"] - 1
                          and r1shape["bad"] == 0
                          and r1shape["tag0"] == "text"
                          and r1shape["label0"] is not None
                          and "Press Enter to sort table by" in r1shape["label0"])
            r1 = False
            r1detail = "shape: %r" % (r1shape,)
            if r1shape_ok:
                # Capture-phase click listener on the svg records clicks on
                # the label; the D3 .on('click') (bubble) listener then
                # handles it. One Enter must produce exactly one click.
                pg.evaluate("""() => {
                  window.__radarClicks = [];
                  const lbl = document.querySelector(
                    '.cmp-radar-dim-label[tabindex="0"]');
                  const svg = lbl ? lbl.closest('svg') : null;
                  if (svg) svg.addEventListener('click', function(e) {
                    var t = e.target.closest ?
                      e.target.closest('.cmp-radar-dim-label') : null;
                    if (t) window.__radarClicks.push(
                      t.textContent.replace(/\\s+/g, ' ').trim());
                  }, true);
                }""")
                pg.evaluate("""() => {
                  document.querySelector(
                    '.cmp-radar-dim-label[tabindex="0"]').focus();
                }""")
                before = pg.evaluate("""() => {
                  const h = document.querySelector(
                    '.cmp-radar-dim-label[tabindex="0"]');
                  return h ? h.textContent.replace(/\\s+/g, ' ').trim() : null;
                }""")
                pg.keyboard.press("Enter")
                pg.wait_for_timeout(900)
                clicks = pg.evaluate("() => window.__radarClicks")
                r1enter = (len(clicks) == 1 and before is not None
                           and before in clicks[0])
                r1detail = "enter clicks: %r (holder text %r)" % (clicks, before)
                r1 = r1enter
                if r1shape["n"] >= 2 and r1enter:
                    pg.evaluate("""() => {
                      document.querySelector(
                        '.cmp-radar-dim-label[tabindex="0"]').focus();
                    }""")
                    pg.keyboard.press("ArrowRight")
                    pg.wait_for_timeout(300)
                    moved = pg.evaluate("""() => {
                      const h = document.querySelector(
                        '.cmp-radar-dim-label[tabindex="0"]');
                      const a = document.activeElement;
                      return {holder: h ?
                        h.textContent.replace(/\\s+/g, ' ').trim() : null,
                              focused: h ? (a === h) : false};
                    }""")
                    r1arrow = (moved["holder"] is not None
                               and moved["holder"] != before
                               and moved["focused"] is True)
                    r1detail += " | arrow: %r" % (moved,)
                    r1 = r1 and r1arrow
            check("R1 radar dim labels: roving group + Enter fires synthetic click + ArrowRight moves",
                  r1, r1detail)

            check("R2 zero JS page errors", len(errors) == 0,
                  ("; ".join(errors))[:400] if errors else "")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


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
