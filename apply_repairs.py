import json
rep_path = '/home/hatch/workspace/goals/s-p-500-executive-compensation-tracker/hidden_files/reparse_20260910_0730/repairs.json'
comp_path = 'data/compensation.json'
repairs = json.load(open(rep_path))
d = json.load(open(comp_path))
cos = {c['ticker']: c for c in d['companies']}

def find_exec(ticker, name, year):
    c = cos.get(ticker)
    if not c:
        return None
    for e in c.get('executives', []):
        if e.get('name')==name and e.get('year')==year:
            return e
    return None

changes = 0
for r in repairs:
    if r['verdict'] == 'fix':
        exe = find_exec(r['ticker'], r['name'], r['year'])
        if exe:
            for k,v in r['corrected_components'].items():
                exe[k] = v
            exe['total'] = r['filing_total']
            exe['_total_source'] = 'def14a_verified_20260910'
            exe.pop('_parse_note', None)
            exe.pop('_relabel_note_20260909', None)
            changes+=1
        else:
            # AKAM rename case: if missing Robert Blumofe 2023, find Paul Joseph 2023
            if r['ticker']=='AKAM' and r['name']=='Robert Blumofe' and r['year']==2023:
                exe = find_exec('AKAM','Paul Joseph',2023)
                if exe:
                    exe['name']='Paul Joseph'
                    for k,v in r['corrected_components'].items():
                        exe[k]=v
                    exe['total']=r['filing_total']
                    exe['_total_source']='def14a_verified_20260910'
                    changes+=1
            # similar for other?
    elif r['verdict']=='filing_side_mismatch':
        exe = find_exec(r['ticker'], r['name'], r['year'])
        if exe:
            exe['_total_source']='component_mismatch'
            exe['_relabel_note_20260910']=r['note']
            changes+=1

with open(comp_path,'w') as f:
    json.dump(d,f,indent=2)
print('applied',changes)
