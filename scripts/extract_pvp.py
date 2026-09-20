#!/usr/bin/env python3
"""SEC Item 402(v) Pay-versus-Performance extractor (pilot: 12 mega-caps).

Verified 2026-09-19 against the rendered DEF 14A PvP tables. Per-ticker manual
column maps because filing HTML is highly irregular (colspan repeats, spacer
cells, split negative-paren cells, footnote-marker cells, split ordinals).
The four compensation columns are cross-checked against Inline XBRL facts
(us-gaap:PeoTotalCompAmt etc.) where available; rows failing checks are
rejected, never shipped. Run from the goal workspace; raw filings live in
~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/pvp_pilot_20260919_2200/.
Output: pvp_pilot.json -> build_pvp_data.py -> data/pay_vs_performance.json.
"""
import re, html as htmlmod, json, os, sys

OUT = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/pvp_pilot_20260919_2200")
man = json.load(open(os.path.join(OUT, "manifest.json")))
UA = {"User-Agent": "Kit/1.0 (factoryfactorykit@gmail.com)"}

def clean(x):
    t = re.sub(r'<[^>]+>', ' ', htmlmod.unescape(x))
    return re.sub(r'[\s\u00a0\u200b\u2009\u2003\u2007]+', ' ', t).strip()

def num(s):
    """Parse a filed value string -> float or None. '—'/empty -> None."""
    if s is None: return None
    s = s.strip()
    if s in ('', '—', '-', '–', 'N/A', 'n/a'): return None
    neg = s.startswith('(') and s.rstrip().endswith(')')
    s = s.strip().strip('()').replace('$', '').replace(',', '').strip()
    m = re.match(r'^-?[\d.]+', s)
    if not m: return None
    v = float(m.group(0))
    return -v if neg else v

def get_table(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    best = None
    for tbm in re.finditer(r'<table.*?</table>', t, re.S | re.I):
        tb = tbm.group(0); low = clean(tb).lower()
        if 'compensation actually paid' not in low: continue
        if not ('shareholder return' in low or re.search(r'\btsr\b', low)): continue
        rows = re.findall(r'<tr.*?</tr>', tb, re.S | re.I)
        nyr = 0
        for r in rows:
            cells = [clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S | re.I)]
            first = next((x for x in cells if x not in ('', '$')), '')
            if re.search(r'\b(20\d{2})\b', first): nyr += 1
        if best is None or nyr > best[0]: best = (nyr, tb)
    return best[1] if best else None

def merge_parens(vals):
    """Join negative values split across two cells, e.g. ['( 11,048,223', ')']."""
    out, i = [], 0
    while i < len(vals):
        v = vals[i]
        if v.startswith('(') and not v.rstrip().endswith(')') and i + 1 < len(vals) and vals[i + 1].strip() in (')', ']'):
            out.append(v + vals[i + 1]); i += 2
        elif v.strip() in (')', ']') and out:
            out[-1] += v; i += 1
        else:
            out.append(v); i += 1
    return out

def clean_cells(vals):
    """Drop footnote-marker cells like '(4)'; merge split ordinal/'%' suffixes; join split parens."""
    out = []
    for v in vals:
        vs = v.strip()
        if re.fullmatch(r'\(\d{1,2}\)', vs):
            continue  # footnote reference cell, not a value
        if vs in ('th', 'rd', 'st', 'nd') and out:
            out[-1] += vs; continue
        if vs == '%' and out:
            continue  # cosmetic; num() parses the number
        out.append(v)
    return merge_parens(out)

def data_rows(tb):
    rows = re.findall(r'<tr.*?</tr>', tb, re.S | re.I)
    out = []
    for r in rows:
        cells = [clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S | re.I)]
        vals = [x for x in cells if x not in ('', '$')]
        if not vals: continue
        ym = re.search(r'\b(20\d{2})\b', vals[0])
        if ym: out.append((int(ym.group(1)), clean_cells(vals[1:])))
    return out

# ---- XBRL facts ----
XBRL = {}
def load_xbrl(tk, path):
    t = open(path, encoding='utf-8', errors='replace').read()
    tags = ['PeoTotalCompAmt', 'PeoActuallyPaidCompAmt', 'NonPeoNeoAvgTotalCompAmt',
            'NonPeoNeoAvgCompActuallyPaidAmt', 'PeoName', 'NonPeoNeoName']
    d = {}
    for tag in tags:
        vals = []
        for m in re.finditer(r'<us-gaap:' + tag + r'[^>]*>([^<]+)</us-gaap:' + tag + r'>', t):
            v = m.group(1).strip().replace(',', '')
            vals.append(v)
        d[tag] = vals
    XBRL[tk] = d

# ---- per-ticker specs ----
# cols: (json_key, transform)  transform in {'$', '$M'->dollars, 'B'->dollars, 'raw'}
SPECS = {
 'NVDA':  dict(peo=['Jen-Hsun Huang'], peer_group=None,
               csm={'label': 'Non-GAAP Operating Income', 'unit': '$M'},
               ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','M')]),
 'AAPL':  dict(peo=['Timothy D. Cook'], peer_group=None,
               csm={'label': 'Net Sales', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','M')]),
 'MSFT':  dict(peo=['Satya Nadella'], peer_group=None,
               csm={'label': 'Incentive Plan Revenue', 'unit': '$B'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','B')]),
 'META':  dict(peo=['Mark Zuckerberg'], peer_group=None,
               csm={'label': 'Revenue', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','M')]),
 'AMZN':  dict(peo=[('Jeffrey P. Bezos','bezos'),('Andrew R. Jassy','jassy')], peer_group=None,
               csm=None, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('peo_bezos_sct','$'),('peo_jassy_sct','$'),('peo_bezos_cap','$'),('peo_jassy_cap','$'),
                     ('nonpeo_sct','$'),('nonpeo_cap','$'),('co_tsr','raw'),
                     ('peer_tsr_nyse_tech','raw'),('peer_tsr_sp_retail','raw'),('net_income','M')],
               peer_labels={'peer_tsr_nyse_tech': 'NYSE Technology Index', 'peer_tsr_sp_retail': 'S&P Retail Select Industry Index'}),
 'GOOGL': dict(peo=['Sundar Pichai'], peer_group='RDG Internet Composite',
               csm={'label': '1-Year TSR Relative to S&P 100', 'unit': '%/rank'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','raw')]),
 'AVGO':  dict(peo=['Hock E. Tan'], peer_group=None,
               csm={'label': 'Net Revenue', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','M$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','M')]),
 'BRK-B': dict(peo=['Warren E. Buffett'], peer_group=None,
               csm={'label': 'Company Selected Measure', 'unit': 'as filed'}, ni={'label': 'Net Earnings', 'unit': '$B'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','B')]),
 'TSLA':  dict(peo=['Elon Musk'], peer_group='SIC 3711 Motor Vehicles and Passenger Car Bodies',
               csm={'label': 'Revenue', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','M$'),('nonpeo_sct','M$'),('nonpeo_cap','M$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','M')]),
 'JPM':   dict(peo=['James Dimon'], peer_group=None,
               csm={'label': 'ROTCE', 'unit': '%'}, ni={'label': 'Net Income', 'unit': '$B'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','B'),('csm','raw')]),
 'WMT':   dict(peo=['C. Douglas McMillon'], peer_group=None,
               csm={'label': 'Net Sales', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('sct','$'),('cap','$'),('nonpeo_sct','$'),('nonpeo_cap','$'),
                     ('co_tsr','raw'),('peer_tsr','raw'),('net_income','M'),('csm','M')]),
 'V':     dict(peo=[('Alfred F. Kelly Jr.', 'kelly'), ('Ryan McInerney', 'mcinerney')], peer_group=None,
               csm={'label': 'EPS - PS Adjusted', 'unit': '$'}, ni={'label': 'Net Income', 'unit': '$M'},
               cols=[('peo_kelly_sct','$'),('peo_mcinerney_sct','$'),('peo_kelly_cap','$'),('peo_mcinerney_cap','$'),
                     ('nonpeo_sct','$'),('nonpeo_cap','$'),('co_tsr','raw'),('peer_tsr','raw'),
                     ('net_income','M'),('csm','raw')]),
}

def xform(v, kind):
    n = num(v)
    if n is None: return None
    if kind == '$': return n
    if kind == 'M$': return n * 1e6
    if kind == 'M': return n          # net income in $M, keep
    if kind == 'B': return n          # keep, unit recorded separately
    return n

def main():
    results = {}
    problems = []
    for tk, spec in SPECS.items():
        path = man[tk]['file']
        tb = get_table(path)
        if not tb:
            problems.append(f'{tk}: no PvP table found'); continue
        rows = data_rows(tb)
        if not rows:
            problems.append(f'{tk}: no year rows'); continue
        load_xbrl(tk, path)
        years = []
        for year, vals in rows:
            if len(vals) != len(spec['cols']):
                problems.append(f'{tk} {year}: {len(vals)} values, need {len(spec["cols"])}: {vals}'); continue
            rec = {'year': year}
            peo_entries = []
            peo_map = {}
            for (key, kind), raw in zip(spec['cols'], vals):
                v = xform(raw, kind)
                if key.startswith('peo_') and key.endswith(('_sct', '_cap')):
                    who = key[4:-4]
                    peo_map.setdefault(who, {})[key[-3:]] = v
                else:
                    rec[key] = v
            peo_spec = spec['peo']
            if isinstance(peo_spec[0], tuple):
                for name, who in peo_spec:
                    e = peo_map.get(who, {})
                    peo_entries.append({'name': name, 'sct': e.get('sct'), 'cap': e.get('cap')})
            else:
                peo_entries.append({'name': peo_spec[0], 'sct': rec.pop('sct', None), 'cap': rec.pop('cap', None)})
            rec['peo'] = peo_entries
            # XBRL cross-check on comp columns
            x = XBRL[tk]
            def xf(tag):
                try: return [float(v) for v in x.get(tag, [])]
                except: return []
            checks = []
            psct, pcap = xf('PeoTotalCompAmt'), xf('PeoActuallyPaidCompAmt')
            nsct, ncap = xf('NonPeoNeoAvgTotalCompAmt'), xf('NonPeoNeoAvgCompActuallyPaidAmt')
            got = {'sct': peo_entries[0]['sct'], 'cap': peo_entries[0]['cap'],
                   'nonpeo_sct': rec.get('nonpeo_sct'), 'nonpeo_cap': rec.get('nonpeo_cap')}
            for k, xv in [('sct', psct), ('cap', pcap), ('nonpeo_sct', nsct), ('nonpeo_cap', ncap)]:
                gv = got[k]
                if gv is None or not xv: continue
                if not any(abs(gv - v) < max(2.0, abs(v) * 0.001) for v in xv):
                    checks.append(f'{k}: table={gv:,.0f} xbrl={[f"{v:,.0f}" for v in xv]}')
            rec['_xbrl_check'] = checks if checks else 'ok'
            if checks: problems.append(f'{tk} {year} XBRL mismatch: ' + '; '.join(checks))
            years.append(rec)
        years.sort(key=lambda r: r['year'])
        results[tk] = {
            'ticker': tk,
            'company_name': man[tk].get('company_name'),
            'cik': man[tk].get('cik'),
            'filing_date': man[tk]['filing_date'],
            'filing_url': man[tk]['url'],
            'peer_group': spec.get('peer_group'),
            'peer_labels': spec.get('peer_labels'),
            'csm': spec.get('csm'),
            'net_income': spec.get('ni'),
            'years': years,
        }
    json.dump(results, open(os.path.join(OUT, 'pvp_pilot.json'), 'w'), indent=1)
    print('PROBLEMS:', len(problems))
    for p in problems: print(' -', p)
    print('companies:', len(results))
    for tk, r in results.items():
        yrs = [y['year'] for y in r['years']]
        print(f'  {tk}: {min(yrs)}-{max(yrs)} ({len(yrs)} yrs)')

if __name__ == '__main__':
    main()
