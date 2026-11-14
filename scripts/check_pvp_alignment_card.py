#!/usr/bin/env python3
"""Regression guard: the "Pay vs Performance Alignment" insight card (#26)
must stay consistent with the Pay vs Performance comparison table.

Background (2026-10-09): the 498-company / 2,466 company-year Item 402(v)
dataset (data/pay_vs_performance.json) was fully computed and tabled but had
no headline insight card answering "does CEO pay track shareholder returns?".
The new card surfaces the panel-wide CAP<->company-TSR Pearson r alignment.

Consistency contract (this guard):
  S1: the card derives its rows from pvpComparisonRows() — the same canonical
      computation the PvP section table renders. It must not reimplement the
      Pearson r or the window aggregation.
  S2: the card classifies via the table's own row.align field
      ('aligned'/'mixed'/'misaligned'), not hard-coded r thresholds that
      could drift from the table's convention.
  S3: the drill-down action navigates to 'pvp-comparison-section' (whose
      default sort is rCo ascending = least-aligned first) and carries an
      actionHint.
  R1-R3 (render, headless Chromium via playwright, 1440px desktop, d3 shim):
      R1 the card renders in #insights-grid with label "Pay vs Performance
         Alignment" and a value of "<n> Misaligned" or "Median r ...".
      R2 the misaligned count in the card matches pvpComparisonRows()'s own
         'misaligned' count (no silent divergence between card and table).
      R3 clicking the card scrolls the page near #pvp-comparison-section;
         zero JS page errors throughout.

Usage:
  scripts/check_pvp_alignment_card.py              # static + render
  scripts/check_pvp_alignment_card.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

459th review (2026-11-14): adopted scripts/render_guard_common.py
(slowest unadopted render guard overall, 24.1s fresh shard-3 verdict
in the 2026-11-14T05:02:05Z canary run; re-profiled with the canary's
exact shard function, per the 455th note (17)). Pre-fix defects were
BOTH 429th-review classes: (#1, no retry wrapper) a transient render
exception raised before any R-check was uncaught -- traceback, exit 1,
0 R-checks, no FAIL verdict; (#2, missing-d3 exit-code mismatch, in
the S4-harness form) main() ignored render_checks()'s return value, so
a render half returning INFRA exited 0 with "4/4 checks passed" while
the render half never ran -- the 430th-review silent-pass variant,
proved in-process before the fix (~/workspace/sp500-459/pre459_proof.py:
Test A rc=0 with "4/4 checks passed" printed and 0 R-checks recorded;
Test B UNCATCHED RuntimeError on a simulated transient Chromium launch
stall). The missing-d3 path itself called sys.exit(2) from inside
render_checks(), so the live silent pass was masked -- but the
return-value contract was still broken and the S4 harness could not
observe the INFRA mapping. The adoption also converts main() to return
its exit code (not sys.exit) so the contract guard's S4 harness can
observe the INFRA mapping, and gives render_checks() an explicit bool
return (it previously fell off the end returning None on success, which
the adopted main() would misread as "skipped"). 62 unadopted guards
remain.
"""
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_guard_common import INFRA, get_d3_bytes, run_render_with_retry  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def card_block(src):
    m = re.search(
        r"// 26\. Pay vs Performance Alignment[\s\S]*?insights\.push\(\{[\s\S]*?\}\);\n    \}\)\(\);",
        src)
    return m.group(0) if m else None


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()
    block = card_block(src)
    check("S0 card #26 block exists", block is not None,
          "" if block else "Pay vs Performance Alignment IIFE not found in js/app.js")
    if not block:
        return
    s1 = ("pvpComparisonRows()" in block
          and "pvpPearson" not in block
          and "dx * dy" not in block)
    check("S1 card uses pvpComparisonRows(), no reimplemented Pearson math",
          s1, "" if s1 else "card must call the table's canonical computation")
    s2 = ("r.align === 'misaligned'" in block
          and "r.align === 'aligned'" in block
          and "r.align === 'mixed'" in block
          and "rCo >= 0.5" not in block
          and "rCo <= -0.5" not in block)
    check("S2 card classifies via row.align (table convention), no own r thresholds",
          s2, "" if s2 else "classification must reuse the table's align field")
    s3 = ("scrollToSectionById('pvp-comparison-section')" in block
          and "actionHint" in block)
    check("S3 drill-down navigates to pvp-comparison-section with actionHint",
          s3, "" if s3 else "action must scroll to the PvP section")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def render_checks():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: render checks need playwright (pip install playwright)")
        return
    d3 = get_d3_bytes()
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        return INFRA
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                            "--bind", "127.0.0.1"],
                           cwd=REPO, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors = []
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 1440, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.route("**/npm/d3@7*",
                     lambda r: r.fulfill(status=200, content_type="application/javascript", body=d3))
            pg.route("**/unpkg.com/d3@7*",
                     lambda r: r.fulfill(status=200, content_type="application/javascript", body=d3))
            pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**",
                     lambda r: r.fulfill(status=200, content_type="application/javascript", body=d3))
            pg.goto("http://127.0.0.1:%d/index.html" % port, wait_until="networkidle")
            pg.wait_for_function(
                "document.querySelectorAll('#insights-grid .insight-card').length > 5",
                timeout=30000)
            card = pg.locator("#insights-grid .insight-card",
                              has_text="Pay vs Performance Alignment")
            r1 = card.count() == 1
            value = card.locator(".insight-value").inner_text() if r1 else ""
            r1 = r1 and (re.match(r"^\d+ Misaligned$", value)
                         or value.startswith("Median r "))
            check("R1 card renders with '<n> Misaligned' / 'Median r' value",
                  r1, "" if r1 else "value was %r" % value)
            # R2: card count must match the table's own classification.
            table_mis = pg.evaluate(
                "() => {"
                "  var el = document.querySelector('#pvp-comp-tbody');"
                "  if (!el) return -1;"
                "  return el.querySelectorAll('span.pvp-align-misaligned').length;"
                "}")
            m = re.match(r"^(\d+) Misaligned$", value)
            r2 = m is not None and table_mis >= 0 and int(m.group(1)) == table_mis
            check("R2 card misaligned count matches PvP table rows",
                  r2, "" if r2 else "card=%r table=%r" % (value, table_mis))
            card.click()
            pg.wait_for_timeout(1200)
            sec_y = pg.locator("#pvp-comparison-section").bounding_box()["y"]
            r3 = 0 <= sec_y < 400
            check("R3 click scrolls near the PvP section", r3,
                  "" if r3 else "section viewport y=%r" % sec_y)
            r4_ok = len(errors) == 0
            check("R4 zero JS page errors", r4_ok,
                  "" if not errors else "; ".join(errors[:3]))
            br.close()
            return r1 and r2 and r3 and r4_ok
    finally:
        srv.terminate()


def main():
    if "--static-only" in sys.argv:
        static_checks()
        failed = [r for r in results if not r[1]]
        print("%d/%d static checks passed" % (len(results) - len(failed), len(results)))
        return 1 if failed else 0
    static_checks()
    ok = run_render_with_retry(render_checks, results, check)
    if ok is INFRA:
        print("render checks infra (d3 shim unavailable)")
        return 2
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
