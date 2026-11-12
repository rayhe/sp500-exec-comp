#!/usr/bin/env python3
"""Guard: the detail-narrative sentence 2 reads grammatically.

Background (424th review, 2026-11-11): the auto-generated Compensation
Profile Summary builds sentence 2 as 'Pay is ' + structParts.join('; ') +
'.', so every struct part must read as a complement of 'Pay is'. Two parts
did not. The zero-equity part was the bare clause 'no equity awards
reported', so the 27 zero-equity CEOs (META, BRK-B, AMZN, GOOGL, ...) all
rendered 'Pay is no equity awards reported.'; and the low-concentration
part repeated the subject ('pay is distributed broadly'), giving META
'Pay is no equity awards reported; pay is distributed broadly (22% CEO
share).' The fix rewords both parts to complement phrases: 'entirely
cash-based (no equity awards reported)' and 'broadly distributed (N%
CEO share)'. The 'CEO takes N% ...' parts stay untouched: after a
semicolon they are standalone clauses, which is grammatical, and no
company has a null stock pct with a concentration part (verified live:
nullStockWithConc == 0), so 'Pay is CEO takes ...' cannot occur as a
first part.

Checks:
  S1 HARD FAIL: the zero-equity struct part is not the complement form
     'entirely cash-based (no equity awards reported)'.
  S2 HARD FAIL: the low-concentration struct part is not the complement
     form 'broadly distributed ('.
  S3 HARD FAIL: the bare-clause push('no equity awards reported') is
     still present anywhere in the sentence-2 builder.
  S4 HARD FAIL: any struct part still starts with 'pay is' (repeated
     subject after the 'Pay is ' lead-in).
  S5 HARD FAIL: the sentence-2 joiner is no longer
     'Pay is ' + structParts.join('; ') + '.' (the fix's premise).
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  META detail: 'Pay is entirely cash-based (no equity awards
      reported); broadly distributed (22% CEO share).'
  R2  BRK-B detail: '...; broadly distributed (1% CEO share).'
  R3  AMZN detail: 'Pay is entirely cash-based (no equity awards
      reported).' (single part, no concentration clause)
  R4  Regression: AAPL 'Pay is heavily equity-weighted (77%
      stock/options).' and MSFT 'Pay is heavily equity-weighted (86%
      stock/options); CEO takes 44% of NEO pay.' byte-identical.
  R5  zero page errors across the render half.

Usage:
  scripts/check_narrative_sentence2_grammar.py
  scripts/check_narrative_sentence2_grammar.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (JS unreadable,
playwright missing, d3 shim unavailable, server would not start).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.

Test hook: SP500_REPO env var overrides the repo path (used only to
prove the guard FAILS on a pre-fix tree).

438th review (2026-11-12): adopted render_guard_common (slowest
remaining render guard, ~25.8s in the 2026-11-12 drift_canary_state.json
run; re-profiled from the freshest drift_canary_state.json entries this
run, per the 432nd note). Pre-fix defect was the 429th-review class,
not the silent-pass variant: main() checked render_checks()'s return
value, but a missing d3 shim made render_checks() return False, which
main() folded into exit 1 (drift) although the docstring promises exit
2 (infra) -- proved in-process before the fix
(~/workspace/pre438_proof.py: rc=1, "5/5 checks passed" printed, 0
R-checks recorded). 72 local copies remain.
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

    # Isolate the sentence-2 builder: from the structParts declaration to
    # the sentences.push that joins them.
    start = app.find("var structParts = [];")
    end = app.find("sentences.push('Pay is '", start)
    if start < 0 or end < 0:
        check("S0 sentence-2 builder block found", False)
        return 1
    block = app[start:end]

    # S1: zero-equity part is the complement form.
    s1 = ("structParts.push('entirely cash-based (no equity awards reported)')" in block)
    check("S1 zero-equity part is complement-form 'entirely cash-based (no equity awards reported)'",
          s1)

    # S2: low-concentration part is the complement form.
    s2 = ("structParts.push('broadly distributed ('" in block)
    check("S2 low-concentration part is complement-form 'broadly distributed ('", s2)

    # S3: the bare-clause push is gone.
    s3 = ("structParts.push('no equity awards reported')" not in block)
    check("S3 bare-clause push('no equity awards reported') absent", s3)

    # S4: no struct part repeats the subject ('pay is ...').
    s4 = not re.search(r"structParts\.push\('pay is ", block)
    check("S4 no struct part starts with 'pay is'", s4)

    # S5: the joiner premise still holds.
    s5 = ("sentences.push('Pay is ' + structParts.join('; ') + '.');" in app)
    check("S5 sentence-2 joiner is 'Pay is ' + structParts.join('; ') + '.'", s5)

    failed = [r for r in results if not r[1]]
    return 1 if failed else 0


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
            pg.wait_for_timeout(1500)

            def sentence2(ticker):
                pg.goto("http://127.0.0.1:%d/index.html#detail=%s" % (port, ticker),
                        timeout=60000)
                pg.wait_for_selector(
                    "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
                pg.wait_for_timeout(2000)
                return pg.evaluate("""() => {
                  const panel = document.querySelector(
                      '#company-detail, .detail-panel, [id*=detail]');
                  if (!panel) return null;
                  const m = panel.innerText.match(/Pay is [^.]*\\./);
                  return m ? m[0] : null;
                }""")

            # R1: META -- both parts fixed.
            s_meta = sentence2("META")
            r1_ok = (s_meta == "Pay is entirely cash-based (no equity awards reported); "
                               "broadly distributed (22% CEO share).")
            check("R1 META sentence 2 is complement-form", r1_ok, repr(s_meta))

            # R2: BRK-B -- 1% CEO share variant.
            s_brk = sentence2("BRK-B")
            r2_ok = (s_brk == "Pay is entirely cash-based (no equity awards reported); "
                               "broadly distributed (1% CEO share).")
            check("R2 BRK-B sentence 2 is complement-form", r2_ok, repr(s_brk))

            # R3: AMZN -- single zero-equity part, no concentration clause.
            s_amzn = sentence2("AMZN")
            r3_ok = (s_amzn == "Pay is entirely cash-based (no equity awards reported).")
            check("R3 AMZN sentence 2 is single complement part", r3_ok, repr(s_amzn))

            # R4: regression -- equity-weighted narratives byte-identical.
            s_aapl = sentence2("AAPL")
            s_msft = sentence2("MSFT")
            r4_ok = (s_aapl == "Pay is heavily equity-weighted (77% stock/options)."
                     and s_msft == "Pay is heavily equity-weighted (86% stock/options); "
                                   "CEO takes 44% of NEO pay.")
            check("R4 AAPL/MSFT sentences unchanged",
                  r4_ok, "AAPL=%r MSFT=%r" % (s_aapl, s_msft))

            r5_ok = len(errors) == 0
            check("R5 zero page errors across the render half",
                  r5_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return r1_ok and r2_ok and r3_ok and r4_ok and r5_ok
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
        return 1 if failed else 0
    failed = [r for r in results if not r[1]]
    if failed or not ok:
        print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
        return 1
    print("%d/%d checks passed" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
