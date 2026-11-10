#!/usr/bin/env python3
"""Guard: the percentile-tier chip keeps its tag in the combined label.

Background (402nd review, 2026-11-09): the percentile-tier chip
(updatePctileFilterIndicator, js/app.js) built its combined label as
'Information Technology x P90+' -- the sector plus the tier label
with no tag. Its lone form is 'Top Decile (P90+)', so the combined
chip was the only surface that dropped the tag -- the tag that says
which bracket the label belongs to ('P90+' alone does not say Top
Decile vs anything else). The combined-filter badge part had the same
defect (it pushed the bare label), so BOTH the chip and the badge
disagreed with the lone form. This is the same
chip-wording-must-match-badge class the 401st review closed for
CEO/CFO ('CEO/CFO: 2-3x'), the 400th for YoY, the 399th for SoP,
and the 398th for concentration. It is the first item of the queued
candidate (2) the 401st review named explicitly: pctile drops the
tag in both the combined chip and the badge; stockpct (tag drops,
'Equity: <label>' vs lone 'tag (label)') remains queued.

The fix: the dim label is factored as pt.tag + ' (' + pt.label + ')'
(the lone form, unchanged) and the combined form is sector + ' x ' +
that dim label, so combined reads 'Information Technology x Top
Decile (P90+)'; the badge part is tag + ' (' + label + ')'. Visible
text changes only by regaining the tag the lone chip already shows;
no relabel, no new wording. The announce already names the tag
('Filtered to Top Decile (P90+)'), so the chip now agrees with all
three surfaces.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the combined label carries the tag (sector +
      ' x ' + dimLabel where dimLabel = pt.tag + ' (' + pt.label
      + ')').
  C2  HARD FAIL: the lone label is unchanged (pt.tag + ' (' +
      pt.label + ')').
  C3  HARD FAIL: the old combined form (sector + ' x ' + pt.label,
      tag dropped) still appears in the updater.
  C4  HARD FAIL: exactly one percentile chip construction site in
      app.js (chip.id = 'pctile-filter-chip' appears once).
  C5  HARD FAIL: the badge part carries the tag (tag + ' (' +
      label + ')').
  C6  HARD FAIL: the close-button x span is still appended in the
      updater.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + Top Decile (P90+) tier: the
      chip textContent contains 'Information Technology x Top
      Decile (P90+)' and the close x is still the chip's last
      child. Pre-fix the chip reads 'Information Technology x
      P90+' (no tag), so the check fails on the pre-fix tree.
  R2  The combined-filter badge renders a part reading exactly
      'Top Decile (P90+)' (the badge half of this fix -- pre-fix
      the part read 'P90+').
  R3  zero page errors across the render half.

Usage:
  scripts/check_pctile_chip_combined_label.py
  scripts/check_pctile_chip_combined_label.py --static-only

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


def pctile_fn(app):
    """Extract the updatePctileFilterIndicator body, or ''."""
    m = re.search(r"function updatePctileFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\n    window._updatePctileFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = pctile_fn(app)
    if not fn:
        for name in (
            "C1 percentile chip combined label keeps the tag",
            "C2 percentile chip lone label unchanged",
            "C3 old combined form without the tag is gone",
            "C4 exactly one percentile chip construction site",
            "C5 badge part still carries the tag",
            "C6 close-button x span still appended in the updater",
        ):
            check(name, False, "updatePctileFilterIndicator not found")
        return 0

    # C1: the combined label carries the tag -- either the factored
    # dimLabel form or the inline ternary form. NOTE (402nd review):
    # this updater spells the separator as the literal \u00d7 escape
    # in the file (unlike the CEO/CFO updater's literal x char), so
    # the pins below match the escape spelling, not the rendered char.
    ok_c1 = (("activeSector + ' \\u00d7 ' + dimLabel" in fn
             and "dimLabel = pt.tag + ' (' + pt.label + ')'" in fn)
             or "activeSector + ' \\u00d7 ' + pt.tag + ' (' + pt.label + ')'" in fn)
    check("C1 percentile chip combined label keeps the tag",
          ok_c1,
          "combined label drops the tag" if not ok_c1 else "")

    # C2: the lone label is unchanged.
    ok_c2 = ("pt.tag + ' (' + pt.label + ')'" in fn)
    check("C2 percentile chip lone label unchanged (tag + ' (' + label + ')')",
          ok_c2,
          "lone label changed or missing" if not ok_c2 else "")

    # C3: the old combined form (sector + ' x ' + pt.label, tag
    # dropped) is gone. The fixed line contains the substring
    # "activeSector + ' x ' + dimLabel" (or the inline tag form),
    # so match the exact old ternary tail instead. The old form
    # spells the separator as the literal \u00d7 escape, same as C1.
    old = "activeSector + ' \\u00d7 ' + pt.label"
    check("C3 old combined form without the tag is gone",
          old not in fn,
          "old tag-less combined label still in the updater" if old in fn else "")

    # C4: exactly one percentile chip construction site.
    n_chip = app.count("chip.id = 'pctile-filter-chip'")
    check("C4 exactly one percentile chip construction site",
          n_chip == 1,
          "%d percentile chip sites" % n_chip if n_chip != 1 else "")

    # C5: the badge part still carries the tag.
    badge = ("window._activePctileTier.tag + ' (' + "
             "window._activePctileTier.label + ')'")
    check("C5 badge part still carries the tag",
          badge in app,
          "badge part changed or missing" if badge not in app else "")

    # C6: close-button x span still appended (the chip is built with
    # innerHTML '...700;">x</span>', so the char before '>' is the
    # double quote closing the style attribute, not the apostrophe
    # that opens the JS string -- see the 398th review lesson).
    # This updater spells the x as the literal \u00d7 escape, same
    # as C1/C3 -- match the escape, not the rendered char.
    ok_c6 = ('">\\u00d7</span>' in fn)
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
                    const c = document.getElementById('pctile-filter-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    const parts = Array.from(
                        document.querySelectorAll('.combined-filter-badge .combined-filter-part')
                    ).map(function(el) { return el.textContent; });
                    return {
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null,
                        label: window._activePctileTier ? window._activePctileTier.tag + ' (' + window._activePctileTier.label + ')' : null,
                        badgeParts: parts
                    };
                }""")

            # R1/R2: sector IT first, then the Top Decile (P90+) tier;
            # filterByPctileTier calls the updater itself, and the
            # updater is re-run explicitly so the chip is born
            # combined. Pre-fix the chip reads 'Information
            # Technology x P90+' with no tag and the badge part
            # reads 'P90+'.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window.filterByPctileTier(90, 101, 'P90+', 'Top Decile')")
            pg.evaluate("() => window._updatePctileFilterIndicator()")
            pg.wait_for_timeout(1200)
            c1 = chip_state()
            want = "Information Technology \u00d7 Top Decile (P90+)"
            r1_ok = (c1 is not None
                     and want in c1["text"]
                     and c1["lastChildText"] == "\u00d7"
                     and c1["label"] == "Top Decile (P90+)")
            check("R1 combined percentile chip reads 'IT x Top Decile (P90+)', tag intact, close x intact",
                  r1_ok,
                  "chip=%r (want text containing %r, last child 'x', label set)"
                  % (c1, want))

            r2_ok = (c1 is not None
                     and "Top Decile (P90+)" in (c1["badgeParts"] or []))
            check("R2 combined-filter badge carries a 'Top Decile (P90+)' part",
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
