from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
frame=read("inference","population_frame.csv");answers={r["person_id"]:r for r in read("inference","voluntary_survey.csv")}
N=len(frame);rows=[];estimate=0;low=0;high=0
for h,rr in groups(frame,"stratum").items():
    obs=[dict(r,**answers[r["person_id"]]) for r in rr if r["person_id"] in answers]
    y=arr(obs,"satisfaction");mu=np.mean(y);n=len(obs);Nh=len(rr);weight=Nh/n;estimate+=Nh/N*mu
    # Pattern-mixture sensitivity: nonrespondents' stratum mean is respondent mean +/-10.
    low+=(n*mu+(Nh-n)*max(0,mu-10))/N;high+=(n*mu+(Nh-n)*min(100,mu+10))/N
    rows.append(dict(stratum=h,N=Nh,n=n,response_rate=n/Nh,respondent_mean=mu,weight=weight,frame_baseline=np.mean(arr(rr,"baseline_score")),response_baseline=np.mean(arr(obs,"baseline_score"))))
emit(dict(N=N,n=len(answers),unweighted=np.mean(arr(list(answers.values()),"satisfaction")),poststratified=estimate,nonresponse_sensitivity=[low,high],strata=rows))
