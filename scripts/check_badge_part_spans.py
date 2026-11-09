#!/usr/bin/env python3
"""Guard: the combined-filter badge renders each part in its own span,
so the part boundary is structural, not textual.

Background (396th review, 2026-11-09): the badge (renderSummaryBar
filterParts, js/app.js) joined its parts into one text node with
' × ' as the separator -- but the vol-tenure part itself contains
the joiner ('Volatility × Tenure: 0-99 yrs'). Splitting the badge
text on the joiner therefore breaks the part boundary: two parts
read as three pieces ('Information Technology', 'Volatility',
'Tenure: 0-99 yrs'). The text is only cosmetic today (no live
consumer splits it), but the badge is the one place where parts
are joined into a single text node, and any future badge-text
parser, screen-reader splitting or per-part interaction would
read the wrong boundary. Queued as candidate (3) by the 395th
review.

The fix: each part renders in its own
<span class="combined-filter-part"> and the separators are their
own <span class="combined-filter-sep"> spans carrying ' × '. The
visible text is unchanged (the separator spans carry the same
' × '), the badge textContent is byte-identical, and the parts
are individually addressable in the DOM. The vol-tenure part
keeps its internal ' × ' -- the fix is structural, not a relabel
(the 387th review deliberately made chip/badge/announce wording
match).

Checks (static - file reads, <1s):
  C1  HARD FAIL: the badge construction maps filterParts to
      .combined-filter-part spans on the summary-stat-label line.
  C2  HARD FAIL: the separators are .combined-filter-sep spans
      carrying ' × ' on that same line.
  C3  HARD FAIL: the old single-text-node join
      (filterParts.join(' × ')) still appears anywhere in app.js.
  C4  HARD FAIL: exactly one combined-filter-badge construction
      site in app.js (the class is closed to this one site).
  C5  HARD FAIL: the vol-tenure part wording is unchanged
      ('Volatility x Tenure: ' + label) -- structural fix only.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + vol-tenure 0-99 yrs: the
      badge has exactly 2 .combined-filter-part nodes with texts
      'Information Technology' and 'Volatility x Tenure: 0-99 yrs',
      exactly 1 .combined-filter-sep node with text ' × ', the badge
      textContent still contains the old joined string (visual
      identical), and the footer is >= 1. Pre-fix there are 0 part
      nodes, so the check fails on the pre-fix tree.
  R2  zero page errors across the render half.

Usage:
  scripts/check_badge_part_spans.py
  scripts/check_badge_part_spans.py --static-only

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

OLD_JOIN = "filterParts.join(' \u00d7 ')"
VOLT_BADGE_LINE = ("filterParts.push('Volatility \u00d7 Tenure: ' "
                   "+ window._activeVolTenureBracket.label)")

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

    # C1/C2: the badge construction line maps parts to spans and
    # carries the separator spans. Pin all three markers to the one
    # summary-stat-label line so a stray span elsewhere cannot
    # satisfy the checks.
    badge_lines = [ln for ln in app.splitlines()
                   if "combined-filter-part" in ln]
    line = badge_lines[0] if badge_lines else ""
    ok_c1 = (len(badge_lines) == 1
             and "filterParts.map(function(p)" in line
             and "summary-stat-label" in line
             and "'<span class=\"combined-filter-part\">' + p + '</span>'" in line)
    check("C1 badge maps each part to a .combined-filter-part span",
          ok_c1,
          "badge construction line missing or malformed" if not ok_c1 else "")
    ok_c2 = ("combined-filter-sep" in line
             and "'<span class=\"combined-filter-sep\"> \u00d7 </span>'" in line)
    check("C2 badge separators are .combined-filter-sep spans carrying the joiner",
          ok_c2,
          "separator span missing from the badge line" if not ok_c2 else "")

    # C3: the old single-text-node join is gone from the whole file
    # (the badge was its only site).
    check("C3 no single-text-node filterParts join remains in app.js",
          OLD_JOIN not in app,
          "old filterParts.join still present" if OLD_JOIN in app else "")

    # C4: exactly one badge construction site.
    n_badge = app.count("combined-filter-badge")
    check("C4 exactly one combined-filter-badge construction site",
          n_badge == 1,
          "%d badge sites" % n_badge if n_badge != 1 else "")

    # C5: the vol-tenure part wording is unchanged -- structural
    # fix only, no relabel.
    check("C5 vol-tenure badge part keeps its 'Volatility x Tenure: ' wording",
          VOLT_BADGE_LINE in app,
          "vol-tenure badge line changed or missing" if VOLT_BADGE_LINE not in app else "")

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

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            def badge_parts():
                return pg.evaluate("""() => {
                    const b = document.querySelector(
                        '#table-summary-bar .combined-filter-badge');
                    if (!b) return null;
                    return {
                        parts: [...b.querySelectorAll('.combined-filter-part')]
                            .map(el => el.textContent),
                        seps: [...b.querySelectorAll('.combined-filter-sep')]
                            .map(el => el.textContent),
                        text: b.textContent
                    };
                }""")

            # R1: sector IT + vol-tenure 0-99 yrs. AAPL passes both
            # (Cook tenure 15), so the footer is >= 1 and the badge
            # shows exactly the two parts. Pre-fix there are 0 part
            # nodes and 0 separator nodes.
            pg.evaluate("""() => {
                window._activeVolTenureBracket = { min: 0, max: Infinity, label: '0-99 yrs' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateVolTenureFilterIndicator()")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            b1 = badge_parts()
            r1_ok = (n1 >= 1 and b1 is not None
                     and b1["parts"] == ["Information Technology",
                                         "Volatility \u00d7 Tenure: 0-99 yrs"]
                     and b1["seps"] == [" \u00d7 "]
                     and "Information Technology \u00d7 Volatility "
                         "\u00d7 Tenure: 0-99 yrs" in b1["text"])
            check("R1 badge exposes exactly 2 part spans + 1 separator span, text unchanged",
                  r1_ok,
                  "footer=%s badge=%r (want >=1 row, parts [IT, Volatility × Tenure: 0-99 yrs], one ' × ' sep, joined text intact)"
                  % (n1, b1))

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
