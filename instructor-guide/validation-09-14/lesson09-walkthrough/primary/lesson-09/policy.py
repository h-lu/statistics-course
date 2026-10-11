"""AI-assisted simulated student's comparison; exact fractions, no random draws."""
import csv
import json
from fractions import Fraction as F
from pathlib import Path
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / 'data' / 'inference-09-14'
def read(name):
    with (DATA/name).open() as f:
        return list(csv.DictReader(f))
groups = read('alert_groups.csv')
methods = {r['method']: r for r in read('screening.csv')}
results = []
for scenario in ('base_low', 'base', 'base_high'):
    for priority_method in ('sensitive', 'precise'):
        for reserve in (0, 40):
            rows = []
            for g in groups:
                method = 'sensitive' if g['group']=='routine' else priority_method
                m = methods[method]
                n, b = int(g['daily_devices']), F(g[scenario])
                faults = n*b
                tp = faults*F(m['sensitivity'])
                fp = (n-faults)*(1-F(m['specificity']))
                pos = tp+fp
                ppv = tp/pos if pos else F(0)
                rows.append(dict(group=g['group'], method=method, faults=faults, tp=tp, fp=fp,
                    positives=pos, ppv=ppv, cap=pos.numerator//pos.denominator,
                    screening_cost=n*F(m['cost_per_device']), miss_unit=F(g['miss_cost']), reviews=0))
            assert sum(r['screening_cost'] for r in rows)<=2000
            # Reserve first, then allocate remaining slots by expected avoided loss.
            rows[0]['reviews'] = min(reserve, rows[0]['cap'])
            left = 90-rows[0]['reviews']
            for r in sorted(rows,key=lambda r:r['ppv']*r['miss_unit'],reverse=True):
                more = min(left,r['cap']-r['reviews'])
                r['reviews'] += more
                left -= more
            for r in rows:
                r['found'] = r['reviews']*r['ppv']
                r['missed'] = r['faults']-r['found']
                r['missed_negative'] = r['faults']-r['tp']
                r['missed_unreviewed_positive'] = r['tp']-r['found']
                r['miss_loss'] = r['missed']*r['miss_unit']
                r['review_cost'] = 3*r['reviews']
                assert 0<=r['reviews']<=r['positives']
                assert r['missed']==r['missed_negative']+r['missed_unreviewed_positive']
            totals = {k:sum(r[k] for r in rows) for k in ('screening_cost','review_cost','missed','miss_loss','reviews')}
            totals['total_cost'] = totals['screening_cost']+totals['review_cost']+totals['miss_loss']
            results.append(dict(scenario=scenario,priority_method=priority_method,reserve_routine=reserve,rows=rows,totals=totals))
def convert(x):
    if isinstance(x,F): return float(x)
    if isinstance(x,dict): return {k:convert(v) for k,v in x.items()}
    if isinstance(x,list): return [convert(v) for v in x]
    return x
out = HERE/'artifacts'
out.mkdir(exist_ok=True)
(out/'policy.json').write_text(json.dumps(convert(results),ensure_ascii=False,indent=2)+'\n')
with (out/'comparison.csv').open('w',newline='') as f:
    keys=['scenario','priority_method','reserve_routine','screening_cost','review_cost','reviews','missed','miss_loss','total_cost']
    writer=csv.DictWriter(f,fieldnames=keys); writer.writeheader()
    for r in results:
        writer.writerow({k:round(float(v),6) if isinstance(v,F) else v for k,v in {**{k:r[k] for k in keys[:3]},**r['totals']}.items()})
print((out/'comparison.csv').read_text())
