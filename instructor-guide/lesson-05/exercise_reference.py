"""教师多方案过程核算；不选学生的路线或结论。"""
from pathlib import Path
from collections import defaultdict
import argparse
import importlib.util
import json
import math


def select(rows, capacities, kind, effectiveness=.85, factor=1, reserve=0):
    days=defaultdict(list)
    fields=('record_id','date','device_id','device_class','risk_score','miss_loss','inspection_cost')
    for row in rows:
        days[row['date']].append({key:row[key] for key in fields})
    chosen=set()
    for day, group in sorted(days.items()):
        limit=math.floor(capacities[day]['max_reviews']*factor)
        def gain(row):
            return row['risk_score'] if kind=='score' else row['risk_score']/100*effectiveness*row['miss_loss']-row['inspection_cost']
        ordered=sorted(group,key=lambda row:(-gain(row),row['device_id']))
        today=set()
        if reserve:
            for cls in sorted({r['device_class'] for r in group}):
                members=[r for r in ordered if r['device_class']==cls][:reserve]
                today.update(r['record_id'] for r in members)
            if len(today)>limit:
                raise ValueError('保障数超过容量')
        for row in ordered:
            if len(today)>=limit:
                break
            if gain(row)>0:
                today.add(row['record_id'])
        chosen.update(today)
    return chosen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--student-root',type=Path,required=True)
    args=parser.parse_args()
    path=args.student_root.resolve()/'lesson-05'/'analysis.py'
    spec=importlib.util.spec_from_file_location('student_helpers_05',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    output={}
    for batch in ('development','evaluation'):
        rows,caps=m.load(batch)
        output[batch]={}
        for kind in ('score','heuristic'):
            selected=select(rows,caps,kind)
            assert all(c['capacity_ok'] for c in m.capacity_check(rows,selected,caps))
            output[batch][kind]=m.evaluate(rows,selected,.85)
        output[batch]['none']=m.evaluate(rows,set(),.85)
    output['sensitivity_fixed_effect_001']={kind:m.evaluate(rows,select(rows,caps,kind),.01) for kind in ('score','heuristic')}
    output['heuristic_reselected_effect_001']=m.evaluate(rows,select(rows,caps,'heuristic',effectiveness=.01),.01)
    output['heuristic_half_capacity']=m.evaluate(rows,select(rows,caps,'heuristic',factor=.5),.85)
    output['heuristic_reserve2_each_class']=m.evaluate(rows,select(rows,caps,'heuristic',reserve=2),.85)
    output['fixed_list_equal_loss_effect']=11110/268000
    print(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
