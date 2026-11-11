#!/usr/bin/env python3
"""Guard: the concentration filter label is one shared form.

Background (420th review, 2026-11-11): the concentration tier carries
tag + label, and the two origins disagree on whether they differ.
Chart-origin tiers name the tier and range it (tag 'Concentrated',
label '50-60%'), while AF-origin tiers store the same display string
in both fields (advanced-filters.js handleConc: tag and label are both
tagMap[val], e.g. '50-60%'). The chip (updateConcFilterIndicator) and
the combined-filter badge part (renderSummaryBar) both rendered the
inline form tag + ' (' + label + ')', so every AF-panel concentration
pick read doubled on both surfaces: '50-60% (50-60%)', 'High 60%+
(High 60%+)', 'Low <30% (Low <30%)'. And the table-summary
announcement used the bare tag, so a chart-origin tier announced
'concentration: Concentrated' with no range while the chip and badge
read 'Concentrated (50-60%)' -- the 415th-review ratio class (the
announcement named the dim but dropped the value). The 398th guard's
docstring even claimed the announce carried the range; that was the
transient set-time announce ('Filtered to ...'), not the persistent
table summary.

The fix: one shared helper concFilterLabel(ct) -- tag alone when tag
== label, tag + ' (' + label + ')' otherwise -- used by the chip, the
combined-filter badge part, and the table-summary announcement, the
same shared-helper shape the 408th review established for position
(positionFilterLabel) and board (boardFilterLabel). AF-origin chips
and badges now read '50-60%'; chart-origin keeps 'Concentrated
(50-60%)' everywhere including the announcement; old hash links
carrying tag == label render collapsed too, since the collapse is in
the renderers, not the stored state.

Checks (static - file reads, <1s):
  C1  HARD FAIL: concFilterLabel exists in js/app.js and collapses
      tag == label to the tag alone.
  C2  HARD FAIL: the conc chip uses the helper
      (dimLabel = concFilterLabel(ct)).
  C3  HARD FAIL: the combined-filter badge part uses the helper.
  C4  HARD FAIL: the table-summary announcement uses the helper.
  C5  HARD FAIL: no remaining inline conc render of
      tag + ' (' + label + ')' (chip updater or badge part).
  C6  HARD FAIL: the helper still returns the range form when tag
      and label differ.
  C7  HARD FAIL: handleConc() in js/advanced-filters.js raises the
      chip at set time, not just on clear -- the indicator call must
      appear in the set branch too (after the _activeConcTier
      assignment), the call every sibling handler makes (tenure
      334th, gov, board, vol, sop). Without it the table filtered
      and the badge named the tier, but no dismiss chip appeared
      until an unrelated sector change refreshed the indicators.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  AF-origin (real #af-conc change to '50-60'): the chip appears
      at set time and reads '50-60%' with no doubled parenthetical,
      the combined badge part reads the same, and the announcement
      names 'concentration: 50-60%'. Pre-fix the chip and badge read
      '50-60% (50-60%)' -- and the chip did not appear at all until
      an unrelated refresh.
  R2  Chart-origin filterByConcTier(50, 101, 'Concentrated', '>=50%'):
      chip and badge read 'Concentrated (>=50%)' and the announcement
      carries the range ('concentration: Concentrated (>=50%)').
      Pre-fix the announcement read 'concentration: Concentrated'.
  R3  zero page errors across the render half.

Usage:
  scripts/check_conc_filter_label.py
  scripts/check_conc_filter_label.py --static-only

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
AF_JS = os.path.join(REPO, "js", "advanced-filters.js")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def conc_fn(app):
    """Extract the updateConcFilterIndicator body, or ''."""
    m = re.search(r"function updateConcFilterIndicator\(\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\n    window._updateConcFilterIndicator =", start)
    return app[start:end if end != -1 else len(app)]


def helper_fn(app):
    """Extract the concFilterLabel body, or ''."""
    m = re.search(r"function concFilterLabel\(ct\) \{", app)
    if not m:
        return ""
    start = m.start()
    end = app.find("\n}\n", start)
    return app[start:end if end != -1 else len(app)]


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2
    try:
        af = open(AF_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/advanced-filters.js: %s" % exc)
        return 2

    names = (
        "C1 concFilterLabel helper exists and collapses tag == label",
        "C2 conc chip uses the shared helper",
        "C3 combined-filter badge part uses the shared helper",
        "C4 table-summary announcement uses the shared helper",
        "C5 no remaining inline conc tag + ' (label)' render",
        "C6 helper still returns the range form when tag != label",
        "C7 handleConc raises the conc chip at set time",
    )
    fn = conc_fn(app)
    helper = helper_fn(app)
    if not fn:
        for name in names:
            check(name, False, "updateConcFilterIndicator not found")
        return 0

    # C1: the helper exists and collapses the equal-fields case.
    ok_c1 = bool(helper) and ("ct.tag === ct.label" in helper
                              or "ct.label === ct.tag" in helper)
    check(names[0], ok_c1,
          "helper missing or no tag == label collapse" if not ok_c1 else "")

    # C2: the chip dim label is the helper, not the inline form.
    ok_c2 = "dimLabel = concFilterLabel(ct)" in fn
    check(names[1], ok_c2,
          "chip dimLabel is not concFilterLabel(ct)" if not ok_c2 else "")

    # C3: the badge part is the helper.
    ok_c3 = "filterParts.push(concFilterLabel(window._activeConcTier))" in app
    check(names[2], ok_c3,
          "badge part is not concFilterLabel(_activeConcTier)" if not ok_c3 else "")

    # C4: the table-summary announcement is the helper.
    ok_c4 = "announceMsg += ', concentration: ' + concFilterLabel(window._activeConcTier)" in app
    check(names[3], ok_c4,
          "announcement still uses the bare tag" if not ok_c4 else "")

    # C5: no inline conc render survives -- neither the chip updater's
    # old dimLabel nor the badge part's old inline form. (Pctile and
    # stockpct still use their own inline tag + ' (label)' forms; their
    # setters always produce distinct tag/label, so they are out of
    # scope here and must not trip this check.)
    old_chip = "dimLabel = ct.tag + ' (' + ct.label + ')'" in fn
    old_badge = "window._activeConcTier.tag + ' (' + window._activeConcTier.label + ')'" in app
    check(names[4], not old_chip and not old_badge,
          ("chip still renders inline" if old_chip else "")
          + ("; badge still renders inline" if old_badge else ""))

    # C6: when the fields differ the helper returns tag + ' (label)'.
    ok_c6 = bool(helper) and "ct.tag + ' (' + ct.label + ')'" in helper
    check(names[5], ok_c6,
          "helper lost the range form for distinct tag/label" if not ok_c6 else "")

    # C7: handleConc calls the indicator in its set branch too -- the
    # call must appear after the _activeConcTier assignment (the set
    # branch), not only in the '' clear branch above it. Count the
    # guarded calls in the whole function: clear + set = 2.
    m_hc = re.search(r"function handleConc\(val\) \{", af)
    hc_body = ""
    if m_hc:
        hend = af.find("\n    function handleVol(val)", m_hc.start())
        hc_body = af[m_hc.start():hend if hend != -1 else len(af)]
    set_idx = hc_body.find("window._activeConcTier = { min: min")
    n_calls = hc_body.count("window._updateConcFilterIndicator")
    ok_c7 = bool(hc_body) and set_idx != -1 and n_calls >= 2 and \
        hc_body.find("window._updateConcFilterIndicator", set_idx) != -1
    check(names[6], ok_c7,
          "handleConc set branch never refreshes the chip" if not ok_c7 else "")

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

            def state():
                return pg.evaluate("""() => {
                    const chip = document.getElementById('conc-filter-chip');
                    const badge = document.querySelector('.combined-filter-badge');
                    return {
                        chip: chip ? chip.textContent : null,
                        badge: badge ? badge.textContent : null,
                        announce: window._lastTableAnnounce || null,
                        tier: window._activeConcTier ? window._activeConcTier.tag + '|' + window._activeConcTier.label : null
                    };
                }""")

            # R1: AF-origin -- the real panel select, with a sector
            # active so the chip is born combined and the badge shows.
            pg.evaluate("() => window.filterBySector('Information Technology')")
            pg.evaluate("""() => {
                const el = document.getElementById('af-conc');
                el.value = '50-60';
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""")
            pg.wait_for_timeout(1200)
            s1 = state()
            r1_ok = (s1["chip"] is not None
                     and "50\u201360%" in s1["chip"]
                     and "50\u201360% (50\u201360%)" not in s1["chip"]
                     and s1["badge"] is not None
                     and "50\u201360% (50\u201360%)" not in s1["badge"]
                     and s1["announce"] is not None
                     and "concentration: 50\u201360%" in s1["announce"])
            check("R1 AF-origin conc reads '50-60%' once on chip, badge and announcement",
                  r1_ok, "state=%r" % (s1,))

            # R2: chart-origin -- distinct tag/label keeps the range
            # form everywhere, including the announcement.
            pg.evaluate("() => window.filterByConcTier(50, 101, 'Concentrated', '\u226550%')")
            pg.evaluate("() => window._updateConcFilterIndicator()")
            pg.wait_for_timeout(1200)
            s2 = state()
            r2_ok = (s2["chip"] is not None
                     and "Concentrated (\u226550%)" in s2["chip"]
                     and s2["badge"] is not None
                     and "Concentrated (\u226550%)" in s2["badge"]
                     and s2["announce"] is not None
                     and "concentration: Concentrated (\u226550%)" in s2["announce"])
            check("R2 chart-origin conc keeps 'Concentrated (>=50%)' on chip, badge and announcement",
                  r2_ok, "state=%r" % (s2,))

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
