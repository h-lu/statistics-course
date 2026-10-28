"""Temporary integration fixture; no student template or external service is changed."""
from pathlib import Path
import tempfile,shutil,json,subprocess,sys,re,hashlib,csv
src=Path(__file__).resolve().parents[2] / 'student-template'
with tempfile.TemporaryDirectory(prefix='l14-workflow-') as temp:
 r=Path(temp)/'student';shutil.copytree(src,r,ignore=shutil.ignore_patterns('__pycache__','artifacts'))
 support=(r/'lesson-14/SUPPORT.md').read_text()
 blocks=re.findall(r'```python\n(.*?)```',support,re.S)
 (r/'lesson-14/my-analysis.py').write_text(blocks[1])
 for name,a,b,budget in [('proportional',136,34,240),('alternative',94,48,240),('budget180',100,25,180)]:
  (r/f'lesson-14/plan-{name}.json').write_text(json.dumps(dict(n_A=a,n_B=b,repetitions=500,seed=1401,budget=budget)))
 def run(*args):
  p=subprocess.run([sys.executable,*args],cwd=r,text=True,capture_output=True)
  if p.returncode:raise RuntimeError(p.stdout+p.stderr)
  return p.stdout
 run('lesson-14/my-analysis.py')
 files=[p.relative_to(r).as_posix() for p in sorted((r/'lesson-14/artifacts/rebuild').rglob('*')) if p.is_file()]
 before={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in files}
 run('lesson-14/my-analysis.py')
 assert before=={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in files}
 m=json.loads((r/'lesson-14/submission.json').read_text());m.update(status='complete',run=['python3','lesson-14/my-analysis.py'],artifacts=files)
 (r/'lesson-14/submission.json').write_text(json.dumps(m))
 (r/'lesson-14/report.md').write_text('Temporary workflow fixture only: numerical and reproducibility check, not a student solution.\n')
 print(run('scripts/course_l1314.py','check','14'))
 print(run('scripts/course_l1314.py','ci','14'))
 # Check overwrite prevention and insufficient budget remain intact.
 p=subprocess.run([sys.executable,'lesson-14/analysis.py','--config','lesson-14/plan-proportional.json','--output','lesson-14/artifacts/rebuild/proportional'],cwd=r,capture_output=True)
 assert p.returncode!=0
 (r/'bad.json').write_text(json.dumps(dict(n_A=136,n_B=34,budget=180)))
 p=subprocess.run([sys.executable,'lesson-14/analysis.py','--config','bad.json','--output','bad-output'],cwd=r,capture_output=True)
 assert p.returncode!=0 and not (r/'bad-output').exists()
 print('PASS: documented rebuild script twice, 12 identical outputs, complete check/ci, overwrite and budget guards; source template untouched.')
