from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
daily=read("experiments","daily_experiment.csv");history=[];totals={a:dict(n=0,obs=0,y=0) for a in ["tool","usual"]}
def z_p(y1,n1,y0,n0):
    pooled=(y1+y0)/(n1+n0);se=np.sqrt(pooled*(1-pooled)*(1/n1+1/n0));return 1.0 if se==0 else float(2*stats.norm.sf(abs((y1/n1-y0/n0)/se)))
for day in range(1,31):
    for r in daily:
        if int(r["day"])==day:
            t=totals[r["arm"]];t["n"]+=int(r["n_assigned"]);t["obs"]+=int(r["n_observed"]);t["y"]+=int(r["conversions"])
    a=totals["tool"];b=totals["usual"]
    history.append(dict(day=day,confirmed_difference=a["y"]/a["n"]-b["y"]/b["n"],confirmed_p=z_p(a["y"],a["n"],b["y"],b["n"]),complete_case_difference=a["y"]/a["obs"]-b["y"]/b["obs"]))
rng=np.random.default_rng(2001);reps=5000;x=np.cumsum(rng.binomial(40,.3,size=(reps,30)),axis=1);y=np.cumsum(rng.binomial(40,.3,size=(reps,30)),axis=1);n=np.arange(1,31)*40;p=(x+y)/(2*n);se=np.sqrt(p*(1-p)*2/n);pv=2*stats.norm.sf(np.abs((x/n-y/n)/se))
a=totals["tool"];b=totals["usual"];low=a["y"]/a["n"]-(b["y"]+b["n"]-b["obs"])/b["n"];high=(a["y"]+a["n"]-a["obs"])/a["n"]-b["y"]/b["n"]
emit(dict(actual_looks=[h for h in history if h["day"] in [10,20,30]],naive_first_crossing=next((h["day"] for h in history if h["confirmed_p"]<.05),None),planned_three_look_first_crossing=next((h["day"] for h in history if h["day"] in [10,20,30] and h["confirmed_p"]<.05/3),None),unobserved_outcome_worst_case_bounds=[low,high],totals=totals,null_simulation=dict(reps=reps,naive_any_day=np.mean(np.any(pv<.05,axis=1)),fixed_day30=np.mean(pv[:,-1]<.05),three_bonferroni_looks=np.mean(np.any(pv[:,[9,19,29]]<.05/3,axis=1)))))
