"""分层与直接标准化计算支架；共同构成和发布用途由学生决定。"""
from pathlib import Path
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(name):
    with (ROOT / "data" / "service" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_counts():
    rows = read("tickets.csv")
    ids = [row["ticket_id"] for row in rows]
    if len(ids) != len(set(ids)) or any(not value.strip() for value in ids):
        raise ValueError("工单编号为空或重复")
    window_rows = read("windows.csv")
    windows = {row["window_id"]: row["center"] for row in window_rows}
    if len(windows) != len(window_rows) or any(not key.strip() or not center.strip() for key, center in windows.items()):
        raise ValueError("窗口登记重复或为空")
    counts = []
    for row in rows:
        if row["window_id"] not in windows or row["completed_same_day"] not in ("0", "1") or row["business_code"] not in ("basic", "case"):
            raise ValueError("有未匹配窗口或未知业务/办结状态，须先核对")
    for center in sorted(set(windows.values())):
        for business in ("basic", "case"):
            group = [row for row in rows if windows[row["window_id"]] == center and row["business_code"] == business]
            complete = sum(int(row["completed_same_day"]) for row in group)
            counts.append({"center": center, "business_code": business, "n": len(group), "completed": complete,
                           "rate": complete / len(group) if group else None})
    return counts


def standardized(cells, weight):
    return weighted_rate({layer: cells[layer]["rate"] for layer in ("basic", "case")},
                         {"basic": 1 - weight, "case": weight})


def weighted_rate(rates, weights):
    """通用共同权重计算，不选择目标，不给出中心排名。"""
    if set(rates) != set(weights) or any(not math.isfinite(w) or w < 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1):
        raise ValueError("各层须有相同标签，权重非负且合计为1")
    total = 0.0
    for layer, weight in weights.items():
        if weight == 0:
            continue
        value = rates[layer]
        if value is None:
            return None
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("比例须在0到1或为None")
        total += value * weight
    return total


def main():
    result = {"counts": load_counts(), "note": "只核对分层计数；共同构成、敏感性范围与发布办法由学生自行组织。"}
    (HERE / "artifacts").mkdir(exist_ok=True)
    path = HERE / "artifacts" / "starting_overview.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
