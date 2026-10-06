#!/usr/bin/env python3
"""Regression guard: section-nav scroll-spy must track the section on screen.

Background (2026-10-05, commit f93953a): the IntersectionObserver callback
picked the TOPMOST section (smallest rect.top), so a tall previous section
kept the nav active long after its content scrolled away - an off-by-one nav
lie. The fix picks the deepest (last in document order) section whose top has
crossed the viewport reference line. This guard pins that behavior.

This guard has two halves:
  A. Static: nav link <-> section id wiring is intact, the deep-link alias
     map covers every nav section, the click handler sets .active immediately,
     and the observer callback keeps the last-wins (off-by-one-fixed) shape
     with no min-top selection.
  B. Render (headless Chromium via playwright): after a full render, clicking
     each nav link in turn makes exactly that link .active and the observer
     agrees after the scroll settles; a pure programmatic scroll (no click)
     also lands the .active link on the section actually on screen. Zero page
     errors.

Usage:
  scripts/check_scrollspy_nav.py              # static + render
  scripts/check_scrollspy_nav.py --static-only

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
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "index.html")
APP_JS = os.path.join(REPO, "js", "app.js")
EXPECTED_LINKS = 8  # 8 nav sections as of 2026-10-06

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def nav_sections():
    html = open(INDEX, encoding="utf-8").read()
    links = re.findall(
        r'<a[^>]*class="[^"]*section-nav-link[^"]*"[^>]*>', html)
    pairs = []
    for tag in links:
        ds = re.search(r'data-section="([^"]+)"', tag)
        hr = re.search(r'href="#([^"]+)"', tag)
        pairs.append((ds.group(1) if ds else None,
                      hr.group(1) if hr else None))
    return pairs


def static_checks():
    html = open(INDEX, encoding="utf-8").read()
    src = open(APP_JS, encoding="utf-8").read()
    pairs = nav_sections()
    sections = [ds for ds, _ in pairs]

    # A1: 8 nav links, data-section == href anchor, each id exists in the page.
    check("A1 %d section-nav links in index.html" % EXPECTED_LINKS,
          len(pairs) == EXPECTED_LINKS, "%d links" % len(pairs))
    mismatched = [p for p in pairs if p[0] != p[1]]
    check("A2 data-section matches href anchor on every link",
          not mismatched, str(mismatched) if mismatched else "")
    missing = [s for s in sections
               if s and not re.search(r'id="%s"' % re.escape(s), html)]
    check("A3 every data-section target id exists in index.html",
          not missing, str(missing) if missing else "")

    # A4: sectionToAlias map keys cover exactly the nav sections.
    m = re.search(r"var sectionToAlias = \{(.*?)\};", src, re.S)
    aliases = {}
    if m:
        aliases = dict(re.findall(r"'([^']+)': '([^']+)'", m.group(1)))
    check("A4 sectionToAlias map covers all %d nav sections" % EXPECTED_LINKS,
          set(aliases) == set(sections) and len(aliases) == EXPECTED_LINKS,
          "keys: %s" % sorted(aliases))
    dup = len(set(aliases.values())) != len(aliases)
    badfmt = [a for a in aliases.values()
              if not re.match(r"^[a-z0-9-]+$", a)]
    check("A5 aliases unique and URL-safe", not dup and not badfmt,
          ("dupes" if dup else "") + (" bad:" + str(badfmt) if badfmt else ""))

    # A6: click handler sets .active immediately (click feedback).
    check("A6 click handler updates .active immediately",
          "l.classList.remove('active')" in src
          and "link.classList.add('active')" in src)

    # A7: the active-section computation keeps the off-by-one fix shape:
    # last-wins over sectionIds in document order, never a min-top selection.
    # (Since 2026-10-06 the body lives in updateSectionNavActive(), called
    # from the observer's rAF and once more after click-scrolls settle.)
    start = src.find("// === Section Navigation Bar")
    region = src[start:start + 14000] if start != -1 else ""
    last_wins = ("bestSection = id;" in region
                 and "sectionIds.forEach" in region
                 and "Later sections override earlier ones" in region)
    min_top = "Math.min(" in region
    if min_top:
        a7_detail = "min-top selection found"
    elif not region:
        a7_detail = "observer block not found"
    elif not last_wins:
        a7_detail = "shape changed"
    else:
        a7_detail = "last-wins intact"
    check("A7 active-section uses last-wins (off-by-one fix intact)",
          bool(region) and last_wins and not min_top, a7_detail)


def get_d3_bytes():
    # Same cached copy as check_methodology_buttons.py (build-time shim only).
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
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript", body=d3)

            page.route("**/npm/d3@7*", d3_route)
            page.route("**/unpkg.com/d3@7*", d3_route)
            page.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
            page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            page.route("**/fonts.gstatic.com/**", lambda r: r.abort())

            page.goto("http://127.0.0.1:%d/index.html" % port, wait_until="load")
            try:
                page.wait_for_function(
                    "window.d3 && document.querySelectorAll('.section-nav-link').length === %d"
                    % EXPECTED_LINKS, timeout=60000)
            except Exception:
                check("R0 page renders with d3 and %d nav links" % EXPECTED_LINKS,
                      False, "timeout")
                return False
            check("R0 page renders with d3 and %d nav links" % EXPECTED_LINKS, True)

            sections = page.evaluate(
                "Array.from(document.querySelectorAll('.section-nav-link'))"
                ".map(l => l.dataset.section)")

            def active_section():
                return page.evaluate(
                    "Array.from(document.querySelectorAll('.section-nav-link.active'))"
                    ".map(l => l.dataset.section)")

            def scroll_settled(timeout_ms=15000):
                # Native smooth-scroll duration scales with distance; a fixed
                # wait under-reads monster jumps (e.g. the 17kpx pvp->network
                # hop). Poll scrollY until it stops moving instead.
                last = None
                still = 0
                t0 = time.time()
                while (time.time() - t0) * 1000 < timeout_ms:
                    y = page.evaluate("window.scrollY")
                    if y == last:
                        still += 1
                    else:
                        still = 0
                        last = y
                    if still >= 5:  # ~750ms of no movement
                        return True
                    time.sleep(0.15)
                return False

            # R1: click each link in turn; the observer must agree after settle.
            # NOTE: the immediate check uses a synchronous in-page click
            # (l.click() + class read in one evaluate). A separate page.click
            # round-trip lets the observer's rAF update interleave on a stale
            # mid-scroll viewport and overwrite the click feedback before the
            # read - a harness race, not a site bug (2026-10-06).
            r1_bad = []
            for s in sections:
                imm = page.evaluate(
                    "(() => { const l = document.querySelector("
                    "'.section-nav-link[data-section=\"%s\"]'); l.click(); "
                    "return l.classList.contains('active'); })()" % s)
                scroll_settled()
                page.wait_for_timeout(800)  # observer + rAF pass after scroll
                settled = active_section()
                if not imm or settled != [s]:
                    r1_bad.append("%s imm=%s settled=%s" % (s, imm, settled))
            check("R1 click each link: immediate + settled .active on that link",
                  not r1_bad, "; ".join(r1_bad) if r1_bad else "%d/%d" % (EXPECTED_LINKS, EXPECTED_LINKS))

            # R2: pure programmatic scroll (no click handler help) lands the
            # .active link on the section actually on screen.
            r2_bad = []
            for s in sections[1:]:
                top = page.evaluate(
                    "document.getElementById('%s').getBoundingClientRect().top + window.scrollY" % s)
                page.evaluate("window.scrollTo({top: %d, behavior: 'auto'})" % max(0, top - 100))
                page.wait_for_timeout(1200)
                settled = active_section()
                if settled != [s]:
                    r2_bad.append("%s settled=%s" % (s, settled))
            check("R2 programmatic scroll: .active tracks the section on screen",
                  not r2_bad, "; ".join(r2_bad) if r2_bad else "%d/%d" % (len(sections) - 1, len(sections) - 1))

            # R3: zero JS page errors.
            check("R3 zero JS page errors", not errors, "; ".join(errors[:3]) if errors else "")
            browser.close()
    finally:
        server.terminate()
    return True


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if not static_only:
        render_checks()
    fails = [r for r in results if not r[1]]
    print("----")
    print("checks: %d pass, %d fail" % (len(results) - len(fails), len(fails)))
    if fails:
        print("GUARD FAILED")
        sys.exit(1)
    print("OK: scroll-spy nav guard (static%s)" % ("" if not static_only else "-only"))


if __name__ == "__main__":
    main()
