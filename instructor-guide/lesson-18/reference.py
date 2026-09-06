from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
_,teams=trial_teams();sigma=float(np.sqrt(sum(np.sum((np.array([t["change"] for t in teams if t["arm"]==a])-np.mean([t["change"] for t in teams if t["arm"]==a]))**2) for a in ["tool","usual"])/(len(teams)-2)));rng=np.random.default_rng(1801);out=[]
for total in [12,20,24,40,60]:
    for effect in [1.5,3,4.5]:
        n=total//2;x=rng.normal(effect,sigma,size=(3000,n));y=rng.normal(0,sigma,size=(3000,n));p=stats.ttest_ind(x,y,axis=1,equal_var=False).pvalue
        cost=600+total*(100+20*18)
        out.append(dict(teams=total,people=20*total,true_ITT_improvement=effect,planning_team_sd=sigma,power=np.mean(p<.05),power_mcse=np.sqrt(np.mean(p<.05)*(1-np.mean(p<.05))/3000),cost=cost,within_budget=cost<=12000,approx_95_halfwidth=stats.t.ppf(.975,total-2)*sigma*np.sqrt(2/n)))
emit(out)
