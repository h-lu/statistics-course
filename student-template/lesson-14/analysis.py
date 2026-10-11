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

result={'example_only':{'proportional_allocation':[16,4],'equal_allocation':[10,10],
        'population_weights':[.8,.2], 'equal_allocation_counts':[5,9], 'equal_allocation_sample_proportions':[.5,.9],
        'equal_allocation_pooled':.7,'design_weighted':.58},
        'inputs':t.table('strata.csv')}

if __name__ == '__main__':
    (HERE/'artifacts').mkdir(exist_ok=True)
    (HERE/'artifacts'/'example.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('小例和输入检查已完成；正式任务需自行分析、比较并解释。')
