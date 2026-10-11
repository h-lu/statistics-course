"""Runnable small example and input preview. Extend for your chosen comparison."""
from pathlib import Path
import sys
import json
import random
import statistics as st
import itertools
from fractions import Fraction as F
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'data'/'inference-09-14'))
import toolkit as t

example = t.natural_frequencies(1000,.01,.9,.95)
# Separate 20-device teaching example from LEARN; not the formal CSV policy.
small_groups = [('甲', 2, 8), ('乙', 6, 4)]
small_policies = []
for name, reviews in [('甲1乙3', (1, 3)), ('甲0乙4', (0, 4))]:
    rows = []
    for (group, faults, nonfaults), reviewed in zip(small_groups, reviews):
        tp, fp = faults*F(1, 2), nonfaults*F(1, 4)
        ppv = tp/(tp+fp)
        found = reviewed*ppv
        rows.append({'group': group, 'true_positive': float(tp), 'false_positive': float(fp),
                     'positive_predictive_value': float(ppv), 'reviewed': reviewed,
                     'found': float(found), 'undetected': float(faults-found),
                     'undetected_negative': float(faults-tp),
                     'undetected_unreviewed_positive': float(tp-found)})
    missed = sum(r['undetected'] for r in rows)
    small_policies.append({'policy': name, 'groups': rows, 'screen_cost': 20,
                           'review_cost': sum(reviews)*3, 'undetected': missed,
                           'undetected_loss': missed*10})
result = {'example_only':example, 'separate_20_device_example': small_policies, 'input_groups':t.table('alert_groups.csv'),
          'input_methods':t.table('screening.csv')}

if __name__ == '__main__':
    (HERE/'artifacts').mkdir(exist_ok=True)
    (HERE/'artifacts'/'example.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print('小例和输入检查已完成；正式任务需自行分析、比较并解释。')
