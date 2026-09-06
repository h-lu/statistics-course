from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
rng=np.random.default_rng(1201);out=[]
for scene,rr in groups(read("inference","estimation_populations.csv"),"scenario").items():
    population=arr(rr,"cost");truth=np.mean(population)
    for n in [20,80,320]:
        # Sampling with replacement defines the empirical population experiment.
        x=rng.choice(population,size=(1500,n),replace=True);means=x.mean(axis=1);se=x.std(axis=1,ddof=1)/np.sqrt(n);q=stats.t.ppf(.975,n-1)
        medians=np.median(x,axis=1);coverage=np.mean((means-q*se<=truth)&(truth<=means+q*se))
        out.append(dict(scenario=scene,n=n,population_mean=truth,population_median=np.median(population),mean_bias=np.mean(means)-truth,mean_rmse=np.sqrt(np.mean((means-truth)**2)),sampling_sd=np.std(means,ddof=1),mean_reported_se=np.mean(se),t_interval_coverage=coverage,median_bias_for_mean_target=np.mean(medians)-truth,coverage_mcse=np.sqrt(coverage*(1-coverage)/1500)))
emit(out)
