#!/usr/bin/env python3
"""Guard: the vol-tenure filter chip renders each part in its own span,
so the part boundary is structural, not textual.

Background (397th review, 2026-11-09): the vol-tenure chip
(updateVolTenureFilterIndicator, js/app.js) built its label as one
text node -- 'Information Technology × Volatility × Tenure: 0-99 yrs'
when combined with a sector. The dim label itself contains the
joiner ('Volatility × Tenure: ...'), so splitting the chip text on
' × ' breaks the part boundary: two parts read as three pieces
('Information Technology', 'Volatility', 'Tenure: 0-99 yrs'). This
is the same latent ambiguity the 396th review closed in the
combined-filter badge (check_badge_part_spans.py); the chip was the
only remaining site where parts were joined into a single text node
(the other combined chips' dim labels carry no internal ' × ').
No live consumer splits chip text today, but any future chip-text
parser, screen-reader splitting or per-part interaction would read
the wrong boundary.

The fix: the sector part and the dim part each render in their own
<span class="combined-filter-part"> and the joiner is its own
<span class="combined-filter-sep"> carrying ' × '. The visible text
is unchanged (chip textContent byte-identical: the separator spans
carry the same ' × '), the dim part keeps its internal ' × '
(structural fix only, no relabel -- the 387th review deliberately
made chip/badge/announce wording match), and the close-button × span
is appended after the part spans, untouched.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the vol-tenure updater maps the sector and dim
      parts to .combined-filter-part spans.
  C2  HARD FAIL: the separator is a .combined-filter-sep span
      carrying ' × ' in the same function.
  C3  HARD FAIL: the old single-text-node assignment
      (chip.textContent = chipLabel) still appears inside
      updateVolTenureFilterIndicator. Scoped to the function:
      the volatility chip and other updaters still use that
      assignment legitimately (their dim labels carry no
      internal ' × ').
  C4  HARD FAIL: exactly one vol-tenure chip construction site
      in app.js (chip.id = 'vol-tenure-chip' appears once).
  C5  HARD FAIL: the dim wording is unchanged
      ('Volatility × Tenure: ' + (vtb.label || '')) -- structural
      fix only.
  C6  HARD FAIL: the close-button × span is still appended in
      the function (xSpan appendChild after the part spans).
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Information Technology sector + vol-tenure 0-99 yrs: the
      chip has exactly 2 .combined-filter-part nodes with texts
      'Information Technology' and 'Volatility × Tenure: 0-99 yrs',
      exactly 1 .combined-filter-sep node with text ' × ', the chip
      textContent still contains the old joined string (visually
      identical), and the close × is still the chip's last child.
      Pre-fix there are 0 part nodes, so the check fails on the
      pre-fix tree.
  R2  zero page errors across the render half.

Usage:
  scripts/check_voltenure_chip_part_spans.py
  scripts/check_voltenure_chip_part_spans.py --static-only

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

DIM_LINE = "'Volatility \u00d7 Tenure: ' + (vtb.label || '')"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def voltenure_fn(app):
    """Extract the updateVolTenureFilterIndicator body, or ''."""
    m = re.search(r"function updateVolTenureFilterIndicator\(\) \{",
                  app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\nwindow._updateVolTenureFilterIndicator =",
                   start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = voltenure_fn(app)
    if not fn:
        check("C1 vol-tenure updater maps parts to .combined-filter-part spans",
              False, "updateVolTenureFilterIndicator not found")
        check("C2 separator is a .combined-filter-sep span carrying the joiner",
              False, "updateVolTenureFilterIndicator not found")
        check("C3 no single-text-node chipLabel assignment in the vol-tenure updater",
              False, "updateVolTenureFilterIndicator not found")
        check("C4 exactly one vol-tenure chip construction site",
              False, "updateVolTenureFilterIndicator not found")
        check("C5 dim wording unchanged ('Volatility x Tenure: ' + vtb.label)",
              False, "updateVolTenureFilterIndicator not found")
        check("C6 close-button x span still appended in the updater",
              False, "updateVolTenureFilterIndicator not found")
        return 0

    # C1: both parts render as .combined-filter-part spans -- the
    # sector span (only when combined) and the dim span (always).
    ok_c1 = ("sectorSpan.className = 'combined-filter-part'" in fn
             and "dimSpan.className = 'combined-filter-part'" in fn
             and "sectorSpan.textContent = activeSector" in fn
             and "dimSpan.textContent = dimLabel" in fn)
    check("C1 vol-tenure chip maps sector + dim parts to .combined-filter-part spans",
          ok_c1,
          "part spans missing from the vol-tenure updater" if not ok_c1 else "")

    # C2: the separator is its own .combined-filter-sep span.
    ok_c2 = ("sepSpan.className = 'combined-filter-sep'" in fn
             and "sepSpan.textContent = ' \u00d7 '" in fn)
    check("C2 vol-tenure chip separator is a .combined-filter-sep span carrying the joiner",
          ok_c2,
          "separator span missing from the vol-tenure updater" if not ok_c2 else "")

    # C3: the old single-text-node assignment is gone from this
    # function (other updaters keep theirs; scope is the fn body).
    check("C3 no single-text-node chipLabel assignment in the vol-tenure updater",
          "chip.textContent = chipLabel" not in fn,
          "old chip.textContent = chipLabel still in the vol-tenure updater"
          if "chip.textContent = chipLabel" in fn else "")

    # C4: exactly one vol-tenure chip construction site.
    n_chip = app.count("chip.id = 'vol-tenure-chip'")
    check("C4 exactly one vol-tenure chip construction site",
          n_chip == 1,
          "%d vol-tenure chip sites" % n_chip if n_chip != 1 else "")

    # C5: dim wording unchanged -- structural fix only, no relabel.
    check("C5 vol-tenure chip dim keeps its 'Volatility x Tenure: ' wording",
          DIM_LINE in fn,
          "dim label changed or missing" if DIM_LINE not in fn else "")

    # C6: close-button x span still appended (after the dim part
    # when the part spans exist; pre-fix there is no dimSpan, so
    # the ordering half is vacuous there and the check pins only
    # that the close button survives).
    has_x = ("xSpan.textContent = '\\u00d7'" in fn
             and "chip.appendChild(xSpan)" in fn)
    has_dim = "chip.appendChild(dimSpan)" in fn
    ok_c6 = has_x and (not has_dim
                       or fn.index("chip.appendChild(dimSpan)")
                       < fn.index("chip.appendChild(xSpan)"))
    check("C6 close-button x span still appended after the part spans",
          ok_c6,
          "close-button span missing or reordered" if not ok_c6 else "")

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

            def chip_parts():
                return pg.evaluate("""() => {
                    const c = document.getElementById('vol-tenure-chip');
                    if (!c) return null;
                    const last = c.lastElementChild;
                    return {
                        parts: [...c.querySelectorAll('.combined-filter-part')]
                            .map(el => el.textContent),
                        seps: [...c.querySelectorAll('.combined-filter-sep')]
                            .map(el => el.textContent),
                        text: c.textContent,
                        lastChildText: last ? last.textContent : null
                    };
                }""")

            # R1: sector IT + vol-tenure 0-99 yrs. AAPL passes both
            # (Cook tenure 15), so the footer is >= 1 and the chip
            # shows exactly the two parts. Pre-fix there are 0 part
            # nodes and 0 separator nodes.
            pg.evaluate("""() => {
                window._activeVolTenureBracket = { min: 0, max: Infinity, label: '0-99 yrs' };
            }""")
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("() => window._updateVolTenureFilterIndicator()")
            pg.wait_for_timeout(1200)
            n1 = footer_count()
            c1 = chip_parts()
            r1_ok = (n1 >= 1 and c1 is not None
                     and c1["parts"] == ["Information Technology",
                                         "Volatility \u00d7 Tenure: 0-99 yrs"]
                     and c1["seps"] == [" \u00d7 "]
                     and "Information Technology \u00d7 Volatility "
                         "\u00d7 Tenure: 0-99 yrs" in c1["text"]
                     and c1["lastChildText"] == "\u00d7")
            check("R1 chip exposes exactly 2 part spans + 1 separator span, text unchanged, close x intact",
                  r1_ok,
                  "footer=%s chip=%r (want >=1 row, parts [IT, Volatility × Tenure: 0-99 yrs], one ' × ' sep, joined text intact, last child '×')"
                  % (n1, c1))

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
