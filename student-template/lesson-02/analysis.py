"""数据读取与描述性统计示例。请根据本课问题修改或扩展分析。"""
from pathlib import Path
import csv
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def read(relative):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

rows = read("service/tickets.csv")
# 本示例使用已整理的第一期数据；遇到意外状态时停止，不猜成0。
if any(r["abandoned"] not in ("0", "1") for r in rows):
    raise ValueError("abandoned 应为0或1；未知或异常状态须先核对。")
ids = [r["ticket_id"] for r in rows]
if len(ids) != len(set(ids)) or any(not value.strip() for value in ids):
    raise ValueError("第一期工单编号为空或重复，请先核对。")
rows = [r for r in rows if r["abandoned"] == "0"]
values = sorted(float(r["wait_minutes"]) for r in rows)
if any(not math.isfinite(value) or value < 0 for value in values):
    raise ValueError("已服务等待须为有限的非负数，请核对原始记录。")

def quantile(p):
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("分位数的比例p应在0到1之间。")
    if not values:
        return None
    h = (len(values) - 1) * p
    lo = int(h)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (h - lo) * (values[hi] - values[lo])
output = {"scope": "第一期已获得服务工单，全部中心合并", "n": len(values), "mean": statistics.mean(values) if values else None, "median": statistics.median(values) if values else None, "q1": quantile(.25), "q3": quantile(.75), "p90": quantile(.90), "quantile_method": "linear (n-1)p", "note": "这里只是一个基准口径；需要自己提出需要核实的结论与有依据的敏感性方案。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
