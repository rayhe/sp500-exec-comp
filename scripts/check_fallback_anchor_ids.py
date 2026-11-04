#!/usr/bin/env python3
"""Guard: position-filter chip fallback anchors must exist in index.html.

Background (333rd review, 2026-11-03): the community-breakdown position
filter renders a dismissible chip into .table-controls, with an else-branch
fallback that inserted the chip before a wrapper element. Both fallback
sites (the empty-filter branch and the populated-filter branch in
js/app.js) referenced getElementById('comp-table-wrapper') -- an id that
never existed in index.html. The real wrapper is id="table-wrapper".
.table-controls exists in the shipped page, so the fallback is currently
unreachable, but if .table-controls is ever removed or restructured the
chip would silently vanish while the position filter stays active: a
filtered table with no affordance to clear it (the same missing-chip
class the 323rd/327th reviews closed elsewhere).

Checks (all static - small reads, <2s):
  C1 HARD FAIL: the dead id 'comp-table-wrapper' appears anywhere in js/.
  C2 HARD FAIL: index.html lacks id="table-wrapper" (the fallback anchor).
  C3 HARD FAIL: fewer than 2 getElementById('table-wrapper') fallback
     sites in js/app.js (the empty-filter and populated-filter branches).

Usage:
  scripts/check_fallback_anchor_ids.py
  scripts/check_fallback_anchor_ids.py --static-only

Exit: 0 = consistent; 1 = drift (loud); 2 = infra (files unreadable).

Honors the pre-commit auto-discovery CONTRACT: named scripts/check_<thing>.py
and contains the literal "--static-only" in sys.argv.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    failures = []
    js_dir = os.path.join(ROOT, "js")
    try:
        js_files = sorted(f for f in os.listdir(js_dir) if f.endswith(".js"))
    except OSError as e:
        print("INFRA: cannot list js/: %s" % e)
        return 2
    dead_hits = []
    for name in js_files:
        path = os.path.join(js_dir, name)
        try:
            src = open(path, encoding="utf-8").read()
        except OSError as e:
            print("INFRA: cannot read %s: %s" % (path, e))
            return 2
        for m in re.finditer(r"comp-table-wrapper", src):
            line = src.count("\n", 0, m.start()) + 1
            dead_hits.append("%s:%d" % (name, line))
    if dead_hits:
        failures.append("C1 dead fallback id 'comp-table-wrapper' still referenced: %s"
                        % ", ".join(dead_hits))

    index_path = os.path.join(ROOT, "index.html")
    try:
        html = open(index_path, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read %s: %s" % (index_path, e))
        return 2
    if 'id="table-wrapper"' not in html:
        failures.append('C2 index.html lacks id="table-wrapper" fallback anchor')

    app_path = os.path.join(js_dir, "app.js")
    try:
        app_src = open(app_path, encoding="utf-8").read()
    except OSError as e:
        print("INFRA: cannot read %s: %s" % (app_path, e))
        return 2
    n_sites = len(re.findall(r"getElementById\('table-wrapper'\)", app_src))
    if n_sites < 2:
        failures.append("C3 only %d getElementById('table-wrapper') fallback site(s) "
                        "in js/app.js, expected >= 2 (empty + populated branches)"
                        % n_sites)

    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        return 1
    print("PASS: fallback anchors consistent "
          "(no comp-table-wrapper refs; table-wrapper in index.html; "
          "%d fallback sites in app.js)" % n_sites)
    return 0


if __name__ == "__main__":
    if "--static-only" in sys.argv:
        pass  # static-only is the only mode; flag accepted for the hook
    sys.exit(main())
