from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
rng=np.random.default_rng(1401);frame=read("inference","population_frame.csv");answers={r["person_id"]:r for r in read("inference","voluntary_survey.csv")};costs=read("inference","sampling_costs.csv")
strata=[]
for c in costs:
    rr=[r for r in frame if r["stratum"]==c["stratum"]];y=np.array([float(answers[r["person_id"]]["satisfaction"]) for r in rr if r["person_id"] in answers])
    strata.append(dict(stratum=c["stratum"],N=len(rr),S=float(np.std(y,ddof=1)),r=float(c["expected_response_rate"]),c=float(c["contact_cost"]),minimum=int(c["min_completed"]),frame=rr))
out=[];selected_rows=[]
for budget in [4500,6000,7500]:
    # Greedy marginal variance reduction under contact cost; expected responding n=r*m.
    m={h["stratum"]:min(h["N"],math.ceil(h["minimum"]/h["r"])) for h in strata}
    cost=sum(h["c"]*m[h["stratum"]] for h in strata)
    while True:
        candidates=[h for h in strata if m[h["stratum"]]<h["N"] and cost+h["c"]<=budget]
        if not candidates:break
        h=max(candidates,key=lambda h:(h["N"]/3600)**2*h["S"]**2/h["r"]*(1/m[h["stratum"]]-1/(m[h["stratum"]]+1))/h["c"])
        m[h["stratum"]]+=1;cost+=h["c"]
    variance=sum((h["N"]/3600)**2*h["S"]**2*(1/(m[h["stratum"]]*h["r"])-1/h["N"]) for h in strata)
    allocation=[]
    for h in strata:
        ids=sorted(rng.choice([r["person_id"] for r in h["frame"]],size=m[h["stratum"]],replace=False).tolist())
        pi=m[h["stratum"]]/h["N"]
        allocation.append(dict(stratum=h["stratum"],contacts=len(ids),expected_completed=len(ids)*h["r"],inclusion_probability=pi,sample_preview=ids[:3]))
        selected_rows.extend(dict(budget=budget,stratum=h["stratum"],person_id=i,inclusion_probability=pi,design_weight=1/pi) for i in ids)
    out.append(dict(budget=budget,cost=cost,approx_margin=1.96*np.sqrt(variance),sd_up_30pct_margin=1.3*1.96*np.sqrt(variance),allocation=allocation))
with Path(__file__).with_name("reference_selected.csv").open("w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(selected_rows[0]));w.writeheader();w.writerows(selected_rows)
emit(out)
