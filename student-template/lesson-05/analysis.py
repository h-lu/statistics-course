"""数据读取与描述性统计示例。请根据本课问题修改或扩展分析。"""
from pathlib import Path
from datetime import date
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def read(relative):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def checked_date(value):
    # 日期统一写成2026-05-04，避免把同一天的不同写法当成不同日期。
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"日期无效：{value!r}，请按YYYY-MM-DD格式核对。") from error
    if parsed.isoformat() != value:
        raise ValueError(f"日期须采用YYYY-MM-DD格式：{value!r}。")
    return value


rows = read("alerts/development.csv")
capacity_rows = read("alerts/daily_capacity.csv")
for row in rows + capacity_rows:
    checked_date(row["date"])
capacities = {r["date"]: int(r["max_reviews"]) for r in capacity_rows}
if len(capacities) != len(capacity_rows) or any(not day.strip() for day in capacities):
    raise ValueError("容量表的日期为空或重复，请先核对。")
if any(value < 0 for value in capacities.values()):
    raise ValueError("每日复核名额不能为负数。")
ids = [r["record_id"] for r in rows]
device_days = [(r["date"], r["device_id"]) for r in rows]
if len(ids) != len(set(ids)) or len(device_days) != len(set(device_days)):
    raise ValueError("开发数据中有重复记录编号或重复设备日，请先核对。")
if any(not r["record_id"].strip() or not r["device_id"].strip() for r in rows):
    raise ValueError("设备编号和记录编号不能为空。")
scores = [float(r["risk_score"]) for r in rows]
if any(not math.isfinite(value) or not 0 <= value <= 100 for value in scores):
    raise ValueError("风险分数须为0到100之间的有限数值。")
if any(r["date"] not in capacities for r in rows):
    raise ValueError("有日期缺少每日容量，请先核对，不能默认名额为0。")
dates = sorted({r["date"] for r in rows})
output = {"batch": "development", "device_days": len(rows), "days": len(dates), "score_min": min(scores) if scores else None, "score_max": max(scores) if scores else None, "daily_rows_and_capacity": [{"date": day, "records": sum(r["date"] == day for r in rows), "max_reviews": capacities[day]} for day in dates], "note": "只检查开发数据与容量，尚未定义名单、估计风险或评价策略。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
