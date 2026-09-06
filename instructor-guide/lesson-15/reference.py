from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
roster=read("experiments","experiment_roster.csv")
import random
rng=random.Random(1501);assign={}
for block in sorted(set(r["block"] for r in roster)):
    teams=sorted(set(r["team"] for r in roster if r["block"]==block));rng.shuffle(teams)
    assign.update({t:"tool" if i<3 else "usual" for i,t in enumerate(teams)})
byarm={}
for arm in ["tool","usual"]:
    rr=[r for r in roster if assign[r["team"]]==arm]
    byarm[arm]=dict(people=len(rr),teams=len(set(r["team"] for r in rr)),baseline_mean=np.mean(arr(rr,"baseline_minutes")),workload_mean=np.mean(arr(rr,"workload")))
emit(dict(seed=1501,randomization_unit="team",assignments=assign,balance=byarm,primary_estimand="all assigned participants' mean follow-up minutes, tool minus usual; missing outcomes require assumptions"))
