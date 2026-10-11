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

result={'example_only':{'normal_interval':[10-1.96*2,10+1.96*2],
        'four_ones_bootstrap_failure':t.bootstrap([1,1,1,1]),
        'four_ones_wilson':t.wilson([1,1,1,1])},
        'population_rows':len(t.population())}

if __name__ == '__main__':
    (HERE/'artifacts').mkdir(exist_ok=True)
    (HERE/'artifacts'/'example.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('小例和输入检查已完成；正式任务需自行分析、比较并解释。')
