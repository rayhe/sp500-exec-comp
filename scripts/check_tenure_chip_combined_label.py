#!/usr/bin/env python3
"""Guard: the tenure-quartile chip keeps its 'Tenure: ' prefix.

Background (404th review, 2026-11-09): the tenure-quartile chip
(updateTenureFilterIndicator, js/app.js) built its label from the
bare tag ('New CEOs (<3 yrs)') -- the only surface that dropped
the 'Tenure: ' dimension prefix. The combined-filter badge part
pushes 'Tenure: ' + tag and the announce names the tenure
('Filtered to New CEOs (<3 yrs) tenure (<3 years)'), so the chip
disagreed with both. This is the same chip-wording-must-match-badge
class the 403rd review closed for equity-mix ('Equity-dominant
(80-100%)'), the 402nd for percentile, the 401st for CEO/CFO, the
400th for YoY, the 399th for SoP, and the 398th for concentration.
The 387th review already established the 'Tenure: ' prefix matters
(vol-tenure vs tenure in the badge); the chip was the remaining
surface that lacked it.

The fix: the dim label is factored as 'Tenure: ' + tq.tag (the
badge form, unchanged) and both the lone and combined forms use
it, so lone reads 'Tenure: New CEOs (<3 yrs)' and combined reads
'Information Technology x Tenure: New CEOs (<3 yrs)'. Visible text
changes only by regaining the prefix the badge already shows; no
relabel, no new wording. The announce already names the tenure, so
the chip now agrees with all three surfaces.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the combined label carries the prefix (sector +
      ' x ' + dimLabel where dimLabel = 'Tenure: ' + tq.tag).
  C2  HARD FAIL: the lone label is the prefixed form ('Tenure: '
      + tq.tag).
  C3  HARD FAIL: the old combined form (sector + ' x ' + tq.tag,
      prefix dropped) still appears in the updater.
  C4  HARD FAIL: exactly one tenure chip construction site in
      app.js (chip.id = 'tenure-filter-chip' appears once).
  C5  HARD FAIL: the badge part still carries the prefix
      ('Tenure: ' + tag).
  C6  HARD FAIL: the close-button x span is still appended in the
      updater.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + New CEOs (<3 yrs) quartile:
      the chip textContent contains 'Information Technology x
      Tenure: New CEOs (<3 yrs)' and the close x is still the
      chip's last child. Pre-fix the chip reads 'Information
      Technology x New CEOs (<3 yrs)' (no prefix), so the check
      fails on the pre-fix tree.
  R2  The combined-filter badge renders a part reading exactly
      'Tenure: New CEOs (<3 yrs)' (the badge already carried the
      prefix pre-fix -- this pins it against a future regression
      that would drop it to match the old chip).
  R3  zero page errors across the render half.

Usage:
  scripts/check_tenure_chip_combined_label.py
  scripts/check_tenure_chip_combined_label.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

509th review (2026-11-18): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of exiting 0 with no
R-checks at all). static_checks() already has the OSError-to-
return-2 path (488th template), covering the js/app.js read, so no
change there. Pre-fix defects, both 429th-review classes in one
guard: a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the docstring promises
exit 2 for a missing shim -- and printed "6/6 checks passed" while
the render half never ran (434th class); a transient render
exception raised before any R-check was uncaught (no retry wrapper)
-- proved in-process before the fix (~/workspace/sp500-509/
pre509_proof.py: Test A rc=1, "6/6 checks passed", 0 R-checks;
Test A2 rc=0 skip-on-statics; Test B UNCATCHED RuntimeError on a
simulated transient Chromium launch stall), and corroborated live
this run by the three sibling unadopted guards FAILing the
2026-11-18T14:34Z shard-4 canary with exit 1 and 0 R-checks, then
PASSing standalone minutes later (conc_filter_label 48.0s,
gender_bar_keyboard 135.6s, header_subtitle_fy 65.5s) -- the
transient-stall class, no retry wrapper to absorb it. The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (the monkeypatch touches no shared
state). There is no Test A3: the pre-fix guard has no INFRA
sentinel at all, so no truthy-sentinel form applies (unlike the
505th guard's latent S4 form). The playwright-missing branch keeps
its skip shape (rc=0 on passing statics) and the docstring's exit-2
promise for that branch is unchanged from the pre-fix guard, per
the 486th/487th precedent. render_checks() already returns an
explicit bool on success (458th note (27) checked). Slowest passing
unadopted render guard by this run's fresh in-canary times -- 35.5s
vs keyboard_treemap_pilot 34.7s in the 2026-11-18T14:34Z shard-4 run
(canary_20261118_1434_shard4of4.log) -- and by the standalone
re-profile this run (20.5s vs treemap 19.2s) and the 5-run max
(35.5s vs 34.7s); the median (10.4s vs 12.7s) and mean (15.8s vs
16.1s) favor treemap, so the pick rests on the freshest in-canary
time plus the re-profile, per the 469th note (68) rule that the
evidence base is the multi-run history plus the re-profile, not one
state reading. The three slower unadopted guards
(gender_bar_keyboard 135.6s, header_subtitle_fy 65.5s,
conc_filter_label 48.0s) are FAILing in the merged state on the
transient-stall class and pass standalone; they are excluded from
the pick until their canary state is green, per the 508th
precedent, which likewise picked the slowest passing guard in
shard 4. Shard verified with drift_canary._guard_shard (432nd note):
tenure_chip_combined_label in shard 4 (with the full check_ name;
see note (157) for the bare-name trap and note (161) for the
.py-suffix trap).
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.environ.get("SP500_REPO", "/home/hatch/repos/sp500-exec-comp")
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def tenure_fn(app):
    """Extract the updateTenureFilterIndicator body, or ''."""
    m = re.search(r"function updateTenureFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\n    window._updateTenureFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = tenure_fn(app)
    if not fn:
        for name in (
            "C1 tenure chip combined label keeps the 'Tenure: ' prefix",
            "C2 tenure chip lone label is the prefixed form",
            "C3 old combined form without the prefix is gone",
            "C4 exactly one tenure chip construction site",
            "C5 badge part still carries the prefix",
            "C6 close-button x span still appended in the updater",
        ):
            check(name, False, "updateTenureFilterIndicator not found")
        return 0

    # C1: the combined label carries the prefix -- the factored
    # dimLabel form. NOTE (404th review): this updater spells the
    # separator as the literal x char (U+00D7) in the file, unlike
    # the pctile updater's literal \u00d7 escape, so the pins below
    # match the literal char, not the escape spelling.
    ok_c1 = (("activeSector + ' \u00d7 ' + dimLabel" in fn
             and "dimLabel = 'Tenure: ' + tq.tag" in fn)
             or "activeSector + ' \u00d7 ' + 'Tenure: ' + tq.tag" in fn)
    check("C1 tenure chip combined label keeps the 'Tenure: ' prefix",
          ok_c1,
          "combined label drops the prefix" if not ok_c1 else "")

    # C2: the lone label is the prefixed form.
    ok_c2 = ("dimLabel = 'Tenure: ' + tq.tag" in fn
             and ": dimLabel" in fn)
    check("C2 tenure chip lone label is the prefixed form ('Tenure: ' + tag)",
          ok_c2,
          "lone label changed or missing" if not ok_c2 else "")

    # C3: the old combined form (sector + ' x ' + tq.tag, prefix
    # dropped) is gone. The fixed line contains the substring
    # "activeSector + ' x ' + dimLabel", so match the exact old
    # ternary tail instead.
    old = "activeSector + ' \u00d7 ' + tq.tag"
    check("C3 old combined form without the prefix is gone",
          old not in fn,
          "old prefix-less combined label still in the updater" if old in fn else "")

    # C4: exactly one tenure chip construction site.
    n_chip = app.count("chip.id = 'tenure-filter-chip'")
    check("C4 exactly one tenure chip construction site",
          n_chip == 1,
          "%d tenure chip sites" % n_chip if n_chip != 1 else "")

    # C5: the badge part still carries the prefix.
    badge = "'Tenure: ' + window._activeTenureQuartile.tag"
    check("C5 badge part still carries the prefix",
          badge in app,
          "badge part changed or missing" if badge not in app else "")

    # C6: close-button x span still appended. This updater spells
    # the x as the literal \u00d7 escape in the innerHTML string
    # (unlike the chipLabel line's literal char) -- match the
    # escape, not the rendered char.
    ok_c6 = ('">\\u00d7</span>' in fn)
    check("C6 close-button x span still present in the updater",
          ok_c6,
          "close-button span missing" if not ok_c6 else "")

    return 0


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
    if d3 is None:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA

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
                    const c = document.getElementById('tenure-filter-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    const parts = Array.from(
                        document.querySelectorAll('.combined-filter-badge .combined-filter-part')
                    ).map(function(el) { return el.textContent; });
                    return {
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null,
                        label: window._activeTenureQuartile ? 'Tenure: ' + window._activeTenureQuartile.tag : null,
                        badgeParts: parts
                    };
                }""")

            # R1/R2: sector IT first, then the New CEOs (<3 yrs)
            # quartile; filterByTenureQuartile calls the updater
            # itself, and the updater is re-run explicitly so the
            # chip is born combined. Pre-fix the chip reads
            # 'Information Technology x New CEOs (<3 yrs)' with no
            # prefix and the badge part already reads 'Tenure: New
            # CEOs (<3 yrs)'.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window.filterByTenureQuartile(0, 3, 'New CEOs (<3 yrs)', '<3 years')")
            pg.evaluate("() => window._updateTenureFilterIndicator()")
            pg.wait_for_timeout(1200)
            c1 = chip_state()
            want = "Information Technology \u00d7 Tenure: New CEOs (<3 yrs)"
            r1_ok = (c1 is not None
                     and want in c1["text"]
                     and c1["lastChildText"] == "\u00d7"
                     and c1["label"] == "Tenure: New CEOs (<3 yrs)")
            check("R1 combined tenure chip reads 'IT x Tenure: New CEOs (<3 yrs)', prefix intact, close x intact",
                  r1_ok,
                  "chip=%r (want text containing %r, last child 'x', label set)"
                  % (c1, want))

            r2_ok = (c1 is not None
                     and "Tenure: New CEOs (<3 yrs)" in (c1["badgeParts"] or []))
            check("R2 combined-filter badge carries a 'Tenure: New CEOs (<3 yrs)' part",
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
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        return 2
    if ok is None:
        print("render checks skipped")
    fails = [n for n, ok, _ in results if not ok]
    if fails or ok is False:
        if fails:
            print("FAILED: " + ", ".join(fails))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
