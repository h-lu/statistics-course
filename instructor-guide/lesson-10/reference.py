from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
rows=read("inference","demand_history.csv");plans=read("inference","capacity_options.csv")
out=[];rng=np.random.default_rng(1001)
for scene,rr in [("history",[r for r in rows if r["split"]=="history"]),("event_history",[r for r in rows if r["split"]=="history" and r["event"]=="1"]),("holdout",[r for r in rows if r["split"]=="holdout"])]:
    y=arr(rr,"requests");sim_y=rng.choice(y,10000,replace=True) if scene!="holdout" else None
    results=[]
    for plan in plans:
        c=float(plan["capacity"]);loss=float(plan["daily_fixed_cost"])+float(plan["unused_unit_cost"])*np.maximum(c-y,0)+float(plan["unserved_unit_loss"])*np.maximum(y-c,0)
        result=dict(plan=plan["plan"],mean_loss=np.mean(loss),overflow_probability=np.mean(y>c),mean_unserved=np.mean(np.maximum(y-c,0)),loss_p90=np.quantile(loss,.9))
        if sim_y is not None:
            simulated=float(plan["daily_fixed_cost"])+float(plan["unused_unit_cost"])*np.maximum(c-sim_y,0)+float(plan["unserved_unit_loss"])*np.maximum(sim_y-c,0)
            result.update(mc_mean_loss=np.mean(simulated),mc_standard_error=np.std(simulated,ddof=1)/np.sqrt(len(simulated)),mc_repetitions=len(simulated))
        results.append(result)
    out.append(dict(scenario=scene,n=len(y),mean=np.mean(y),variance=np.var(y,ddof=1),plans=results))
emit(out)
