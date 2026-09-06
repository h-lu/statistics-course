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

rows = read("service/tickets.csv")
windows = {r["window_id"]: r["center"] for r in read("service/windows.csv")}
summary = []
for center in sorted(set(windows.values())):
    for business in sorted({r["business_code"] for r in rows}):
        selected = [r for r in rows if windows[r["window_id"]] == center and r["business_code"] == business]
        summary.append({"center": center, "business_code": business, "n": len(selected), "completed": sum(int(r["completed_same_day"]) for r in selected)})
output = {"counts": summary, "note": "这是分层计数示例，尚未确定共同业务构成、检查比较结果的稳定性或提出发布建议。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
