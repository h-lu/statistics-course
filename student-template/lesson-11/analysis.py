"""Runnable small example and input preview. Extend for your chosen comparison."""
from pathlib import Path
import sys
import json
import random
import statistics as st
import itertools
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'data'/'inference-09-14'))
import toolkit as t

pop=t.population()
rows=t.acquire(pop,80,11,'srs','ordinary')
result={'example_only':{'unweighted':(.5+.9)/2,'composition_adjusted':.8*.5+.2*.9},
        'input_preview':{
            'not_invited':next(r for r in rows if not r['invited']),
            'invited_not_answered':next(r for r in rows if r['invited'] and not r['answered']),
            'answered':next(r for r in rows if r['answered'])},'invited':sum(r['invited'] for r in rows),
        'answered':sum(r['answered'] for r in rows)}
# observed_need is None for every unobserved result; do not replace it by zero.

if __name__ == '__main__':
    (HERE/'artifacts').mkdir(exist_ok=True)
    (HERE/'artifacts'/'example.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('小例和输入检查已完成；正式任务需自行分析、比较并解释。')
