#!/usr/bin/env python3
"""Guard: insight-card actions are assigned by label, not by index.

Background (390th review, 2026-11-08): the 389th review queued an
index-fragility bug -- populateInsights assigned card actions by
numeric index (insights[11], insights[12], insights[13]), but the
pushes above are conditional, so the runtime order shifts whenever a
card is absent. Render-proved at runtime (39 cards):

  index  8 = Top 1% vs Bottom 50%   (intended 'Percentile Concentration',
                                     absent at runtime) -- got a stray
                                     'Sort by percentile' action.
  index  9 = CEO Concentration      (intended) -- correct by luck.
  index 10 = CEO Turnover          (intended) -- correct by luck.
  index 11 = CEO Tenure            (intended 'C-Suite Pay Gap') -- got
                                     'View role analysis'.
  index 12 = Tenure vs Pay         (intended 'Team Completeness') -- got
                                     'Filter missing roles', clobbering
                                     its own inline 'View scatter plot'.
  index 13 = Sector Tenure         (intended 'Pay Inequality', card #14
                                     per fc1120f) -- got 'View
                                     distribution', clobbering its own
                                     inline filter-to-longest-sector
                                     action: clicking it sorted by comp
                                     and scrolled to the comp-dist chart
                                     while the table stayed at all 518
                                     companies with the 'All' chip active.
  C-Suite Pay Gap, Team Completeness, Pay Inequality and Data Quality
  (indices 17-20) had no action at all -- four dead cards.

The fix: findInsight(label) / setInsightAction(label, action, hint)
inside populateInsights; every index assignment is now a label
lookup. A label with no card at runtime (Percentile Concentration)
simply gets no action, and a missing or reordered card can never
steal another card's action. Data Quality never had an assignment
and stays action-less by design.

Checks:
  C1  HARD FAIL: findInsight / setInsightAction helpers missing.
  C2  HARD FAIL: any numeric insights[N].action(.actionHint)
      assignment remains (comment prose excluded).
  C3-C16 HARD FAIL: each intended label has its action assigned by
      label with the right hint (Sector Spread / vs S&P 500 and
      Zero Pay / Below $1M via findInsight with fallback).
  C17 HARD FAIL: Tenure vs Pay's inline 'View scatter plot' action
      is gone (clobbered) or a label assignment targets it.
  C18 HARD FAIL: Sector Tenure's inline 'Filter to <sector>' action
      is gone (clobbered) or a label assignment targets it.
  C19 HARD FAIL: 'Highest Paid' -- the no-$50M+ alternative for the
      $50M+ Club slot (same index under the old code) -- does not
      share the top-CEO action. It is unreachable at runtime (there
      ARE $50M+ CEOs) but the label fix must not silently drop the
      action the old index assignment gave it in that world.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1 Sector Tenure click filters to the longest-tenure sector (active
     sector chip is a real sector, footer < 518, hash has sector=).
     Pre-fix: 'All' stayed active, footer stayed 518, no hash.
  R2 Tenure vs Pay click keeps its inline action: the scatter axes
     become tenure vs total comp. Pre-fix: it filtered to missing
     roles instead.
  R3 C-Suite Pay Gap is clickable and scrolls to the role-comp chart.
     Pre-fix: not clickable at all.
  R4 Team Completeness is clickable and filters to missing-roles
     companies (footer < 518). Pre-fix: not clickable at all.
  R5 Pay Inequality is clickable and scrolls to the comp-dist panel.
     Pre-fix: not clickable at all.
  R6 Data Quality stays non-clickable (it never had an action).
  R7 Top 1% vs Bottom 50% is non-clickable (its accidental
     'Sort by percentile' action is gone).
  R8 zero page errors across the render half.

Usage:
  scripts/check_insight_action_labels.py
  scripts/check_insight_action_labels.py --static-only

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

# (label, hint) assigned through setInsightAction.
LABEL_ACTIONS = [
    ("Pay Concentration", "View top earners"),
    ("$50M+ Club", "Explore top CEO"),
    ("Extreme Ratios", "Filter extreme ratios"),
    ("Pay Range", "View full range"),
    ("Biggest Pay Swing", "Sort by YoY change"),
    ("Equity-Heavy Pay", "Sort by equity %"),
    ("Percentile Concentration", "Sort by percentile"),
    ("CEO Concentration", "View top CEOs"),
    ("CEO Turnover", "Filter to CEO transitions"),
    ("C-Suite Pay Gap", "View role analysis"),
    ("Team Completeness", "Filter missing roles"),
    ("Pay Inequality", "View distribution"),
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL") + ": " + name + ((" - " + detail) if detail else ""))


def fn_body(app, marker):
    """Brace-matched body starting at the first '{' after marker."""
    i = app.find(marker)
    if i < 0:
        return None
    j = app.find("{", i)
    if j < 0:
        return None
    depth = 0
    k = j
    while k < len(app):
        if app[k] == "{":
            depth += 1
        elif app[k] == "}":
            depth -= 1
            if depth == 0:
                return app[j:k + 1]
        k += 1
    return None


def static_checks():
    try:
        app = open(APP_JS, encoding="utf-8").read()
    except OSError as exc:
        print("INFRA: cannot read js/app.js: %s" % exc)
        return 2

    pop = fn_body(app, "function populateInsights(comp, trends, sectorFilter) {")
    if pop is None:
        check("C1 helpers exist inside populateInsights", False,
              "populateInsights not found")
        return 0

    check("C1 findInsight / setInsightAction helpers exist in populateInsights",
          "function findInsight(label) {" in pop
          and "function setInsightAction(label, action, hint) {" in pop
          and "insights[i].label === label" in pop
          and "card.action = action;" in pop,
          "helper missing or wrong shape")

    # C2: no numeric index assignment remains. Comment prose (the 390th
    # review note names the old indices) is excluded by stripping //
    # comments before matching.
    code = re.sub(r"//[^\n]*", "", pop)
    numeric = re.findall(r"insights\[\d+\]\s*\.\s*action", code)
    check("C2 no numeric insights[N].action assignment remains",
          len(numeric) == 0,
          "found: %s" % (numeric[:3],) if numeric else "")

    for label, hint in LABEL_ACTIONS:
        call = "setInsightAction('%s'," % label
        ok = call in pop and ("'%s'" % hint) in pop
        check("C%d '%s' assigned by label with hint '%s'" % (
            3 + LABEL_ACTIONS.index((label, hint)), label, hint),
            ok, "" if ok else "setInsightAction call or hint missing")

    # C15/C16: the two conditional cards resolve by label with fallback.
    check("C15 Sector Spread resolved by label (vs S&P 500 fallback)",
          "findInsight('Sector Spread') || findInsight('vs S&P 500')" in pop,
          "label lookup with fallback missing")
    check("C16 Zero Pay resolved by label (Below $1M fallback)",
          "findInsight('Zero Pay') || findInsight('Below $1M')" in pop,
          "label lookup with fallback missing")

    # C17/C18: the two inline actions the index drift clobbered must
    # survive in their own push blocks, and no label assignment may
    # target those cards. (fn_body cannot scope these: the push object
    # opens before the label, so slice a window after the label.)
    li = app.find("label: 'Tenure vs Pay',")
    tvp = app[li:li + 4000] if li >= 0 else ""
    check("C17 Tenure vs Pay keeps its inline 'View scatter plot' action",
          li >= 0 and "actionHint: 'View scatter plot'" in tvp
          and "setInsightAction('Tenure vs Pay'" not in pop,
          "inline action missing or clobbered by a label assignment")
    li = app.find("label: 'Sector Tenure',")
    st = app[li:li + 4000] if li >= 0 else ""
    check("C18 Sector Tenure keeps its inline filter-to-sector action",
          li >= 0 and "actionHint: 'Filter to ' + longestSec.name" in st
          and "setInsightAction('Sector Tenure'" not in pop,
          "inline action missing or clobbered by a label assignment")

    # C19: 'Highest Paid' is the else-branch alternative to '$50M+ Club'
    # for the same slot -- under the old index code it sat at index 1
    # and got the top-CEO action. The label fix must carry it over.
    check("C19 'Highest Paid' shares the $50M+ Club top-CEO action",
          "setInsightAction('Highest Paid'," in pop
          and "setInsightAction('Highest Paid', exploreTopCeo, 'Explore top CEO')" in pop,
          "'Highest Paid' has no top-CEO action (dropped in the label conversion)")

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

            def load():
                pg.goto("http://127.0.0.1:%d/index.html" % port, timeout=60000)
                pg.wait_for_selector(
                    "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
                pg.wait_for_timeout(800)

            def footer_count():
                txt = pg.locator("#table-footer").inner_text()
                m = re.search(r"of (\d+) companies", txt)
                return int(m.group(1)) if m else -1

            def card_info(label):
                return pg.evaluate("""(label) => {
                    const el = [...document.querySelectorAll('.insight-card')]
                        .find(c => (c.querySelector('.insight-label') || {}).textContent.trim() === label);
                    if (!el) return null;
                    return { clickable: el.classList.contains('insight-clickable') };
                }""", label)

            def click_card(label):
                pg.locator(".insight-card.insight-clickable",
                           has_text=label).first.click()
                pg.wait_for_timeout(1500)

            def panel_in_view(panel_id):
                return pg.evaluate("""(id) => {
                    const el = document.getElementById(id);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return { top: Math.round(r.top), inView: r.top >= -50 && r.top < 800 };
                }""", panel_id)

            # R1: Sector Tenure filters to the longest-tenure sector.
            load()
            st = card_info("Sector Tenure")
            click_card("Sector Tenure")
            sector = pg.evaluate("""() => {
                const c = [...document.querySelectorAll('#sector-chips .chip')]
                    .find(el => el.classList.contains('active'));
                return c ? c.textContent.trim() : null;
            }""")
            n1 = footer_count()
            h1 = pg.evaluate("() => location.hash")
            r1_ok = (st is not None and st["clickable"]
                     and sector is not None and sector != "All"
                     and 0 < n1 < 518 and "sector=" in h1)
            check("R1 Sector Tenure click filters to a sector (chip=%s footer=%s hash=%s)" % (sector, n1, h1),
                  r1_ok,
                  "want a real sector chip active, footer 1-517, sector= in hash")

            # R2: Tenure vs Pay keeps its inline scatter action.
            load()
            click_card("Tenure vs Pay")
            axes = pg.evaluate("""() => {
                const x = document.getElementById('scatter-x-metric');
                const y = document.getElementById('scatter-y-metric');
                return { x: x ? x.value : null, y: y ? y.value : null };
            }""")
            r2_ok = axes["x"] == "_ceoTenureYears" and axes["y"] == "total_compensation"
            check("R2 Tenure vs Pay click sets scatter axes to tenure vs comp",
                  r2_ok, "axes=%r (want tenure/total_compensation)" % (axes,))

            # R3: C-Suite Pay Gap is clickable and scrolls to the role chart.
            load()
            gap = card_info("C-Suite Pay Gap")
            click_card("C-Suite Pay Gap")
            role = panel_in_view("role-comp-chart")
            r3_ok = (gap is not None and gap["clickable"]
                     and role is not None and role["inView"])
            check("R3 C-Suite Pay Gap clickable, scrolls to role-comp chart",
                  r3_ok, "clickable=%r panel=%r" % (gap, role))

            # R4: Team Completeness is clickable and filters to missing roles.
            load()
            team = card_info("Team Completeness")
            click_card("Team Completeness")
            n4 = footer_count()
            r4_ok = (team is not None and team["clickable"] and 0 < n4 < 518)
            check("R4 Team Completeness clickable, filters to missing roles (footer=%s)" % n4,
                  r4_ok, "clickable=%r footer=%s (want < 518)" % (team, n4))

            # R5: Pay Inequality is clickable and scrolls to the comp-dist panel.
            load()
            ineq = card_info("Pay Inequality")
            click_card("Pay Inequality")
            dist = panel_in_view("comp-dist-panel")
            r5_ok = (ineq is not None and ineq["clickable"]
                     and dist is not None and dist["inView"])
            check("R5 Pay Inequality clickable, scrolls to comp-dist panel",
                  r5_ok, "clickable=%r panel=%r" % (ineq, dist))

            # R6/R7: cards that never had an action stay non-clickable,
            # and the accidental percentile action is gone.
            load()
            dq = card_info("Data Quality")
            top1 = card_info("Top 1% vs Bottom 50%")
            r6_ok = dq is not None and not dq["clickable"]
            check("R6 Data Quality stays non-clickable (never had an action)",
                  r6_ok, "card=%r" % (dq,))
            r7_ok = top1 is not None and not top1["clickable"]
            check("R7 Top 1% vs Bottom 50% lost its accidental percentile action",
                  r7_ok, "card=%r" % (top1,))

            r8_ok = len(errors) == 0
            check("R8 zero page errors across the render half",
                  r8_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return all([r1_ok, r2_ok, r3_ok, r4_ok, r5_ok, r6_ok, r7_ok, r8_ok])
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
