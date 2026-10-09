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
    selected = [r for r in rows if windows[r["window_id"]] == center]
    waits = [float(r["wait_minutes"]) for r in selected if r["abandoned"] == "0"]
    if any(not math.isfinite(value) or value < 0 for value in waits):
        raise ValueError("已服务等待须为有限的非负数，请核对原始记录。")
    # 没有有效记录时不能计算均值或中位数，JSON中的null不表示0分钟。
    summary.append({"center": center, "registered_tickets": len(selected), "served_n": len(waits), "served_wait_mean_minutes": statistics.mean(waits) if waits else None, "served_wait_median_minutes": statistics.median(waits) if waits else None})
output = {"scope": "第一期已登记工单；等待时间的均值和中位数仅根据未放弃者计算", "note": "这是数据概览示例，尚未确定具体分析问题或形成结论。", "centers": summary}

(HERE / "artifacts").mkdir(exist_ok=True)
path = HERE / "artifacts" / "starting_overview.json"
path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(path.relative_to(ROOT))

# 可供任意自选分析复用的基础统计函数，不筛选记录、不指定分组。
def linear_quantile(sample, probability):
    """按排序位置(n-1)p线性插值；空集合返回None。"""
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("分位数比例须在0到1之间。")
    if not sample:
        return None
    if any(not math.isfinite(value) for value in sample):
        raise ValueError("数值须为有限数。")
    ordered = sorted(sample)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def describe(sample):
    """描述调用者选定的一组数；单位与原变量相同，std_n分母为n。"""
    if any(not math.isfinite(value) for value in sample):
        raise ValueError("数值须为有限数。")
    return {"n": len(sample), "mean": statistics.mean(sample) if sample else None,
            "median": statistics.median(sample) if sample else None,
            "p90": linear_quantile(sample, .9),
            "iqr": linear_quantile(sample, .75)-linear_quantile(sample, .25) if sample else None,
            "std_n": statistics.pstdev(sample) if sample else None}


def rate(numerator, denominator):
    """调用者决定分子分母；0分母未定义，返回None。"""
    return numerator / denominator if denominator else None
