"""Teacher-only worked project, independently implemented from reference.py.

Read the first-period tickets and dictionaries; never modify supplied data.
Run: python instructor-guide/lesson-04/walkthrough.py --output /tmp/lesson04-work
The two reporting rules are illustrative choices, not prescribed student answers.
"""
from pathlib import Path
import argparse
import csv
import json
import math
import statistics


def read_table(path, required):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(required) - set(reader.fieldnames or []):
            raise ValueError(f"Missing required columns in {path.name}")
        return list(reader)


def unique_index(rows, field):
    result = {}
    for row in rows:
        key = row.get(field)
        if not isinstance(key, str) or not key.strip() or key in result:
            raise ValueError(f"Missing or duplicate {field}")
        result[key] = row
    return result


def ratio(a, b):
    return a / b if b else None


def quantile(values, p):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * p
    lo = math.floor(position)
    hi = math.ceil(position)
    return values[lo] + (position - lo) * (values[hi] - values[lo])


def analyze(tickets, windows, business):
    ticket_index = unique_index(tickets, "ticket_id")
    window_index = unique_index(windows, "window_id")
    business_index = unique_index(business, "business_code")
    thresholds = {code: float(row["reference_wait_minutes"]) for code, row in business_index.items()}
    if any(not math.isfinite(v) or v < 0 for v in thresholds.values()):
        raise ValueError("Invalid business waiting threshold")
    centers = sorted({row["center"] for row in windows})
    if any(not name.strip() for name in centers):
        raise ValueError("A window is missing its center")
    details = []
    for tid, row in sorted(ticket_index.items()):
        if row["window_id"] not in window_index or row["business_code"] not in thresholds:
            raise ValueError("Unknown dictionary code; resolve it before this first-period exercise")
        if row["abandoned"] not in ("0", "1"):
            raise ValueError("Unknown abandonment; do not silently treat it as no abandonment")
        wait = float(row["wait_minutes"])
        if not math.isfinite(wait) or wait < 0:
            raise ValueError("Invalid first-period waiting time")
        abandoned = int(row["abandoned"])
        over = wait > thresholds[row["business_code"]]
        details.append({**row, "center": window_index[row["window_id"]]["center"],
                        "wait": wait, "is_served": int(abandoned == 0),
                        "over_15": int(wait > 15), "over_business": int(over),
                        "abandoned_or_over_business": int(bool(abandoned) or over)})
    profiles, strata = [], []
    for center in centers:
        group = [r for r in details if r["center"] == center]
        served = [r for r in group if r["is_served"]]
        values = [r["wait"] for r in served]
        abandoned = sum(int(r["abandoned"]) for r in group)
        c15 = sum(r["over_15"] for r in served)
        cb = sum(r["over_business"] for r in served)
        event = sum(r["abandoned_or_over_business"] for r in group)
        profile = {"center": center, "registered": len(group), "served": len(served),
                   "abandoned": abandoned, "abandon_rate": ratio(abandoned, len(group)),
                   "case_count": sum(r["business_code"] == "case" for r in group),
                   "case_share": ratio(sum(r["business_code"] == "case" for r in group), len(group)),
                   "mean": statistics.mean(values) if values else None,
                   "median": statistics.median(values) if values else None,
                   "p90": quantile(values, .9), "served_wait_sum": math.fsum(values),
                   "over15_count": c15, "over15_rate": ratio(c15, len(served)),
                   "over_business_count": cb, "over_business_rate": ratio(cb, len(served)),
                   "registered_event_count": event, "registered_event_rate": ratio(event, len(group))}
        profiles.append(profile)
        for code in sorted(thresholds):
            subgroup = [r for r in group if r["business_code"] == code]
            strata.append({"center": center, "business_code": code,
                           "registered": len(subgroup),
                           "served": sum(r["is_served"] for r in subgroup),
                           "abandoned": sum(int(r["abandoned"]) for r in subgroup)})
    if sum(r["registered"] for r in profiles) != len(tickets):
        raise RuntimeError("Registered counts do not reconcile")
    if any(r["served"] + r["abandoned"] != r["registered"] for r in profiles):
        raise RuntimeError("Service status counts do not reconcile")
    decisions = []
    for rule, metric in (("uniform_15_minutes", "over15_rate"), ("business_15_30_minutes", "over_business_rate")):
        for trigger in (.08, .10, .12):
            for row in profiles:
                value = row[metric]
                decisions.append({"rule": rule, "center": row["center"], "trigger": trigger,
                                  "rate": value, "investigate_long_wait": None if value is None else value > trigger})
    dates = sorted({r["date"] for r in tickets})
    return {"synthetic_data": True, "registered_total": len(tickets),
            "period": [dates[0], dates[-1]] if dates else None,
            "thresholds_minutes": thresholds, "quantile_method": "linear (n-1)p",
            "profiles": profiles, "business_counts": strata, "decisions": decisions,
            "notes": ["The 10% investigation trigger is an explicit management assumption, not a universal standard.",
                      "Both rules publish all profiles, abandonment and business counts; a flag is not a total quality rank.",
                      "Different business thresholds do not hold business composition constant.",
                      "Missing refusal records prevent a refusal rate or a claim that selection is absent."]}, details


def write_csv(path, rows):
    # Write a header even for an empty output, rather than emitting invalid CSV.
    fields = list(rows[0]) if rows else ["ticket_id"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def render_report(result):
    def pct(value):
        return "不能计算" if value is None else f"{value * 100:.4f}%"
    lines = ["# 第4课模拟项目报告（教师演练，不是唯一答案）", "",
             "## 使用者与规则摘要", "",
             "服务委员会需要决定先调查哪些长等待，同时公开日常表现。只描述第一期已登记工单；不把中心差异解释为人员效果。",
             "两套办法均公开中位数、P90、已服务数量、放弃数量与比例、业务构成；不合成总分。",
             "办法甲以已服务工单等待严格超过15分钟的比例判断；办法乙改用常规15、复杂30分钟。两者都假定比例严格大于10%时调查该类长等待。",
             "10%是演练中的管理假设。其余中心只标记为未触发这项条件，不称全面合格，不把有调查标记的中心强排先后。缺少有效分母时暂不作该项评价。",
             "", "## 实际结果", "",
             "| 中心 | 登记/已服务/放弃 | 已服务超15分钟 | 已服务超业务参考时间 | 全登记放弃或超业务线 |",
             "|---|---|---|---|---|"]
    for row in result["profiles"]:
        lines.append(f"| {row['center']} | {row['registered']}/{row['served']}/{row['abandoned']} | {row['over15_count']}/{row['served']}={pct(row['over15_rate'])} | {row['over_business_count']}/{row['served']}={pct(row['over_business_rate'])} | {row['registered_event_count']}/{row['registered']}={pct(row['registered_event_rate'])} |")
    lines += ["", "详细中位数、P90、业务构成和总等待见summary.json。两个超时指标的分母为已服务工单，最后一列为全部登记工单；合并事件只计一次。", "", "## 替代办法与敏感性", "", "10%是基准管理假设；8%代表更重视及早发现、愿意承担更多核查工作的取舍，12%代表优先处理超时更集中情形的取舍。这些值用于检查建议是否依赖门槛，不宣称已由数据识别最优值。"]
    for rule in ("uniform_15_minutes", "business_15_30_minutes"):
        for trigger in (.08, .10, .12):
            flagged = [r["center"] for r in result["decisions"] if r["rule"] == rule and r["trigger"] == trigger and r["investigate_long_wait"] is True]
            lines.append(f"- {rule}，比例门槛{trigger:.0%}：调查标记为{'、'.join(flagged) or '无'}。")
    lines += ["", "本情境选择按业务参考时间的办法作为针对业务要求的调查入口，并同步公布统一15分钟结果，避免将不同规则的排序当成矛盾。", 
              "改变业务时间线改变了事件定义，没有统一业务构成，也不能消除所有不可比因素。门槛改变可能使某些调查标记消失，实际记录和等待没有因此改善。", "",
              "## 防范措施与适用范围", "",
              "每次核对登记数等于已服务数加放弃数，保留全部工单及排除原因，单列各类业务和放弃，不删除最慢记录。发现重复编号、未知状态或缺少必要字段时先核实，暂停受影响指标。",
              "每期比较业务构成与纳入范围，变化时复核规则用途；现有数据没有全部申请和拒接记录，不能据此排除少接困难业务的可能，建议下一期补记申请、接单与拒接。",
              "只选择容易业务是风险推测，不是已经证实的事实。8%、10%、12%的比较是有明确取舍的情境检查，不是另一个时期的验证。", "",
              "## 复核文件", "",
              "summary.json保存规则、分母、指标与决定；profiles.csv便于逐中心核对；ticket_checks.csv保留每张原工单及事件标记。",
              "同一输入和脚本可重复生成上述结果；不修改CSV，不读取教师reference.py或潜在真值。", ""]
    return "\n".join(lines)


def run(student_root, output):
    data = student_root.resolve() / "data/service"
    output = output.resolve()
    if output == student_root.resolve() or output == data or output.is_relative_to(student_root.resolve() / "data"):
        raise ValueError("Use a separate output directory, not the supplied data directory")
    result, details = analyze(
        read_table(data / "tickets.csv", ("ticket_id", "date", "window_id", "business_code", "wait_minutes", "abandoned")),
        read_table(data / "windows.csv", ("window_id", "center")),
        read_table(data / "business_types.csv", ("business_code", "reference_wait_minutes")))
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_csv(output / "profiles.csv", result["profiles"])
    write_csv(output / "ticket_checks.csv", details)
    (output / "practice_report.md").write_text(render_report(result), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-root", type=Path, default=Path(__file__).resolve().parents[2] / "student-template")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.student_root, args.output)
