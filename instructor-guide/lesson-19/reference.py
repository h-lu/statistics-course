from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
rows=read("experiments","experiment_metrics.csv");plan={r["metric"]:r for r in read("experiments","metric_plan.csv")};results=[]
for metric,rr in groups(rows,"metric").items():
    team=[dict(arm=x[0]["assigned_arm"],value=np.mean(arr(x,"value"))) for x in groups(rr,"team").values()]
    out=difference(arr([x for x in team if x["arm"]=="tool"],"value"),arr([x for x in team if x["arm"]=="usual"],"value"));out.update(metric=metric,family=plan[metric]["family"],threshold=float(plan[metric]["practical_threshold"]));results.append(out)
# Both full-family alternatives displayed; the reporting family must be justified in advance.
order=sorted(range(len(results)),key=lambda i:results[i]["p"]);m=len(order);last=0
for rank,i in enumerate(order):
    last=max(last,min(1,(m-rank)*results[i]["p"]));results[i]["holm_all12"]=last
last=1
for rank in range(m-1,-1,-1):
    i=order[rank];last=min(last,results[i]["p"]*m/(rank+1));results[i]["bh_all12"]=last
emit(results)
