#!/usr/bin/env python3
"""Regression guard: realized-comp footnote cross-reference must be card-relative.

Background (2026-10-06): the TSLA 10-K/A realized-comp footnote is emitted in
full the first time a ticker needs it inside the insights section; later cards
for the same ticker got a compact cross-reference that read "realized-comp note
above" (and its title "in the card above"). That positional claim is only true
on the mobile single-column stack - on the desktop 3-column layout the emitting
card (usually Pay Concentration) sits to the LEFT of the referencing cards.
The fix made realizedNote() card-aware: realizedNote(ticker, cardLabel)
records the emitting card's label at emit time and the cross-reference names
that card ("realized-comp note in the Pay Concentration card"). This also
fixed a latent escaping bug (double-backslash \\u2020 rendered as literal
text instead of the dagger).

This guard has two halves:
  A. Static: (S1) no positional wording in the cross-reference return;
     (S2) the cross-reference is card-relative (interpolates the emitting
     card label); (S3) every realizedNote() call site passes a string-literal
     card label as the second argument; (S4) the emit-map stores the label.
  B. Render (headless Chromium via playwright): the insights section renders
     cross-ref spans whose text starts with the real dagger, names a card,
     and never says "above"/"below", on desktop (1440px) and phone (360px).

Usage:
  scripts/check_realized_note_ref.py              # static + render
  scripts/check_realized_note_ref.py --static-only

Exit: 0 = all checks pass; 1 = a check failed; 2 = infra problem
(playwright missing, d3 shim unavailable, server would not start).

504th review (2026-11-17): adopts the shared render helpers
(render_guard_common): the local d3-shim fetcher is deleted (it was
cache-first with a curl fallback, byte-identical to the shared one),
the render half returns the INFRA sentinel when the shim is
unavailable, and main() is restructured around
run_render_with_retry with the INFRA-to-exit-2 mapping, in the
493rd shape (including the late-raise hole fix: a render half
returning False with no FAIL recorded now returns 1 with "render
half failed (see INFRA lines above)" instead of exiting 0 with no
R-checks at all), and gains the "%d/%d checks passed" summary line
in place of the "RESULT: PASS" line. static_checks() gains the
OSError-to-return-2 path (488th template). Pre-fix defects, both
429th-review classes in one guard: a missing d3 shim made
render_checks() return False, which main() ignored entirely, so it
exited 0 (the silent-pass variant, 430th shape, although the
docstring promises exit 2 for a missing shim) -- and printed
"RESULT: PASS (4/4)" while the render half never ran; a missing
playwright install exited 0 the same way (the silent-pass variant,
although the docstring promises exit 2 for playwright missing);
and a transient render exception raised before any R-check was
uncaught (no retry wrapper) -- proved in-process before the fix
(~/workspace/sp500-504/pre504_proof.py: Test A-live rc=0,
0 R-checks; Test A2 rc=0, 0 R-checks; Test B UNCATCHED RuntimeError
on a simulated transient Chromium launch stall). The proof
monkeypatches get_d3_bytes to None and stubs
sys.modules['playwright.sync_api'] to None (ImportError) rather
than moving the d3 cache aside (the monkeypatch touches no shared
state). The playwright-missing branch keeps its skip shape (rc=0
on passing statics) and the docstring's exit-2 promise for that
branch is unchanged from the pre-fix guard, per the 486th/487th
precedent. render_checks() already returns an explicit bool on
success (458th note (27) checked). Slowest unadopted shard-4
render guard by the multi-run history plus a clean standalone
re-profile before the canary (500th note (152) rule): realized_note
median 12.1s / mean 13.9s / max 35.8s over 18 shard-4 runs, freshest
10.4s, 13.60s standalone this run vs voltenure_chip_part_spans
median 11.7s / mean 14.0s / max 42.1s, freshest 8.5s, 10.17s
standalone and keyboard_treemap_pilot median 11.5s / mean 15.1s /
max 37.7s, freshest 13.6s, 10.31s standalone -- the pick stands on
the median lead plus the standalone lead, per the 469th note (68)
rule; treemap leads only the freshest single state run, within
noise. Shard verified with drift_canary._guard_shard (432nd note):
realized_note_ref in shard 4 (with the full check_ name).
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


POSITIONAL = ["note above", "note below", "card above", "card below",
              "to the left", "to the right"]


def static_checks():
    try:
        src = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read guard inputs: %s" % exc)
        return 2

    # S1: no positional wording anywhere in the cross-reference construction.
    bad = [p for p in POSITIONAL if p in src and "realized" in src[max(0, src.find(p) - 120):src.find(p) + 120]]
    check("S1 no positional wording in realized-comp cross-reference",
          not bad, "found: %s" % bad if bad else "")

    # S2: the cross-ref return names the emitting card (card-relative).
    s2 = bool(re.search(
        r"insight-footnote-ref.*_realizedNoteEmitted\[ticker\]", src, re.S))
    check("S2 cross-reference interpolates the emitting card label",
          s2, "" if s2 else "expected _realizedNoteEmitted[ticker] inside the footnote-ref span")

    # S3: every realizedNote() call passes a string-literal card label.
    calls = re.findall(r"realizedNote\(([^)]*)\)", src)
    # Filter out the function definition itself ("ticker, cardLabel").
    call_args = [c for c in calls if "ticker" not in c or "'" in c]
    defn = [c for c in calls if c.strip() == "ticker, cardLabel"]
    s3a = len(defn) == 1
    s3b = all(re.match(r"^\s*[a-zA-Z0-9_.()\[\]]+\s*,\s*'[^']+'\s*$", c)
              for c in call_args)
    check("S3 every realizedNote call passes a string-literal card label",
          s3a and s3b,
          "" if (s3a and s3b) else
          "defn=%d calls=%r" % (len(defn), call_args))

    # S4: the emit-map stores the card label, not a boolean flag.
    s4 = "_realizedNoteEmitted[ticker] = cardLabel" in src
    check("S4 emit-map stores the card label at emit time",
          s4, "" if s4 else "expected `_realizedNoteEmitted[ticker] = cardLabel`")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


REF_JS = ("els => Array.from(document.querySelectorAll('.insight-footnote-ref'))"
          ".map(e => ({text: e.textContent, title: e.title}))")


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
            browser = pw.chromium.launch()
            errors = []

            def d3_route(route):
                route.fulfill(status=200, content_type="application/javascript", body=d3)

            for width, tag in [(1440, "desktop"), (360, "mobile")]:
                pg = browser.new_page(viewport={"width": width, "height": 900})
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.route("**/npm/d3@7*", d3_route)
                pg.route("**/unpkg.com/d3@7*", d3_route)
                pg.route("**/cdnjs.cloudflare.com/ajax/libs/d3/**", d3_route)
                pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
                pg.route("**/fonts.gstatic.com/**", lambda r: r.abort())
                pg.goto("http://127.0.0.1:%d/index.html" % port, wait_until="load")
                pg.wait_for_function(
                    "window.d3 && document.querySelectorAll('.insight-footnote-ref').length > 0",
                    timeout=90000)
                refs = pg.evaluate(REF_JS)
                card_ok = all(
                    r["text"].startswith("\u2020")
                    and re.match(r"^\u2020 realized-comp note in the .+ card$", r["text"])
                    and "above" not in r["text"] and "below" not in r["text"]
                    and r["title"].startswith("See the realized-compensation footnote in the ")
                    for r in refs)
                check("R-%s cross-refs are card-relative, dagger-rendered, no positional wording" % tag,
                      bool(refs) and card_ok,
                      "" if (refs and card_ok) else "refs=%r" % (refs,))
                pg.close()
            check("R page errors", not errors, "; ".join(errors[:3]) if errors else "")
            browser.close()
    finally:
        server.terminate()
    return True


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
