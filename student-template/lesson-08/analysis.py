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

keys = {"tickets.csv": ("ticket_id",), "tickets_raw.csv": ("ticket_id",), "satisfaction.csv": ("ticket_id",), "visits.csv": ("contact_id",), "windows.csv": ("window_id",), "business_types.csv": ("business_code",), "staffing.csv": ("date", "window_id")}
summary = []
for filename, key in keys.items():
    rows = read("service/" + filename)
    summary.append({"file": filename, "rows": len(rows), "proposed_key": list(key), "unique_keys": len({tuple(r[k] for k in key) for r in rows})})
output = {"inventory": summary, "note": "这是连接前清单，raw中的ticket_id重复需按版本处理；尚未完成连接或发布核对。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
