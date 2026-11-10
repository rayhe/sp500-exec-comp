#!/usr/bin/env python3
"""Guard: the community filter has a dismiss chip whose label matches the badge.

Background (407th review, 2026-11-10): the community filter was the
only filter dim with no chip at all. The combined badge named it
('Community: ' + label, js/app.js) and the announce named it
('Filtered to N companies in <label>'), but the table controls showed
no dismiss chip, so a reader on the table tab could not clear the
filter without returning to the network tab and re-clicking the
community. The 406th run's sweep listed community as the last
unaudited dim (PvP and dist were verified consistent: the PvP toggle
label and badge part both say 'PvP-covered', and the dist chip,
badge and announce all use df.label verbatim).

The fix: updateCommunityFilterIndicator (js/network.js), mirroring
updateQuartileFilterIndicator in the same file. Lone label is the
badge form ('Community: ' + cf.label); combined gains the sector
prefix (sector + ' x ' + dimLabel); lone is network cyan (#00b4d8),
combined is purple (#a78bfa). The updater is called at all five
community set/clear sites in network.js (legend click set/clear,
community-metrics row set/clear, flow-cell set) and at all six
sector-refresh sites in js/app.js, so a sector change re-renders the
chip combined instead of leaving it lone (the 394th-review defect
class). resetPaths removes the chip (resetAllFilters already listed
'community-filter-chip' before any chip existed). The Escape path
deliberately keeps community (343rd review), so no chip removal is
needed there -- the chip stays truthful while the filter stays active.

Checks (static - file reads, <1s):
  C1  HARD FAIL: the updater builds the dim label as the badge form
      ('Community: ' + cf.label).
  C2  HARD FAIL: the combined label is sector + ' x ' + dimLabel.
      NOTE: this updater spells the separator as the literal x char
      (U+00D7) in the file, like the quartile/peer-dist updaters, not
      the \\u00d7 escape, so the pins match the literal spelling.
  C3  HARD FAIL: lone styling is network cyan and combined styling
      stays purple (the three style ternaries).
  C4  HARD FAIL: exactly one community chip construction site in
      network.js (chip.id = 'community-filter-chip' appears once).
  C5  HARD FAIL: the updater is called at all five community
      set/clear sites in network.js (bare calls, not the definition).
  C6  HARD FAIL: all six sector-refresh sites in js/app.js re-run
      the community updater (guarded window._ calls), so the chip
      never keeps a lone label while combined. Update (409th review,
      2026-11-10): a seventh guarded call exists -- the applyHashState
      restore site, which raises the chip on a community deep link --
      so the count is now seven, six sector-refresh sites + the
      restore site.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Lone community filter (no sector): the chip reads
      'Community: Info Tech' with computed background
      rgba(0, 180, 216, 0.15) and color rgb(0, 180, 216). Pre-fix
      there is no chip at all, so the check fails on the pre-fix tree.
  R2  Sector Information Technology + the same community filter:
      the chip re-renders (filterBySector re-runs the updater) with
      computed background rgba(167, 139, 250, 0.15), color
      rgb(167, 139, 250), and label
      'Information Technology x Community: Info Tech'.
  R3  zero page errors across the render half.

Usage:
  scripts/check_community_chip_combined_label.py
  scripts/check_community_chip_combined_label.py --static-only

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
APP_JS = os.path.join(REPO, "js", "app.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def community_fn(net):
    """Extract the updateCommunityFilterIndicator body, or ''."""
    m = re.search(r"function updateCommunityFilterIndicator\(\) \{", net)
    if not m:
        return ""
    start = m.start()
    end = net.find("\n    window._updateCommunityFilterIndicator =", start)
    return net[start:end if end != -1 else len(net)]


def static_checks():
    try:
        net = open(NET_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/network.js: %s" % exc)
        return 2
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    fn = community_fn(net)
    if not fn:
        for name in (
            "C1 community chip dim label is the badge form ('Community: ' + label)",
            "C2 community chip combined label gains the sector prefix",
            "C3 community chip lone styling is network cyan, combined stays purple",
            "C4 exactly one community chip construction site",
            "C5 updater called at all five community set/clear sites",
            "C6 all six sector-refresh sites re-run the community updater (+ restore site)",
        ):
            check(name, False, "updateCommunityFilterIndicator not found")
        return 0

    # C1: dim label is the badge form ('Community: ' + cf.label).
    ok_c1 = "var dimLabel = 'Community: ' + cf.label;" in fn
    check("C1 community chip dim label is the badge form ('Community: ' + label)",
          ok_c1,
          "dim label is not the badge form" if not ok_c1 else "")

    # C2: combined label is sector + ' x ' + dimLabel. NOTE (407th
    # review): this updater spells the separator as the literal x char
    # (U+00D7) in the file, like the quartile updater, so the pin
    # matches the literal spelling, not the \\u00d7 escape.
    ok_c2 = ("var chipLabel = isCombined ? window._activeSector + ' \u00d7 ' + dimLabel : dimLabel;" in fn)
    check("C2 community chip combined label gains the sector prefix",
          ok_c2,
          "combined label does not prefix the sector" if not ok_c2 else "")

    # C3: lone styling is the network cyan, combined stays purple.
    ok_c3 = ("chip.style.background = isCombined ? 'rgba(167,139,250,0.15)' : 'rgba(0,180,216,0.15)'" in fn
             and "chip.style.borderColor = isCombined ? 'rgba(167,139,250,0.5)' : 'rgba(0,180,216,0.5)'" in fn
             and "chip.style.color = isCombined ? '#a78bfa' : '#00b4d8'" in fn)
    check("C3 community chip lone styling is network cyan, combined stays purple",
          ok_c3,
          "style ternaries are not cyan-lone / purple-combined" if not ok_c3 else "")

    # C4: exactly one community chip construction site.
    n_chip = net.count("chip.id = 'community-filter-chip'")
    check("C4 exactly one community chip construction site",
          n_chip == 1,
          "%d community chip sites" % n_chip if n_chip != 1 else "")

    # C5: the updater is called at all five community set/clear sites
    # in network.js (legend set/clear, metrics-row set/clear,
    # flow-cell set). Bare calls only: the definition line is
    # 'function updateCommunityFilterIndicator() {' and the exposure
    # is a window._ assignment, neither of which matches.
    n_calls = len(re.findall(r"^[ ]+updateCommunityFilterIndicator\(\);$", net, re.M))
    check("C5 updater called at all five community set/clear sites",
          n_calls == 5,
          "%d bare call sites" % n_calls if n_calls != 5 else "")

    # C6: all six sector-refresh sites in app.js re-run the updater
    # (guarded window._ calls), so the chip never keeps a lone label
    # while combined (the 394th-review defect class). Update (409th
    # review, 2026-11-10): the applyHashState restore site adds a
    # seventh guarded call, which raises the chip on a community deep
    # link -- the six sector-refresh sites are unchanged, the count
    # is now seven.
    n_sites = app.count("if (window._updateCommunityFilterIndicator) window._updateCommunityFilterIndicator();")
    check("C6 all six sector-refresh sites re-run the community updater (+ restore site)",
          n_sites == 7,
          "%d sector-refresh call sites" % n_sites if n_sites != 7 else "")

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

            if pg.evaluate("() => typeof window._updateCommunityFilterIndicator") != "function":
                print("INFRA: community updater not exposed (network.js failed to load?)")
                browser.close()
                return False

            def chip_state():
                return pg.evaluate("""() => {
                    const c = document.getElementById('community-filter-chip');
                    if (!c) return null;
                    const cs = getComputedStyle(c);
                    return {
                        text: c.textContent,
                        bg: cs.backgroundColor,
                        border: cs.borderColor,
                        color: cs.color
                    };
                }""")

            # R1: lone community filter, no sector. The updater reads
            # only the stored state, so state + updater is the same
            # code path as the legend click.
            pg.evaluate("""() => {
                window._activeCommunityFilter = {
                    tickers: ['AAPL', 'MSFT', 'NVDA'],
                    label: 'Info Tech',
                    id: 0
                };
                window._updateCommunityFilterIndicator();
            }""")
            pg.wait_for_timeout(500)
            lone = chip_state()
            r1_ok = (lone is not None
                     and lone["bg"] == "rgba(0, 180, 216, 0.15)"
                     and lone["color"] == "rgb(0, 180, 216)"
                     and "Community: Info Tech" in lone["text"])
            check("R1 lone community chip reads 'Community: Info Tech' in cyan (bg rgba(0,180,216,0.15))",
                  r1_ok,
                  "chip=%r" % (lone,))

            # R2: sector IT first -- filterBySector re-runs the
            # community updater, so the chip is reborn combined.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.wait_for_timeout(1200)
            comb = chip_state()
            r2_ok = (comb is not None
                     and comb["bg"] == "rgba(167, 139, 250, 0.15)"
                     and comb["color"] == "rgb(167, 139, 250)"
                     and "Information Technology \u00d7 Community: Info Tech" in comb["text"])
            check("R2 combined community chip is purple (bg rgba(167,139,250,0.15), sector prefix in label)",
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
