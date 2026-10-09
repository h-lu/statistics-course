"""教师覆盖、不同缺失假设与补采取舍过程核算。"""
from pathlib import Path
from collections import defaultdict
import argparse
import importlib.util
import json


def adjusted(m,rows,detail=False):
    cells=defaultdict(list)
    for row in rows:
        key=(row['business_code'], 'over15' if row['wait']>15 else 'at_most15',row['abandoned']) if detail else (row['business_code'],)
        cells[key].append(row)
    counts=[]; rates={};weights={}
    for key,members in sorted(cells.items()):
        known=[r for r in members if r['score'] is not None]
        happy=sum(r['score']>=4 for r in known)
        rates[key]=m.rate(happy,len(known));weights[key]=len(members)/len(rows)
        counts.append({'cell':list(key),'target_n':len(members),'responded':len(known),'happy':happy,'observed_rate':rates[key]})
    return {'cells':counts,'adjusted_under_representativeness':m.weighted_rate(rates,weights)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--student-root',type=Path,required=True)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('student_helpers_07',args.student_root.resolve()/'lesson-07'/'analysis.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    rows=m.records();overview=m.overview(rows,4)
    output={'observed':overview,'scenario_qU06_qN05':(1856+401*.6+1100*.5)/3600,
            'scenario_qU08_qN08':(1856+401*.8+1100*.8)/3600,
            'needed_qN_if_qU06_and_threshold08':(3600*.8-1856-401*.6)/1100,
            'common_missing_q_for_80':1024/1501,'business_adjustment':adjusted(m,rows),'detailed_adjustment':adjusted(m,rows,True),
            'hypothetical_budget400_widths':{'before':1501/3600,'100_new_responses':1401/3600,'25_new_responses':1476/3600}}
    assert m.unknown_score_bounds(0,0,0)==[None,None]
    assert m.weighted_rate({'x':None},{'x':1}) is None
    print(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
