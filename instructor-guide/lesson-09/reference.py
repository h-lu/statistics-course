from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
g=read("inference","screening_groups.csv");v={(r["group"],r["test"]):r for r in read("inference","screening_validation.csv")}
results=[]
for ratekey in ["base_rate_low","base_rate","base_rate_high"]:
 for name,choice in [("all_rapid",lambda group:"rapid"),("mixed",lambda group:"rapid" if group=="routine" else "precise"),("all_precise",lambda group:"precise")]:
    candidates=[];testcost=0
    for r in g:
        vv=v[(r["group"],choice(r["group"]))];n=float(r["daily_volume"]);p=float(r[ratekey])
        se=float(vv["true_positive_n"])/float(vv["condition_positive_n"]);sp=float(vv["true_negative_n"])/float(vv["condition_negative_n"])
        tp=n*p*se;fp=n*(1-p)*(1-sp);ppv=tp/(tp+fp);testcost+=n*float(vv["test_cost"])
        candidates.append(dict(group=r["group"],positive=tp+fp,tp=tp,fp=fp,cases=n*p,ppv=ppv,loss=float(r["missed_case_loss"]),priority=(ppv*float(r["missed_case_loss"])-(1-ppv)*2)/12))
    capacity=120;loss=testcost;rows=[]
    for c in sorted(candidates,key=lambda x:-x["priority"]):
        reviewed=min(capacity,c["positive"]);capacity-=reviewed;share=reviewed/c["positive"]
        missed=c["cases"]-c["tp"]*share;fp_review=c["fp"]*share;loss+=missed*c["loss"]+fp_review*2
        rows.append(dict(group=c["group"],ppv=c["ppv"],expected_positive=c["positive"],reviewed=reviewed,expected_missed=missed))
    results.append(dict(base_rate_scenario=ratekey,policy=name,screening_cost=testcost,budget_feasible=testcost<=4500,expected_total_loss=loss,groups=rows))
emit(results)
