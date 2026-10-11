"""Local deterministic numerical, delivery and scope checks. No network or Actions."""
from pathlib import Path
import sys
import json
import subprocess
import hashlib
import importlib.util
import tempfile
import shutil
import math
import statistics as st
import itertools
import time
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'student-template/data/inference-09-14'))
import toolkit as t
import generate
import reference_suite as refs

BASE='28011d9d51f46444171aaa3bf502619293101600'
SHARED={'README.md','instructor-guide/README.md','instructor-guide/COURSE_MAP.md',
        'instructor-guide/scripts/validate_course.py','student-template/README.md',
        'student-template/data/README.md','student-template/scripts/course.py',
        'student-template/tests/test_incremental_release.py'}
SHARED.update(f'instructor-guide/lesson-{n:02}/README.md' for n in range(9,15))


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def require(condition,message):
    if not condition: raise AssertionError(message)


def scope():
    before={}
    tracked=git('ls-tree','-rz','--name-only',BASE).decode().rstrip('\0').split('\0')
    for p in tracked:
        if p in SHARED: continue
        original=git('show',f'{BASE}:{p}')
        require((ROOT/p).is_file() and (ROOT/p).read_bytes()==original,f'protected bytes changed: {p}')
        before[p]=hashlib.sha256(original).hexdigest()
    old=git('show',f'{BASE}:instructor-guide/COURSE_MAP.md').decode()
    new=(ROOT/'instructor-guide/COURSE_MAP.md').read_text()
    for n in list(range(1,9))+list(range(15,33)):
        pat=rf'<a id="l{n:02}"></a>.*?(?=<a id=|## 核验与实施状态)'
        require(re.search(pat,old,re.S).group()==re.search(pat,new,re.S).group(),f'course map protected section {n}')
        oldrow=next(x for x in old.splitlines() if f'](#l{n:02})|' in x)
        newrow=next(x for x in new.splitlines() if f'](#l{n:02})|' in x)
        require(oldrow==newrow,f'course map protected row {n}')
    (HERE/'protected_sha256.json').write_text(json.dumps({'baseline':BASE,'files':before},indent=2)+'\n')
    return len(before)


def numeric(result):
    pop=t.population(); vals=[r['need_weekend'] for r in pop]
    require(len(pop)==4000 and len({r['person_id'] for r in pop})==4000,'population units')
    require(sum(vals)==1640 and st.mean(vals)==.41,'fixed target truth')
    with tempfile.TemporaryDirectory() as folder:
        generate.generate(Path(folder))
        require((Path(folder)/'weekend_population.csv').read_bytes()==(t.HERE/'weekend_population.csv').read_bytes(),'data generation bytes')
    rows=t.acquire(pop,80,123,'srs','ordinary')
    require(sum(r['invited'] for r in rows)==80,'invitation size')
    require(all(r['observed_need'] is None for r in rows if not r['answered']),'unobserved hidden')
    require(rows==t.acquire(pop,80,123,'srs','ordinary'),'acquisition determinism')
    voluntary=t.acquire(pop,80,123,'volunteer')
    require(all(not r['invited'] and r['invite_probability']==0 for r in voluntary if not r['in_frame']),'coverage zero probability')
    try: t.poststratified([{'group':'A','answered':1,'observed_need':1}])
    except ValueError: pass
    else: raise AssertionError('empty stratum silently accepted')
    example=t.natural_frequencies(1000,.01,.9,.95)
    require(math.isclose(example['positive_predictive_value'],2/13),'natural frequency posterior')
    require(t.natural_frequencies(10,0,.9,1)['positive_predictive_value'] is None,'undefined denominator')
    for r in result['09']:
        require(r['screen_cost']<=2000 and sum(g['reviewed'] for g in r['groups'])<=90,'L09 budget')
        for g in r['groups']:
            require(0<=g['reviewed']<=g['positive'] and 0<=g['undetected_faults']<=g['faults'],'L09 accounting')
    for scenario in ('base','stress'):
        entries=[r for r in t.table('demand.csv') if r['scenario']==scenario]
        require(math.isclose(sum(float(r['probability']) for r in entries),1),'demand mass')
        require(math.isclose(sum(float(r['demand'])*float(r['probability']) for r in entries),88),'same mean demand')
    costs={(r['scenario'],r['capacity']):r for r in result['10'] if r['shortage_cost']==8}
    require(costs[('base',80)]['expected_cost'] < costs[('base',120)]['expected_cost'],'main capacity cost trade-off')
    require(costs[('base',80)]['maximum_possible_shortage'] > costs[('base',120)]['maximum_possible_shortage'],'main capacity severity trade-off')
    require(math.isclose(costs[('stress',80)]['expected_cost'],costs[('stress',120)]['expected_cost']),'stress contrast is equal expected cost')
    for r in result['10']:
        require(abs(r['shortage_probability']-r['simulated_shortage_probability'])<.025,'capacity probability convergence')
        require(abs(r['expected_cost']-r['simulated_cost'])<25,'capacity loss convergence')
    m=[st.mean(pair) for pair in itertools.combinations([2,4,6,8],2)]
    require(m==[3,4,5,5,6,7] and math.isclose(st.pstdev(m),math.sqrt(5/3)),'four choose two enumeration')
    require(math.isclose(st.pstdev([2,4,6,8]),math.sqrt(5)),'raw SD')
    for r in result['12']:
        require(abs(r['bias'])<4*r['exact_design_SE']/math.sqrt(r['repetitions']),'SRS bias')
        require(abs(r['SE']/r['exact_design_SE']-1)<.08,'SRS simulated SE vs exact design')
    survey={r['mode']+r['response']:r for r in result['11']}
    require(survey['volunteercomplete']['composition_adjusted']['bias']>.15,'within-group selection remains after weights')
    require(abs(survey['srsordinary']['composition_adjusted']['bias'])<.02,'ordinary within-group response adjustment')
    require(t.bootstrap([1]*4)==(1.,1.) and t.bootstrap([0]*4)==(0.,0.),'bootstrap boundary degeneracy')
    require(math.isclose(t.wilson([1]*4)[0],4/(4+1.959963984540054**2)),'Wilson independent endpoint identity')
    for r in result['13']['main_and_boundary_coverage']:
        if r.get('case'): continue
        if r['method']=='wilson': require(.90<r['coverage']<.99,'Wilson main coverage implausible')
        require(0<=r['mean_width']<=1,'interval width')
    rare=[r for r in result['13']['main_and_boundary_coverage'] if r.get('case') and r['method']=='bootstrap'][0]
    require(rare['coverage']<.2,'rare-event bootstrap failure not demonstrated')
    for r in result['14']:
        require(r['cost']<=r['budget'],'stratified cost')
        require(abs(r['overall']['bias'])<4*r['exact_overall_SE']/math.sqrt(1500),'stratified bias')
        require(abs(r['overall']['SE']/r['exact_overall_SE']-1)<.08,'stratified SE vs independent exact design')
    full=[t.stratified(pop,{'A':3200,'B':800},seed)[0] for seed in (1,2)]
    require(full[0]==full[1] and math.isclose(full[0],.41),'census finite-population zero variation')
    require(math.isclose(.8*.5+.2*.9,.58) and not math.isclose((.5+.9)/2,.58),'weighted vs pooled counterexample')


def quiz():
    sys.path.insert(0,str(ROOT/'stat-check'))
    from app.questions import QuestionBank, BANKS, CURRENT_BANKS
    require(all(not 9<=int(b.lesson_id.split('-')[1][1:])<=14 for b in CURRENT_BANKS),'draft activation changed')
    count=0
    for n in range(9,15):
        path=ROOT/f'instructor-guide/knowledge-check/drafts/lessons-09-14-2026-10-11/lesson-v2r2-{n:02}.yml'
        copy=ROOT/f'stat-check/app/question_bank/drafts/lessons-09-14-2026-10-11/{path.name}'
        require(path.read_bytes()==copy.read_bytes(),'quiz copies mismatch')
        bank=QuestionBank(path)
        require(bank.lesson_id not in BANKS,'draft ID collides with published history')
        require(len(bank.items)==5,'five concept pairs')
        answers=[]
        for item in bank.items:
            require(item['pair']['a']['prompt']!=item['pair']['b']['prompt'],'A/B same stem')
            for q in item['pair'].values():
                answers.append(q['answer'])
                require(len({o['text'] for o in q['options']})==4,'duplicate options')
                require([o['id'] for o in q['options'] if o['misconception'] is None]==[q['answer']],'answer marker')
                count+=1
        require(set(answers)==set('ABCD'),'answer distribution')
    return count


def delivery():
    import ast
    for base in ('student-template/data/inference-09-14', 'instructor-guide/validation-09-14'):
        for path in (ROOT/base).glob('*.py'):
            ast.parse(path.read_text(), feature_version=(3,10))
    timings={}
    for n in range(9,15):
        script=ROOT/f'student-template/lesson-{n:02}/analysis.py'
        artifact=script.parent/'artifacts/example.json'
        start=time.perf_counter()
        subprocess.run([sys.executable,str(script)],cwd=ROOT/'student-template',check=True,capture_output=True)
        first=artifact.read_bytes()
        subprocess.run([sys.executable,str(script)],cwd=ROOT/'student-template',check=True,capture_output=True)
        require(first==artifact.read_bytes(),f'lesson {n} reproducibility')
        timings[f'L{n:02}_two_runs_seconds']=round(time.perf_counter()-start,4)
        if n == 9:
            a,b=json.loads(first)['separate_20_device_example']
            require(math.isclose(a['undetected'],65/12) and b['undetected']==5,'L09 bridge missed count')
            require(math.isclose(a['undetected_loss']-b['undetected_loss'],25/6),'L09 bridge service trade-off')
            for policy in (a,b):
                require(policy['screen_cost']==20 and policy['review_cost']==12,'L09 bridge separate budgets')
                for row in policy['groups']:
                    require(math.isclose(row['undetected'],row['undetected_negative']+row['undetected_unreviewed_positive']),'L09 bridge both missed sources')
        meta=json.loads((script.parent/'submission.json').read_text())
        require(meta['status']=='not_started' and not meta['artifacts'],'template falsely marked complete')
    # Validate realistic submission operations in a disposable copy; never mark templates complete.
    spec=importlib.util.spec_from_file_location('course_new',ROOT/'student-template/scripts/course.py')
    course=importlib.util.module_from_spec(spec);spec.loader.exec_module(course)
    with tempfile.TemporaryDirectory() as folder:
        scratch=Path(folder)/'student'
        shutil.copytree(ROOT/'student-template',scratch,ignore=shutil.ignore_patterns('__pycache__','.git'))
        for n in range(9,15):
            name=f'lesson-{n:02}';course.start(scratch,name);course.run(scratch,name)
            p=scratch/name/'submission.json';meta=json.loads(p.read_text())
            meta['status']='complete';meta['artifacts']=[f'{name}/artifacts/example.json'];p.write_text(json.dumps(meta))
            course.check(scratch,name)
            course.reproduce(scratch,name)
        for n in (15,32):
            try: course.manifest(scratch,f'lesson-{n:02}')
            except ValueError: pass
            else: raise AssertionError('future lesson enabled')
    return timings


def main():
    started=time.perf_counter()
    first=refs.run(); second=refs.run()
    require(first==second,'teacher full-suite deterministic rerun')
    suite_seconds=time.perf_counter()-started
    (HERE/'reference_results.json').write_text(json.dumps(first,ensure_ascii=False,indent=2)+'\n')
    for n in range(9,15):
        (ROOT/f'instructor-guide/lesson-{n:02}/reference_result.json').write_text(json.dumps(first[f'{n:02}'],ensure_ascii=False,indent=2)+'\n')
    numeric(first)
    report={'python':sys.version,'baseline':BASE,'teacher_suite_two_runs_seconds':round(suite_seconds,3),
            'numeric_checks':'passed','quiz_questions':quiz(),'protected_original_files':scope(),
            'student_example_timings':delivery(),'classroom_trial':'not conducted',
            'publication':'local only; no push, merge, deployment or GitHub Actions'}
    report['total_seconds']=round(time.perf_counter()-started,3)
    (HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
