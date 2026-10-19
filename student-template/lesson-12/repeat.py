"""Repeat one declared sampling condition on the unchanged lesson-11 population."""
from pathlib import Path
import argparse,csv,hashlib,json,math,random,statistics,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lesson-11'))
import sampling_tools as survey


def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def one_sample(population,frame,mechanism,n,selection_seed,response_seed,costs):
    invited=set(survey.choose_invites(frame,n,selection_seed,mechanism))
    rng=random.Random(response_seed);rows=[]
    eligible_n=sum(mechanism!='web_voluntary' or row['online_frame'] for row in population)
    for row in population:
        selected=row['person_id'] in invited
        pr=(.85 if row['need_weekend'] else .25) if mechanism=='web_voluntary' else 1. if mechanism=='register_complete' else {'A':.8,'B':.6}[row['group']]
        answered=selected and rng.random()<pr
        rows.append(dict(person_id=row['person_id'],group=row['group'],in_frame=int(mechanism!='web_voluntary' or bool(row['online_frame'])),invited=int(selected),answered=int(answered),invite_probability=n/eligible_n if mechanism!='web_voluntary' or row['online_frame'] else 0.,observed_need=row['need_weekend'] if answered else None,invitation_cost_units=costs[row['group']] if selected else 0))
    return rows

def run(config,out):
    required={'mechanism','n','estimator','repetitions','seed'}
    if set(config)!=required:raise ValueError('配置字段须为 mechanism,n,estimator,repetitions,seed')
    if config['estimator'] not in ('raw','poststrat'):raise ValueError('estimator须为raw或poststrat')
    for k in ['n','repetitions','seed']:
        if type(config[k]) is not int:raise ValueError(k+'须为整数')
    if config['repetitions']<2 or config['seed']<0:raise ValueError('repetitions至少2，seed非负')
    pop=survey._population();frame=survey.load_frame();costs=survey._costs()
    survey.choose_invites(frame,config['n'],0,config['mechanism'])
    if out.exists():raise FileExistsError('请使用尚不存在的输出目录')
    out.mkdir(parents=True);write_json(out/'plan.json',config)
    counts={g:sum(r['group']==g for r in pop) for g in ['A','B']}
    truth=statistics.mean(r['need_weekend'] for r in pop)
    rng=random.Random(config['seed']);trials=[]
    for trial in range(config['repetitions']):
        ss,rs=rng.getrandbits(64),rng.getrandbits(64)
        rows=one_sample(pop,frame,config['mechanism'],config['n'],ss,rs,costs)
        a=[r for r in rows if r['answered'] and r['group']=='A'];b=[r for r in rows if r['answered'] and r['group']=='B']
        value=survey.response_mean(rows) if config['estimator']=='raw' else survey.composition_estimate(rows,counts)
        trials.append(dict(trial=trial+1,selection_seed=ss,response_seed=rs,invited_n=config['n'],answered_n=len(a)+len(b),answered_A=len(a),answered_B=len(b),need_A=sum(r['observed_need'] for r in a),need_B=sum(r['observed_need'] for r in b),estimate=value,invitation_cost=sum(r['invitation_cost_units'] for r in rows)))
        if trial==0:write_csv(out/'first_observations.csv',rows)
    values=[r['estimate'] for r in trials if r['estimate'] is not None]
    avg=statistics.mean(values) if values else None
    sd=statistics.stdev(values) if len(values)>1 else None
    exact=math.sqrt(truth*(1-truth)/config['n']*(len(pop)-config['n'])/(len(pop)-1)) if config['mechanism']=='register_complete' and config['estimator']=='raw' else None
    summary=dict(plan=config,population_n=len(pop),truth=truth,valid_repetitions=len(values),undefined_repetitions=len(trials)-len(values),mean_estimate=avg,bias=None if avg is None else avg-truth,estimated_se=sd,monte_carlo_se_of_mean=None if sd is None else sd/math.sqrt(len(values)),rmse=None if not values else math.sqrt(statistics.mean((v-truth)**2 for v in values)),mean_answered=statistics.mean(r['answered_n'] for r in trials),mean_invitation_cost=statistics.mean(r['invitation_cost'] for r in trials),exact_se_complete_raw=exact,conditional_on_defined=len(values)!=len(trials),population_sha256=hashlib.sha256((survey.DATA/'simulator/weekend_population.csv').read_bytes()).hexdigest(),synthetic_teaching_data=True)
    write_csv(out/'trials.csv',trials);write_json(out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:run(json.loads(a.config.read_text(encoding='utf-8')),a.output)
    except (ValueError,OSError,KeyError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
