#!/usr/bin/env python3
"""Targeted FY2026-proxy watch: the 8 watch CIKs from the 465th note (52).

Lands in scripts/ in the 538th review (allowlist class 1, deliberate
pipeline tools, same standing as scripts/sweep_def14a_full_roster.py).
Light re-confirm between full-roster sweeps, not a re-sweep: for each CIK
fetch data.sec.gov submissions and report the latest DEF 14A date +
accession plus the newest filing of any form. UA per the task body (SEC
limit 10 req/s); ~0.3s spacing, 8 fetches, seconds of wall time.

Known states (535th/537th notes, re-verified 538th): SKYD and FDXF have
never filed a DEF 14A; VMRK's latest is the pre-merger EQR 2026-04-14
proxy; MU/INTU/JBL/COST/ACN latest are their FY2025 proxies (2025-11-25,
2025-11-26, 2025-12-12, 2025-12-04, 2025-12-12). A latest DEF 14A dated
after the stored proxy FY is a real enrichment task. Do NOT send
Accept-Encoding: gzip: urllib does not decompress it and the parse fails
with a UTF-8 decode error on the gzip magic bytes (538th lesson)."""
import json, time, urllib.request
UA = "Kit/1.0 (factoryfactorykit@gmail.com)"
WATCH = {
    "SKYD": "0002041610", "JBL": "0000898293", "COST": "0000909832",
    "ACN": "0001467373", "MU": "0000723125", "INTU": "0000896878",
    "VMRK": "0000906107", "FDXF": "0002082247",
}
for ticker, cik in WATCH.items():
    url = "https://data.sec.gov/submissions/CIK%s.json" % cik.zfill(10)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            sub = json.load(r)
    except Exception as e:
        print("%s: FETCH ERROR %s: %s" % (ticker, type(e).__name__, e))
        time.sleep(0.3)
        continue
    rec = sub.get("filings", {}).get("recent", {})
    forms = rec.get("form", [])
    dates = rec.get("filingDate", [])
    accs = rec.get("accessionNumber", [])
    def14a = [(d, a) for f, d, a in zip(forms, dates, accs) if f == "DEF 14A"]
    latest = def14a[0] if def14a else None
    newest_any = (forms[0], dates[0]) if forms else (None, None)
    print("%s: latest DEF 14A %s acc %s | newest filing %s %s | n DEF 14A in recent: %d"
          % (ticker, latest[0] if latest else "NONE", latest[1] if latest else "-",
             newest_any[0], newest_any[1], len(def14a)))
    time.sleep(0.3)
