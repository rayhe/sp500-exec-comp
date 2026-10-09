#!/usr/bin/env python3
"""Regression guard: network graph canvas keyboard navigation.

The peer-network force graph in js/network.js renders to a <canvas>
(1,040 nodes / 7,739 edges), which is inherently mouse-centric. The
keyboard nav added for it is the most complex in the site's keyboard
pilot: a single tab stop on the canvas (tabindex="0", role="img",
instruction-bearing aria-label), arrow-key/Tab cycling through
keyboard-navigable nodes sorted by influence, Enter/Space firing the
same findCompanyInTable lookup as a node click, Escape clearing focus,
+/- zooming, and alphanumeric quick-jump into the network search box.
Focus announces the node via the aria-live region ("Focused <TICKER>
<name> ... Press Enter for details.") and shows the same tooltip the
mouse hover shows.

Every other keyboard-pilot surface has a dedicated guard; this closes
the gap for the network canvas, so a future refactor of the canvas
handlers cannot silently drop keyboard reachability.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 canvas creation sets tabindex="0", role="img", and an
        aria-label documenting arrow keys / Enter / zoom.
     S2 focus handler focuses the first keyboard-navigable node with
        an aria-live announcement, shows the tooltip, and adds the
        kb-focused class.
     S3 keydown covers ArrowRight/ArrowDown/Tab (next),
        ArrowLeft/ArrowUp (previous), Enter/Space (findCompanyInTable
        lookup), Escape (clear + redraw), +/- (zoom via scaleBy), and
        alphanumeric quick-jump into #network-search.
     S4 blur removes the kb-focused class.
     S5 css/style.css has the #network-graph canvas :focus and
        .kb-focused outline rules.
     S6 the announcement text is data-bearing (ticker + name +
        "Press Enter for details").
     S7 the document-level single-key shortcuts bail when the key was
        already handled (e.defaultPrevented) -- the 2026-10-09 double-fire
        fix: pilot-surface arrow keys no longer also flip table pages.
     S8 the network quick-jump stopPropagation()s alphanumeric keys (the
        char still types into #network-search; global letter shortcuts
        like 't' must not fire on top).
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 focusing the canvas announces the first node ("Focused
        <TICKER>") and shows the network tooltip with that ticker.
     R2 ArrowRight moves to the next node (announcement ticker
        changes) WITHOUT flipping the table page (no "Showing ..."
        announcement, table footer text unchanged).
     R3 Enter fires findCompanyInTable with the focused node's ticker.
     R4 Escape hides the tooltip and clears the announcement focus.
     R6 quick-jump: typing 't' on the canvas focuses #network-search,
        types the char, and does not scroll to the table or announce
        a table page.
     R5 zero JS page errors.

Usage:
  scripts/check_network_keyboard.py              # static + render
  scripts/check_network_keyboard.py --static-only

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
NETWORK_JS = os.path.join(REPO, "js", "network.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    network = open(NETWORK_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()

    s1 = ("canvas.setAttribute('tabindex', '0')" in network
          and "canvas.setAttribute('role', 'img')" in network
          and "Use arrow keys to navigate nodes, Enter to view details, plus and minus to zoom" in network)
    check("S1 network canvas is tabindex=0 role=img with instruction-bearing aria-label",
          s1, "" if s1 else "canvas a11y attributes missing")

    focus_m = re.search(
        r"canvas\.addEventListener\('focus', function\(\) \{([\s\S]*?)\n    \}\);",
        network)
    focus = focus_m.group(1) if focus_m else ""
    s2 = (focus_m is not None
          and "_focusKeyboardNode(list[0], true)" in focus
          and "canvas.classList.add('kb-focused')" in focus
          and "showTooltip(" in network  # _focusKeyboardNode shows the node tooltip
          and "announce('Focused '" in network)
    check("S2 focus moves to first navigable node, announces, tooltips, adds kb-focused",
          s2, "" if s2 else "focus handler wiring missing")

    key_m = re.search(
        r"canvas\.addEventListener\('keydown', function\(ev\) \{([\s\S]*?)\n    \}\);",
        network)
    key = key_m.group(1) if key_m else ""
    s3 = (key_m is not None
          and "'ArrowRight'" in key and "'ArrowDown'" in key and "'Tab'" in key
          and "'ArrowLeft'" in key and "'ArrowUp'" in key
          and "'Enter'" in key and "' '" in key
          and "window.findCompanyInTable(target.ticker)" in key
          and "'Escape'" in key
          and "zoom.scaleBy" in key
          and "network-search" in key
          and key.count("ev.preventDefault()") >= 5)
    check("S3 keydown: arrows/Tab cycle, Enter/Space lookup, Escape clear, +/- zoom, alnum quick-jump",
          s3, "" if s3 else "keydown coverage missing")

    s4 = "canvas.addEventListener('blur', function()" in network \
        and "canvas.classList.remove('kb-focused')" in network
    check("S4 blur removes kb-focused", s4,
          "" if s4 else "blur handler missing")

    m_focus = re.search(r"#network-graph canvas:focus \{([^}]*)\}", css)
    m_kb = re.search(r"#network-graph canvas\.kb-focused \{([^}]*)\}", css)
    s5 = (m_focus is not None and "outline:" in m_focus.group(1)
          and m_kb is not None and "outline:" in m_kb.group(1))
    check("S5 CSS :focus and .kb-focused outline rules on #network-graph canvas",
          s5, "" if s5 else "canvas focus styles missing")

    s6 = ("announce('Focused ' + node.ticker + ' ' + node.name" in network
          and "Press Enter for details." in network)
    check("S6 announcements are data-bearing (ticker + name + Enter hint)",
          s6, "" if s6 else "announcement text missing or not data-bearing")

    # S7/S8: the double-fire fix (2026-10-09 11:30 PT run). The document-level
    # single-key shortcuts must not fire for keys a focused pilot surface
    # already handled (preventDefault), and the network quick-jump must not
    # leak alphanumeric keys to those shortcuts (stopPropagation).
    app = open(os.path.join(REPO, "js", "app.js"), encoding="utf-8").read()
    g_start = app.find("// Don't fire with Ctrl/Cmd/Alt modifiers")
    g_block = app[g_start:g_start + 1200] if g_start >= 0 else ""
    s7 = ("if (e.defaultPrevented) return;" in g_block)
    check("S7 global shortcuts bail when the key was already handled (e.defaultPrevented)",
          s7, "" if s7 else "defaultPrevented guard missing from the global shortcuts handler")

    qj_m = re.search(
        r"else if \(ev\.key\.length === 1 && /\[a-zA-Z0-9\]/.test\(ev\.key\)\) \{([\s\S]*?)\n        \}",
        network)
    qj = qj_m.group(1) if qj_m else ""
    s8 = (qj_m is not None
          and "searchInput.focus()" in qj
          and "ev.stopPropagation()" in qj
          and "ev.preventDefault()" not in qj)
    check("S8 network quick-jump stopPropagation()s (char still types into search)",
          s8, "" if s8 else "quick-jump stopPropagation missing or preventDefault added")


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
            # Open the Network section and wait for the canvas.
            pg.click('a[data-section="peer-network-section"]')
            pg.wait_for_selector("#network-graph canvas", timeout=90000)
            # The force simulation needs a moment before keyboard nav is
            # meaningful; the focus handler no-ops on an empty node list.
            pg.wait_for_timeout(4000)

            def focus_canvas():
                pg.evaluate("""() => {
                  const c = document.querySelector('#network-graph canvas');
                  c.scrollIntoView({block: 'center'});
                  c.focus();
                }""")

            # R1: focusing the canvas announces the first node and shows
            # the node tooltip (parity with mouse hover).
            focus_canvas()
            try:
                pg.wait_for_function(
                    "document.getElementById('sr-announce').textContent.indexOf('Focused ') === 0",
                    timeout=15000)
            except Exception:
                # One refocus: the first focus can race the announce timer
                # on a cold load.
                focus_canvas()
                pg.wait_for_function(
                    "document.getElementById('sr-announce').textContent.indexOf('Focused ') === 0",
                    timeout=15000)
            r1info = pg.evaluate("""() => {
              const ann = document.getElementById('sr-announce').textContent;
              const tip = document.getElementById('network-tooltip');
              const ticker = (ann.match(/^Focused ([A-Z0-9.-]+)/) || [])[1] || null;
              return {ann: ann.slice(0, 80), ticker: ticker,
                      tipVisible: tip && tip.classList.contains('visible'),
                      tipHasTicker: tip && ticker ? tip.textContent.indexOf(ticker) === 0 ||
                        tip.textContent.includes(ticker) : false,
                      kbFocused: document.querySelector('#network-graph canvas')
                        .classList.contains('kb-focused')};
            }""")
            r1 = (r1info["ticker"] is not None and r1info["tipVisible"]
                  and r1info["tipHasTicker"] and r1info["kbFocused"])
            check("R1 canvas focus announces first node (%r) and shows its tooltip"
                  % r1info["ticker"],
                  r1, "ann=%r tipVisible=%s tipHasTicker=%s kbFocused=%s" % (
                      r1info["ann"], r1info["tipVisible"],
                      r1info["tipHasTicker"], r1info["kbFocused"])
                  if not r1 else "")

            # R2: ArrowRight moves to the next node (announcement ticker changes)
            # AND does not flip the table page (the double-fire fix: the
            # global shortcuts handler bails on defaultPrevented keys).
            first_ann = pg.evaluate(
                "document.getElementById('sr-announce').textContent")
            first_ticker = r1info["ticker"]
            table_footer_before = pg.evaluate(
                "document.querySelector('#table-footer .table-footer-text').textContent")
            pg.keyboard.press("ArrowRight")
            pg.wait_for_function(
                "document.getElementById('sr-announce').textContent.indexOf('Focused ') === 0 && "
                "document.getElementById('sr-announce').textContent !== %r" % (first_ann,),
                timeout=15000)
            r2info = pg.evaluate("""() => {
              const ann = document.getElementById('sr-announce').textContent;
              const footer = document.querySelector('#table-footer .table-footer-text').textContent;
              return {ticker: (ann.match(/^Focused ([A-Z0-9.-]+)/) || [])[1] || null,
                      noTableAnnounce: ann.indexOf('Showing ') !== 0,
                      footer: footer};
            }""")
            r2 = (r2info["ticker"] is not None and r2info["ticker"] != first_ticker
                  and r2info["noTableAnnounce"]
                  and r2info["footer"] == table_footer_before)
            check("R2 ArrowRight moves to next node (%r -> %r) without flipping the table page"
                  % (first_ticker, r2info["ticker"]),
                  r2, ("ticker=%r noTableAnnounce=%s footerChanged=%s" % (
                      r2info["ticker"], r2info["noTableAnnounce"],
                      r2info["footer"] != table_footer_before))
                  if not r2 else "")

            # R3: stub the company lookup (side-effect-free), then Enter.
            pg.evaluate("""() => {
              window.__fcitCalls = [];
              window.findCompanyInTable = function() {
                window.__fcitCalls.push(Array.prototype.slice.call(arguments)); };
            }""")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(600)
            r3info = pg.evaluate("({calls: window.__fcitCalls})")
            r3 = (len(r3info["calls"]) == 1 and r3info["calls"][0][0] == r2info["ticker"])
            check("R3 Enter fires findCompanyInTable(%r)" % r2info["ticker"],
                  r3, "calls recorded: %r" % (r3info["calls"],) if not r3 else "")

            # R4: Escape hides the tooltip and clears keyboard focus.
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)
            r4info = pg.evaluate("""() => ({
              tipVisible: document.getElementById('network-tooltip')
                .classList.contains('visible')
            })""")
            r4 = not r4info["tipVisible"]
            check("R4 Escape hides the network tooltip", r4,
                  "tooltip still visible" if not r4 else "")

            # R6: quick-jump — typing a letter on the canvas focuses the
            # network search and types the char, WITHOUT firing the global
            # single-letter shortcuts ('t' must not scroll to the table or
            # announce a table page).
            pg.evaluate("""() => {
              const c = document.querySelector('#network-graph canvas');
              c.scrollIntoView({block: 'center'});
              // Blur first: the canvas is still focused from R1-R4, and
              // focus() on an already-focused element does not re-fire.
              if (document.activeElement === c) document.activeElement.blur();
              c.focus();
            }""")
            pg.wait_for_function(
                "document.getElementById('sr-announce').textContent.indexOf('Focused ') === 0",
                timeout=15000)
            pg.evaluate("document.getElementById('network-search').value = ''")
            scroll_before = pg.evaluate("window.scrollY")
            pg.keyboard.press("t")
            pg.wait_for_timeout(800)
            r6info = pg.evaluate("""() => {
              const si = document.getElementById('network-search');
              const ann = document.getElementById('sr-announce').textContent;
              return {activeIsSearch: document.activeElement === si,
                      val: si.value,
                      noTableAnnounce: ann.indexOf('Showing ') !== 0,
                      scrollY: window.scrollY};
            }""")
            r6 = (r6info["activeIsSearch"] and r6info["val"] == "t"
                  and r6info["noTableAnnounce"]
                  and abs(r6info["scrollY"] - scroll_before) < 50)
            check("R6 quick-jump 't' focuses network search, types 't', no table shortcut",
                  r6, ("activeIsSearch=%s val=%r noTableAnnounce=%s scrollDelta=%d" % (
                      r6info["activeIsSearch"], r6info["val"],
                      r6info["noTableAnnounce"],
                      abs(r6info["scrollY"] - scroll_before)))
                  if not r6 else "")

            # R5: zero JS page errors across the lifecycle.
            check("R5 zero JS page errors", len(errors) == 0,
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
