#!/usr/bin/env python3
"""Guard: the vol-tenure badge part carries its own prefix, not the
tenure quartile's.

Background (387th review, 2026-11-08): the combined-filter badge
(renderSummaryBar filterParts, js/app.js) rendered the volatility x
tenure bracket as 'Tenure: ' + label -- the exact prefix the tenure
quartile uses ('Tenure: ' + tag). With both dims active the badge
showed two 'Tenure: ...' parts ('Tenure: Established (10-20 yrs) x
Tenure: 0-99 yrs') and the reader could not tell which was which.
The announcement (386th review) and the chip already used the
distinct wording 'volatility x tenure' / 'Volatility x Tenure: '.

The fix: the badge part is now 'Volatility x Tenure: ' + label,
matching the chip (updateVolTenureFilterIndicator) and the
announcement word-for-word, so the badge names each dim once under
its own prefix.

Checks:
  C1 HARD FAIL: the badge vol-tenure line does not use the
     'Volatility x Tenure: ' prefix.
  C2 HARD FAIL: the old collision wording
     ("filterParts.push('Tenure: ' + window._activeVolTenureBracket")
     still appears anywhere in js/app.js.
  C3 HARD FAIL: more than one filterParts.push('Tenure: ' remains --
     only the tenure quartile line may use the bare prefix.
Render (headless Chromium, d3 shim from the goal hidden_files cache --
the summary bar and table are pure app.js, the shim keeps the chart
layer quiet):
  R1 tenure quartile Established (10-20 yrs) + vol-tenure 0-99 yrs +
     Information Technology sector filters to >= 1 company (AAPL:
     Cook tenure 15) and the badge reads 'Tenure: Established
     (10-20 yrs) x Volatility x Tenure: 0-99 yrs', the chip reads
     'Volatility x Tenure: 0-99 yrs', and the announcement names both
     dims distinctly. Pre-fix: the badge read 'Tenure: ... x Tenure:
     0-99 yrs' with no 'Volatility x Tenure' part.
  R2 zero page errors across the render half.

Usage:
  scripts/check_voltenure_badge_prefix.py
  scripts/check_voltenure_badge_prefix.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")

BADGE_LINE = ("filterParts.push('Volatility \u00d7 Tenure: ' "
              "+ window._activeVolTenureBracket.label)")
OLD_LINE = ("filterParts.push('Tenure: ' "
            "+ window._activeVolTenureBracket.label)")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # C1: the badge vol-tenure line uses the distinct prefix.
    check("C1 badge vol-tenure part uses 'Volatility x Tenure: ' prefix",
          BADGE_LINE in app,
          "" if BADGE_LINE in app else "badge line not found")

    # C2: the old collision wording is gone from the whole file.
    check("C2 no 'Tenure: ' + vol-tenure badge wording remains",
          OLD_LINE not in app,
          "" if OLD_LINE not in app else "old collision line still present")

    # C3: exactly one filterParts.push('Tenure: ' remains -- the tenure
    # quartile line. The new line starts with 'Volatility', so it does
    # not match this prefix.
    n_bare = app.count("filterParts.push('Tenure: ")
    check("C3 only the tenure quartile keeps the bare 'Tenure: ' badge prefix",
          n_bare == 1,
          "" if n_bare == 1 else "%d bare 'Tenure: ' badge pushes" % n_bare)

    return 0


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
            pg = browser.new_page(viewport={"width": 1280, "height": 800})
            pg.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript",
                              body=d3)

            pg.route("**/npm/d3@7*", d3_route)
            pg.route("**/unpkg.com/d3@7*", d3_route)
            pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
            pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
            pg.wait_for_selector(
                "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
            pg.wait_for_timeout(800)

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            def badge_text():
                return pg.evaluate("""() => {
                    const b = document.querySelector(
                        '#table-summary-bar .combined-filter-badge');
                    return b ? b.textContent : null;
                }""")

            def last_announce():
                return pg.evaluate(
                    "() => (typeof window._lastTableAnnounce === 'string' "
                    "&& window._lastTableAnnounce) || ''")

            # R1: tenure quartile Established (10-20 yrs) + vol-tenure
            # 0-99 yrs + Information Technology sector. AAPL passes
            # all three (Cook tenure 15). Pre-fix the badge read
            # '... x Tenure: Established (10-20 yrs) x Tenure: 0-99
            # yrs'; post-fix the second part carries its own prefix.
            # The indicator is called after filterBySector: the sector
            # path strips 'active' from existing chips, so re-render
            # the chip last.
            pg.evaluate("""() => {
                window._activeTenureQuartile = { min: 10, max: 20, tag: 'Established (10\\u201320 yrs)', label: '10\\u201320 years' };
                window._activeVolTenureBracket = { min: 0, max: Infinity, label: '0-99 yrs' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateVolTenureFilterIndicator()")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            b1 = badge_text()
            a1 = last_announce()
            chip1 = pg.evaluate(
                "() => { const c = document.getElementById('vol-tenure-chip');"
                " return c ? c.textContent : null; }")
            r1_ok = (n1 >= 1 and b1 is not None and a1 is not None
                     and chip1 is not None
                     and "Tenure: Established (10\u201320 yrs)" in b1
                     and "Volatility \u00d7 Tenure: 0-99 yrs" in b1
                     and "Volatility \u00d7 Tenure: 0-99 yrs" in chip1
                     and "tenure: Established (10\u201320 yrs)" in a1
                     and "volatility \u00d7 tenure: 0-99 yrs" in a1)
            check("R1 badge/chip/announce give vol-tenure its own prefix",
                  r1_ok,
                  "footer=%s badge=%r chip=%r announce=%r (want >=1 row, "
                  "distinct Tenure and Volatility x Tenure parts)"
                  % (n1, b1, chip1, a1))

            r2_ok = len(errors) == 0
            check("R2 zero page errors across the render half",
                  r2_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok
    finally:
        server.terminate()


def main():
    rc = static_checks()
    if rc == 2:
        return 2
    if "--static-only" in sys.argv:
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    ok = render_checks()
    if ok is None:
        print("render checks skipped")
        failed = [r for r in results if not r[1]]
        return 1 if failed else 0
    failed = [r for r in results if not r[1]]
    if failed or not ok:
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
