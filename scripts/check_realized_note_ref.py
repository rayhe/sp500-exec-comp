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
"""
import argparse
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


POSITIONAL = ["note above", "note below", "card above", "card below",
              "to the left", "to the right"]


def static_checks():
    src = open(APP_JS, encoding="utf-8").read()

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


REF_JS = ("els => Array.from(document.querySelectorAll('.insight-footnote-ref'))"
          ".map(e => ({text: e.textContent, title: e.title}))")


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--static-only", action="store_true",
                    help="run only the fast static checks")
    args = ap.parse_args()

    static_checks()
    if not args.static_only:
        render_checks()
    failed = [n for n, ok, _ in results if ok is False]
    infra = [n for n, ok, _ in results if ok is None]
    if failed:
        print("RESULT: FAIL (%d)" % len(failed))
        return 1
    if infra:
        print("RESULT: INFRA")
        return 2
    print("RESULT: PASS (%d/%d)" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
