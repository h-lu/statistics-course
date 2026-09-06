"""Regenerate explicitly synthetic inference teaching data; fixed seeds, standard library."""
from pathlib import Path
import csv, random, math
ROOT=Path(__file__).resolve().parents[1]/"data"/"inference"
def write(name, rows):
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    rng=random.Random(20260909)
    groups=[]
    for name,volume,rate,lo,hi,loss in [("routine",1200,.01,.005,.02,60),("referred",600,.04,.02,.07,80),("priority",200,.14,.08,.22,120)]:
        groups.append(dict(group=name,daily_volume=volume,base_rate=rate,base_rate_low=lo,base_rate_high=hi,review_minutes=12,missed_case_loss=loss,unnecessary_review_loss=2))
    write("screening_groups.csv",groups)
    rows=[]
    for g in groups:
        for test,se,sp,cost in [("rapid",.90,.94,1),("precise",.86,.985,4)]:
            rows.append(dict(group=g["group"],test=test,condition_positive_n=200,true_positive_n=round(se*200),condition_negative_n=1000,true_negative_n=round(sp*1000),test_cost=cost))
    write("screening_validation.csv",rows)
    rows=[]
    for d in range(168):
        weekday=d%7; event=int(d%23 in [4,5]); rain=int(rng.random()<.22)
        mean=145+([15,8,2,0,12,-25,-32][weekday])+event*60+rain*18
        demand=max(0,round(rng.gauss(mean,18)+(rng.expovariate(1/40) if rng.random()<.1 else 0)))
        rows.append(dict(day=d+1,weekday=weekday,event=event,rain=rain,requests=demand,split="history" if d<126 else "holdout"))
    write("demand_history.csv",rows)
    write("capacity_options.csv",[dict(plan=f"C{c}",capacity=c,daily_fixed_cost=c*3,unused_unit_cost=.4,unserved_unit_loss=24) for c in [140,170,200,230]])
    frame=[];survey=[];costs=[];population_counts=[500,700,600,800,550,450]
    for h,n in enumerate(population_counts):
        campus=["north","central","south"][h//2]; year="early" if h%2==0 else "late"; stratum=f"{campus}_{year}"
        contactcost=[3,4,5,6,4,7][h]; propensity=[.62,.35,.5,.28,.42,.2][h]
        costs.append(dict(stratum=stratum,population_n=n,contact_cost=contactcost,expected_response_rate=propensity,min_completed=15))
        for j in range(n):
            uid=f"P{h+1}-{j+1:04d}";baseline=max(5,min(95,rng.gauss(64-h*3,12)))
            sat=max(0,min(100,baseline+rng.gauss(0,10)-h*1.8))
            # Selection remains related to unobserved satisfaction within each published stratum.
            responded=int(rng.random()<max(.04,min(.95,propensity+(sat-55)*.006)))
            frame.append(dict(person_id=uid,campus=campus,stage=year,stratum=stratum,baseline_score=round(baseline,2),responded=responded))
            if responded:survey.append(dict(person_id=uid,satisfaction=round(sat,2),weekly_use=max(0,round(rng.gauss(4,2),1))))
    write("population_frame.csv",frame);write("voluntary_survey.csv",survey);write("sampling_costs.csv",costs)
    rows=[]
    for scenario in ["symmetric","long_tail","rare_cost"]:
        for i in range(6000):
            value=rng.gauss(40,10) if scenario=="symmetric" else (rng.lognormvariate(3.5,.85) if scenario=="long_tail" else (rng.gauss(180,20) if rng.random()<.05 else rng.gauss(20,3)))
            rows.append(dict(unit_id=f"{scenario}-{i+1:04d}",scenario=scenario,cost=round(max(0,value),4)))
    write("estimation_populations.csv",rows)
    selected=rng.sample([r for r in rows if r["scenario"]=="long_tail"],80)
    write("decision_sample.csv",[dict(sample_id=f"S{i+1:03d}",source_id=r["unit_id"],cost=r["cost"]) for i,r in enumerate(selected)])
    print("Generated inference synthetic data:",ROOT)
if __name__=="__main__": main()
