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

rows = read("alerts/development.csv")
capacities = {r["date"]: int(r["max_reviews"]) for r in read("alerts/daily_capacity.csv")}
dates = sorted({r["date"] for r in rows})
output = {"batch": "development", "device_days": len(rows), "days": len(dates), "score_min": min(float(r["risk_score"]) for r in rows), "score_max": max(float(r["risk_score"]) for r in rows), "daily_rows_and_capacity": [{"date": day, "records": sum(r["date"] == day for r in rows), "max_reviews": capacities[day]} for day in dates], "note": "只检查开发数据与容量，尚未定义名单、估计风险或评价策略。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
