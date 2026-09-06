"""数据读取与描述性统计示例。请根据本课问题修改或扩展分析。"""
from pathlib import Path
from collections import Counter
import csv
import json
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def read(relative):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

rows = [r for r in read("service/tickets.csv") if r["abandoned"] == "0"]
values = sorted(float(r["wait_minutes"]) for r in rows)
def quantile(p):
    h = (len(values) - 1) * p
    lo = int(h)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (h - lo) * (values[hi] - values[lo])
output = {"scope": "第一期已获得服务工单，全部中心合并", "n": len(values), "mean": statistics.mean(values), "median": statistics.median(values), "q1": quantile(.25), "q3": quantile(.75), "p90": quantile(.90), "quantile_method": "linear (n-1)p", "note": "这里只是一个基准口径；需要自己提出需要核实的结论与有依据的敏感性方案。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
