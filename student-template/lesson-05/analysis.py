"""读表、逐日容量检查与给定名单的后果计算；学生自行设计分析路线。"""
from pathlib import Path
from collections import defaultdict
from datetime import date
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(name):
    with (ROOT / "data" / "alerts" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def unique(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if not value.strip() or value in result:
            raise ValueError(f"{key}为空或重复：{value}")
        result[value] = row
    return result


def load(batch, include_devices=True):
    capacities = unique(read("daily_capacity.csv"), "date")
    for day, item in capacities.items():
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("日期须为YYYY-MM-DD")
        item["max_reviews"] = int(item["max_reviews"])
        if item["max_reviews"] < 0:
            raise ValueError("容量不能为负")
    rows = read(batch + ".csv")
    unique(rows, "record_id")
    pairs = set()
    for row in rows:
        pair = (row["date"], row["device_id"])
        if pair in pairs or pair[0] not in capacities or not pair[1].strip():
            raise ValueError("设备日重复、空设备编号或缺少容量登记")
        if date.fromisoformat(pair[0]).isoformat() != pair[0]:
            raise ValueError("日期须为YYYY-MM-DD")
        pairs.add(pair)
        row["risk_score"] = float(row["risk_score"])
        if not math.isfinite(row["risk_score"]) or not 0 <= row["risk_score"] <= 100:
            raise ValueError("风险分数须为0到100之间有限数值")
    if include_devices:
        devices = unique(read("devices.csv"), "device_id")
        for row in rows:
            if row["device_id"] not in devices:
                raise ValueError("设备日缺少设备登记")
            row.update(devices[row["device_id"]])
            for field in ("miss_loss", "inspection_cost"):
                row[field] = float(row[field])
                if not math.isfinite(row[field]) or row[field] < 0:
                    raise ValueError(f"无效数值：{field}")
            if row["failure_within_24h"] not in ("0", "1"):
                raise ValueError("故障标记须为0或1")
    return rows, capacities


def capacity_check(rows, selected, capacities):
    """核对学生给定名单，不生成或改变名单。"""
    ids = {row["record_id"] for row in rows}
    selected = set(selected)
    if not selected <= ids:
        raise ValueError("名单包含当前批次以外的记录编号")
    days = defaultdict(list)
    for row in rows:
        days[row["date"]].append(row)
    result = []
    for day, values in sorted(days.items()):
        cap = capacities[day]["max_reviews"]
        number = sum(row["record_id"] in selected for row in values)
        result.append({"date": day, "records": len(values), "max_reviews": cap,
                       "selected": number, "capacity_ok": number <= cap})
    return result


def rate(num, den):
    return num / den if den else None


def evaluate(rows, selected, effectiveness):
    """仅评价学生给定的名单；效果比例是显式情境假设。"""
    if not math.isfinite(effectiveness) or not 0 <= effectiveness <= 1:
        raise ValueError("effectiveness须在0到1之间")
    selected = set(selected)
    if not selected <= {row["record_id"] for row in rows}:
        raise ValueError("名单包含当前批次以外的记录编号")
    counts = dict.fromkeys(("TP", "FP", "FN", "TN"), 0)
    costs = dict.fromkeys(("review_cost", "missed_failure_loss", "reviewed_remaining_loss", "no_review_loss"), 0.0)
    groups = defaultdict(lambda: {"n": 0, "selected": 0, "faults": 0, "missed": 0, "loss": 0.0})
    for row in rows:
        chosen = row["record_id"] in selected
        failure = int(row["failure_within_24h"])
        outcome = "TP" if chosen and failure else "FP" if chosen else "FN" if failure else "TN"
        counts[outcome] += 1
        review = row["inspection_cost"] if chosen else 0
        missed = failure * row["miss_loss"] if not chosen else 0
        remain = failure * row["miss_loss"] * (1 - effectiveness) if chosen else 0
        costs["review_cost"] += review
        costs["missed_failure_loss"] += missed
        costs["reviewed_remaining_loss"] += remain
        costs["no_review_loss"] += failure * row["miss_loss"]
        group = groups[row["device_class"]]
        group["n"] += 1
        group["selected"] += chosen
        group["faults"] += failure
        group["missed"] += failure and not chosen
        group["loss"] += review + missed + remain
    total = sum(costs[key] for key in ("review_cost", "missed_failure_loss", "reviewed_remaining_loss"))
    return {"device_days": len(rows), "selected": len(selected), **counts,
            "false_positive_rate": rate(counts["FP"], counts["FP"] + counts["TN"]),
            "false_negative_rate": rate(counts["FN"], counts["FN"] + counts["TP"]),
            "nonfault_share_of_selected": rate(counts["FP"], counts["TP"] + counts["FP"]),
            **costs, "total_loss": total, "by_device_class": dict(groups)}


def write_json(name, value):
    (HERE / "artifacts").mkdir(exist_ok=True)
    path = HERE / "artifacts" / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


def write_csv(name, rows, fieldnames=None):
    (HERE / "artifacts").mkdir(exist_ok=True)
    if not rows and not fieldnames:
        raise ValueError("空表须显式给fieldnames")
    path = HERE / "artifacts" / name
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows, capacities = load("development", include_devices=False)
    days = sorted({row["date"] for row in rows})
    write_json("starting_overview.json", {"batch": "development", "device_days": len(rows), "days": len(days),
               "score_min": min((row["risk_score"] for row in rows), default=None),
               "score_max": max((row["risk_score"] for row in rows), default=None),
               "daily_rows_and_capacity": [{"date": day, "records": sum(row["date"] == day for row in rows),
               "max_reviews": capacities[day]["max_reviews"]} for day in days],
               "note": "只核对起点。规则、名单、备选、后期评价与条件变化由学生自行组织。"})


if __name__ == "__main__":
    main()
