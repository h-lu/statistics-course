"""Teacher candidate comparisons for lesson 14."""
from pathlib import Path
import sys
import json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'validation-09-14'))
import reference_suite as suite

if __name__=='__main__':
    result=suite.l14(suite.t.population())
    (HERE/'reference_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
