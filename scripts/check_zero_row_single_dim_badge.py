#!/usr/bin/env python3
"""Guard: the zero-row summary bar names a lone active filter dim.

Background (423rd review, 2026-11-11): the 410th review hoisted the
combined-filter badge into the zero-row path of renderSummaryBar, but
kept the normal path's filterDims >= 2 gate there. A LONE dim that
yields zero rows -- a search term with no matches, a single empty
position filter -- therefore still showed only 'No companies match
current filters' in the bar, with no dim named. The dismiss chips in
table-controls named it and the ARIA announcement named it, but the
bar itself did not. The fix: the zero-row branch gates the badge on
filterDims >= 1. The normal path keeps >= 2 (a lone dim's stats line
already names it via the sector/count text), but the zero-row state
has no stats at all, so any active dim gets the badge there.

Checks:
  S1 HARD FAIL: the zero-row branch (filtered.length === 0) gates
     the combined badge on filterDims >= 1, not >= 2.
  S2 HARD FAIL: the normal path still gates the badge on
     filterDims >= 2 (the 423rd fix is zero-row-only).
  S3 HARD FAIL: the zero-row branch still renders the 'No companies
     match current filters' message.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  A search term with no matches ('zzzzqq'): the bar shows the
      combined badge naming the term ('"zzzzqq"') alongside the
      zero-row message, and the announcement names the search.
  R2  Two-dim zero-row (same search + Information Technology
      sector): the badge names both dims (410th regression cover).
  R3  zero page errors across the render half.

Usage:
  scripts/check_zero_row_single_dim_badge.py
  scripts/check_zero_row_single_dim_badge.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

496th review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of printing "3/3
checks passed" and returning 0). static_checks() already carries
the OSError-to-return-2 path (488th template). Pre-fix defects,
both 429th-review classes in one guard (459th-review shape):
main() folded a missing d3 shim into exit 1 (drift) although the
docstring promises exit 2 for a missing shim (Test A-live rc=1,
"3/3 checks passed", 0 R-checks -- the exit-1 drift class,
436th-review shape); a missing playwright install returned 0 with
"render checks skipped" on the statics alone (the silent-pass
variant, 430th-review shape, although the docstring promises exit
2 for playwright missing); and a transient render exception raised
before any R-check was uncaught (no retry wrapper) -- proved
in-process before the fix (~/workspace/sp500-496/pre496_proof.py:
Test A-live rc=1, "3/3 checks passed", 0 R-checks; Test A2 rc=0,
"render checks skipped", 0 R-checks; Test B UNCATCHED
RuntimeError on a simulated transient Chromium launch stall). The
proof monkeypatches get_d3_bytes to None rather than moving the d3
cache aside (the canary shard 4 is live concurrently this run at
proof time; the monkeypatch touches no shared state).
render_checks() already returns an explicit bool on success
(458th note (27) checked). Slowest unadopted shard-4 render guard
by the multi-run history plus the re-profile: 17 shard-4 runs:
zero_row median 12.4s / max 38.2s / mean 15.40s vs hist_bar median
12.2s / max 33.2s / mean 14.67s vs scatter_dots median 11.9s /
max 33.9s / mean 14.94s vs treemap median 11.4s / max 37.7s /
mean 15.26s; freshest state reading zero_row 11.4s vs hist_bar
9.9s vs scatter_dots 9.6s vs treemap 9.4s; clean standalone
re-profile this run (before the canary): zero_row 8.27s rc=0 6/6
vs hist_bar 9.83s rc=0 11/11 vs scatter_dots 9.09s vs treemap
9.21s -- the re-profile inverts the order but all four are within
1.6s, load noise per the 494th note (128); the pick stands on the
multi-run history (median/mean/latest all favor zero_row) per the
469th note (68) rule. Shard 4 is the stalest shard (last run
2026-11-17T06:34Z vs shard 1 09:02Z, shard 2 10:34Z, shard 3
13:13Z), continuing the re-baseline sequence 492nd shard 4, 493rd
shard 1, 494th shard 2, 495th shard 3. hist_bar_keyboard stays
queued next for shard 4.
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


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    # Isolate the zero-row branch: from the filtered.length === 0
    # guard to its early return.
    zr = app[app.find("if (filtered.length === 0) {"):]
    zr = zr[:zr.find("return;\n    }\n\n    // 361st review")]

    # S1: the zero-row branch gates the badge on filterDims >= 1.
    s1 = ("if (filterDims >= 1) emptyHtml += combinedFilterBadgeHtml(filterParts);"
          in zr)
    check("S1 zero-row branch gates badge on filterDims >= 1",
          s1, "" if s1 else "zero-row gate is not >= 1")

    # S2: the normal path still gates on filterDims >= 2.
    s2 = "if (filterDims >= 2) {\n        html += combinedFilterBadgeHtml(filterParts);" in app
    check("S2 normal path still gates badge on filterDims >= 2",
          s2, "" if s2 else "normal-path gate changed (423rd fix is zero-row-only)")

    # S3: the zero-row message still renders in that branch.
    s3 = "No companies match current filters" in zr
    check("S3 zero-row branch still renders the no-match message",
          s3, "" if s3 else "zero-row message missing from the branch")

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

            def bar_text():
                return pg.evaluate(
                    "() => { const b = document.getElementById('table-summary-bar');"
                    " return b ? b.textContent : null; }")

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

            # R1: lone search dim with no matches. Pre-fix the bar
            # showed only the no-match message; post-fix the badge
            # names the term.
            pg.fill("#table-search", "zzzzqq")
            pg.wait_for_timeout(1200)
            b1 = badge_text()
            bar1 = bar_text()
            a1 = last_announce()
            r1_ok = (b1 is not None and '"zzzzqq"' in b1
                     and bar1 is not None and "No companies match" in bar1
                     and "search: zzzzqq" in a1)
            check("R1 lone no-match search shows badge naming the term + zero-row message",
                  r1_ok,
                  "badge=%r bar=%r announce=%r" % (b1, bar1, a1))

            # R2: two-dim zero-row (same search + sector) still
            # badges both dims (410th regression cover).
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            b2 = badge_text()
            bar2 = bar_text()
            r2_ok = (b2 is not None and '"zzzzqq"' in b2
                     and "Information Technology" in b2
                     and bar2 is not None and "No companies match" in bar2)
            check("R2 two-dim zero-row badges both dims",
                  r2_ok,
                  "badge=%r bar=%r" % (b2, bar2))

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
