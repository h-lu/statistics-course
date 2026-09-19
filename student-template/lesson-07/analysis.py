"""数据读取与描述性统计示例。请根据本课问题修改或扩展分析。"""
from pathlib import Path
from collections import Counter
import csv
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def read(relative):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

rows = read("service/tickets.csv")
ids = {r["ticket_id"] for r in rows}
if len(ids) != len(rows) or any(not value.strip() for value in ids):
    raise ValueError("目标工单编号为空或重复，请先核对。")
surveys = [r for r in read("service/satisfaction.csv") if r["ticket_id"] in ids]
survey_ids = [r["ticket_id"] for r in surveys]
if len(survey_ids) != len(set(survey_ids)):
    raise ValueError("同一目标工单有多条调查登记，不能重复计入回答人数。")
for row in surveys:
    # 空白仍是未知，不是0分，也不是默认未受邀。
    row["score"] = (row.get("score") or "").strip()
    row["invited"] = (row.get("invited") or "").strip()
    if row["score"] not in ("", "1", "2", "3", "4", "5"):
        raise ValueError("评价须为1到5的整数等级或空白，请先核对。")
    if row["invited"] not in ("", "0", "1"):
        raise ValueError("邀请状态须为0、1或空白，请先核对。")
    if row["invited"] == "0" and row["score"]:
        raise ValueError("未受邀却有评分，调查字段相互矛盾，须先核对。")
output = {"target_tickets": len(ids), "matched_surveys": len(surveys), "unmatched_tickets": len(ids - set(survey_ids)), "unknown_invitation": sum(r["invited"] == "" for r in surveys), "invited": sum(r["invited"] == "1" for r in surveys), "responded": sum(r["score"] != "" for r in surveys), "observed_score_counts": dict(Counter(r["score"] for r in surveys if r["score"] != "")), "note": "只描述调查覆盖；无回答者未知，不能直接将回答者比例推广到全部工单。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
