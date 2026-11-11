#!/usr/bin/env python3
"""Guard: the ratio chip, badge and announcement agree on 'Ratio: '.

Background (415th review, 2026-11-10): the ratio dim was the last
unaudited dim of the combined-chip sweep (candidate (2) from the
403rd review; the 414th closed crosstab and audited dist
CONSISTENT). Two surfaces disagreed with the chip:

  * Badge: renderSummaryBar pushed 'Ratio ' + rb.min + ... (no
    colon), so combined with a sector the badge read
    'Information Technology x Ratio 100–200:1' while the chip read
    'Information Technology x Ratio: 100–200:1' -- a one-char colon
    drop, the same chip-wording-must-match-badge class the 414th
    review closed for crosstab, the 405th for peer-dist, the 404th
    for tenure, the 403rd for equity-mix and the 402nd for
    percentile. The chip form is canonical: every other dim's badge
    part uses the 'Dim: value' form ('SoP: ', 'Tenure: ',
    'Crosstab: ', 'CEO/CFO: ', 'YoY: ', 'Volatility: ', 'Gov: ',
    'Peer Delta: ', 'Community: ', 'Peers: ').
  * Announce: renderTable appended ', pay ratio filter active' --
    the only dim that named itself without its value. Every other
    dim carries its value (SoP label, board label, dist label,
    conc tag, CEO/CFO label, ...), so a screen-reader user heard
    the filter was on but not which bucket.

The fix: the badge part is now 'Ratio: ' + rb.min + ... (chip
form verbatim) and the announce carries ', pay ratio: ' + min +
'-' + max + ':1'. Visible text changes only by regaining the
colon the chip already shows; the announce gains the bucket range.

This run also audited the dist dim CONSISTENT, no fix needed --
chip, badge and announce all carry df.label verbatim (lone chip
= df.label; combined chip = sector + ' x ' + label; badge part =
df.label when sector-less, and a sector-carrying dist filter is
represented by the sector part by design, 383rd review; announce
= ', ' + df.label, and the set-time announce names it: 'Filtered
to ' + label + ' compensation bracket'). With dist and ratio
audited, the combined-chip sweep is closed: every dim verified.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the badge part carries the 'Ratio: ' prefix
      ('Ratio: ' + rb.min).
  C2  HARD FAIL: the chip baseLabel is the 'Ratio: ' form
      ('Ratio: ' + bucket.min).
  C3  HARD FAIL: the old badge form without the colon
      (filterParts.push('Ratio ' + rb.min) is gone. NOTE: the
      gov-components line ('Ratio ' + company._govComponents.ratio)
      is a different dim (gov score sub-component), not the ratio
      filter badge -- the pin matches the filterParts.push form
      exactly so that line does not trip it.
  C4  HARD FAIL: exactly one ratio chip construction site in
      app.js (chip.id = 'ratio-filter-chip' appears once).
  C5  HARD FAIL: the announcement carries the bucket
      (', pay ratio: ' + arb.min).
  C6  HARD FAIL: the old announce form ('pay ratio filter active')
      is gone.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + ratio bucket 100-200: the
      chip textContent contains 'Information Technology x Ratio:
      100–200:1' and the close x is still the chip's last child;
      the last table announcement contains 'pay ratio: 100–200:1'.
      Pre-fix the chip already read 'Ratio: ...' but the badge
      read 'Ratio 100–200:1' and the announcement read 'pay ratio
      filter active', so R1/R2 fail on the pre-fix tree.
  R2  The combined-filter badge renders a part reading exactly
      'Ratio: 100–200:1' (the badge already carried the range
      pre-fix, without the colon -- this pins the colon against a
      future regression that would drop it to match nothing).
  R3  zero page errors across the render half.

Usage:
  scripts/check_ratio_chip_combined_label.py
  scripts/check_ratio_chip_combined_label.py --static-only

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


def ratio_fn(app):
    """Extract the updateRatioFilterIndicator body, or ''."""
    m = re.search(r"function updateRatioFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\nwindow._updateRatioFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = ratio_fn(app)
    if not fn:
        for name in (
            "C1 ratio badge part carries the 'Ratio: ' prefix",
            "C2 ratio chip baseLabel is the 'Ratio: ' form",
            "C3 old badge form without the colon is gone",
            "C4 exactly one ratio chip construction site",
            "C5 announcement carries the ratio bucket",
            "C6 old announce form ('pay ratio filter active') is gone",
        ):
            check(name, False, "updateRatioFilterIndicator not found")
        return 0

    # C1: the badge part carries the prefix. NOTE (415th review):
    # the badge builder spells the separator with the literal x
    # char (U+00D7) in filterParts.join, like the crosstab updater,
    # but this pin matches the 'Ratio: ' + rb.min fragment only.
    ok_c1 = "filterParts.push('Ratio: ' + rb.min" in app
    check("C1 ratio badge part carries the 'Ratio: ' prefix",
          ok_c1,
          "badge part drops the colon" if not ok_c1 else "")

    # C2: the chip baseLabel is the prefixed form.
    ok_c2 = "var baseLabel = 'Ratio: ' + bucket.min" in fn
    check("C2 ratio chip baseLabel is the 'Ratio: ' form",
          ok_c2,
          "chip baseLabel changed or missing" if not ok_c2 else "")

    # C3: the old badge form (no colon) is gone. Match the exact
    # filterParts.push form so the gov-components 'Ratio ' +
    # company._govComponents.ratio line does not trip it.
    old = "filterParts.push('Ratio ' + rb.min"
    check("C3 old badge form without the colon is gone",
          old not in app,
          "old colon-less badge part still in the badge builder" if old in app else "")

    # C4: exactly one ratio chip construction site.
    n_chip = app.count("chip.id = 'ratio-filter-chip'")
    check("C4 exactly one ratio chip construction site",
          n_chip == 1,
          "%d ratio chip sites" % n_chip if n_chip != 1 else "")

    # C5: the announcement carries the bucket range.
    ok_c5 = "announceMsg += ', pay ratio: ' + arb.min" in app
    check("C5 announcement carries the ratio bucket",
          ok_c5,
          "announcement still drops the bucket" if not ok_c5 else "")

    # C6: the old announce form is gone. Pin the code statement
    # (announceMsg += ', pay ratio filter active'), not the bare
    # phrase -- the 415th review comment above the new line quotes
    # the old wording, and the bare phrase would false-trip on it.
    old_ann = "announceMsg += ', pay ratio filter active'"
    check("C6 old announce form ('pay ratio filter active') is gone",
          old_ann not in app,
          "old bucket-less announce still in renderTable" if old_ann in app else "")

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
                    const c = document.getElementById('ratio-filter-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    const parts = Array.from(
                        document.querySelectorAll('.combined-filter-badge .combined-filter-part')
                    ).map(function(el) { return el.textContent; });
                    return {
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null,
                        badgeParts: parts,
                        announce: window._lastTableAnnounce || null
                    };
                }""")

            # R1/R2: sector IT first, then the 100-200 ratio bucket
            # (the click path goes through the ratio histogram; the
            # updater reads only the stored state, so the API call
            # is the same code path). renderTable runs inside
            # filterByRatioBucket, so the badge re-renders and the
            # announce is stored in _lastTableAnnounce. Pre-fix the
            # chip already reads 'Ratio: 100–200:1' but the badge
            # part reads 'Ratio 100–200:1' and the announcement
            # reads 'pay ratio filter active'.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window.filterByRatioBucket(100, 200)")
            pg.wait_for_timeout(1200)
            c1 = chip_state()
            want = "Information Technology \u00d7 Ratio: 100–200:1"
            r1_ok = (c1 is not None
                     and want in c1["text"]
                     and c1["lastChildText"] == "\u00d7"
                     and c1["announce"] is not None
                     and "pay ratio: 100–200:1" in c1["announce"])
            check("R1 combined ratio chip reads 'IT x Ratio: 100–200:1', close x intact, announce carries 'pay ratio: 100–200:1'",
                  r1_ok,
                  "chip=%r (want text containing %r, last child 'x', announce carrying 'pay ratio: 100–200:1')"
                  % (c1, want))

            r2_ok = (c1 is not None
                     and "Ratio: 100–200:1" in (c1["badgeParts"] or []))
            check("R2 combined-filter badge carries a 'Ratio: 100–200:1' part",
                  r2_ok,
                  "badgeParts=%r" % (c1["badgeParts"] if c1 else None))

            r3_ok = len(errors) == 0
            check("R3 zero page errors across the render half",
                  r3_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok and r3_ok
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
