"""Two feasible policies, base only. Student-authored with AI assistance."""
import csv
import json
from fractions import Fraction as F
from pathlib import Path
HERE=Path(__file__).resolve().parent
DATA=HERE.parent/'data'/'inference-09-14'
def read(name):
    with (DATA/name).open() as f: return list(csv.DictReader(f))
groups=read('alert_groups.csv')
methods={r['method']:r for r in read('screening.csv')}
answers=[]
for policy,priority_method,reserve in [('A','sensitive',30),('B','precise',0)]:
    rows=[]
    for g in groups:
        method='sensitive' if g['group']=='routine' else priority_method
        m=methods[method]; n=int(g['daily_devices']); faults=n*F(g['base'])
        tp=faults*F(m['sensitivity']); fp=(n-faults)*(1-F(m['specificity']))
        positive=tp+fp; risk=tp/positive
        rows.append(dict(group=g['group'],method=method,faults=faults,true_positive=tp,false_positive=fp,
                         positive=positive,risk=risk,screen_cost=n*F(m['cost_per_device']),
                         miss_unit=F(g['miss_cost']),reviews=0,cap=positive.numerator//positive.denominator))
    rows[0]['reviews']=min(reserve,rows[0]['cap'])
    left=90-rows[0]['reviews']
    for row in sorted(rows,key=lambda r:r['risk']*r['miss_unit'],reverse=True):
        extra=min(left,row['cap']-row['reviews']);row['reviews']+=extra;left-=extra
    for row in rows:
        row['found']=row['reviews']*row['risk']
        row['missed']=row['faults']-row['found']
        row['miss_loss']=row['missed']*row['miss_unit']
        row['review_cost']=3*row['reviews']
        assert 0<=row['reviews']<=row['positive']
    totals={k:sum(r[k] for r in rows) for k in ('screen_cost','review_cost','missed','miss_loss')}
    totals['total_cost']=totals['screen_cost']+totals['review_cost']+totals['miss_loss']
    assert totals['screen_cost']<=2000 and sum(r['reviews'] for r in rows)<=90
    answers.append(dict(policy=policy,scenario='base',reserve_routine=reserve,groups=rows,totals=totals))
def serial(x):
    if isinstance(x,F):return float(x)
    if isinstance(x,dict):return {k:serial(v) for k,v in x.items()}
    if isinstance(x,list):return [serial(v) for v in x]
    return x
out=HERE/'artifacts';out.mkdir(exist_ok=True)
(out/'minimum.json').write_text(json.dumps(serial(answers),ensure_ascii=False,indent=2)+'\n')
for answer in answers: print(answer['policy'],serial(answer['totals']))
