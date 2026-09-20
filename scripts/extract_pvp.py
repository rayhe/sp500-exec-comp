#!/usr/bin/env python3
"""SEC Item 402(v) Pay-versus-Performance extractor (pilot: 12 mega-caps; wave 2: 10 large-caps).

Verified 2026-09-19 (pilot) and 2026-09-20 (wave 2) against the rendered DEF 14A
PvP tables. Per-ticker manual column maps because filing HTML is highly irregular
(colspan repeats, spacer cells, split negative-paren cells, footnote-marker cells,
split ordinals, per-year column layouts for CEO transitions, fiscal-year labels).
The four compensation columns are cross-checked against Inline XBRL facts
(ecd:PeoTotalCompAmt etc. via ix: elements, us-gaap: element form for the pilot)
where available; rows failing checks are rejected, never shipped. Run from the
goal workspace; raw filings live in
~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/pvp_pilot_20260919_2200/
(pilot) and .../pvp_wave2_20260920_0730/ (wave 2).
Output: pvp_pilot.json / pvp_wave2.json -> build_pvp_data*.py -> data/pay_vs_performance.json.
Usage: python3 extract_pvp.py        # pilot (default, unchanged verified behavior)
       python3 extract_pvp.py wave2  # second wave
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
        # wave 2: Chevron labels the column "CAP for CEO" and "Total stockholder return"
        if 'compensation actually paid' not in low and 'cap for' not in low: continue
        if not ('shareholder return' in low or 'stockholder return' in low or re.search(r'\btsr\b', low)): continue
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

# ---- wave 2 (2026-09-20): 10 large-caps ----
WAVE2_OUT = os.path.expanduser("~/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/pvp_wave2_20260920_0730")
man2 = json.load(open(os.path.join(WAVE2_OUT, "manifest_raw.json")))

# company names from the tracker's compensation.json (same source as the site)
_COMP = {c['ticker']: c['company_name'] for c in
         json.load(open(os.path.expanduser("~/repos/sp500-exec-comp/data/compensation.json")))['companies']}

def _cols(ni_kind, csm_kind):
    return [('sct', '$'), ('cap', '$'), ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
            ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', ni_kind), ('csm', csm_kind)]

# members: map our per-person key -> Inline XBRL explicitMember for cross-checks
SPECS_WAVE2 = {
 'XOM':  dict(peo=['Darren W. Woods'], peer_group='IOC Peers (BP, Chevron, Shell, TotalEnergies)',
              csm={'label': 'CFOAS', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
              cols=_cols('M', 'M'),
              notes=["Peer TSR is the IOC peer group (BP, Chevron, Shell, TotalEnergies)."]),
 'CVX':  dict(peo=['Michael K. Wirth'], peer_group='Competitor Peer Group (BP, ExxonMobil, Shell, TotalEnergies)',
              csm={'label': 'Return on Capital Employed (ROCE)', 'unit': '%'},
              ni={'label': 'Net Income', 'unit': '$B'},
              cols=_cols('B', 'raw'),
              notes=["Peer TSR is the Competitor Peer Group (BP, ExxonMobil, Shell, TotalEnergies), market-cap weighted."]),
 'LLY':  dict(peo=['David A. Ricks'], peer_group='Pharma Peer Group plus Novo Nordisk',
              csm={'label': 'Adjusted Non-GAAP EPS', 'unit': '$'}, ni={'label': 'Net Income', 'unit': '$M'},
              cols=_cols('M', '$'),
              notes=["Peer TSR is a pharmaceutical peer group plus Novo Nordisk."]),
 'UNH':  dict(peo=[('Stephen J. Hemsley', 'hemsley'), ('Andrew Witty', 'witty')],
              # 2021 columns are Witty (then-current PEO) + Wichmann (then-former PEO)
              peo_by_year={2021: [('Andrew Witty', 'witty'), ('Dave Wichmann', 'wichmann')]},
              peer_group='S&P 500 Health Care Index',
              csm={'label': 'Adjusted EPS', 'unit': '$'}, ni={'label': 'Net Income', 'unit': '$'},
              members={'hemsley': 'unh:StephenHemsleyMember', 'witty': 'unh:AndrewWittyMember',
                       'wichmann': 'unh:DaveWichmannMember'},
              cols=[('peo_hemsley_sct', '$'), ('peo_witty_sct', '$'),
                    ('peo_hemsley_cap', '$'), ('peo_witty_cap', '$'),
                    ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                    ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', '$'), ('csm', '$')],
              cols_by_year={2021: [('peo_witty_sct', '$'), ('peo_wichmann_sct', '$'),
                                   ('peo_witty_cap', '$'), ('peo_wichmann_cap', '$'),
                                   ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                                   ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', '$'), ('csm', '$')]},
              notes=["Stephen J. Hemsley became PEO on May 12, 2025; Andrew Witty served as PEO until then.",
                     "In 2021 the columns show Andrew Witty (then PEO) and Dave Wichmann (then former PEO)."]),
 'HD':   dict(peo=[('Ted Decker', 'decker'), ('Craig Menear', 'menear')],
              peer_group='S&P 500 Retail Index',
              csm={'label': 'Operating Profit', 'unit': '$B'}, ni={'label': 'Net Income', 'unit': '$B'},
              members={'decker': 'hd:TedDeckerMember', 'menear': 'hd:CraigAMenearMember'},
              xbrl_year_offset=1,  # fiscal year ends late Jan/early Feb; FY2025 facts end 2026-02-01
              cols=[('peo_decker_sct', '$'), ('peo_menear_sct', '$'),
                    ('peo_decker_cap', '$'), ('peo_menear_cap', '$'),
                    ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                    ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', 'B'), ('csm', 'B')],
              notes=["Fiscal years (ending late January/early February); year shown as filed.",
                     "Ted Decker and Craig Menear each served as CEO during fiscal 2022; Menear was CEO in fiscal 2021."]),
 'PG':   dict(peo=[('Shailesh Jejurikar', 'jejurikar'), ('Jon R. Moeller', 'moeller'), ('David S. Taylor', 'taylor')],
              peer_group='S&P 500 Consumer Staples',
              csm={'label': 'Organic Sales Growth', 'unit': '%'}, ni={'label': 'Net Income', 'unit': '$B'},
              members={'jejurikar': 'pg:MrJejurikarMember', 'moeller': 'pg:Mr.MoellerMember',
                       'taylor': 'pg:DavidTaylorMember'},
              year_fn=lambda cell: (lambda ms: (lambda y: y if 2000 <= y <= 2030 else None)(
                  int(ms[-1]) + (2000 if int(ms[-1]) < 100 else 0)) if ms else None)(
                  re.findall(r'\d{2,4}', cell)),
              # column layout varies by year: only CEOs who served that year get columns
              cols_by_year={
                  2026: [('peo_jejurikar_sct', '$'), ('peo_jejurikar_cap', '$'),
                         ('peo_moeller_sct', '$'), ('peo_moeller_cap', '$'),
                         ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                         ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', 'B'), ('csm', 'raw')],
                  2022: [('peo_moeller_sct', '$'), ('peo_moeller_cap', '$'),
                         ('peo_taylor_sct', '$'), ('peo_taylor_cap', '$'),
                         ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                         ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', 'B'), ('csm', 'raw')],
              },
              cols_default=[('peo_moeller_sct', '$'), ('peo_moeller_cap', '$'),
                            ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                            ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', 'B'), ('csm', 'raw')],
              notes=["Fiscal years ending June 30; year shown is the fiscal year-end year.",
                     "Three CEOs across the window: Taylor and Moeller in FY2022, Moeller in FY2023-2025, Jejurikar and Moeller in FY2026."]),
 'MA':   dict(peo=['Michael Miebach'], peer_group='S&P 500 Financials',
              csm={'label': 'Adjusted Net Revenue', 'unit': '$M'}, ni={'label': 'Net Income', 'unit': '$M'},
              cols=_cols('M', 'M'),
              notes=["Peer TSR is the S&P 500 Financials Index."]),
 'ORCL': dict(peo=['Safra A. Catz'], peer_group='Dow Jones U.S. Technology Total Return Index',
              csm={'label': 'Non-GAAP Operating Income Growth', 'unit': '$M'},
              ni={'label': 'Net Income', 'unit': '$M'},
              cols=_cols('M', 'M'),
              notes=["Fiscal years ending May 31; year shown as filed. Safra A. Catz is PEO (CEO)."]),
 'COST': dict(peo=[('Ron M. Vachris', 'vachris'), ('W. Craig Jelinek', 'jelinek')],
              peer_group='S&P Retail Select Index',
              csm={'label': 'Net Sales Adjusted for Changes in Foreign Currencies', 'unit': '$M'},
              ni={'label': 'Net Income', 'unit': '$M'},
              members={'vachris': 'cost:RonM.VachrisMember', 'jelinek': 'cost:W.CraigJelinekMember'},
              cols=[('peo_vachris_sct', '$'), ('peo_jelinek_sct', '$'),
                    ('peo_vachris_cap', '$'), ('peo_jelinek_cap', '$'),
                    ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                    ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', 'M'), ('csm', 'M')],
              notes=["Fiscal years (ending late August/early September); year shown as filed.",
                     "Ron M. Vachris became PEO in fiscal 2024; W. Craig Jelinek was PEO in fiscal 2021-2023."]),
 'NFLX': dict(peo=[('Reed Hastings', 'hastings'), ('Ted Sarandos', 'sarandos'), ('Greg Peters', 'peters')],
              peer_group='RDG Internet Composite',
              csm={'label': 'F/X Neutral Operating Margin', 'unit': '%'},
              ni={'label': 'Net Income', 'unit': '$M'},
              members={'hastings': 'nflx:ReedHastingsMember', 'sarandos': 'nflx:TedSarandosMember',
                       'peters': 'nflx:GregPetersMember'},
              cols=[('peo_hastings_sct', '$'), ('peo_sarandos_sct', '$'), ('peo_peters_sct', '$'),
                    ('peo_hastings_cap', '$'), ('peo_sarandos_cap', '$'), ('peo_peters_cap', '$'),
                    ('nonpeo_sct', '$'), ('nonpeo_cap', '$'),
                    ('co_tsr', 'raw'), ('peer_tsr', 'raw'), ('net_income', 'M'), ('csm', 'raw')],
              notes=["Reed Hastings served as co-CEO through January 2023; Ted Sarandos and Greg Peters are co-CEOs from 2023."]),
}

def parse_year(cell, spec):
    fn = spec.get('year_fn')
    if fn:
        return fn(cell)
    m = re.search(r'\b(20\d{2})\b', cell)
    return int(m.group(1)) if m else None

def data_rows2(tb, spec):
    rows = re.findall(r'<tr.*?</tr>', tb, re.S | re.I)
    out = []
    for r in rows:
        cells = [clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S | re.I)]
        vals = [x for x in cells if x not in ('', '$')]
        if not vals:
            continue
        y = parse_year(vals[0], spec)
        if y:
            out.append((y, clean_cells(vals[1:])))
    return out

# ---- Inline XBRL facts via ix: elements (ecd: / us-gaap:) ----
def load_ix_facts(path):
    """Return list of (tag, start_date, end_date, members, value)."""
    t = open(path, encoding='utf-8', errors='replace').read()
    ctx = {}
    for m in re.finditer(r'<xbrli:context\b[^>]*id="([^"]+)"[^>]*>(.*?)</xbrli:context>', t, re.S):
        cid, body = m.group(1), m.group(2)
        sd = re.search(r'<xbrli:startDate>([^<]+)</xbrli:startDate>', body)
        ed = re.search(r'<xbrli:endDate>([^<]+)</xbrli:endDate>', body)
        inst = re.search(r'<xbrli:instant>([^<]+)</xbrli:instant>', body)
        members = re.findall(r'<xbrldi:explicitMember[^>]*>([^<]+)</xbrldi:explicitMember>', body)
        ctx[cid] = (sd.group(1) if sd else None,
                    ed.group(1) if ed else (inst.group(1) if inst else None),
                    members)
    facts = []
    for m in re.finditer(r'<ix:non(?:Fraction|Numeric)\b[^>]*>', t):
        el = m.group(0)
        nm = re.search(r'name="([a-zA-Z]+):([^"]+)"', el)
        cr = re.search(r'contextRef="([^"]+)"', el)
        if not nm or not cr:
            continue
        ns, tag = nm.group(1), nm.group(2)
        if ns not in ('ecd', 'us-gaap'):
            continue
        me = re.search(r'</ix:non(?:Fraction|Numeric)>', t[m.end():])
        if not me:
            continue
        raw = t[m.end():m.end() + me.start()]
        v = num(re.sub(r'<[^>]+>', '', raw))
        if v is None:
            continue
        if re.search(r'sign="-"', el):
            v = -v
        sd, ed, members = ctx.get(cr.group(1), (None, None, []))
        facts.append((tag, sd, ed, members, v))
    return facts

IX_TAGS = {'sct': 'PeoTotalCompAmt', 'cap': 'PeoActuallyPaidCompAmt',
           'nonpeo_sct': 'NonPeoNeoAvgTotalCompAmt', 'nonpeo_cap': 'NonPeoNeoAvgCompActuallyPaidAmt'}

def ix_check(tk, spec, year, rec, peo_entries, facts, problems):
    """Cross-check the four comp columns against Inline XBRL facts. Strict: mismatches are problems."""
    members = spec.get('members', {})
    offset = spec.get('xbrl_year_offset', 0)
    peo_spec = spec.get('peo_by_year', {}).get(year, spec['peo'])
    checks = []
    # (key, tag, required_member_or_None)
    jobs = []
    if isinstance(peo_spec[0], tuple):
        for name, who in peo_spec:
            e = next((p for p in peo_entries if p['name'] == name), {})
            mem = members.get(who)
            jobs.append((f'peo_{who}_sct', e.get('sct'), 'PeoTotalCompAmt', mem))
            jobs.append((f'peo_{who}_cap', e.get('cap'), 'PeoActuallyPaidCompAmt', mem))
    else:
        jobs.append(('sct', peo_entries[0]['sct'], 'PeoTotalCompAmt', None))
        jobs.append(('cap', peo_entries[0]['cap'], 'PeoActuallyPaidCompAmt', None))
    jobs.append(('nonpeo_sct', rec.get('nonpeo_sct'), 'NonPeoNeoAvgTotalCompAmt', 'ecd:NonPeoNeoMember'))
    jobs.append(('nonpeo_cap', rec.get('nonpeo_cap'), 'NonPeoNeoAvgCompActuallyPaidAmt', 'ecd:NonPeoNeoMember'))
    for key, gv, tag, mem in jobs:
        if gv is None:
            continue
        cands = [f for f in facts if f[0] == tag and f[2] and f[2][:4] == str(year + offset)]
        if not cands:
            continue  # filer did not tag this column; nothing to check against
        if mem:
            cands_m = [f for f in cands if mem in f[3]]
            cands = cands_m or cands
        if not any(abs(gv - f[4]) < max(2.0, abs(f[4]) * 0.001) for f in cands):
            checks.append(f'{key}: table={gv:,.0f} xbrl={[f"{f[4]:,.0f}" for f in cands]}')
    return checks

def main_wave2():
    results = {}
    problems = []
    for tk, spec in SPECS_WAVE2.items():
        path = os.path.join(WAVE2_OUT, man2[tk]['file'])
        tb = get_table(path)
        if not tb:
            problems.append(f'{tk}: no PvP table found')
            continue
        rows = data_rows2(tb, spec)
        if not rows:
            problems.append(f'{tk}: no year rows')
            continue
        facts = load_ix_facts(path)
        years = []
        for year, vals in rows:
            cols = spec.get('cols_by_year', {}).get(year, spec.get('cols_default', spec.get('cols')))
            if cols is None:
                problems.append(f'{tk} {year}: no column map')
                continue
            if len(vals) != len(cols):
                problems.append(f'{tk} {year}: {len(vals)} values, need {len(cols)}: {vals}')
                continue
            rec = {'year': year}
            peo_entries = []
            peo_map = {}
            for (key, kind), raw in zip(cols, vals):
                v = xform(raw, kind)
                if key.startswith('peo_') and key.endswith(('_sct', '_cap')):
                    who = key[4:-4]
                    peo_map.setdefault(who, {})[key[-3:]] = v
                else:
                    rec[key] = v
            peo_spec = spec.get('peo_by_year', {}).get(year, spec['peo'])
            if isinstance(peo_spec[0], tuple):
                for name, who in peo_spec:
                    e = peo_map.get(who, {})
                    peo_entries.append({'name': name, 'sct': e.get('sct'), 'cap': e.get('cap')})
            else:
                peo_entries.append({'name': peo_spec[0], 'sct': rec.pop('sct', None),
                                    'cap': rec.pop('cap', None)})
            rec['peo'] = peo_entries
            checks = ix_check(tk, spec, year, rec, peo_entries, facts, problems)
            rec['_xbrl_check'] = checks if checks else 'ok'
            if checks:
                problems.append(f'{tk} {year} XBRL mismatch: ' + '; '.join(checks))
            years.append(rec)
        years.sort(key=lambda r: r['year'])
        results[tk] = {
            'ticker': tk,
            'company_name': _COMP.get(tk),
            'cik': man2[tk].get('cik'),
            'filing_date': man2[tk]['filing_date'],
            'filing_url': man2[tk]['url'],
            'peer_group': spec.get('peer_group'),
            'peer_labels': spec.get('peer_labels'),
            'csm': spec.get('csm'),
            'net_income': spec.get('ni'),
            'notes': spec.get('notes', []),
            'years': years,
        }
    json.dump(results, open(os.path.join(WAVE2_OUT, 'pvp_wave2.json'), 'w'), indent=1)
    print('PROBLEMS:', len(problems))
    for p in problems:
        print(' -', p)
    print('companies:', len(results))
    for tk, r in results.items():
        yrs = [y['year'] for y in r['years']]
        ok = sum(1 for y in r['years'] if y.get('_xbrl_check') == 'ok')
        print(f'  {tk}: {min(yrs)}-{max(yrs)} ({len(yrs)} yrs, {ok} xbrl-ok)')

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
    if len(sys.argv) > 1 and sys.argv[1] == 'wave2':
        main_wave2()
    else:
        main()
