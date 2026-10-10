#!/usr/bin/env python3
"""Regression guard: the scatter trend-trail year dots are keyboard-operable.

The 2026-10-10 06:00 PT panel audit found the scatter-plot trend trail
(_drawScatterTrendTrail in js/charts.js: ghost year dots + dashed polyline
drawn when a scatter dot is clicked/Enter-activated) was the last
click-without-keyboard surface on the site, missed by the 2026-10-10 03:30
PT audit because the transient 8s auto-fade made the dots invisible to the
static class sweeps:
  (1) the trail year dots (.scatter-trend-trail-dots circle) - D3
      .on('click') calling window.findCompanyInTable(ticker) (the same
      navigation as the parent scatter dot), no tabindex/role/keydown;
  (2) the FY-breakdown hover tooltip (salary/stock/options/bonus/other +
      YoY change) - the info-only hover values keyboard users got nothing
      of.

Fixes (js/charts.js _drawScatterTrendTrail; js/app.js; css/style.css):
  A. Dots: .datum(pt) binds the trend point, then _enableDotKeyboard (the
     scatter-dot pilot) upgrades them: one tab stop per trail,
     Arrow/Home/End move between year dots, focus fires the exact
     mouseenter tooltip path via a synthetic MouseEvent (which also pauses
     the auto-fade, mirroring the mouse hover-pause), blur fires
     mouseleave (restores the dot, hides the tooltip, restarts the fade),
     Enter/Space runs the same findCompanyInTable navigation as click.
     The dots carry a data-bearing aria-label (FY, ticker, total,
     component breakdown, YoY change, "Press Enter to view in table") so
     the info-only hover values are available without the tooltip.
  B. Year text labels are aria-hidden (they duplicate the dot labels).
  C. window.announce = announce exposure in js/app.js (standard
     cross-scope pattern); the trail draw announces itself for
     screen-reader discoverability ("Trend trail for META: FY2022 to
     FY2025. Tab to a year dot ...") since the trail auto-fades.
  D. css/style.css: #scatter-chart .scatter-trend-trail-dots
     circle:focus-visible gets the site's --accent ring.

Checks:
  A. Static (fast, runs in the pre-commit hook):
     S1 .datum(pt) bound on the trail-dot circle creation.
     S2 _enableDotKeyboard(d3.select(container),
        '.scatter-trend-trail-dots circle') with hoverIn 'mouseenter',
        hoverOut 'mouseleave', label + activate.
     S3 window.announce exposure in js/app.js + window.announce( call in
        the trail function.
     S4 trail year labels carry aria-hidden="true".
     S5 CSS :focus-visible rule for the trail dots.
     S6 node --check green on js/app.js and js/charts.js.
  B. Render (headless Chromium via playwright, 1440px desktop, d3 shim):
     R1 synthetic click on a scatter dot with _ceoTrend -> >=1 trail dot;
        roving shape (exactly one tabindex="0" holder, rest "-1", all
        role="button" with "Press Enter to view in table" aria-labels
        containing an FY year); year text labels aria-hidden.
     R2 focus the holder -> .chart-tooltip.visible appears with the FY
        breakdown; the auto-fade timer is paused (window._trendTrailTimer
        null, mirroring the mouse hover-pause).
     R3 ArrowRight moves the holder (focus follows); Enter on the moved
        holder calls window.findCompanyInTable exactly once with the
        company ticker.
     R4 #sr-announce received the "Trend trail for <TICKER>" text.
     R5 zero JS page errors.

Usage:
  scripts/check_trend_trail_keyboard.py              # static + render
  scripts/check_trend_trail_keyboard.py --static-only

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
CHARTS_JS = os.path.join(REPO, "js", "charts.js")
CSS = os.path.join(REPO, "css", "style.css")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ("" if ok else " -- " + detail))


def trail_fn_body(charts):
    """Return the _drawScatterTrendTrail function source (to the next top-level close)."""
    i = charts.find("function _drawScatterTrendTrail(company)")
    if i < 0:
        return ""
    # The function ends with "\n}\n" at column 0 before the next section comment.
    j = charts.find("\n}\n", i)
    return charts[i:j] if j > 0 else ""


def static_checks():
    app = open(APP_JS, encoding="utf-8").read()
    charts = open(CHARTS_JS, encoding="utf-8").read()
    css = open(CSS, encoding="utf-8").read()
    body = trail_fn_body(charts)

    s1 = bool(body) and ".datum(pt)" in body and "dotsGroup.append('circle')" in body
    check("S1 .datum(pt) bound on the trail-dot circle creation",
          s1, "" if s1 else "trail function body missing or datum not bound")

    s2 = ("_enableDotKeyboard(d3.select(container), '.scatter-trend-trail-dots circle'" in charts
          and "hoverIn: 'mouseenter'" in body
          and "hoverOut: 'mouseleave'" in body)
    check("S2 _enableDotKeyboard trail call with mouseenter/mouseleave hover pair",
          s2, "" if s2 else "keyboard upgrade call missing or hover pair wrong")

    s3 = "window.announce = announce" in app and "window.announce(" in body
    check("S3 window.announce exposure + trail-draw announcement",
          s3, "" if s3 else "announce exposure or trail call missing")

    s4 = ".attr('aria-hidden', 'true')" in body
    check("S4 trail year labels aria-hidden",
          s4, "" if s4 else "year label text would double-announce the dot label")

    s5 = "#scatter-chart .scatter-trend-trail-dots circle:focus-visible" in css
    check("S5 CSS :focus-visible ring for trail dots",
          s5, "" if s5 else "focus ring rule missing")

    for label, path in (("js/app.js", APP_JS), ("js/charts.js", CHARTS_JS)):
        r = subprocess.run(["node", "--check", path],
                           capture_output=True, text=True, timeout=60)
        check("S6 node --check %s is green" % label,
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
                "window.d3 && document.querySelector('#scatter-chart .scatter-dot')",
                timeout=90000)
            pg.wait_for_timeout(1500)

            # Draw a trail: synthetic click on a scatter dot with _ceoTrend.
            # (Default scatter x-axis is total_compensation, so the trail
            # draws without changing axes.)
            clicked = pg.evaluate("""() => {
              const dots = [...document.querySelectorAll('#scatter-chart .scatter-dot')];
              for (const el of dots) {
                const d = window.d3.select(el).datum();
                if (d && d._ceoTrend && d._ceoTrend.length >= 2) {
                  el.dispatchEvent(new MouseEvent('click',
                    {bubbles: true, cancelable: true, view: window}));
                  return d.ticker;
                }
              }
              return null;
            }""")
            if not clicked:
                check("R1 trail dots drawn with roving keyboard shape", False,
                      "no scatter dot with _ceoTrend found")
                browser.close()
                return
            pg.wait_for_timeout(600)

            # ---------- R1: roving shape + labels ----------
            r1 = pg.evaluate("""() => {
              const dots = [...document.querySelectorAll('.scatter-trend-trail-dots circle')];
              const holders = dots.filter(x => x.getAttribute('tabindex') === '0');
              const neg = dots.filter(x => x.getAttribute('tabindex') === '-1');
              const bad = dots.filter(x =>
                x.getAttribute('role') !== 'button' ||
                !(x.getAttribute('aria-label') || '').includes('Press Enter to view in table') ||
                !/FY\\d{4}/.test(x.getAttribute('aria-label') || ''));
              const labels = [...document.querySelectorAll('.scatter-trend-trail text')];
              const labelsHidden = labels.filter(t => t.getAttribute('aria-hidden') === 'true');
              return {n: dots.length, holders: holders.length, neg: neg.length,
                      bad: bad.length, labels: labels.length,
                      labelsHidden: labelsHidden.length};
            }""")
            r1ok = (r1["n"] >= 1 and r1["holders"] == 1
                    and r1["neg"] == r1["n"] - 1 and r1["bad"] == 0
                    and r1["labels"] >= 1 and r1["labelsHidden"] == r1["labels"])
            check("R1 trail dots drawn with roving shape + FY aria-labels; year labels aria-hidden",
                  r1ok, "shape: %r" % (r1,))

            # ---------- R4: screen-reader announcement ----------
            r4txt = pg.evaluate(
                "() => (document.getElementById('sr-announce') || {}).textContent || ''")
            r4ok = ("Trend trail for %s" % clicked) in r4txt
            check("R4 #sr-announce carries the trend-trail announcement",
                  r4ok, "announce text: %r" % (r4txt[:120],))

            # ---------- R2: focus -> tooltip + fade paused ----------
            pg.evaluate("""() => {
              document.querySelector('.scatter-trend-trail-dots circle[tabindex="0"]').focus();
            }""")
            pg.wait_for_timeout(400)
            r2 = pg.evaluate("""() => {
              const tip = document.querySelector('.chart-tooltip.visible');
              return {tipVisible: !!tip,
                      tipHasFY: tip ? /FY\\d{4}/.test(tip.innerHTML) : false,
                      tipHasTicker: tip ? tip.innerHTML.includes('""" + clicked + """') : false,
                      tipHasTotal: tip ? /total/i.test(tip.innerHTML) : false,
                      timerPaused: window._trendTrailTimer === null};
            }""")
            r2ok = (r2["tipVisible"] is True and r2["tipHasFY"] is True
                    and r2["tipHasTicker"] is True and r2["tipHasTotal"] is True
                    and r2["timerPaused"] is True)
            check("R2 focus shows the FY-breakdown tooltip and pauses the auto-fade",
                  r2ok, "state: %r" % (r2,))

            # ---------- R3: arrows move the holder, Enter fires navigation ----------
            r3 = False
            r3detail = ""
            n_dots = pg.evaluate(
                "() => document.querySelectorAll('.scatter-trend-trail-dots circle').length")
            if n_dots >= 2:
                t0 = pg.evaluate("""() => {
                  const h = document.querySelector('.scatter-trend-trail-dots circle[tabindex="0"]');
                  return h ? h.getAttribute('aria-label') : null;
                }""")
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(300)
                moved = pg.evaluate("""() => {
                  const h = document.querySelector('.scatter-trend-trail-dots circle[tabindex="0"]');
                  const a = document.activeElement;
                  return {label: h ? h.getAttribute('aria-label') : null,
                          focused: h ? (a === h) : false};
                }""")
                r3arrow = (moved["label"] is not None and moved["label"] != t0
                           and moved["focused"] is True)
                r3detail = "arrow: moved=%r" % (r3arrow,)
                if r3arrow:
                    pg.evaluate("""() => {
                      window.__ttFindCalls = [];
                      const orig = window.findCompanyInTable;
                      window.findCompanyInTable = function(t) {
                        window.__ttFindCalls.push(t);
                        return orig ? orig.apply(this, arguments) : null;
                      };
                    }""")
                    pg.keyboard.press("Enter")
                    pg.wait_for_timeout(900)
                    calls = pg.evaluate("() => window.__ttFindCalls")
                    r3enter = (len(calls) == 1 and calls[0] == clicked)
                    r3detail += (" | enter findCompanyInTable calls: %r (ticker %r)"
                                 % (calls, clicked))
                    r3 = r3arrow and r3enter
            else:
                r3detail = "only %d trail dot(s); arrow test needs >= 2" % n_dots
            check("R3 ArrowRight moves the holder + Enter fires findCompanyInTable(ticker)",
                  r3, r3detail)

            check("R5 zero JS page errors", len(errors) == 0,
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
