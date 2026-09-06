from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
rows,teams=trial_teams();blockdiff=[];sensitivity={}
for b,tt in groups(teams,"block").items():
    a=[t["change"] for t in tt if t["arm"]=="tool"];c=[t["change"] for t in tt if t["arm"]=="usual"];blockdiff.append(np.mean(a)-np.mean(c))
rng=np.random.default_rng(1601);observed=np.mean(blockdiff);perm=[]
for _ in range(6000):
    ds=[]
    for b,tt in groups(teams,"block").items():
        y=np.array([t["change"] for t in tt]);order=rng.permutation(6);ds.append(y[order[:3]].mean()-y[order[3:]].mean())
    perm.append(np.mean(ds))
for delta_tool in [-5,0,5]:
 for delta_usual in [-5,0,5]:
    values={}
    for arm,delta in [("tool",delta_tool),("usual",delta_usual)]:
        rr=[r for r in rows if r["assigned_arm"]==arm]
        values[arm]=np.mean([float(r["followup_minutes"])-float(r["baseline_minutes"]) if r["followup_minutes"] else delta for r in rr])
    sensitivity[f"tool:{delta_tool},usual:{delta_usual}"]=values["tool"]-values["usual"]
a=[t["change"] for t in teams if t["arm"]=="tool"];c=[t["change"] for t in teams if t["arm"]=="usual"]
emit(dict(arm_records={arm:dict(assigned=sum(r["assigned_arm"]==arm for r in rows),observed=sum(r["assigned_arm"]==arm and bool(r["followup_minutes"]) for r in rows),received=sum(r["assigned_arm"]==arm and r["received_tool"]=="1" for r in rows)) for arm in ["tool","usual"]},cluster_change_difference=difference(a,c),block_adjusted_observed_case_change=observed,randomization_p=(1+sum(abs(x)>=abs(observed) for x in perm))/(len(perm)+1),missing_change_by_arm_sensitivity=sensitivity,block_differences=blockdiff))
