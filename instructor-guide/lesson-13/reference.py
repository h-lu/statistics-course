from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
rng=np.random.default_rng(1301);sample=arr(read("inference","decision_sample.csv"),"cost");population=arr([r for r in read("inference","estimation_populations.csv") if r["scenario"]=="long_tail"],"cost")
boot=rng.choice(sample,size=(6000,len(sample)),replace=True).mean(axis=1);ci=ci_mean(sample)
coverage={"t":0,"percentile":0};truth=np.mean(population);reps=400
for _ in range(reps):
    x=rng.choice(population,len(sample),replace=False);tci=ci_mean(x);bs=rng.choice(x,size=(600,len(x)),replace=True).mean(axis=1);lo,hi=np.quantile(bs,[.025,.975])
    coverage["t"]+=int(tci["low"]<=truth<=tci["high"]);coverage["percentile"]+=int(lo<=truth<=hi)
emit(dict(sample=ci,bootstrap_percentile=np.quantile(boot,[.025,.975]).tolist(),action_threshold=45,population_benchmark=truth,simulation_replicates=reps,coverage={k:v/reps for k,v in coverage.items()},coverage_mcse_upper=1/(2*np.sqrt(reps))))
