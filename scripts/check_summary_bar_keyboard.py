#!/usr/bin/env python3
"""Regression guard: #table-summary-bar distribution filter bars are keyboard-operable.

The 2026-10-11 11:30 PT run closed the last click-only inline-onclick surface
class: the sort-contextual / filtered distribution filter bars rendered into
#table-summary-bar by renderSummaryBar (comp/yoy/ratio/eq/pctile/conc/sop/asp
dist-bar-group spans from renderSortContextSummary, plus the
sector-sort-bar-group CEO-transition bars on the filtered-summary path).
All of them carried inline onclick= filter calls with "click to filter"
titles but no tabindex/role/keydown - a keyboard user could not reach the
table's own distribution-exploration controls.

The fix hoists _upgradeInlineOnclickControls to top-level scope (it was
nested inside populateInsights and only reachable from the insight-card
render path; the helper is closure-free - DOM APIs only) and invokes it on
the summary bar at both bar.innerHTML injection sites in renderSummaryBar
(the sort-contextual site and the filtered-summary site).

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 _upgradeInlineOnclickControls is a single top-level function with
        the skip set (native tags, tabindex, onkeydown, data-kbd-upgraded,
        role=button), tabindex="0", role="button", aria-label derivation,
        and an Enter/Space keydown that preventDefault()s,
        stopPropagation()s and fires e.currentTarget.click().
     S2 the helper is invoked at all three wiring sites: the insight card
        (existing), and both renderSummaryBar injection sites
        (sort-contextual and filtered-summary).
     S3 exactly one definition exists (no duplicate-definition shadowing
        from the hoist).
     S4 aria-label derivation turns "click to" titles into "Press Enter to".
     S5 node --check js/app.js is green.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 on the default sort the comp-dist-bar-group spans are tabindex=0
        role=button with Press-Enter aria-labels.
     R2 Enter on a comp-dist bar calls window.filterByCompBracket exactly
        once (keyboard/click parity), and the table filters.
     R3 zero JS page errors.

Usage:
  scripts/check_summary_bar_keyboard.py              # static + render
  scripts/check_summary_bar_keyboard.py --static-only

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
        r"^function _upgradeInlineOnclickControls\(root\) \{$",
        app, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    # find the matching close brace at column 0
    depth = 0
    for i, line in enumerate(app[start:].split("\n")):
        depth += line.count("{") - line.count("}")
        if i > 0 and depth == 0 and line == "}":
            end = start + sum(len(l) + 1 for l in app[start:].split("\n")[:i + 1])
            return app[start:end]
    return None


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()

    defs = re.findall(r"function _upgradeInlineOnclickControls\(root\)", app)
    s3 = len(defs) == 1
    check("S3 exactly one _upgradeInlineOnclickControls definition (no hoist shadowing)",
          s3, "" if s3 else "found %d definitions" % len(defs))

    hb = helper_block(app)
    s1 = (hb is not None
          and hb.startswith("function _upgradeInlineOnclickControls")
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
    check("S1 top-level helper: skip set, tabindex=0 role=button aria-label, Enter/Space -> preventDefault/stopPropagation/click()",
          s1, "" if s1 else "top-level helper missing or diverged")

    card_calls = app.count("_upgradeInlineOnclickControls(card);")
    bar_calls = app.count("_upgradeInlineOnclickControls(bar);")
    s2 = card_calls >= 1 and bar_calls >= 2
    check("S2 helper invoked at the insight-card site and both summary-bar sites (card=%d, bar=%d)"
          % (card_calls, bar_calls),
          s2, "" if s2 else "a wiring call is missing")

    s4 = (hb is not None
          and "title.replace(/click to/gi, 'Press Enter to')" in hb)
    check("S4 aria-label derivation: 'click to' titles become 'Press Enter to'",
          s4, "" if s4 else "label derivation missing")

    r = subprocess.run(["node", "--check", APP_JS],
                       capture_output=True, text=True, timeout=60)
    check("S5 node --check js/app.js is green",
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
            # Default sort is total_compensation -> renderCompDistSummary
            # renders the comp-dist-bar-group filter bars.
            pg.wait_for_function(
                "document.querySelectorAll('#table-summary-bar .comp-dist-bar-group').length >= 4",
                timeout=90000)
            pg.wait_for_timeout(1200)

            # R1: comp-dist bars are focusable buttons with Press-Enter labels.
            r1info = pg.evaluate("""() => {
              const bars = [...document.querySelectorAll('#table-summary-bar .comp-dist-bar-group')];
              const ok = bars.length >= 4 &&
                bars.every(e => e.getAttribute('tabindex') === '0' &&
                                e.getAttribute('role') === 'button' &&
                                /Press Enter/i.test(e.getAttribute('aria-label') || ''));
              return {n: bars.length, ok: ok};
            }""")
            r1 = r1info["ok"]
            check("R1 comp-dist-bar-group spans are tabindex=0 role=button with Press-Enter aria-labels",
                  r1, ("" if r1 else "state: %r" % (r1info,)))

            # Spy on the filter entry point.
            pg.evaluate("""() => {
              window.__fbCalls = [];
              const orig = window.filterByCompBracket;
              window.filterByCompBracket = function(a, b, l) {
                window.__fbCalls.push([a, b, l]);
                return orig.apply(this, arguments);
              };
            }""")

            # R2: Enter on a comp-dist bar calls filterByCompBracket once and
            # the table filters to the bracket.
            r2info = pg.evaluate("""() => {
              const bar = document.querySelector('#table-summary-bar .comp-dist-bar-group[tabindex="0"]');
              if (!bar) return {err: 'NO_BAR'};
              const before = document.querySelectorAll('#comp-tbody tr:not(.detail-row)').length;
              bar.focus();
              bar.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true}));
              return new Promise(res => setTimeout(() => {
                const after = document.querySelectorAll('#comp-tbody tr:not(.detail-row)').length;
                res({fbCalls: window.__fbCalls.length,
                     label: window.__fbCalls.length ? window.__fbCalls[0][2] : null,
                     rowsBefore: before, rowsAfter: after,
                     chip: !!document.getElementById('comp-filter-chip') ||
                           !!document.getElementById('dist-filter-chip')});
              }, 1500));
            }""")
            r2 = (r2info.get("fbCalls") == 1
                  and r2info.get("rowsAfter", 0) > 0
                  and r2info.get("rowsAfter", 0) < r2info.get("rowsBefore", 0))
            check("R2 Enter on a comp-dist bar calls window.filterByCompBracket once and filters the table",
                  r2, ("" if r2 else "state: %r" % (r2info,)))

            r3 = len(errors) == 0
            check("R3 zero JS page errors",
                  r3, ("" if r3 else "; ".join(errors[:3])))
            browser.close()
    finally:
        server.terminate()
    return True


def main():
    static_checks()
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("STATIC-ONLY: %d/%d passed" % (len(results) - len(failed), len(results)))
        sys.exit(1 if failed else 0)
    render_checks()
    failed = [r for r in results if not r[1]]
    print("TOTAL: %d/%d passed" % (len(results) - len(failed), len(results)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
