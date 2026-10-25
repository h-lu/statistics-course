"""One chosen survey condition at a time. No automatic recommendation.

Uses the unchanged lesson-11 synthetic population. SRSWOR/full response only.
Wilson and ordinary percentile bootstrap are low-fraction approximations;
wald_fpc uses the design's finite-population correction. None is exact 95%.
"""
import csv, hashlib, json, math, random, statistics, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lesson-11'))
import sampling_tools as old

def save(p,x):
 Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def csvout(p,rows):
 with Path(p).open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def integer(x,name,low=1):
 if type(x)!=int or x<low:raise ValueError(name+' must be integer >= '+str(low))
 return x
def quantile(xs,q):
 s=sorted(xs);a=(len(s)-1)*q;i=int(a);return s[i]+(a-i)*(s[min(i+1,len(s)-1)]-s[i])
def interval(values,method='wilson',N=4000,rng=None,B=500):
 n=len(values)
 if n<2 or any(v not in (0,1) for v in values):raise ValueError('Need >=2 binary observations')
 p=sum(values)/n;z=1.959963984540054
 if n==N:return p,p
 if method=='wilson':
  d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
  return max(0.,c-r),min(1.,c+r)
 if method=='wald_fpc':
  # Unbiased sample variance for a binary variable, multiplied by (1-n/N)/n.
  se=math.sqrt((1-n/N)*p*(1-p)/(n-1));return max(0.,p-z*se),min(1.,p+z*se)
 if method=='bootstrap':
  integer(B,'bootstrap draws',100);rng=rng or random.Random(0)
  b=[sum(rng.choices(values,k=n))/n for _ in range(B)]
  return quantile(b,.025),quantile(b,.975)
 raise ValueError('method must be wilson, wald_fpc or bootstrap')
def _out(path):
 path=Path(path)
 if path.exists():raise ValueError('Use a new output directory; preserve old results')
 path.mkdir(parents=True);return path

def coverage(cfg,output):
 allowed={'n','repetitions','seed','method','bootstrap_draws','decision_threshold'}
 if set(cfg)-allowed:raise ValueError('Unknown fields')
 c={'n':80,'repetitions':500,'seed':1301,'method':'wilson','bootstrap_draws':500,'decision_threshold':.4,**cfg}
 n=integer(c['n'],'n',2);R=integer(c['repetitions'],'repetitions',2);seed=integer(c['seed'],'seed',0)
 pop=old._population();N=len(pop)
 if n>N:raise ValueError('n exceeds population')
 if c['method'] not in ['wilson','wald_fpc','bootstrap']:raise ValueError('Unknown method')
 if not 0<=c['decision_threshold']<=1:raise ValueError('Threshold outside [0,1]')
 truth=statistics.mean(r['need_weekend'] for r in pop);rows=[];first=None
 for j in range(R):
  selected=random.Random(seed+j).sample(pop,n);values=[r['need_weekend'] for r in selected]
  lo,hi=interval(values,c['method'],N,random.Random(seed+1000000+j),c['bootstrap_draws']);p=statistics.mean(values)
  action='support_above' if lo>c['decision_threshold'] else 'support_below' if hi<c['decision_threshold'] else 'uncertain'
  rows.append(dict(trial=j+1,selection_seed=seed+j,n=n,need=sum(values),estimate=p,lower=lo,upper=hi,width=hi-lo,covered=int(lo<=truth<=hi),decision=action))
  if j==0:first=[dict(person_id=r['person_id'],group=r['group'],observed_need=r['need_weekend']) for r in selected]
 out=_out(output);rate=statistics.mean(r['covered'] for r in rows)
 summary=dict(population_id=old.POPULATION_ID,synthetic=True,N=N,truth_for_audit_only=truth,method=c['method'],nominal_coverage=.95,observed_coverage=rate,coverage_mc_se=math.sqrt(rate*(1-rate)/R),average_width=statistics.mean(r['width'] for r in rows),first_trial=rows[0],repetitions=R,finite_population_note='Wilson/bootstrap approximate low sampling fraction; empirical coverage, not exact guarantee',population_sha256=old._sha((old.DATA/'simulator/weekend_population.csv').read_bytes()))
 save(out/'plan.json',c);save(out/'summary.json',summary);csvout(out/'trials.csv',rows);csvout(out/'first_sample.csv',first)
 return summary

def allocation(cfg,output):
 allowed={'n_A','n_B','repetitions','seed','budget'}
 if set(cfg)-allowed:raise ValueError('Unknown fields')
 c={'n_A':128,'n_B':32,'repetitions':500,'seed':1401,'budget':240,**cfg}
 pop=old._population();groups={g:[r for r in pop if r['group']==g] for g in ['A','B']};costs=old._costs();n={g:integer(c['n_'+g],'n_'+g,2) for g in groups};R=integer(c['repetitions'],'repetitions',2);seed=integer(c['seed'],'seed',0)
 for g in groups:
  if n[g]>len(groups[g]):raise ValueError('Allocation exceeds group')
 cost=sum(n[g]*costs[g] for g in groups)
 if not isinstance(c['budget'],(int,float)) or not math.isfinite(c['budget']) or cost>c['budget']:raise ValueError('Plan exceeds finite budget')
 W={g:len(groups[g])/len(pop) for g in groups};pg={g:statistics.mean(r['need_weekend'] for r in groups[g]) for g in groups};truth=sum(W[g]*pg[g] for g in groups)
 rows=[];first=[]
 for j in range(R):
  rng=random.Random(seed+j);sel={g:rng.sample(groups[g],n[g]) for g in groups};rates={g:statistics.mean(r['need_weekend'] for r in sel[g]) for g in groups}
  rows.append(dict(trial=j+1,seed=seed+j,n_A=n['A'],n_B=n['B'],estimate=W['A']*rates['A']+W['B']*rates['B'],B_estimate=rates['B'],pooled=(rates['A']*n['A']+rates['B']*n['B'])/sum(n.values()),cost=cost))
  if j==0:
   first=[dict(person_id=r['person_id'],group=g,observed_need=r['need_weekend'],inclusion_probability=n[g]/len(groups[g]),design_weight=len(groups[g])/n[g]) for g in groups for r in sel[g]]
 def stat(k,p):
  a=[r[k] for r in rows];return dict(mean=statistics.mean(a),bias=statistics.mean(a)-p,empirical_se=statistics.stdev(a))
 variance=sum(W[g]**2*pg[g]*(1-pg[g])/n[g]*(len(groups[g])-n[g])/(len(groups[g])-1) for g in groups)
 total=sum(n.values());srsvar=truth*(1-truth)/total*(len(pop)-total)/(len(pop)-1)
 summary=dict(population_id=old.POPULATION_ID,synthetic=True,truth_for_audit_only=truth,B_truth_for_audit_only=pg['B'],total=stat('estimate',truth),B=stat('B_estimate',pg['B']),pooled=stat('pooled',truth),design_se_exact=math.sqrt(variance),design_effect_same_n=variance/srsvar if srsvar else None,design_effect_comparator='SRSWOR with same total n, NOT same cost',cost=cost,cost_scope='Invitation costs only, full-response idealization; real followup must be separately budgeted',allocation={g:dict(N=len(groups[g]),n=n[g],population_weight=W[g],inclusion_probability=n[g]/len(groups[g]),design_weight=len(groups[g])/n[g],unit_cost=costs[g]) for g in groups},first_trial=rows[0],repetitions=R)
 out=_out(output);save(out/'plan.json',c);save(out/'summary.json',summary);csvout(out/'trials.csv',rows);csvout(out/'first_sample.csv',first);return summary
