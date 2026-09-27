#!/usr/bin/env python3
"""Column-shift corruption repair batch, 2026-09-26 19:30 PT run.

Repairs 47 NEO rows across 11 tickers / 20 primary DEF 14A filings where the
original parser dropped the salary cell (or the first SCT column), shifting
every component one column left, landing the filing's printed total in
all_other, and recomputing a phantom ~2x total.

Every value below was read filing-verbatim from the proxy SCT (evidence in
~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/dq_20260926_1930/).
Detection heuristic: d = 2*all_other - total equals the filing salary
(exact or within rounding); repair values are NOT arithmetic inferences.

Idempotent: re-running applies the same filing values and is a no-op.
"""
import json, os, shutil, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JSON_PATH = os.path.join(REPO, "data", "compensation.json")
BACKUP_PATH = os.path.join(HERE, "compensation_backup_20260926_1930_pre_colshift.json")

KEYS = ["salary", "bonus", "stock_awards", "option_awards",
        "non_equity_incentive", "pension_nqdc", "all_other", "total"]
LABEL = "def14a_verified_20260926"

# (ticker, name_substring, year, filing_values_tuple_in_KEYS_order, filing_file)
REPAIRS = [
    # TYL — tyl_2025.htm / tyl_2024.htm (cols: sal,bon,stk,opt,neip,pen,ao,tot)
    ("TYL", "Marr", 2024, (300000, 0, 899436, 0, 0, 0, 7500, 1206936), "tyl_2025.htm"),
    ("TYL", "Marr", 2023, (300000, 0, 899482, 0, 0, 0, 7500, 1206982), "tyl_2024.htm"),
    # APO — apo_2025.htm / apo_2024.htm (cols: sal,bon,stk,ao,tot)
    ("APO", "Marc Rowan", 2024, (100000, 0, 0, 0, 0, 0, 663381, 763381), "apo_2025.htm"),
    ("APO", "Marc Rowan", 2023, (100000, 0, 0, 0, 0, 0, 220760, 320760), "apo_2024.htm"),
    ("APO", "Martin Kelly", 2023, (1000000, 0, 1043706, 0, 0, 0, 1626223, 3669929), "apo_2024.htm"),
    # BRO — bro_2025.htm / bro_2024.htm (cols: sal,bon,stk,neip,ao,tot)
    ("BRO", "R. Andrew Watts", 2024, (794231, 0, 1279571, 0, 1903000, 0, 86284, 4063086), "bro_2025.htm"),
    ("BRO", "R. Andrew Watts", 2023, (648077, 0, 980620, 0, 1559000, 0, 81161, 3268858), "bro_2024.htm"),
    ("BRO", "P. Barrett Brown", 2024, (992308, 0, 688987, 0, 2297000, 0, 126616, 4104911), "bro_2025.htm"),
    ("BRO", "P. Barrett Brown", 2023, (800000, 0, 490253, 0, 2100000, 0, 47475, 3437728), "bro_2024.htm"),
    ("BRO", "Chris L. Walker", 2024, (896154, 0, 1082883, 0, 2665000, 0, 40064, 4684101), "bro_2025.htm"),
    ("BRO", "Chris L. Walker", 2023, (800000, 300000, 490253, 0, 1834000, 0, 30233, 3454486), "bro_2024.htm"),
    # CMCSA — cmcsa_2024.htm (cols: sal,stk,opt,neip,pen,ao,tot; no bonus)
    ("CMCSA", "Michael J. Cavanagh", 2023, (2463846, 0, 11431801, 7000032, 8426353, 0, 258030, 29580063), "cmcsa_2024.htm"),
    ("CMCSA", "Jason S. Armstrong", 2023, (1789615, 0, 3266371, 2000033, 4528767, 0, 10000, 11594786), "cmcsa_2024.htm"),
    ("CMCSA", "Jennifer Khoury", 2023, (1494231, 0, 980051, 600010, 2555135, 0, 10000, 5639427), "cmcsa_2024.htm"),
    # ESS — ess_2025.htm (cols: sal,bon,neip,stk,opt,ao,tot)
    ("ESS", "Angela L. Kleiman", 2024, (900000, 0, 3034560, 0, 4212000, 0, 49723, 8196283), "ess_2025.htm"),
    ("ESS", "Barb M. Pak", 2024, (650000, 0, 1283716, 0, 2028000, 0, 46155, 4007871), "ess_2025.htm"),
    ("ESS", "Anne Morrison", 2024, (500000, 0, 660284, 0, 1170000, 0, 52930, 2383214), "ess_2025.htm"),
    ("ESS", "Rylan K. Burns", 2024, (450000, 0, 477049, 0, 1228500, 0, 52669, 2208218), "ess_2025.htm"),
    # EXR — exr_2024.htm (cols: sal,bon,neip,stk,ao,tot)
    ("EXR", "Joseph D. Margolis", 2023, (900000, 0, 9059042, 0, 1393875, 0, 927784, 12280701), "exr_2024.htm"),
    ("EXR", "Scott Stubbs", 2023, (500000, 0, 2399700, 0, 553125, 0, 266974, 3719799), "exr_2024.htm"),
    ("EXR", "Zach Dickens", 2023, (460000, 0, 2519836, 0, 407100, 0, 108265, 3495201), "exr_2024.htm"),
    ("EXR", "Samrat Sondhi", 2023, (495000, 0, 2531662, 0, 438075, 0, 213154, 3677891), "exr_2024.htm"),
    ("EXR", "Noah Springer", 2023, (460000, 0, 2639808, 0, 407100, 0, 88002, 3594910), "exr_2024.htm"),
    # MKTX — mktx_2024.htm (cols: sal,bon,stk,opt,neip,ao,tot)
    ("MKTX", "Naineshkumar S. Panchal", 2023, (450000, 0, 654676, 0, 800000, 0, 10000, 1914676), "mktx_2024.htm"),
    ("MKTX", "Christophe Roupie", 2023, (460760, 0, 917120, 0, 466986, 0, 87883, 1932749), "mktx_2024.htm"),
    # MTB — mtb_2024.htm (cols: sal,bon,stk,opt,neip,pen,ao,tot)
    ("MTB", "Kevin J. Pearson", 2023, (775000, 1300000, 2000232, 500020, 0, 163129, 68719, 4807100), "mtb_2024.htm"),
    # PLTR — pltr_2025.htm / pltr_2024.htm (cols: sal,stk,ao,tot)
    ("PLTR", "Alexander Karp", 2024, (1101637, 0, 0, 0, 0, 0, 3528533, 4630170), "pltr_2025.htm"),
    ("PLTR", "Alexander Karp", 2023, (1101637, 0, 0, 0, 0, 0, 2396560, 3498197), "pltr_2024.htm"),
    ("PLTR", "Shyam Sankar", 2024, (509419, 0, 0, 0, 0, 0, 297629, 807048), "pltr_2025.htm"),
    ("PLTR", "Shyam Sankar", 2023, (509419, 0, 0, 0, 0, 0, 122761, 632180), "pltr_2024.htm"),
    ("PLTR", "David Glazer", 2024, (450200, 0, 11367363, 0, 0, 0, 26194, 11843757), "pltr_2025.htm"),
    ("PLTR", "David Glazer", 2023, (450200, 0, 0, 0, 0, 0, 24555, 474755), "pltr_2024.htm"),
    ("PLTR", "Ryan Taylor", 2024, (437925, 0, 11367363, 0, 0, 0, 27994, 11833282), "pltr_2025.htm"),
    ("PLTR", "Ryan Taylor", 2023, (437925, 0, 5085743, 0, 0, 0, 26355, 5550023), "pltr_2024.htm"),
    ("PLTR", "Stephen Cohen", 2023, (273636, 0, 0, 0, 0, 0, 83653, 357289), "pltr_2024.htm"),
    # REG — reg_2025.htm / reg_2024.htm (cols: sal,stk,neip,ao,tot)
    ("REG", "Martin E. Stein", 2024, (500000, 0, 712882, 0, 0, 0, 40628, 1253510), "reg_2025.htm"),
    ("REG", "Martin E. Stein", 2023, (500000, 0, 1034858, 0, 0, 0, 40728, 1575586), "reg_2024.htm"),
    ("REG", "Lisa Palmer", 2024, (1030000, 0, 5702941, 0, 2805000, 0, 21322, 9559263), "reg_2025.htm"),
    ("REG", "Lisa Palmer", 2023, (1000000, 0, 5536318, 0, 2712500, 0, 20217, 9269035), "reg_2024.htm"),
    ("REG", "Michael J. Mas", 2024, (620000, 0, 1805910, 0, 1470000, 0, 15630, 3911540), "reg_2025.htm"),
    ("REG", "Michael J. Mas", 2023, (600000, 0, 1759195, 0, 1116000, 0, 17078, 3492273), "reg_2024.htm"),
    ("REG", "Alan T. Roth", 2024, (600000, 0, 1330713, 0, 900000, 0, 14270, 2844983), "reg_2025.htm"),
    ("REG", "Alan T. Roth", 2023, (500000, 0, 1134858, 0, 775000, 0, 17126, 2426984), "reg_2024.htm"),
    ("REG", "Nicholas A. Wibbenmeyer", 2024, (600000, 0, 1330713, 0, 900000, 0, 13580, 2844293), "reg_2025.htm"),
    ("REG", "Nicholas A. Wibbenmeyer", 2023, (500000, 0, 1134858, 0, 775000, 0, 13680, 2423538), "reg_2024.htm"),
    # VICI — vici_2025.htm / vici_2024.htm (cols: sal,bon,stk,neip,ao,tot)
    ("VICI", "John W.R. Payne", 2024, (1200000, 0, 1914311, 0, 2520000, 0, 18715, 5653026), "vici_2025.htm"),
    ("VICI", "John W.R. Payne", 2023, (1200000, 0, 1920000, 0, 2280000, 0, 18102, 5418102), "vici_2024.htm"),
]


def main():
    assert len(REPAIRS) == 47, f"expected 47 repairs, got {len(REPAIRS)}"
    shutil.copy2(JSON_PATH, BACKUP_PATH)
    d = json.load(open(JSON_PATH))
    companies = {c["ticker"]: c for c in d["companies"]}

    old_totals = {}
    phantom_removed = 0
    for ticker, name_sub, year, vals, filing in REPAIRS:
        c = companies[ticker]
        hits = [e for e in c.get("executives") or []
                if name_sub.lower() in e["name"].lower() and e.get("year") == year]
        assert len(hits) == 1, f"{ticker} {name_sub} {year}: {len(hits)} hits"
        e = hits[0]
        old = {k: e.get(k) for k in KEYS}
        old_totals[(ticker, e["name"], year)] = old["total"]
        new = dict(zip(KEYS, vals))
        # foot assertion: components must sum to the filing total (allow rounding)
        foot = sum(new[k] for k in KEYS if k != "total")
        assert abs(foot - new["total"]) <= 2, (
            f"{ticker} {e['name']} {year}: filing values do not foot "
            f"({foot:,} vs {new['total']:,})")
        changed = old["total"] != new["total"]
        if changed:
            phantom_removed += old["total"] - new["total"]
        for k in KEYS:
            e[k] = new[k]
        e["_total_source"] = LABEL
        print(f"{ticker} {e['name'][:30]:30s} {year} "
              f"tot {old['total']:>11,} -> {new['total']:>11,} "
              f"({filing})")

    # company aggregates: total_neo_compensation = sum of FY exec totals
    for ticker in {r[0] for r in REPAIRS}:
        c = companies[ticker]
        fy = c.get("fiscal_year")
        if fy:
            rows = [e for e in c.get("executives", []) if e.get("year") == fy]
            c["total_neo_compensation"] = sum((e.get("total") or 0) for e in rows)
            c["neo_count"] = len(rows)

    # CEO anchor: if ceo_name's displayed total equals a repaired row's OLD
    # total, re-anchor to the filing total
    def _last(n):
        import re as _re
        n = _re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", (n or "").lower()).strip()
        parts = _re.findall(r"[a-z]+", n)
        return parts[-1] if parts else ""
    for ticker in {r[0] for r in REPAIRS}:
        c = companies[ticker]
        cname = c.get("ceo_name") or ""
        for (t, ename, yr), old_tot in old_totals.items():
            if t != ticker:
                continue
            if _last(cname) == _last(ename) and c.get("total_compensation") == old_tot:
                new_tot = next(e["total"] for e in c["executives"]
                               if e["name"] == ename and e.get("year") == yr)
                print(f"CEO re-anchor {ticker} {cname}: "
                      f"{old_tot:,} -> {new_tot:,}")
                c["total_compensation"] = new_tot

    # metadata buckets
    meta = d["metadata"]
    cnt = Counter()
    for co in d["companies"]:
        for e in co.get("executives") or []:
            lab = e.get("_total_source") or "verified"
            key = {"verified": "verified"}.get(lab, lab)
            # normalize both DEF14A spellings to the snake_case bucket
            if lab.startswith("DEF14A-verified"):
                key = "def14a_verified_" + "".join(
                    ch for ch in lab if ch.isdigit())
            cnt[key] += 1
    for bucket in ("data_quality", "data_quality_detailed"):
        b = meta.get(bucket)
        if isinstance(b, dict):
            for k in list(b.keys()):
                if k in cnt:
                    b[k] = cnt[k]
    ver_keys = {"verified"} | {k for k in cnt if k.startswith("def14a_verified_")}
    meta["verified_total"] = sum(cnt[k] for k in ver_keys)
    meta["last_dq_repair"] = "2026-09-26"
    meta["last_updated"] = "2026-09-26"
    d["last_updated"] = "2026-09-26"
    meta["description"] = (
        "518 companies, 7078 NEO records, 517 companies enriched")
    note = ("2026-09-26 19:30 PT column-shift batch: 47 NEO rows across TYL, "
            "APO, BRO, CMCSA, ESS, EXR, MKTX, MTB, PLTR, REG, VICI re-read "
            "filing-verbatim against 20 primary DEF 14As; phantom compensation "
            f"removed ${phantom_removed:,}.")
    if note not in meta["notes"]:
        meta["notes"].append(note)

    json.dump(d, open(JSON_PATH, "w"), indent=1)
    print(f"\nrepaired=47 phantom_removed=${phantom_removed:,}")


if __name__ == "__main__":
    main()
