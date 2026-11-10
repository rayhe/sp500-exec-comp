#!/usr/bin/env python3
"""Guard: every sort-header indicator loop keeps aria-sort in sync.

Background (392nd review, 2026-11-08): the 391st review's R7 observed
ariaSort 'none' on the _compPercentile header while sortedDesc was
true after the 'Top 1% vs Bottom 50%' card sorted the table. Root
cause: insightResetAndSort's header loop toggled only the
sorted-asc/sorted-desc classes and never set aria-sort, while the
sibling sort paths (sortTableByKey, setupSorting.activateSort and the
chart-bucket sort handlers) set both. A screen reader therefore heard
'none' on a header the eye saw as sorted-desc. The same class-only
shape existed at three more sites: applyHashState's sort restore
(a shared sort= deep link left aria-sort stale), filterByRatioBucket's
pay-ratio sort (clicking a ratio-dist bar), and the hashchange
handler's default reset to total_compensation desc. All four now set
aria-sort 'none' on every header and 'ascending'/'descending' on the
matched one, mirroring the good sites.

Checks (static - one file read, <1s):
  C1  HARD FAIL: class-level scan -- every
      classList.remove('sorted-asc', 'sorted-desc') site in js/app.js
      is followed within 10 lines by a setAttribute('aria-sort', ...)
      (no comment in the file contains the marker, verified 392nd
      review, so the plain line scan cannot false-positive).
  C2  HARD FAIL: insightResetAndSort sets aria-sort none +
      ascending/descending.
  C3  HARD FAIL: applyHashState's sort branch sets aria-sort.
  C4  HARD FAIL: filterByRatioBucket sets aria-sort 'descending' on
      the pay_ratio header.
  C5  HARD FAIL: the hashchange handler's default reset sets
      aria-sort 'descending' on the total_compensation header.
Render (headless Chromium, d3 shim from the goal hidden_files cache):
  R1  Top 1% vs Bottom 50% card click: pctile header sorted-desc
      AND aria-sort 'descending'. Pre-fix: sorted-desc true,
      aria-sort 'none' (the 391st R7 observation).
  R2  Deep link #sort=_ceoTenureYears&dir=asc: tenure header
      aria-sort 'ascending'. Pre-fix: 'none'.
  R3  Ratio-bucket filter (filterByRatioBucket, the ratio-bar
      onclick target) sorts by pay ratio: pay_ratio header
      sorted-desc AND aria-sort 'descending', footer < 518.
      Pre-fix: sorted-desc true, aria-sort 'none'. The bars only
      render while the sort IS pay_ratio, so the check calls the
      handler directly on a fresh load -- a bar click after a
      header click would be vacuous (the good header path already
      set aria-sort).
  R4  Hash change to a hashless URL: total_compensation header
      aria-sort 'descending' (the default reset). Pre-fix: 'none'
      -- the setup clicks the tenure header first, because the
      initial HTML already carries aria-sort 'descending' on
      total_compensation and a bare hashchange passes vacuously
      without it.
  R5  zero page errors across the render half.

Usage:
  scripts/check_sort_aria_sort.py
  scripts/check_sort_aria_sort.py --static-only

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
    lines = app.splitlines()

    # C1: class-level scan -- every sorted-asc/sorted-desc removal site
    # must set aria-sort within the next 10 lines (the forEach callback
    # body). No comment in the file contains the marker (verified 392nd
    # review), so the plain line scan cannot match comment prose.
    bad = []
    for i, l in enumerate(lines):
        if "classList.remove('sorted-asc', 'sorted-desc')" not in l:
            continue
        window = "\n".join(lines[i:i + 11])
        if "setAttribute('aria-sort'" not in window:
            bad.append(i + 1)
    check("C1 every sort-indicator loop sets aria-sort",
          len(bad) == 0,
          "class-only loop(s) at app.js line(s): %s" % (bad,) if bad else "")

    # C2: insightResetAndSort (the 391st R7 observation).
    body = fn_body(app, "function insightResetAndSort(sortKey, sortDir) {")
    check("C2 insightResetAndSort sets aria-sort",
          body is not None
          and "t.setAttribute('aria-sort', 'none');" in body
          and "t.setAttribute('aria-sort', sortDir === 'asc' ? 'ascending' : 'descending');" in body,
          "header loop missing the aria-sort pair" if body else "insightResetAndSort not found")

    # C3: applyHashState sort restore (deep-link sort).
    body = fn_body(app, "function applyHashState(companies) {")
    check("C3 applyHashState sort restore sets aria-sort",
          body is not None
          and "t.setAttribute('aria-sort', 'none');" in body
          and "t.setAttribute('aria-sort', currentSort.dir === 'asc' ? 'ascending' : 'descending');" in body,
          "sort branch missing the aria-sort pair" if body else "applyHashState not found")

    # C4: filterByRatioBucket pay-ratio sort (always desc).
    i = app.find("window.filterByRatioBucket = function(minRatio, maxRatio) {")
    seg = app[i:i + 3000] if i >= 0 else ""
    check("C4 filterByRatioBucket sets aria-sort 'descending' on pay_ratio",
          i >= 0 and "t.setAttribute('aria-sort', 'none');" in seg
          and "t.setAttribute('aria-sort', 'descending');" in seg
          and "t.dataset.sort === 'pay_ratio'" in seg,
          "pay-ratio sort loop missing the aria-sort pair" if i >= 0 else "filterByRatioBucket not found")

    # C5: hashchange handler default reset to total_compensation desc.
    # The handler has no named function; scope to the window after the
    # 'hashchange' listener registration. Update (409th review,
    # 2026-11-10): the window was 8000 chars and the community
    # hash-serialization additions to the reset block (nulls, chip
    # removal, legend/metrics clearing) pushed the aria-sort loop
    # from ~7000 to ~8640 chars past the listener -- the loop itself
    # is untouched, only the window was too small. 12000 still ends
    # inside the handler (the next listener registration is ~20000
    # chars out), so the scope is unchanged.
    i = app.find("window.addEventListener('hashchange'")
    seg = app[i:i + 12000] if i >= 0 else ""
    check("C5 hashchange default reset sets aria-sort 'descending'",
          i >= 0 and "t.setAttribute('aria-sort', 'none');" in seg
          and "t.setAttribute('aria-sort', 'descending');" in seg
          and "t.dataset.sort === 'total_compensation'" in seg,
          "default-reset loop missing the aria-sort pair" if i >= 0 else "hashchange listener not found")

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

            def load(url=None):
                pg.goto(url or "http://127.0.0.1:%d/index.html" % port, timeout=60000)
                pg.wait_for_selector(
                    "#comp-tbody > tr:not(.skeleton-table-row-tr)", timeout=30000)
                pg.wait_for_timeout(800)

            def header_state(sort_key):
                return pg.evaluate("""(key) => {
                    const th = document.querySelector('th.sortable[data-sort="' + key + '"]');
                    return th ? { sortedAsc: th.classList.contains('sorted-asc'),
                                  sortedDesc: th.classList.contains('sorted-desc'),
                                  ariaSort: th.getAttribute('aria-sort') } : null;
                }""", sort_key)

            # R1: insight-card sort sets aria-sort (the 391st R7 defect).
            load()
            pg.locator(".insight-card.insight-clickable",
                       has_text="Top 1% vs Bottom 50%").first.click()
            pg.wait_for_timeout(1500)
            h1 = header_state("_compPercentile")
            r1_ok = (h1 is not None and h1["sortedDesc"]
                     and h1["ariaSort"] == "descending")
            check("R1 Top 1%% card click: pctile header aria-sort 'descending' (hdr=%r)" % (h1,),
                  r1_ok, "want sortedDesc + aria-sort descending")

            # R2: deep-link sort restore sets aria-sort.
            load("http://127.0.0.1:%d/index.html#sort=_ceoTenureYears&dir=asc" % port)
            h2 = header_state("_ceoTenureYears")
            r2_ok = (h2 is not None and h2["sortedAsc"]
                     and h2["ariaSort"] == "ascending")
            check("R2 deep-link sort: tenure header aria-sort 'ascending' (hdr=%r)" % (h2,),
                  r2_ok, "want sortedAsc + aria-sort ascending")

            # R3: ratio-bucket filter sorts by pay ratio. The bars
            # only render while the sort IS pay_ratio (renderRatioSortSummary
            # is the sort-summary branch), so a bar click after a
            # header click would be vacuous -- the good header path
            # already set aria-sort. Call the bar's own handler
            # (filterByRatioBucket, the onclick target) directly on a
            # fresh load, where pay_ratio aria-sort is 'none'.
            load()
            pg.evaluate("() => filterByRatioBucket(0, 50)")
            pg.wait_for_timeout(1500)
            h3 = header_state("pay_ratio")
            n3 = pg.evaluate("""() => {
                const m = document.getElementById('table-footer').innerText.match(/of (\\d+) companies/);
                return m ? parseInt(m[1], 10) : -1;
            }""")
            r3_ok = (h3 is not None and h3["sortedDesc"]
                     and h3["ariaSort"] == "descending" and 0 < n3 < 518)
            check("R3 ratio-bucket filter: pay_ratio header aria-sort 'descending' (hdr=%r footer=%s)" % (h3, n3),
                  r3_ok, "want sortedDesc + aria-sort descending + footer 1-517")

            # R4: hash change to a hashless URL resets to the default
            # sort with aria-sort 'descending' on total_compensation.
            # Setup matters: the initial HTML already carries
            # aria-sort 'descending' on total_compensation, so a bare
            # hashchange after a sort deep-link passes vacuously
            # pre-fix. Click the tenure header first (the good click
            # path sets aria-sort 'none' on total_compensation), then
            # the reset must restore 'descending'.
            load()
            pg.locator('th.sortable[data-sort="_ceoTenureYears"]').click()
            pg.wait_for_timeout(800)
            pre = header_state("total_compensation")
            pg.evaluate("() => { history.pushState(null, '', location.pathname); window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            pg.wait_for_timeout(1500)
            h4 = header_state("total_compensation")
            r4_ok = (pre is not None and pre["ariaSort"] == "none"
                     and h4 is not None and h4["sortedDesc"]
                     and h4["ariaSort"] == "descending")
            check("R4 hashless hashchange: total_comp header aria-sort 'descending' (hdr=%r)" % (h4,),
                  r4_ok, "want sortedDesc + aria-sort descending")

            r5_ok = len(errors) == 0
            check("R5 zero page errors across the render half",
                  r5_ok, "; ".join(errors[:3]) if errors else "")
            browser.close()
            return all([r1_ok, r2_ok, r3_ok, r4_ok, r5_ok])
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
