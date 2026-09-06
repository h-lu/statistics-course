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

rows = read("service/tickets_raw.csv")
output = {"raw_rows": len(rows), "unique_ticket_ids": len({r["ticket_id"] for r in rows}), "wait_units": dict(Counter(r["wait_unit"] for r in rows)), "revision_counts": dict(Counter(r["export_revision"] for r in rows)), "missing_wait_code_rows": sum(r["wait_minutes"] in ("999", "-1") for r in rows), "note": "原行级概览，不是去重后工单质量报告，也未处理修订或单位。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
