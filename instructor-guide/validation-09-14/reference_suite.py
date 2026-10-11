"""Teacher-only candidate analyses. No student policy is preselected by this file.
Run from repository root: python3 instructor-guide/validation-09-14/reference_suite.py
"""
from pathlib import Path
import sys
import random
import statistics as st
import math
import json
import itertools

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'student-template/data/inference-09-14'))
import toolkit as t


def l09():
    groups=t.table('alert_groups.csv'); methods={r['method']:r for r in t.table('screening.csv')}
    outcomes=[]
    for method_names in itertools.product(methods,repeat=2):
        screen_cost=sum(int(g['daily_devices'])*float(methods[m]['cost_per_device']) for g,m in zip(groups,method_names))
        if screen_cost>2000: continue
        for rule in ('expected_loss','reserve_routine30'):
            for scenario in ('base_low','base','base_high'):
                cells=[]
                for g,m in zip(groups,method_names):
                    n=int(g['daily_devices']); p=float(g[scenario]); method=methods[m]
                    cells.append({**t.natural_frequencies(n,p,float(method['sensitivity']),float(method['specificity'])),
                                  'group':g['group'],'faults':n*p,'miss_cost':float(g['miss_cost'])})
                review=[0,0]
                if rule=='reserve_routine30': review[0]=min(30,math.floor(cells[0]['positive']))
                remaining=90-sum(review)
                for i in sorted(range(2),key=lambda i:cells[i]['positive_predictive_value']*cells[i]['miss_cost'],reverse=True):
                    extra=min(remaining,max(0,math.floor(cells[i]['positive'])-review[i]))
                    review[i]+=extra; remaining-=extra
                for c,r in zip(cells,review):
                    c['reviewed']=r
                    c['undetected_faults']=c['faults']-r*c['positive_predictive_value']
                loss=sum(c['undetected_faults']*c['miss_cost'] for c in cells)
                outcomes.append({'methods':method_names,'rule':rule,'scenario':scenario,'screen_cost':screen_cost,
                                 'review_cost':3*sum(review),'miss_loss':loss,'total_cost':screen_cost+3*sum(review)+loss,
                                 'groups':cells})
    return outcomes


def l10():
    result=[]
    for scenario in ('base','stress'):
        rows=[r for r in t.table('demand.csv') if r['scenario']==scenario]
        ds=[int(r['demand']) for r in rows]; ps=[float(r['probability']) for r in rows]
        rng=random.Random(100); days=rng.choices(ds,weights=ps,k=10000)
        for shortage_cost in (8,12,20):
            for capacity in (60,80,90,120):
                losses=[t.capacity_loss(d,capacity,shortage_cost=shortage_cost) for d in days]
                shortages=[max(0,d-capacity) for d in days]
                result.append({'scenario':scenario,'capacity':capacity,'shortage_cost':shortage_cost,
                    'mean_demand':sum(d*p for d,p in zip(ds,ps)),
                    'expected_cost':sum(t.capacity_loss(d,capacity,shortage_cost=shortage_cost)*p for d,p in zip(ds,ps)),
                    'shortage_probability':sum(p for d,p in zip(ds,ps) if d>capacity),
                    'simulated_cost':st.mean(losses),'simulated_shortage_probability':st.mean(d>capacity for d in days),
                    'shortage_p95_linear':t.percentile(shortages,.95),'maximum_possible_shortage':max(0,max(ds)-capacity)})
    return result


def l11(pop):
    truth=st.mean(r['need_weekend'] for r in pop)
    results=[]
    for mode,response in [('srs','complete'),('srs','ordinary'),('volunteer','complete')]:
        unweighted=[]; weighted=[]; count=[]; one=None
        for seed in range(200):
            rows=t.acquire(pop,200,11000+seed,mode,response)
            vals=t.observed(rows)
            if not vals: raise AssertionError('no answers')
            unweighted.append(st.mean(vals)); weighted.append(t.poststratified(rows)); count.append(len(vals))
            if seed==0:
                one={'invited':sum(r['invited'] for r in rows),'answered':len(vals),
                     'respondents_B':sum(r['answered'] and r['group']=='B' for r in rows),
                     'unweighted':unweighted[-1],'adjusted':weighted[-1]}
        results.append({'mode':mode,'response':response,'invited':200,'repetitions':200,
                        'mean_answers':st.mean(count),'one_sample':one,
                        'unweighted':t.summary(unweighted,truth),'composition_adjusted':t.summary(weighted,truth)})
    return results


def l12(pop):
    truth=st.mean(r['need_weekend'] for r in pop); vals=[r['need_weekend'] for r in pop]
    results=[]
    for n in (80,200,800):
        rng=random.Random(12000+n)
        estimates=[st.mean(rng.sample(vals,n)) for _ in range(2000)]
        # Independent design benchmark: population variance with denominator N-1.
        exact_se=math.sqrt((1-n/len(vals))*st.variance(vals)/n)
        results.append({'n':n,'repetitions':2000,'exact_design_SE':exact_se,**t.summary(estimates,truth)})
    return results


def coverage(vals,n,repetitions=600,seed=13000,include_bootstrap=False):
    truth=st.mean(vals); rng=random.Random(seed)
    methods={'wilson':t.wilson,'wald':t.wald}
    storage={name:[] for name in methods}
    if include_bootstrap: storage['bootstrap']=[]
    for k in range(repetitions):
        sample=rng.sample(vals,n)
        for name,fun in methods.items(): storage[name].append(fun(sample))
        if include_bootstrap: storage['bootstrap'].append(t.bootstrap(sample,seed+k,199))
    return [{'method':name,'n':n,'R':repetitions,'truth':truth,
             'coverage':st.mean(lo<=truth<=hi for lo,hi in intervals),
             'mean_width':st.mean(hi-lo for lo,hi in intervals),
             'coverage_MC_SE':math.sqrt((c:=st.mean(lo<=truth<=hi for lo,hi in intervals))*(1-c)/repetitions)}
            for name,intervals in storage.items()]


def l13(pop):
    vals=[r['need_weekend'] for r in pop]
    result=[]
    for n in (80,200): result.extend(coverage(vals,n,include_bootstrap=True))
    # Boundary stress population is explicitly separate, not a changed main estimand.
    result.extend([{**r,'case':'separate_rare_event_population'} for r in coverage([1]*40+[0]*3960,4,include_bootstrap=True)])
    sample=random.Random(1313).sample(vals,200)
    return {'main_and_boundary_coverage':result,'one_main_sample':{'estimate':st.mean(sample),'wilson':t.wilson(sample),'n':200},
            'four_ones':{'bootstrap':t.bootstrap([1]*4),'wilson':t.wilson([1]*4)},
            'note':'Bootstrap B=199 is a bounded optional demonstration; coverage is Monte Carlo evidence, not a guarantee.'}


def l14(pop):
    truth=st.mean(r['need_weekend'] for r in pop)
    btruth=st.mean(r['need_weekend'] for r in pop if r['group']=='B')
    results=[]
    for budget,allocation in [(240,{'A':168,'B':24}),(240,{'A':136,'B':34}),(240,{'A':96,'B':48}),
                              (180,{'A':100,'B':25}),(180,{'A':72,'B':36})]:
        overall=[]; b=[]
        for seed in range(1500):
            estimate,means=t.stratified(pop,allocation,14000+seed)
            overall.append(estimate); b.append(means['B'])
        cost=allocation['A']+3*allocation['B']
        # exact finite-population SRS variance verifies the simulation; not a required student formula
        variance=sum((sum(r['group']==g for r in pop)/len(pop))**2 *
                     (1-allocation[g]/sum(r['group']==g for r in pop))*
                     st.variance([r['need_weekend'] for r in pop if r['group']==g])/allocation[g]
                     for g in allocation)
        results.append({'budget':budget,'allocation':allocation,'cost':cost,'overall':t.summary(overall,truth),
                        'B':t.summary(b,btruth),'exact_overall_SE':math.sqrt(variance),
                        'weights':{g:sum(r['group']==g for r in pop)/n for g,n in allocation.items()}})
    return results


def run():
    pop=t.population()
    return {'data':'teaching synthetic; fixed 4000-person population','truth':st.mean(r['need_weekend'] for r in pop),
            '09':l09(),'10':l10(),'11':l11(pop),'12':l12(pop),'13':l13(pop),'14':l14(pop)}

if __name__=='__main__':
    result=run()
    dest=Path(__file__).with_name('reference_results.json')
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(dest)
