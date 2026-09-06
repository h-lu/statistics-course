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
    selected = [r for r in rows if windows[r["window_id"]] == center and r["abandoned"] == "0"]
    x = sorted(float(r["wait_minutes"]) for r in selected)
    summary.append({"center": center, "served_n": len(x), "mean": statistics.mean(x), "median": statistics.median(x), "maximum": max(x)})
output = {"statistics": summary, "scope": "第一期已服务工单；未形成评价规则", "note": "请自行设计指标目标、尾部保护和替代制度，不能直接把该表当排名。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
