"""Generate synthetic observational, panel, forecasting and decision data."""
from pathlib import Path
import csv, math, random
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"data"/"policy";SEED=2026090527
def write(name,rows):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    OUT.mkdir(parents=True,exist_ok=True);r=random.Random(SEED);obs=[]
    for i in range(1400):
        severity=r.uniform(0,10);baseline=40+3*severity+r.gauss(0,8)
        access=int(r.random()<.6);age=r.uniform(20,70);motivation=r.gauss(0,1)
        z=-3+.65*severity+1.2*access+.5*motivation
        support=int(r.random()<1/(1+math.exp(-z)))
        outcome=baseline+2*severity-4*support-1.2*motivation+r.gauss(0,7)
        mediator=2+.8*support+.2*motivation+r.gauss(0,.4)
        followup=int(r.random()<1/(1+math.exp(-(.8+.5*support-.15*(outcome-55)))))
        obs.append(dict(person_id=f"P{i:04d}",severity=round(severity,2),baseline_burden=round(baseline,2),
            access=access,age=round(age,1),support=support,followup_burden=round(outcome,2),
            contact_after=round(mediator,2),responded_after=followup))
    write("support_observational.csv",obs)
    panel=[]
    for district in range(24):
        treated=int(district<8);near=int(8<=district<16);level=r.gauss(50,5)
        serial=0
        for month in range(36):
            post=month>=18;serial=.55*serial+r.gauss(0,1.5)
            seasonal=3*math.sin(2*math.pi*month/12)
            y=level+.18*month+seasonal+serial
            if treated and post:y-=4
            if near and post:y-=1.2
            panel.append(dict(district=f"D{district:02d}",month=month,
                group="treated" if treated else "near_control" if near else "far_control",
                policy_active=int(treated and post),outcome=round(y,3),population=1000+district*30))
    write("district_panel.csv",panel)
    demand=[];serial=0
    for week in range(156):
        holiday=int(week%52 in (0,1,50,51));serial=.6*serial+r.gauss(0,9)
        mean=170+.5*week+30*math.sin(2*math.pi*week/52)+22*holiday+(25 if week>=130 else 0)
        demand.append(dict(week=week,demand=max(0,round(mean+serial)),holiday_known=holiday,
            available_capacity=230 if week<130 else 245))
    write("weekly_demand.csv",demand)
    write("decision_options.csv",[
       dict(action="wait",state="low",loss=0),dict(action="wait",state="high",loss=160),
       dict(action="pilot",state="low",loss=25),dict(action="pilot",state="high",loss=65),
       dict(action="rollout",state="low",loss=90),dict(action="rollout",state="high",loss=15)])
    write("pilot_test.csv",[
       dict(state="low",prior_probability=.65,positive_probability=.20),
       dict(state="high",prior_probability=.35,positive_probability=.80)])
    print(f"policy: {len(obs)} observational, {len(panel)} panel, {len(demand)} weekly rows; seed={SEED}")
if __name__=="__main__":main()

