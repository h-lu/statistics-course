"""Shared numerical helpers for L09-20 teacher reference routes (NumPy/SciPy)."""
from pathlib import Path
import sys,csv,json,math
from collections import defaultdict
import numpy as np
from scipy import stats
def student_root():
    return Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/"lesson-01-first-green"
def read(world,name):
    with (student_root()/"data"/world/name).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def groups(rows,key):
    out=defaultdict(list)
    for r in rows:out[r[key]].append(r)
    return out
def arr(rows,key):return np.array([float(r[key]) for r in rows],dtype=float)
def ci_mean(x):
    x=np.asarray(x);se=np.std(x,ddof=1)/np.sqrt(len(x));q=stats.t.ppf(.975,len(x)-1)
    return dict(n=len(x),estimate=float(np.mean(x)),se=float(se),low=float(np.mean(x)-q*se),high=float(np.mean(x)+q*se))
def difference(a,b):
    a=np.asarray(a);b=np.asarray(b);va=np.var(a,ddof=1)/len(a);vb=np.var(b,ddof=1)/len(b);se=np.sqrt(va+vb)
    df=(va+vb)**2/(va*va/(len(a)-1)+vb*vb/(len(b)-1))
    d=np.mean(a)-np.mean(b);q=stats.t.ppf(.975,df);p=2*stats.t.sf(abs(d/se),df)
    return dict(effect=float(d),se=float(se),df=float(df),low=float(d-q*se),high=float(d+q*se),p=float(p))
def emit(value):
    print(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,"item") else str(x)))
def trial_teams():
    roster={r["person_id"]:r for r in read("experiments","experiment_roster.csv")}
    rows=[dict(roster[r["person_id"]],**r) for r in read("experiments","experiment_outcomes.csv")]
    teams=[]
    for team,rr in groups(rows,"team").items():
        obs=[r for r in rr if r["followup_minutes"]!=""]
        teams.append(dict(team=team,block=rr[0]["block"],arm=rr[0]["assigned_arm"],n=len(rr),observed=len(obs),mean=np.mean(arr(obs,"followup_minutes")),baseline=np.mean(arr(rr,"baseline_minutes")),change=np.mean([float(r["followup_minutes"])-float(r["baseline_minutes"]) for r in obs])))
    return rows,teams
