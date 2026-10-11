"""Small general tools, not a completed lesson analysis. Standard library only."""
from pathlib import Path
import csv
import math
import random
import statistics as st

HERE = Path(__file__).resolve().parent

def table(name):
    with (HERE/name).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))

def population():
    return [{**r,'need_weekend':int(r['need_weekend']),'online_frame':int(r['online_frame'])}
            for r in table('weekend_population.csv')]

def acquire(pop, n, seed, mode='srs', response='complete'):
    """Separate frame/selection/response; result value is hidden unless answered.

    srs: full-register equal-probability invitations.
    volunteer: sample n from online frame, then need-dependent volunteering.
    ordinary: group-dependent response, independent of need within group.
    complete: ideal contracted complete response, NOT realistic by default.
    """
    if mode not in ('srs','volunteer') or response not in ('complete','ordinary'):
        raise ValueError('unknown acquisition/response mode')
    rng=random.Random(seed)
    frame=pop if mode=='srs' else [r for r in pop if r['online_frame']]
    chosen={r['person_id'] for r in rng.sample(frame,n)}
    out=[]
    for r in pop:
        selected=r['person_id'] in chosen
        eligible=mode=='srs' or bool(r['online_frame'])
        q=(.85 if r['need_weekend'] else .25) if mode=='volunteer' else (
            1.0 if response=='complete' else {'A':.8,'B':.6}[r['group']])
        answered=selected and rng.random()<q
        out.append({'person_id':r['person_id'],'group':r['group'],
                    'in_frame':int(eligible),'invited':int(selected),'answered':int(answered),
                    'invite_probability':n/len(frame) if eligible else 0,
                    'observed_need':r['need_weekend'] if answered else None})
    return out

def observed(rows):
    return [r['observed_need'] for r in rows if r['answered']]

def poststratified(rows, weights=None):
    """Composition adjustment; does not remove within-group selection bias."""
    weights=weights or {'A':.8,'B':.2}
    values={g:[r['observed_need'] for r in rows if r['answered'] and r['group']==g]
            for g in weights}
    if any(not v for v in values.values()):
        raise ValueError('empty response stratum: estimate unsupported')
    return sum(weights[g]*st.mean(values[g]) for g in weights)

def stratified(pop, allocation, seed):
    rng=random.Random(seed)
    groups={g:[r for r in pop if r['group']==g] for g in allocation}
    if sum(map(len,groups.values())) != len(pop):
        raise ValueError('allocation must cover every population stratum')
    means={g:st.mean(r['need_weekend'] for r in rng.sample(groups[g],n))
           for g,n in allocation.items()}
    return sum(len(groups[g])/len(pop)*means[g] for g in groups), means

def summary(estimates, truth):
    if len(estimates)<2: raise ValueError('need repeated samples')
    return {'mean':st.mean(estimates),'bias':st.mean(estimates)-truth,
            'SE':st.stdev(estimates),'RMSE':math.sqrt(st.mean((x-truth)**2 for x in estimates))}

def wilson(values,z=1.959963984540054):
    """Binomial score interval; approximate for low-fraction full-response SRS."""
    n=len(values)
    if not n or any(x not in (0,1) for x in values): raise ValueError('binary nonempty sample required')
    p=st.mean(values); d=1+z*z/n
    center=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0.,center-half),min(1.,center+half)

def wald(values,z=1.959963984540054):
    n=len(values)
    if not n: raise ValueError('empty sample')
    p=st.mean(values); h=z*math.sqrt(p*(1-p)/n)
    return p-h,p+h

def percentile(values,q):
    """Linear interpolation at (m-1)*q in the sorted m values."""
    a=sorted(values); i=(len(a)-1)*q; j=int(i)
    return a[j] if j==len(a)-1 else a[j]+(i-j)*(a[j+1]-a[j])

def bootstrap(values,seed=13,repetitions=399):
    """Optional iid row resampling demo, NOT a stratified survey interval."""
    if not values or repetitions<2: raise ValueError('nonempty sample and repetitions>=2 required')
    rng=random.Random(seed)
    means=[sum(rng.choices(values,k=len(values)))/len(values) for _ in range(repetitions)]
    return percentile(means,.025),percentile(means,.975)

def natural_frequencies(n,base,sensitivity,specificity):
    if n<0 or any(not 0<=p<=1 for p in (base,sensitivity,specificity)):
        raise ValueError('invalid probability or size')
    tp=n*base*sensitivity; fp=n*(1-base)*(1-specificity)
    return {'true_positive':tp,'false_positive':fp,'positive':tp+fp,
            'missed':n*base-tp,'positive_predictive_value':tp/(tp+fp) if tp+fp else None}

def capacity_loss(demand,capacity,unit_cost=2,shortage_cost=8):
    if min(demand,capacity,unit_cost,shortage_cost)<0: raise ValueError('negative input')
    return unit_cost*capacity+shortage_cost*max(0,demand-capacity)
