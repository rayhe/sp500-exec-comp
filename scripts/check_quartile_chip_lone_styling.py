#!/usr/bin/env python3
"""Guard: the quartile chip's lone state is cyan, not combined purple.

Background (406th review, 2026-11-10): the quartile chip
(updateQuartileFilterIndicator, js/network.js) was the only filter
indicator whose lone/combined states differed by label alone. The
394th review had fixed its label (sector prefix when a sector is
active) but left the styling unconditional: background
rgba(167,139,250,0.15), border rgba(167,139,250,0.5), color #a78bfa
-- the combined purple -- in both states. Every app.js updater
conditions bg/border/color on isCombined and reserves purple for the
combined state (peer-dist, volatility, vol-tenure, dist, YoY all use
the network cyan #00b4d8 lone), so a lone quartile chip falsely
signalled a combined sector + quartile filter. The 394th comment
even recorded the fact ("The lone styling is already the combined
purple, so only the label gains the sector prefix") as if it were
acceptable; the 406th review treats it as the same state-fidelity
class the 393rd-405th reviews closed for labels, now in the styling
dimension.

The fix: the three style lines are ternaries on isCombined --
combined keeps the purple, lone uses the network cyan (#00b4d8)
the peer-dist / volatility / dist siblings use. The 394th comment
is updated to record the change (its old claim is now false).

Checks (static - file reads, <1s):
  C1  HARD FAIL: the combined styling is still the purple
      (background ternary keeps rgba(167,139,250,0.15) on the
      isCombined branch).
  C2  HARD FAIL: the lone styling is the network cyan (the else
      branches are rgba(0,180,216,0.15) / rgba(0,180,216,0.5) /
      '#00b4d8').
  C3  HARD FAIL: the old unconditional purple lines are gone (no
      bare `chip.style.background = 'rgba(167,139,250,0.15)';`
      assignment without the ternary).
  C4  HARD FAIL: exactly one quartile chip construction site in
      network.js (chip.id = 'quartile-filter-chip' appears once).
  C5  HARD FAIL: the updater still reads window._activeSector for
      isCombined (the sector source the 394th review established).
  C6  HARD FAIL: the close-button x span is still appended in the
      updater.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Lone quartile filter (no sector): the chip's computed
      background is rgba(0, 180, 216, 0.15) and its color is
      rgb(0, 180, 216). Pre-fix both are the purple
      rgba(167, 139, 250, 0.15) / rgb(167, 139, 250), so the check
      fails on the pre-fix tree.
  R2  Sector Information Technology + the same quartile filter:
      the chip re-renders (filterBySector re-runs the updater) with
      computed background rgba(167, 139, 250, 0.15), color
      rgb(167, 139, 250), and label 'Information Technology x ...'.
  R3  zero page errors across the render half.

Usage:
  scripts/check_quartile_chip_lone_styling.py
  scripts/check_quartile_chip_lone_styling.py --static-only

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
NET_JS = os.path.join(REPO, "js", "network.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def quartile_fn(net):
    """Extract the updateQuartileFilterIndicator body, or ''."""
    m = re.search(r"function updateQuartileFilterIndicator\(\) \{", net)
    if not m:
        return ""
    start = m.start()
    end = net.find("\n    window._updateQuartileFilterIndicator =", start)
    return net[start:end if end != -1 else len(net)]


def static_checks():
    try:
        net = open(NET_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/network.js: %s" % exc)
        return 2

    fn = quartile_fn(net)
    if not fn:
        for name in (
            "C1 quartile chip combined styling stays purple",
            "C2 quartile chip lone styling is network cyan",
            "C3 old unconditional purple lines are gone",
            "C4 exactly one quartile chip construction site",
            "C5 updater still reads window._activeSector for isCombined",
            "C6 close-button x span still present in the updater",
        ):
            check(name, False, "updateQuartileFilterIndicator not found")
        return 0

    # C1: combined branch keeps the purple. NOTE (406th review): this
    # updater spells the separator as the literal x char (U+00D7) in
    # the file, like the peer-dist updater, not the \\u00d7 escape, so
    # the pins below match the literal style strings.
    ok_c1 = ("chip.style.background = isCombined ? 'rgba(167,139,250,0.15)'" in fn
             and "chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)'" in fn
             and "chip.style.color = isCombined ? '#a78bfa'" in fn)
    check("C1 quartile chip combined styling stays purple",
          ok_c1,
          "combined branch lost the purple" if not ok_c1 else "")

    # C2: lone branch is the network cyan.
    ok_c2 = (": 'rgba(0,180,216,0.15)'" in fn
             and ": 'rgba(0,180,216,0.5)'" in fn
             and ": '#00b4d8'" in fn)
    check("C2 quartile chip lone styling is network cyan",
          ok_c2,
          "lone branch is not the cyan" if not ok_c2 else "")

    # C3: the old unconditional purple assignments are gone. The
    # fixed lines contain the same rgba strings but behind the
    # ternary, so match the exact bare-assignment form (equals sign
    # followed directly by the string and a semicolon).
    old_bg = "chip.style.background = 'rgba(167,139,250,0.15)';"
    old_border = "chip.style.borderColor = 'rgba(167,139,250,0.5)';"
    old_color = "chip.style.color = '#a78bfa';"
    old_present = [s for s in (old_bg, old_border, old_color) if s in fn]
    check("C3 old unconditional purple lines are gone",
          not old_present,
          "still present: %s" % old_present if old_present else "")

    # C4: exactly one quartile chip construction site.
    n_chip = net.count("chip.id = 'quartile-filter-chip'")
    check("C4 exactly one quartile chip construction site",
          n_chip == 1,
          "%d quartile chip sites" % n_chip if n_chip != 1 else "")

    # C5: isCombined still reads window._activeSector.
    ok_c5 = "var isCombined = !!window._activeSector;" in fn
    check("C5 updater still reads window._activeSector for isCombined",
          ok_c5,
          "isCombined source changed or missing" if not ok_c5 else "")

    # C6: close-button x span still appended. This updater builds
    # the span via innerHTML with the literal x char.
    ok_c6 = ("<span style=\"margin-left:4px;font-weight:700;\">\u00d7</span>" in fn)
    check("C6 close-button x span still present in the updater",
          ok_c6,
          "close-button span missing" if not ok_c6 else "")

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

            if pg.evaluate("() => typeof window._updateQuartileFilterIndicator") != "function":
                print("INFRA: quartile updater not exposed (network.js failed to load?)")
                browser.close()
                return False

            def chip_state():
                return pg.evaluate("""() => {
                    const c = document.getElementById('quartile-filter-chip');
                    if (!c) return null;
                    const cs = getComputedStyle(c);
                    return {
                        text: c.textContent,
                        bg: cs.backgroundColor,
                        border: cs.borderColor,
                        color: cs.color
                    };
                }""")

            # R1: lone quartile filter, no sector. The updater reads
            # only the stored state, so state + updater is the same
            # code path as the box-plot zone click.
            pg.evaluate("""() => {
                window._activeQuartileFilter = {
                    tickers: ['AAPL', 'MSFT', 'NVDA'],
                    label: 'Test Community Top 25% (3)',
                    communityId: 0, _lo: 8000000, _hi: 12000000
                };
                window._updateQuartileFilterIndicator();
            }""")
            pg.wait_for_timeout(500)
            lone = chip_state()
            r1_ok = (lone is not None
                     and lone["bg"] == "rgba(0, 180, 216, 0.15)"
                     and lone["color"] == "rgb(0, 180, 216)"
                     and "Test Community Top 25% (3)" in lone["text"])
            check("R1 lone quartile chip is cyan (bg rgba(0,180,216,0.15), color rgb(0,180,216))",
                  r1_ok,
                  "chip=%r" % (lone,))

            # R2: sector IT first -- filterBySector re-runs the
            # quartile updater, so the chip is reborn combined.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            comb = chip_state()
            r2_ok = (comb is not None
                     and comb["bg"] == "rgba(167, 139, 250, 0.15)"
                     and comb["color"] == "rgb(167, 139, 250)"
                     and "Information Technology \u00d7 Test Community Top 25% (3)" in comb["text"])
            check("R2 combined quartile chip is purple (bg rgba(167,139,250,0.15), sector prefix in label)",
                  r2_ok,
                  "chip=%r" % (comb,))

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
