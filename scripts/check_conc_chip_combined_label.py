#!/usr/bin/env python3
"""Guard: the concentration chip keeps its range in the combined label.

Background (398th review, 2026-11-09): the concentration chip
(updateConcFilterIndicator, js/app.js) built its combined label as
'Information Technology x Concentrated' -- the sector plus the tier
tag only. Its lone form is 'Concentrated (>=50%)' and the
combined-filter badge part is the same 'Concentrated (>=50%)', so the
combined chip was the only surface that dropped the parenthetical
range -- the quantitative content of the tier. A reader combining a
sector with a concentration tier lost exactly the number that says
which bracket is active ('>=50%' vs '35-49%' vs '<35%'), while the
badge right above it still showed it. This is the same chip-wording
must-match-badge class the 393rd/394th/387th reviews closed for the
other dims (sector prefix on every chip, vol-tenure prefix in the
badge part); the conc chip was the last dim whose combined form
disagreed with both its lone form and the badge.

The fix: the dim label is factored as ct.tag + ' (' + ct.label + ')'
(the lone form, unchanged) and the combined form is sector + ' x ' +
that dim label, so combined reads 'Information Technology x
Concentrated (>=50%)'. Visible text changes only by regaining the
' (>=50%)' the lone chip and the badge already show; no relabel,
no new wording. The announce already carries the range
('Filtered to Concentrated CEO concentration (>=50%)'), so the chip
now agrees with all three surfaces.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the combined label carries the parenthetical
      (sector + ' x ' + tag + ' (' + label + ')') in
      updateConcFilterIndicator.
  C2  HARD FAIL: the lone label is unchanged
      (ct.tag + ' (' + ct.label + ')').
  C3  HARD FAIL: the old combined form (sector + ' x ' + ct.tag
      with no parenthetical) still appears in the updater.
  C4  HARD FAIL: exactly one conc chip construction site in app.js
      (chip.id = 'conc-filter-chip' appears once).
  C5  HARD FAIL: the badge part is unchanged
      (tag + ' (' + label + ')').
  C6  HARD FAIL: the close-button x span is still appended in the
      updater.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + Concentrated (>=50%) tier:
      the chip textContent contains
      'Information Technology x Concentrated (>=50%)' and the close
      x is still the chip's last child. Pre-fix the chip reads
      'Information Technology x Concentrated' (no parenthetical),
      so the check fails on the pre-fix tree.
  R2  zero page errors across the render half.

Usage:
  scripts/check_conc_chip_combined_label.py
  scripts/check_conc_chip_combined_label.py --static-only

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


def conc_fn(app):
    """Extract the updateConcFilterIndicator body, or ''."""
    m = re.search(r"function updateConcFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\n    window._updateConcFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = conc_fn(app)
    if not fn:
        for name in (
            "C1 conc chip combined label keeps the range parenthetical",
            "C2 conc chip lone label unchanged",
            "C3 old combined form without the parenthetical is gone",
            "C4 exactly one conc chip construction site",
            "C5 badge part still carries the range parenthetical",
            "C6 close-button x span still appended in the updater",
        ):
            check(name, False, "updateConcFilterIndicator not found")
        return 0

    # C1: the combined label carries the parenthetical -- either the
    # factored dimLabel form or the inline ternary form.
    ok_c1 = (("activeSector + ' \u00d7 ' + dimLabel" in fn
             and "dimLabel = ct.tag + ' (' + ct.label + ')'" in fn)
             or "activeSector + ' \u00d7 ' + ct.tag + ' (' + ct.label + ')'" in fn)
    check("C1 conc chip combined label keeps the range parenthetical",
          ok_c1,
          "combined label drops the ' (label)' range" if not ok_c1 else "")

    # C2: the lone label is unchanged.
    ok_c2 = ("ct.tag + ' (' + ct.label + ')'" in fn)
    check("C2 conc chip lone label unchanged (tag + ' (label)')",
          ok_c2,
          "lone label changed or missing" if not ok_c2 else "")

    # C3: the old combined form (sector + ' x ' + bare tag, no
    # parenthetical) is gone. The fixed line contains the substring
    # "activeSector + ' x ' + ct.tag" too, so match the exact old
    # ternary tail instead: bare tag followed by ' : ct.tag'.
    old = "activeSector + ' \u00d7 ' + ct.tag : ct.tag"
    check("C3 old combined form without the parenthetical is gone",
          old not in fn,
          "old bare-tag combined label still in the updater" if old in fn else "")

    # C4: exactly one conc chip construction site.
    n_chip = app.count("chip.id = 'conc-filter-chip'")
    check("C4 exactly one conc chip construction site",
          n_chip == 1,
          "%d conc chip sites" % n_chip if n_chip != 1 else "")

    # C5: the badge part still carries the range parenthetical.
    badge = "window._activeConcTier.tag + ' (' + window._activeConcTier.label + ')'"
    check("C5 badge part still carries the range parenthetical",
          badge in app,
          "badge part changed or missing" if badge not in app else "")

    # C6: close-button x span still appended (after the label html;
    # pre-fix the chip is built with innerHTML, so pin only that the
    # trailing x span survives in the function).
    ok_c6 = ('">×</span>' in fn)
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
                    const c = document.getElementById('conc-filter-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    return {
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null,
                        tier: window._activeConcTier ? window._activeConcTier.tag + ' (' + window._activeConcTier.label + ')' : null
                    };
                }""")

            # R1: sector IT first, then the Concentrated (>=50%) tier;
            # the updater is re-run explicitly so the chip is born
            # combined. Pre-fix the chip reads 'Information
            # Technology x Concentrated' with no parenthetical.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window.filterByConcTier(50, 101, 'Concentrated', '\u226550%')")
            pg.evaluate("() => window._updateConcFilterIndicator()")
            pg.wait_for_timeout(1200)
            c1 = chip_state()
            want = "Information Technology \u00d7 Concentrated (\u226550%)"
            r1_ok = (c1 is not None
                     and want in c1["text"]
                     and c1["lastChildText"] == "\u00d7"
                     and c1["tier"] == "Concentrated (\u226550%)")
            check("R1 combined conc chip reads 'IT x Concentrated (>=50%)', range intact, close x intact",
                  r1_ok,
                  "chip=%r (want text containing %r, last child 'x', tier set)"
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
