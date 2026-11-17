#!/usr/bin/env python3
"""Guard: the crosstab chip keeps its 'Crosstab: ' prefix.

Background (414th review, 2026-11-10): the crosstab chip
(updateCrosstabFilterIndicator, js/app.js) built its label from the
bare cell label (e.g. 'Tenure: 0-5 x Gov: A') plus a count suffix --
the only surface that dropped the 'Crosstab: ' dimension prefix.
The combined-filter badge part pushes 'Crosstab: ' + label and the
renderTable announce names it ('crosstab: ' + label), so the chip
disagreed with both: combined with a sector it read 'Information
Technology x Tenure: 0-5 x Gov: A (12)', a cell label with no
indication it is the crosstab filter (it reads like a tenure or gov
filter). This is the same chip-wording-must-match-badge class the
405th review closed for peer-dist ('Peers: ' + label), the 404th
for tenure ('Tenure: ' + tag), the 403rd for equity-mix, the 402nd
for percentile, the 401st for CEO/CFO, the 400th for YoY, the 399th
for SoP, and the 398th for concentration.

The fix: the dim label is factored as 'Crosstab: ' + xf.label +
' (n)' (the badge form plus the count suffix, which is quantitative
content also carried by the filterTableByTickers announce) and both
the lone and combined forms use it, so lone reads 'Crosstab:
Tenure: 0-5 x Gov: A (12)' and combined reads 'Information
Technology x Crosstab: Tenure: 0-5 x Gov: A (12)'. Visible text
changes only by regaining the prefix the badge already shows; no
relabel, no new wording. The announce already names the crosstab
dimension, so the chip now agrees with all three surfaces.

This run also audited four more sweep dims CONSISTENT, no fix
needed -- team (chip/badge/announce all 'Missing Roles' /
'Complete Teams'), transition ('CEO Transitions' on all three),
PvP (toggle 'PvP-covered' = badge part; announce describes it),
asp-delta ('Peer Delta: ' + tag on chip, badge and announce; the
histogram bar title carries tag + ' (' + label + ')' but that is a
chart title, not the chip's lone form), community ('Community: ' +
label on all three) and quartile (chip = badge = announce, all
qf.label verbatim). Remaining unaudited dims: dist, ratio.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the combined label carries the prefix (sector +
      ' x ' + dimLabel where dimLabel = 'Crosstab: ' + xf.label +
      ' (' + count + ')').
  C2  HARD FAIL: the lone label is the prefixed form (the chip
      label falls back to dimLabel, not the bare cell label).
  C3  HARD FAIL: the old combined form (sector + ' x ' + xf.label
      + ' (', prefix dropped) still appears in the updater.
  C4  HARD FAIL: exactly one crosstab chip construction site in
      app.js (chip.id = 'crosstab-filter-chip' appears once).
  C5  HARD FAIL: the badge part still carries the prefix
      ('Crosstab: ' + label).
  C6  HARD FAIL: the close-button x span is still appended in the
      updater.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + crosstab cell 'Tenure: 0-5
      x Gov: A' (3 tickers): the chip textContent contains
      'Information Technology x Crosstab: Tenure: 0-5 x Gov: A
      (3)' and the close x is still the chip's last child.
      Pre-fix the chip reads 'Information Technology x Tenure:
      0-5 x Gov: A (3)' (no prefix), so the check fails on the
      pre-fix tree.
  R2  The combined-filter badge renders a part reading exactly
      'Crosstab: Tenure: 0-5 x Gov: A' (the badge already carried
      the prefix pre-fix -- this pins it against a future
      regression that would drop it to match the old chip).
  R3  zero page errors across the render half.

Usage:
  scripts/check_crosstab_chip_combined_label.py
  scripts/check_crosstab_chip_combined_label.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

497th review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of printing "6/6
checks passed" and returning 0). static_checks() already carries
the OSError-to-return-2 path (488th template). Pre-fix defects,
both 429th-review classes in one guard: main() folded a missing d3
shim into exit 1 (drift) although the docstring promises exit 2
for a missing shim (Test A-live rc=1, "6/6 checks passed", 0
R-checks -- the exit-1 drift class, 436th-review shape); a missing
playwright install returned 0 with "render checks skipped" on the
statics alone (the silent-pass variant, 430th-review shape,
although the docstring promises exit 2 for playwright missing);
and the INFRA sentinel itself is truthy, so a render half
returning INFRA would have exited 0 the same way (latent silent
pass, S4 form); and a transient render exception raised before
any R-check was uncaught (no retry wrapper) -- proved in-process
before the fix (~/workspace/sp500-497/pre497_proof.py: Test A-live
rc=1, "6/6 checks passed", 0 R-checks; Test A2 rc=0, "render
checks skipped", 0 R-checks; Test B UNCATCHED RuntimeError on a
simulated transient Chromium launch stall). The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (no canary live concurrently this
run; the monkeypatch touches no shared state). The playwright-missing
branch keeps its skip shape (rc=0 on passing statics) and the
docstring's exit-2 promise for that branch is unchanged from the
pre-fix guard, per the 486th/487th precedent. render_checks()
already returns an explicit bool on success (458th note (27)
checked). Slowest unadopted shard-1 render guard by the multi-run
history plus the re-profile: 21 shard-1 runs: crosstab median 9.8s
/ mean 11.48s / max 33.7s vs sop_chip_combined_label median 9.8s /
mean 12.78s / max 43.1s vs network_coverage_desc median 7.8s /
mean 9.83s / max 26.0s; freshest state reading crosstab 15.5s vs
sop 13.8s vs network_coverage 14.8s (2026-11-17T09:02Z shard-1
run); clean standalone re-profile this run crosstab 16.89s rc=0
9/9 vs sop 11.30s rc=0 8/8 vs network_coverage 7.65s rc=0 7/7 --
crosstab leads the freshest state and the re-profile and ties sop
on the median; sop leads only the mean/max, so the pick stands on
the freshest pre-run state plus the re-profile, per the 469th note
(68) rule. Shard 1 is the stalest shard (last run 2026-11-17T09:02Z
vs shard 2 10:34Z, shard 3 13:13Z, shard 4 14:37Z), continuing the
re-baseline sequence 493rd shard 1, 494th shard 2, 495th shard 3,
496th shard 4. sop_chip_combined_label stays queued next for
shard 1.
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


def crosstab_fn(app):
    """Extract the updateCrosstabFilterIndicator body, or ''."""
    m = re.search(r"function updateCrosstabFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\nwindow._updateCrosstabFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = crosstab_fn(app)
    if not fn:
        for name in (
            "C1 crosstab chip combined label keeps the 'Crosstab: ' prefix",
            "C2 crosstab chip lone label is the prefixed form",
            "C3 old combined form without the prefix is gone",
            "C4 exactly one crosstab chip construction site",
            "C5 badge part still carries the prefix",
            "C6 close-button x span still appended in the updater",
        ):
            check(name, False, "updateCrosstabFilterIndicator not found")
        return 0

    # C1: the combined label carries the prefix -- the factored
    # dimLabel form. NOTE (414th review): this updater spells the
    # separator as the literal x char (U+00D7) in the file, like the
    # peer-dist updater's, not the pctile updater's literal \u00d7
    # escape, so the pins below match the literal char, not the
    # escape spelling.
    ok_c1 = (("activeSector + ' \u00d7 ' + dimLabel" in fn
             and "dimLabel = 'Crosstab: ' + xf.label" in fn)
             or "activeSector + ' \u00d7 ' + 'Crosstab: ' + xf.label" in fn)
    check("C1 crosstab chip combined label keeps the 'Crosstab: ' prefix",
          ok_c1,
          "combined label drops the prefix" if not ok_c1 else "")

    # C2: the lone label is the prefixed form (chipLabel falls back
    # to dimLabel).
    ok_c2 = ("dimLabel = 'Crosstab: ' + xf.label" in fn
             and ": dimLabel" in fn)
    check("C2 crosstab chip lone label is the prefixed form ('Crosstab: ' + label)",
          ok_c2,
          "lone label changed or missing" if not ok_c2 else "")

    # C3: the old combined form (sector + ' x ' + xf.label + ' (',
    # prefix dropped) is gone. The fixed line contains the substring
    # "activeSector + ' x ' + dimLabel", so match the exact old
    # ternary tail instead.
    old = "activeSector + ' \u00d7 ' + xf.label + ' ('"
    check("C3 old combined form without the prefix is gone",
          old not in fn,
          "old prefix-less combined label still in the updater" if old in fn else "")

    # C4: exactly one crosstab chip construction site.
    n_chip = app.count("chip.id = 'crosstab-filter-chip'")
    check("C4 exactly one crosstab chip construction site",
          n_chip == 1,
          "%d crosstab chip sites" % n_chip if n_chip != 1 else "")

    # C5: the badge part still carries the prefix.
    badge = "'Crosstab: ' + window._activeCrosstabFilter.label"
    check("C5 badge part still carries the prefix",
          badge in app,
          "badge part changed or missing" if badge not in app else "")

    # C6: close-button x span still appended. This updater builds
    # the span with textContent '\u00d7' (the literal escape in the
    # file), not an innerHTML string -- match the escape.
    ok_c6 = ("xSpan.textContent = '\\u00d7'" in fn)
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
                    const c = document.getElementById('crosstab-filter-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    const parts = Array.from(
                        document.querySelectorAll('.combined-filter-badge .combined-filter-part')
                    ).map(function(el) { return el.textContent; });
                    return {
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null,
                        label: window._activeCrosstabFilter ? 'Crosstab: ' + window._activeCrosstabFilter.label : null,
                        badgeParts: parts
                    };
                }""")

            # R1/R2: sector IT first, then set a 3-ticker crosstab
            # cell directly (the click path goes through the crosstab
            # table; the updater reads only the stored state, so
            # state + updater is the same code path). renderTable
            # must follow: the badge is built by the summary render,
            # not by the chip updater, so without it the badge never
            # re-renders and R2 would read an empty part list.
            # Pre-fix the chip reads 'Information Technology x
            # Tenure: 0-5 x Gov: A (3)' with no prefix and the badge
            # part already reads 'Crosstab: Tenure: 0-5 x Gov: A'.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("""() => {
                window._activeCrosstabFilter = {
                    tickers: ['AAPL', 'MSFT', 'NVDA'],
                    label: 'Tenure: 0-5 \\u00d7 Gov: A',
                    cellKey: 'probe'
                };
                window._updateCrosstabFilterIndicator();
                var all = (typeof _chartData !== 'undefined' && _chartData && _chartData.companies)
                    ? _chartData.companies : compData.companies;
                renderTable(all);
            }""")
            pg.wait_for_timeout(1200)
            c1 = chip_state()
            want = "Information Technology \u00d7 Crosstab: Tenure: 0-5 \u00d7 Gov: A (3)"
            r1_ok = (c1 is not None
                     and want in c1["text"]
                     and c1["lastChildText"] == "\u00d7"
                     and c1["label"] == "Crosstab: Tenure: 0-5 \u00d7 Gov: A")
            check("R1 combined crosstab chip reads 'IT x Crosstab: Tenure: 0-5 x Gov: A (3)', prefix intact, close x intact",
                  r1_ok,
                  "chip=%r (want text containing %r, last child 'x', label set)"
                  % (c1, want))

            r2_ok = (c1 is not None
                     and "Crosstab: Tenure: 0-5 \u00d7 Gov: A" in (c1["badgeParts"] or []))
            check("R2 combined-filter badge carries a 'Crosstab: Tenure: 0-5 x Gov: A' part",
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
    failed = [r for r in results if not r[1]]
    if failed or ok is False:
        if failed:
            print("FAILED: " + ", ".join(r[0] for r in failed))
        else:
            print("render half failed (see INFRA lines above)")
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
