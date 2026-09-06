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
ids = {r["ticket_id"] for r in rows}
surveys = [r for r in read("service/satisfaction.csv") if r["ticket_id"] in ids]
output = {"target_tickets": len(ids), "matched_surveys": len(surveys), "invited": sum(r["invited"] == "1" for r in surveys), "responded": sum(r["score"] != "" for r in surveys), "observed_score_counts": dict(Counter(r["score"] for r in surveys if r["score"] != "")), "note": "只描述调查覆盖；无回答者未知，不能直接将回答者比例推广到全部工单。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
