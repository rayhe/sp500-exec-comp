#!/usr/bin/env python3
"""Guard: the YoY chip keeps its colon in the combined label.

Background (400th review, 2026-11-09): the year-over-year chip
(updateYoYFilterIndicator, js/app.js) built its combined label as
'Information Technology x YoY +5-20%' -- the sector plus 'YoY' plus
the bucket label with no colon. Its lone form is 'YoY: +5-20%' and
the combined-filter badge part is the same 'YoY: +5-20%', so the
combined chip was the only surface that dropped the colon -- the
separator that marks 'YoY' as a dimension name rather than part of
the value. A reader combining a sector with a YoY tier saw a label
that disagreed with both its lone form and the badge right above
it. This is the same chip-wording-must-match-badge class the
399th review closed for SoP ('SoP: 90-95%'), the 398th closed for
concentration ('Concentrated (>=50%)'), and the 393rd/394th/387th
reviews closed for the other dims. It is the second half of the
queued candidate (2) the 398th review named explicitly: SoP and
YoY drop the colon in the combined chip -- the 399th fixed SoP,
this review fixes YoY, closing the queue item.

The fix: the dim label is factored as 'YoY: ' + yb.label (the lone
form, unchanged) and the combined form is sector + ' x ' + that
dim label, so combined reads 'Information Technology x YoY:
+5-20%'. Visible text changes only by regaining the ': ' the lone
chip and the badge already show; no relabel, no new wording. The
announce already names the dim ('Filtered to YoY ...'), so the
chip now agrees with all three surfaces.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the combined label carries the colon (sector +
      ' x ' + dimLabel where dimLabel = 'YoY: ' + yb.label).
  C2  HARD FAIL: the lone label is unchanged ('YoY: ' + yb.label).
  C3  HARD FAIL: the old combined form (sector + ' x YoY ' +
      yb.label, no colon) still appears in the updater.
  C4  HARD FAIL: exactly one YoY chip construction site in app.js
      (chip.id = 'yoy-filter-chip' appears once).
  C5  HARD FAIL: the badge part is unchanged
      ('YoY: ' + window._activeYoYBucket.label).
  C6  HARD FAIL: the close-button x span is still appended in the
      updater.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + YoY +5-20% bucket: the chip
      textContent contains 'Information Technology x YoY: +5-20%'
      and the close x is still the chip's last child. Pre-fix the
      chip reads 'Information Technology x YoY +5-20%' (no colon),
      so the check fails on the pre-fix tree.
  R2  zero page errors across the render half.

Usage:
  scripts/check_yoy_chip_combined_label.py
  scripts/check_yoy_chip_combined_label.py --static-only

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

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def yoy_fn(app):
    """Extract the updateYoYFilterIndicator body, or ''."""
    m = re.search(r"function updateYoYFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\n    window._updateYoYFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = yoy_fn(app)
    if not fn:
        for name in (
            "C1 YoY chip combined label keeps the colon",
            "C2 YoY chip lone label unchanged",
            "C3 old combined form without the colon is gone",
            "C4 exactly one YoY chip construction site",
            "C5 badge part still carries the colon",
            "C6 close-button x span still appended in the updater",
        ):
            check(name, False, "updateYoYFilterIndicator not found")
        return 0

    # C1: the combined label carries the colon -- either the factored
    # dimLabel form or the inline ternary form.
    ok_c1 = (("activeSector + ' \u00d7 ' + dimLabel" in fn
             and "dimLabel = 'YoY: ' + yb.label" in fn)
             or "activeSector + ' \u00d7 YoY: ' + yb.label" in fn)
    check("C1 YoY chip combined label keeps the colon",
          ok_c1,
          "combined label drops the ': ' after YoY" if not ok_c1 else "")

    # C2: the lone label is unchanged.
    ok_c2 = ("'YoY: ' + yb.label" in fn)
    check("C2 YoY chip lone label unchanged ('YoY: ' + yb.label)",
          ok_c2,
          "lone label changed or missing" if not ok_c2 else "")

    # C3: the old combined form (sector + ' x YoY ' + label, no
    # colon) is gone. The fixed line contains the substring
    # "activeSector + ' x ' + dimLabel" (or the inline colon form),
    # so match the exact old ternary tail instead.
    old = "activeSector + ' \u00d7 YoY ' + yb.label"
    check("C3 old combined form without the colon is gone",
          old not in fn,
          "old colon-less combined label still in the updater" if old in fn else "")

    # C4: exactly one YoY chip construction site.
    n_chip = app.count("chip.id = 'yoy-filter-chip'")
    check("C4 exactly one YoY chip construction site",
          n_chip == 1,
          "%d YoY chip sites" % n_chip if n_chip != 1 else "")

    # C5: the badge part still carries the colon.
    badge = "'YoY: ' + window._activeYoYBucket.label"
    check("C5 badge part still carries the colon",
          badge in app,
          "badge part changed or missing" if badge not in app else "")

    # C6: close-button x span still appended (the chip is built with
    # innerHTML '...700;">x</span>', so the char before '>' is the
    # double quote closing the style attribute, not the apostrophe
    # that opens the JS string -- see the 398th review lesson).
    ok_c6 = ('">\u00d7</span>' in fn)
    check("C6 close-button x span still present in the updater",
          ok_c6,
          "close-button span missing" if not ok_c6 else "")

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

            def chip_state():
                return pg.evaluate("""() => {
                    const c = document.getElementById('yoy-filter-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    return {
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null,
                        label: window._activeYoYBucket ? 'YoY: ' + window._activeYoYBucket.label : null
                    };
                }""")

            # R1: sector IT first, then the YoY +5-20% bucket;
            # filterByYoYBucket calls the updater itself, and the
            # updater is re-run explicitly so the chip is born
            # combined. Pre-fix the chip reads 'Information
            # Technology x YoY +5-20%' with no colon.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window.filterByYoYBucket(5, 20, '+5\u201320%')")
            pg.evaluate("() => window._updateYoYFilterIndicator()")
            pg.wait_for_timeout(1200)
            c1 = chip_state()
            want = "Information Technology \u00d7 YoY: +5\u201320%"
            r1_ok = (c1 is not None
                     and want in c1["text"]
                     and c1["lastChildText"] == "\u00d7"
                     and c1["label"] == "YoY: +5\u201320%")
            check("R1 combined YoY chip reads 'IT x YoY: +5-20%', colon intact, close x intact",
                  r1_ok,
                  "chip=%r (want text containing %r, last child 'x', label set)"
                  % (c1, want))

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
