"""教师多目标与缺层过程核算。"""
from pathlib import Path
import argparse
import importlib.util
import json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--student-root',type=Path,required=True)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('student_helpers_06',args.student_root.resolve()/'lesson-06'/'analysis.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    counts=m.load_counts()
    cells={c:{r['business_code']:r for r in counts if r['center']==c} for c in sorted({r['center'] for r in counts})}
    pooled=sum(r['n'] for r in counts if r['business_code']=='case')/sum(r['n'] for r in counts)
    result={'counts':counts,'pooled_case_weight':pooled,'common_targets':{str(w):{c:m.standardized(v,w) for c,v in cells.items()} for w in (pooled,.75)},
            'A_weight_for_80':(cells['A']['basic']['rate']-.8)/(cells['A']['basic']['rate']-cells['A']['case']['rate']),
            'A_missing_case_at_half_weight_bounds':[.5*cells['A']['basic']['rate'],.5*cells['A']['basic']['rate']+.5]}
    missing={'basic':{'rate':.8},'case':{'rate':None}}
    assert m.standardized(missing,.4) is None
    assert m.standardized(missing,0)==.8
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
