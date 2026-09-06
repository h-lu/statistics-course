"""Shared auditable V2 reference computations, not a unique student solution.
Run each lesson's reference.py --student-root /path/to/course-student-template.
Requires numpy and scipy. Nothing in this module changes student sources/data.
"""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata,t
def read(root,world,name):
    with (root/"data"/world/name).open(encoding="utf-8") as f:return list(csv.DictReader(f))
def nums(rows,key):return np.array([float(r[key]) for r in rows])
def design(rows,kind="base"):
    x=[]
    for r in rows:
        b=float(r["backlog"])/10;w=float(r["workload"])/10;c=int(r["complexity"]=="complex")
        east=int(r["region"]=="east");west=int(r["region"]=="west")
        v=[1,b,w,c,float(r["prior_failures"]),float(r["age_years"])/10,east,west]
        if kind in ("interaction","rich","collinear"):v+=[b*west,b*b]
        if kind=="collinear":v+=[float(r["staffing_index"])/10]
        if kind=="cheap":v=[1,b,c,float(r["prior_failures"]),float(r["age_years"])/10,east,west]
        x.append(v)
    return np.array(x,float)
def fit(x,y,alpha=0):
    penalty=np.eye(x.shape[1])*alpha;penalty[0,0]=0
    return np.linalg.pinv(x.T@x+penalty)@x.T@y
def logistic(x,y,alpha=.2):
    penalty=np.ones(x.shape[1]);penalty[0]=0
    def fun(b):
        z=x@b
        loss=np.logaddexp(0,z).sum()-y@z+alpha*np.sum(penalty*b*b)/2
        grad=x.T@(expit(z)-y)+alpha*penalty*b
        return loss,grad
    result=minimize(fun,np.zeros(x.shape[1]),jac=True,method="BFGS",options={"gtol":1e-6,"maxiter":500})
    if np.linalg.norm(result.jac)>1e-3:raise RuntimeError(f"logistic convergence: {result.message}")
    return result.x
def mse(y,p):return float(np.mean((y-p)**2))
def mae(y,p):return float(np.mean(abs(y-p)))
def auc(y,p):
    n1=y.sum();n0=len(y)-n1
    return float((rankdata(p)[y==1].sum()-n1*(n1+1)/2)/(n1*n0)) if n1*n0 else None
def classification(y,p):
    return dict(n=len(y),prevalence=float(y.mean()),mean_probability=float(p.mean()),brier=mse(y,p),auc=auc(y,p))
def cluster_interval(x,y,ids,index):
    b=fit(x,y);res=y-x@b;bread=np.linalg.pinv(x.T@x);meat=np.zeros((x.shape[1],x.shape[1]))
    groups=sorted(set(ids))
    for group in groups:
        m=np.array(ids)==group;s=x[m].T@res[m];meat+=np.outer(s,s)
    g=len(groups);n=len(y);k=x.shape[1]
    cov=bread@meat@bread*(g/(g-1))*((n-1)/(n-k))
    se=math.sqrt(max(0,cov[index,index]));q=t.ppf(.975,g-1)
    return dict(coefficient=float(b[index]),cluster_se=se,ci95=[float(b[index]-q*se),float(b[index]+q*se)],clusters=g)
def policy_design(rows):
    return np.array([[1,float(r["severity"])/10,float(r["baseline_burden"])/100,float(r["access"]),float(r["age"])/100] for r in rows])
def prediction(root,lesson):
    rows=read(root,"prediction","requests.csv")
    tr=[r for r in rows if int(r["month"])<12]
    va=[r for r in rows if 12<=int(r["month"])<16]
    te=[r for r in rows if 16<=int(r["month"])<20]
    future=[r for r in rows if int(r["month"])>=20]
    y=nums(tr,"resolution_minutes");yv=nums(va,"resolution_minutes")
    if lesson==21:
        x=np.c_[np.ones(len(tr)),nums(tr,"backlog")];xv=np.c_[np.ones(len(va)),nums(va,"backlog")]
        b=fit(x,y);res=y-x@b;h=np.einsum("ij,jk,ik->i",x,np.linalg.pinv(x.T@x),x)
        cook=res**2/(2*np.mean(res**2))*h/(1-h)**2;idx=int(np.argmax(cook))
        keep=np.arange(len(tr))!=idx;alter=fit(x[keep],y[keep])
        bins=[]
        for lo,hi in [(0,10),(10,20),(20,40)]:
            m=(x[:,1]>=lo)&(x[:,1]<hi)
            bins.append(dict(backlog_range=[lo,hi],n=int(m.sum()),mean_residual=float(res[m].mean())))
        return dict(train_n=len(tr),correlation=float(np.corrcoef(x[:,1],y)[0,1]),
          slope_per_backlog_unit=cluster_interval(x,y,[r["entity_id"] for r in tr],1),
          validation_mae=mae(yv,xv@b),residual_bins=bins,
          influence_record=tr[idx]["record_id"],slope_without_one_record=float(alter[1]),
          caution="Sensitivity exclusion is not evidence that this record is invalid; association is not intervention effect.")
    if lesson==22:
        out={}
        for kind in ["base","interaction","collinear"]:
            x=design(tr,kind);xv=design(va,kind);b=fit(x,y)
            out[kind]=dict(validation_mae=mae(yv,xv@b),validation_rmse=math.sqrt(mse(yv,xv@b)),
              condition_number=float(np.linalg.cond(x)),coefficients=b.tolist())
        out["note"]="backlog and workload coefficients use 10-unit scales; region reference=north. Validation compares future observed rows, not causal effects."
        return out
    if lesson in (23,24,26):
        y=nums(tr,"escalated");yv=nums(va,"escalated")
        models={k:logistic(design(tr,k),y) for k in ["base","interaction"]}
        val={k:classification(yv,expit(design(va,k)@b)) for k,b in models.items()}
        best=min(val,key=lambda k:val[k]["brier"]);b=models[best]
        if lesson==23:
            p=expit(design(va,best)@b);rules=[]
            for cutoff in [0,.08,.12,.18,.25,.4]:
                chosen=np.zeros(len(va),bool)
                for month in sorted({r["month"] for r in va}):
                    inds=np.array([i for i,r in enumerate(va) if r["month"]==month])
                    cap=int(math.floor(len(inds)*.25));ordered=inds[np.argsort(-p[inds],kind="stable")[:cap]]
                    chosen[ordered[p[ordered]>=cutoff]]=True
                tp=int(((yv==1)&chosen).sum());fp=int(((yv==0)&chosen).sum());fn=int(((yv==1)&~chosen).sum())
                rules.append(dict(cutoff=cutoff,selected=int(chosen.sum()),tp=tp,fp=fp,fn=fn,
                  diagnostic_loss=fp+8*fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn)))
            return dict(validation=val,selected_model=best,rules=rules,limits="Loss is a supplied screening scenario, not an identified treatment benefit.")
        if lesson==24:
            yt=nums(te,"escalated");p=expit(design(te,best)@b)
            groups={}
            for name,mask in [("known_entity",np.array([int(r["entity_id"][1:])<200 for r in te])),
                              ("new_entity",np.array([int(r["entity_id"][1:])>=200 for r in te]))]:
                groups[name]=classification(yt[mask],p[mask])
            # Cold-start alternative: no held-out entity contributes any training row.
            ctr=[r for r in tr if int(r["entity_id"][1:])<160]
            cv=[r for r in va if int(r["entity_id"][1:])>=160]
            cb=logistic(design(ctr,best),nums(ctr,"escalated"))
            return dict(split_counts=dict(train=len(tr),validation=len(va),test=len(te)),
              selection_on_validation=val,chosen=best,test=classification(yt,p),test_groups=groups,
              cold_start_validation=classification(nums(cv,"escalated"),expit(design(cv,best)@cb)),
              cold_start_train_entities=len({r["entity_id"] for r in ctr}),
              forbidden_features=["after_close_minutes","satisfaction_after","resolution_minutes"],
              note="Earlier L21–23 did not use months16–19. After this lesson they are no longer an untouched test set.")
        # Reuse 16–19 as explicitly declared redevelopment/calibration data, NOT a fresh test.
        pc=expit(design(te,best)@b);yc=nums(te,"escalated")
        z=np.log(np.clip(pc,1e-8,1-1e-8)/(1-np.clip(pc,1e-8,1-1e-8)))
        cb=logistic(np.c_[np.ones(len(z)),z],yc,alpha=.01)
        pf=expit(design(future,best)@b);yf=nums(future,"escalated")
        pcal=expit(np.c_[np.ones(len(pf)),np.log(pf/(1-pf))]@cb)
        bins=[]
        for lo,hi in [(0,.1),(.1,.2),(.2,.4),(.4,1.0001)]:
            m=(pcal>=lo)&(pcal<hi)
            if m.any():bins.append(dict(range=[lo,hi],**classification(yf[m],pcal[m])))
        return dict(preceding_calibration=classification(yc,pc),future_raw=classification(yf,pf),
          future_calibrated=classification(yf,pcal),calibration_coefficients=cb.tolist(),future_bins=bins,
          future_groups={g:classification(yf[np.array([r["region"]==g for r in future])],
              pcal[np.array([r["region"]==g for r in future])]) for g in ["east","west","north"]},
          missing_sensor_rate=sum(r["sensor_quality"]=="" for r in future)/len(future))
    if lesson==25:
        out={}
        for kind in ["base","rich","cheap"]:
            x=design(tr,kind);xv=design(va,kind)
            for alpha in [0,1,10,100]:
                b=fit(x,y,alpha);out[f"{kind}-ridge-{alpha}"]=dict(mae=mae(yv,xv@b),rmse=math.sqrt(mse(yv,xv@b)))
        out["mean_baseline"]=dict(mae=mae(yv,np.repeat(y.mean(),len(yv))))
        for part in [0,1]:
            sub=[r for r in tr if (int(r["month"])<6)==(part==0)]
            out[f"half{part}_base_coefficients"]=fit(design(sub),nums(sub,"resolution_minutes")).tolist()
        out["note"]="rich adds nonlinear backlog/region terms; cheap omits workload. Validation is for selection; reused historical test performance is not fresh confirmation."
        return out
def smd(x,a,w):
    ans=[]
    for col in x.T:
        m1=np.average(col[a==1],weights=w[a==1]);m0=np.average(col[a==0],weights=w[a==0])
        denominator=math.sqrt((np.var(col[a==1])+np.var(col[a==0]))/2)
        ans.append(float((m1-m0)/denominator) if denominator>0 else None)
    return ans
def observational(root,lesson):
    rows=read(root,"policy","support_observational.csv");x=policy_design(rows);a=nums(rows,"support");y=nums(rows,"followup_burden")
    crude=float(y[a==1].mean()-y[a==0].mean());ps=expit(x@logistic(x,a))
    if lesson==27:return dict(n=len(rows),crude_burden_difference=crude,
      support_rate=float(a.mean()),severity_by_group=[float(nums(rows,"severity")[a==j].mean()) for j in [0,1]],
      baseline_covariates=["severity","baseline_burden","access","age"],
      post_treatment_not_baseline=["contact_after","responded_after"],
      note="Unobserved common causes remain possible. Generator settings are not observational identification evidence.")
    keep=(ps>=.1)&(ps<=.9);xx=x[keep];aa=a[keep];yy=y[keep]
    # Fix the overlap-defined population, then refit within it consistently in point/boot fits.
    ee=np.clip(expit(xx@logistic(xx,aa)),.01,.99)
    w=np.where(aa==1,1/ee,1/(1-ee));estimate=float(np.average(yy[aa==1],weights=w[aa==1])-np.average(yy[aa==0],weights=w[aa==0]))
    # Standardize fitted outcome models to the same retained covariate distribution.
    b1=fit(xx[aa==1],yy[aa==1]);b0=fit(xx[aa==0],yy[aa==0]);standardized=float(np.mean(xx@b1-xx@b0))
    # Bootstrap refits propensity on resampled retained population; estimand is explicitly restricted.
    rng=np.random.default_rng(2801);boot=[]
    for _ in range(120):
        ix=rng.integers(0,len(xx),len(xx));bx=xx[ix];ba=aa[ix];by=yy[ix]
        be=np.clip(expit(bx@logistic(bx,ba)),.01,.99);bw=np.where(ba==1,1/be,1/(1-be))
        boot.append(float(np.average(by[ba==1],weights=bw[ba==1])-np.average(by[ba==0],weights=bw[ba==0])))
    return dict(crude=crude,retained_n=int(keep.sum()),excluded_n=int((~keep).sum()),
      propensity_range=[float(ps.min()),float(ps.max())],restricted_hajek_difference=estimate,
      restricted_standardized_difference=standardized,bootstrap_ci95=np.quantile(boot,[.025,.975]).tolist(),
      unweighted_smd=smd(xx[:,1:],aa,np.ones(len(aa))),weighted_smd=smd(xx[:,1:],aa,w),
      effective_sample_size={str(j):float(w[aa==j].sum()**2/(w[aa==j]**2).sum()) for j in [0,1]},
      caution="Trimmed target differs from full-population ATE. Bootstrap interval conditional on original retained set; no uncertainty about unmeasured confounding is included.")
def policy_panel(root):
    rows=read(root,"policy","district_panel.csv")
    means={}
    for group in ["treated","near_control","far_control"]:
        means[group]={}
        for name,lo,hi in [("early",0,9),("late_pre",9,18),("post",18,36)]:
            rr=[r for r in rows if r["group"]==group and lo<=int(r["month"])<hi]
            means[group][name]=float(nums(rr,"outcome").mean())
    changes={}
    rng=np.random.default_rng(2901)
    for control in ["near_control","far_control"]:
        district_changes={}
        for r in rows:district_changes.setdefault(r["district"],dict(group=r["group"],pre=[],post=[]))
        for r in rows:district_changes[r["district"]]["pre" if int(r["month"])<18 else "post"].append(float(r["outcome"]))
        a=np.array([np.mean(v["post"])-np.mean(v["pre"]) for v in district_changes.values() if v["group"]=="treated"])
        b=np.array([np.mean(v["post"])-np.mean(v["pre"]) for v in district_changes.values() if v["group"]==control])
        boot=[float(rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean()) for _ in range(1000)]
        changes[control]=dict(did=float(a.mean()-b.mean()),cluster_bootstrap_ci95=np.quantile(boot,[.025,.975]).tolist(),
          pre_placebo=(means["treated"]["late_pre"]-means["treated"]["early"])-(means[control]["late_pre"]-means[control]["early"]))
    event_time=[]
    for month in range(36):
        vals={g:np.mean([float(r["outcome"]) for r in rows if r["group"]==g and int(r["month"])==month]) for g in means}
        event_time.append(dict(event_time=month-18,treated_minus_far=float(vals["treated"]-vals["far_control"])))
    return dict(group_means=means,comparisons=changes,event_time=event_time,
      note="Equal-district target; district is bootstrap unit. Few clusters and interference limit inference; pre-trend compatibility does not establish parallel counterfactual trends.")
def forecasting(root):
    rows=read(root,"policy","weekly_demand.csv");y=nums(rows,"demand");holiday=nums(rows,"holiday_known")
    def predict(end,h,method):
        if method=="last":return y[end-1]
        if method=="seasonal":return y[end+h-52]
        tt=np.arange(end);x=np.c_[np.ones(end),tt,np.sin(2*np.pi*tt/52),np.cos(2*np.pi*tt/52),holiday[:end]]
        b=fit(x,y[:end]);target=end+h
        return float(np.array([1,target,math.sin(2*math.pi*target/52),math.cos(2*math.pi*target/52),holiday[target]])@b)
    scores={};cal_errors={}
    for method in ["last","seasonal","trend_seasonal"]:
        validation=[];errors=[]
        for end in range(80,116,4):
            for h in range(4):validation.append(y[end+h]-predict(end,h,method))
        for end in range(116,132,4):
            for h in range(4):errors.append(y[end+h]-predict(end,h,method))
        scores[method]=dict(validation_mae=float(np.mean(abs(np.array(validation)))),calibration_mae=float(np.mean(abs(np.array(errors)))))
        cal_errors[method]=np.array(errors)
    best=min(scores,key=lambda k:scores[k]["validation_mae"]);q=float(np.quantile(abs(cal_errors[best]),.9,method="higher"))
    records=[]
    for end in range(132,156,4):
        for h in range(4):
            p=predict(end,h,best);actual=y[end+h]
            records.append(dict(week=end+h,actual=float(actual),prediction=p,lower=max(0,p-q),upper=p+q))
    return dict(rolling_scores=scores,chosen=best,calibrated_half_width=q,
      test_mae=float(np.mean([abs(z["actual"]-z["prediction"]) for z in records])),
      test_coverage=float(np.mean([z["lower"]<=z["actual"]<=z["upper"] for z in records])),
      test_predictions=records,note="Approximate empirical 90% band, not guaranteed conditional coverage under serial dependence or drift. Parameters refit with past only.")
def decision(root,affordable=False):
    rows=read(root,"policy","decision_options.csv");pilot=read(root,"policy","pilot_test.csv")
    losses={a:{r["state"]:float(r["loss"]) for r in rows if r["action"]==a} for a in sorted({r["action"] for r in rows})}
    prior={r["state"]:float(r["prior_probability"]) for r in pilot};sensitivity={r["state"]:float(r["positive_probability"]) for r in pilot}
    if affordable:
        # A separately declared teaching offer, not estimated from the panel:
        # cost4, sensitivity0.70, false-positive probability0.25, budget ceiling6.
        sensitivity={"low":.25,"high":.70}
    expected={a:sum(prior[s]*v[s] for s in prior) for a,v in losses.items()};current=min(expected.values())
    after=0;posteriors={}
    for signal in ["positive","negative"]:
        joint={s:prior[s]*(sensitivity[s] if signal=="positive" else 1-sensitivity[s]) for s in prior}
        prob=sum(joint.values());post={s:joint[s]/prob for s in prior}
        risk={a:sum(post[s]*v[s] for s in prior) for a,v in losses.items()}
        after+=prob*min(risk.values());posteriors[signal]=dict(probability=prob,posterior=post,expected_losses=risk)
    perfect=sum(prior[s]*min(v[s] for v in losses.values()) for s in prior)
    result=dict(expected_losses=expected,best_now=min(expected,key=expected.get),
      expected_loss_with_signal=after,evsi_before_cost=current-after,evpi=current-perfect,
      sample_information=posteriors,net_information_value_at_cost8_delay3=current-after-11,
      sensitivity=[dict(high_probability=float(p),best_action=min(losses,key=lambda a:(1-p)*losses[a]["low"]+p*losses[a]["high"])) for p in np.linspace(.1,.8,8)],
      note="Priors, test properties and losses are supplied scenarios; not causal estimates from the panel.")
    if affordable:
        result.pop("net_information_value_at_cost8_delay3")
        result.update(budget_ceiling=6,original_cost8_feasible=False,alternative_survey_cost=4,
          alternative_signal_positive_probabilities=sensitivity,delay_cost=3,
          alternative_net_information_value=current-after-7,
          recommendation="Keep the current pilot action: original survey exceeds budget; cheaper survey does not repay cost plus delay.")
    return result
def main(lesson):
    parser=argparse.ArgumentParser();parser.add_argument("--student-root",type=Path,required=True);args=parser.parse_args()
    if lesson<=26:result=prediction(args.student_root,lesson)
    elif lesson<=28:result=observational(args.student_root,lesson)
    elif lesson==29:result=policy_panel(args.student_root)
    elif lesson==30:result=forecasting(args.student_root)
    else:result=decision(args.student_root,affordable=lesson==32)
    result={"lesson":lesson,"reference_only":True,"results":result}
    path=Path(__file__).resolve().parents[1]/f"lesson-{lesson:02d}"/"reference_results.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
