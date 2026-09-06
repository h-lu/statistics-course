"""Regenerate explicitly synthetic experiment teaching data; fixed seeds."""
from pathlib import Path
import csv,random,math
ROOT=Path(__file__).resolve().parents[1]/"data"/"experiments"
def write(name,rows):
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    rng=random.Random(20260915); alloc_rng=random.Random(1501)
    roster=[];outcomes=[];metrics=[];assigned={}
    for b in range(4):
        teams=[f"T{b*6+k+1:02d}" for k in range(6)];alloc_rng.shuffle(teams)
        assigned.update({team:("tool" if k<3 else "usual") for k,team in enumerate(teams)})
    metric_plan=[("handling_minutes","primary","lower",3),("error_rate","safety","lower",.02),("quality_score","safety","higher",3),("weekly_output","exploratory","higher",3),("fatigue_score","exploratory","lower",3),("satisfaction","exploratory","higher",4),("training_minutes","exploratory","lower",5),("handoff_count","exploratory","lower",1),("rework_minutes","exploratory","lower",2),("escalations","exploratory","lower",1),("confidence_score","exploratory","higher",4),("workload_score","exploratory","lower",3)]
    for t in range(24):
        team=f"T{t+1:02d}";block=f"B{t//6+1}";arm=assigned[team]
        team_base=rng.gauss(0,6);team_follow=rng.gauss(0,3);team_metric=[rng.gauss(0,2) for _ in metric_plan]
        for j in range(20):
            uid=f"E{t+1:02d}-{j+1:02d}";baseline=58+team_base+rng.gauss(0,7); workload=round(rng.uniform(.6,1.5),3)
            roster.append(dict(person_id=uid,team=team,block=block,baseline_minutes=round(baseline,3),workload=workload))
            received=int(rng.random()<(.83 if arm=="tool" else .06))
            observed=int(rng.random()>(.05+.07*(workload>1.15)+(.025 if arm=="tool" else 0)))
            y=baseline+team_follow-5.2*received+rng.gauss(0,4)
            outcomes.append(dict(person_id=uid,assigned_arm=arm,received_tool=received,followup_observed=observed,followup_minutes=round(y,3) if observed else "",implementation_cost=8 if arm=="tool" else 0))
            vals=[y,.08-.007*received+rng.gauss(0,.03),76+2.5*received+rng.gauss(0,7),32+2.8*received+rng.gauss(0,7),52-1.5*received+rng.gauss(0,8),65+1*received+rng.gauss(0,9),20+6*received+rng.gauss(0,6),6+rng.gauss(0,1.5),10-1*received+rng.gauss(0,4),4+rng.gauss(0,1),62+2*received+rng.gauss(0,8),50+rng.gauss(0,8)]
            for k,(metric,family,direction,threshold) in enumerate(metric_plan):
                value=vals[k]+(team_metric[k] if k not in [0,1] else 0)
                if metric=="error_rate":value=max(0,min(1,value))
                elif metric in ["weekly_output","handoff_count","escalations"]:value=max(0,round(value))
                elif metric.endswith("score") or metric=="satisfaction":value=max(0,min(100,value))
                else:value=max(0,value)
                metrics.append(dict(person_id=uid,team=team,assigned_arm=arm,metric=metric,value=round(value,5)))
    write("experiment_roster.csv",roster);write("experiment_outcomes.csv",outcomes);write("experiment_metrics.csv",metrics)
    write("metric_plan.csv",[dict(metric=m,family=f,desirable_direction=d,practical_threshold=v) for m,f,d,v in metric_plan])
    paired=[]
    for i in range(60):
        seq="AB" if i%2==0 else "BA";person=rng.gauss(50,14)
        for period,method in enumerate(seq,1):
            value=person+(2 if period==2 else 0)+(-3.5 if method=="B" else 0)+rng.gauss(0,3)
            paired.append(dict(person_id=f"X{i+1:03d}",sequence=seq,period=period,method=method,minutes=round(value,3)))
    write("paired_study.csv",paired)
    independent=[]
    for i in range(100):
        arm="B" if i%2 else "A";independent.append(dict(person_id=f"I{i+1:03d}",arm=arm,minutes=round(rng.gauss(50-(3.5 if arm=="B" else 0),14),3)))
    write("independent_comparison.csv",independent)
    repeated=[]
    for i in range(48):
        arm="tool" if i%2 else "usual";u=rng.gauss(0,8)
        for week in range(1,7):
            repeated.append(dict(person_id=f"R{i+1:03d}",arm=arm,week=week,minutes=round(60+u-.8*week-(2+week*.3 if arm=="tool" else 0)+rng.gauss(0,2),3)))
    write("repeated_measurements.csv",repeated)
    write("experiment_costs.csv",[dict(item=k,value=v,unit=u) for k,v,u in [("fixed_setup",600,"currency"),("per_participant",18,"currency"),("per_team",100,"currency"),("team_size",20,"people"),("budget",12000,"currency"),("minimum_worthwhile_effect",3,"minutes"),("minute_value",2,"currency/minute")]])
    daily=[]
    for day in range(1,31):
        for arm in ["usual","tool"]:
            n=40;observed=0;conversions=0
            for _ in range(n):
                y=int(rng.random()<(.30+.04*math.sin(day/5)+(.045 if arm=="tool" else 0)))
                response=rng.random()>(.025+(.025 if arm=="tool" else 0)+(.025 if not y else 0))
                if response:observed+=1;conversions+=y
            daily.append(dict(day=day,arm=arm,n_assigned=n,n_observed=observed,conversions=conversions))
    write("daily_experiment.csv",daily)
    print("Generated experiments synthetic data:",ROOT)
if __name__=="__main__":main()
