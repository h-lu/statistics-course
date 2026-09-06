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
    selected = [r for r in rows if windows[r["window_id"]] == center]
    waits = [float(r["wait_minutes"]) for r in selected if r["abandoned"] == "0"]
    summary.append({"center": center, "registered_tickets": len(selected), "served_n": len(waits), "served_wait_mean_minutes": statistics.mean(waits), "served_wait_median_minutes": statistics.median(waits)})
output = {"scope": "第一期已登记工单；等待时间的均值和中位数仅根据未放弃者计算", "note": "这是数据概览示例，尚未确定具体分析问题或形成结论。", "centers": summary}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
