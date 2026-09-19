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
# 字典中的编号必须唯一，否则不能确定工单属于哪个中心。
window_rows = read("service/windows.csv")
windows = {r["window_id"]: r["center"] for r in window_rows}
if len(windows) != len(window_rows) or any(not key.strip() for key in windows):
    raise ValueError("窗口编号为空或重复，请先核对 windows.csv。")
if any(not center.strip() for center in windows.values()):
    raise ValueError("窗口缺少所属中心，请先核对 windows.csv。")
if any(r["window_id"] not in windows for r in rows):
    raise ValueError("有工单未匹配到窗口，请先核对，不能直接删去未匹配工单。")
summary = []
for center in sorted(set(windows.values())):
    selected = [r for r in rows if windows[r["window_id"]] == center and r["abandoned"] == "0"]
    x = sorted(float(r["wait_minutes"]) for r in selected)
    if any(not math.isfinite(value) or value < 0 for value in x):
        raise ValueError("已服务等待须为有限的非负数，请核对原始记录。")
    # 空组的统计量记为null，不将它评为等待0分钟的最佳中心。
    summary.append({"center": center, "served_n": len(x), "mean": statistics.mean(x) if x else None, "median": statistics.median(x) if x else None, "maximum": max(x) if x else None})
output = {"statistics": summary, "scope": "第一期已服务工单；未形成评价规则", "note": "请自行设计指标目标、尾部保护和替代制度，不能直接把该表当排名。"}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))
