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

d=[0,1,2]; p=[.2,.5,.3]
mu=sum(x*w for x,w in zip(d,p))
rng=random.Random(10)
sim=rng.choices(d,weights=p,k=10000)
result={'example_only':{'mean_exact':mu,'variance_exact':sum(w*(x-mu)**2 for x,w in zip(d,p)),
        'shortage_probability_capacity1':.3,'simulated_mean':st.mean(sim)},
        'inputs':t.table('demand.csv')}

if __name__ == '__main__':
    (HERE/'artifacts').mkdir(exist_ok=True)
    (HERE/'artifacts'/'example.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('小例和输入检查已完成；正式任务需自行分析、比较并解释。')
