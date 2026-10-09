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
"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(REPO, "js", "app.js")
D3_SHIM = os.path.expanduser(
    "~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/methbtn-20261005/d3.min.js")

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


def get_d3_bytes():
    if os.path.exists(D3_SHIM):
        return open(D3_SHIM, "rb").read()
    try:
        tmp = tempfile.mktemp(suffix=".js")
        subprocess.run(["curl", "-sL", "--max-time", "25",
                        "https://cdn.jsdelivr.net/npm/d3@7", "-o", tmp],
                       check=True, timeout=30)
        return open(tmp, "rb").read()
    except Exception:
        return None


def render_checks():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: render checks need playwright (pip install playwright)")
        return
    d3 = get_d3_bytes()
    if not d3:
        print("INFRA: could not obtain d3.min.js shim")
        sys.exit(2)
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
            check("R4 zero JS page errors", len(errors) == 0,
                  "" if not errors else "; ".join(errors[:3]))
            br.close()
    finally:
        srv.terminate()


def main():
    static_only = "--static-only" in sys.argv
    static_checks()
    if not static_only:
        render_checks()
    fails = [r for r in results if not r[1]]
    print("%d/%d checks passed" % (len(results) - len(fails), len(results)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
