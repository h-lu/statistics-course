"""Bounded revision audit and independently specified transfer examples."""
from pathlib import Path
import subprocess,json,hashlib,math,sys,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE='460df03314f2d2a85098ab3d4ef2a27defc47b82'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
allowed={'instructor-guide/lesson-13/RUNBOOK.md','instructor-guide/COURSE_MAP.md','instructor-guide/lesson-09/RUNBOOK.md','instructor-guide/lesson-09/REFERENCE.md',
         'instructor-guide/knowledge-check/drafts/lessons-09-14-2026-10-11/README.md',
         'instructor-guide/validation-09-14/REPORT.md','instructor-guide/validation-09-14/verification.json',
         'student-template/lesson-09/report.md'}
allowed.update(f'student-template/lesson-{n:02}/{name}.md' for n in range(9,15) for name in ('README','LEARN','SUPPORT'))
protected={}
for name in git('ls-tree','-rz','--name-only',BASE).decode().rstrip('\0').split('\0'):
    if name in allowed:continue
    original=git('show',f'{BASE}:{name}')
    assert (ROOT/name).read_bytes()==original,name
    protected[name]=hashlib.sha256(original).hexdigest()
old=git('show',f'{BASE}:instructor-guide/COURSE_MAP.md').decode()
new=(ROOT/'instructor-guide/COURSE_MAP.md').read_text()
def outside09(s):
    a=s.index('<a id="l09">');b=s.index('<a id="l10">');return s[:a]+s[b:]
assert outside09(old)==outside09(new)
# Preserve the complete 20-device bridge verbatim.
def bridge(s):return s.split('## 一个20台设备的小政策')[1].split('## 回到任务与自问')[0]
assert bridge(git('show',f'{BASE}:student-template/lesson-09/LEARN.md').decode())==bridge((ROOT/'student-template/lesson-09/LEARN.md').read_text())
# Student-derived fresh examples, not the assignment answer.
sys.path.insert(0,str(ROOT/'student-template/data/inference-09-14'))
import toolkit as t
assert math.isclose(t.natural_frequencies(200,.2,.75,.9)['positive_predictive_value'],30/46)
intervals=[(.3,.5),(.41,.6),(.2,.4),(.35,.45)]
coverage=sum(lo<=.4<=hi for lo,hi in intervals)/4
width=sum(hi-lo for lo,hi in intervals)/4
assert coverage==.75 and math.isclose(width,.1725)
weighted=(3*(60/6)+2*(40/8))/100
assert math.isclose(weighted,.4) and math.isclose(.6*(3/6)+.4*(2/8),weighted)
assert math.isclose(t.percentile([0,1,2,2,5,8],.9),6.5)
wilson=t.wilson([1,0,1,0]);assert math.isclose(wilson[0],.15003898915214947)
work=HERE/'student-work';before=json.loads((work/'input_snapshot.json').read_text())
for name in ('alert_groups.csv','screening.csv'):
    rel='data/inference-09-14/'+name
    assert hashlib.sha256((work/rel).read_bytes()).hexdigest()==before[rel]
results=json.loads((work/'lesson-09/artifacts/minimum.json').read_text())
assert len(results)==2 and all(r['scenario']=='base' for r in results)
a,b=results
assert math.isclose(a['totals']['total_cost'],3486.417910447761)
assert math.isclose(b['totals']['total_cost'],3773.4512829112864)
assert math.isclose(b['totals']['total_cost']-a['totals']['total_cost'],287.0333724635253)
assert all(sum(g['reviews'] for g in r['groups'])==90 for r in results)
start=time.perf_counter();run=subprocess.run([sys.executable,'scripts/course.py','ci'],cwd=work,capture_output=True,text=True)
(HERE/'rebuild.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stderr
meta=json.loads((ROOT/'student-template/lesson-09/submission.json').read_text());assert meta['status']=='not_started' and meta['artifacts']==[]
report={'baseline':BASE,'protected_existing_files':len(protected),'course_map_outside09_unchanged':True,
        'bridge_example_unchanged':True,'fresh_examples':'passed: conditional risk, coverage/width, weighting, quantile, Wilson',
        'base_policies':len(results),'student_input_csv_unchanged':True,'delete_outputs_then_rebuild':'passed',
        'rebuild_seconds':round(time.perf_counter()-start,4),'classroom_trial':'not conducted'}
(HERE/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'protected_sha256.json').write_text(json.dumps(protected,indent=2)+'\n')
print(json.dumps(report,indent=2))
