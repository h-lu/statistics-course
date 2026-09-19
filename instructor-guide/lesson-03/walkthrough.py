"""Teacher-only simulated submission, independently implemented from reference.py.

Uses declared CSV rules, not the data generator's latent values. Writes only to
an explicit output directory. This is a worked audit, not a real student trial.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


def read(path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def write_table(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def binary(value, field, issues):
    text = "" if value is None else str(value).strip()
    if text in ("0", "1"):
        return int(text)
    issues.append(("missing_" if not text else "invalid_") + field)
    return None


def proportions(rows):
    successes = sum(row["completed_value"] for row in rows)
    return {"n": len(rows), "completed": successes,
            "rate": successes / len(rows) if rows else None}


def solve(student_root, output):
    source = student_root.resolve() / "data/service"
    output = output.resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Output must be separate from the source data directory")
    names = ("tickets_raw.csv", "windows.csv", "business_types.csv")
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in names}
    fields, raw = read(source / names[0])
    window_rows = read(source / names[1])[1]
    business_rows = read(source / names[2])[1]
    windows = {row["window_id"]: row["center"] for row in window_rows}
    businesses = {row["business_code"] for row in business_rows}
    if len(windows) != len(window_rows) or len(businesses) != len(business_rows):
        raise ValueError("Duplicate lookup key")
    grouped, seen, trace = defaultdict(list), set(), []
    for number, row in enumerate(raw, 1):
        tid = row.get("ticket_id")
        if not tid or not tid.strip():
            raise ValueError("Missing ticket identifier")
        revision = int(row["export_revision"])
        if revision < 1:
            raise ValueError("Invalid revision")
        signature = tuple(row.get(field) for field in fields)
        trace.append({"data_row": number, "ticket_id": tid,
                      "export_revision": row["export_revision"], "disposition": "duplicate" if signature in seen else "pending"})
        if signature not in seen:
            grouped[tid].append((revision, number, row))
            seen.add(signature)
    cleaned, issue_rows = [], []
    for tid, versions in sorted(grouped.items()):
        version = max(v[0] for v in versions)
        candidates = [entry for entry in versions if entry[0] == version]
        if len(candidates) != 1:
            raise ValueError(f"Conflicting latest revision: {tid}")
        _, chosen_number, original = candidates[0]
        for _, number, _ in versions:
            trace[number - 1]["disposition"] = "selected" if number == chosen_number else "superseded"
        issues = []
        value = (original.get("wait_minutes") or "").strip()
        wait = None
        if not value:
            issues.append("wait_not_measured")
        else:
            try:
                numeric = float(value)
            except ValueError:
                numeric = math.nan
            if numeric in (999, -1):
                issues.append("wait_not_measured")
            elif not math.isfinite(numeric) or numeric < 0 or original["wait_unit"] not in ("second", "minute"):
                issues.append("wait_invalid")
            else:
                wait = numeric / 60 if original["wait_unit"] == "second" else numeric
        center = windows.get(original["window_id"])
        if not center:
            issues.append("unknown_window")
        if original["business_code"] not in businesses:
            issues.append("unknown_business")
        completed = binary(original.get("completed_same_day"), "completion", issues)
        abandoned = binary(original.get("abandoned"), "abandonment", issues)
        row = {**original, "source_data_row": chosen_number, "wait_normalized_minutes": wait,
               "completed_value": completed, "abandoned_value": abandoned, "resolved_center": center,
               "quality_flags": ";".join(issues),
               "use_served_wait": int(wait is not None and abandoned == 0),
               "use_completion": int(completed is not None),
               "use_shared_three": int(wait is not None and completed is not None and center is not None),
               "use_shared_five": int(not issues)}
        cleaned.append(row)
        for issue in issues:
            issue_rows.append({"ticket_id": tid, "issue": issue})
    states = Counter(row["disposition"] for row in trace)
    if len(raw) != states["selected"] + states["duplicate"] + states["superseded"]:
        raise RuntimeError("Row counts do not reconcile")
    waits = [row["wait_normalized_minutes"] for row in cleaned if row["use_served_wait"]]
    summary = {
        "raw_rows": len(raw), "unique_tickets": len(cleaned),
        "duplicate_rows": states["duplicate"], "superseded_rows": states["superseded"],
        "converted_from_seconds": sum(row["wait_unit"] == "second" and row["wait_normalized_minutes"] is not None for row in cleaned),
        "issue_counts": dict(sorted(Counter(row["issue"] for row in issue_rows).items())),
        "tickets_with_any_issue": len({row["ticket_id"] for row in issue_rows}),
        "served_wait": {"n": len(waits), "mean_minutes": statistics.mean(waits) if waits else None},
        "completion": proportions([row for row in cleaned if row["use_completion"]]),
        "shared_three": proportions([row for row in cleaned if row["use_shared_three"]]),
        "shared_five": proportions([row for row in cleaned if row["use_shared_five"]]),
        "known_window_counts": dict(sorted(Counter(row["window_id"] for row in cleaned if row["resolved_center"] is not None).items())),
        "unknown_window_tickets": sum(row["resolved_center"] is None for row in cleaned),
        "source_sha256": hashes,
    }
    output.mkdir(parents=True, exist_ok=True)
    extras = ["source_data_row", "wait_normalized_minutes", "completed_value", "abandoned_value", "resolved_center",
              "quality_flags", "use_served_wait", "use_completion", "use_shared_three", "use_shared_five"]
    write_table(output / "cleaned.csv", cleaned, fields + extras)
    write_table(output / "row_handling.csv", trace, ["data_row", "ticket_id", "export_revision", "disposition"])
    write_table(output / "issues.csv", issue_rows, ["ticket_id", "issue"])
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    def percent(value):
        return "不能计算" if value is None else f"{value * 100:.4f}%"
    report = f'''# 第3课模拟项目报告（教师审读演练，不是真实学生作业）

使用第二期已登记工单，分析单位为工单，未读取第一期结果或生成器中的未知真值。

## 处理与核对

{len(raw)}行＝{len(cleaned)}张工单＋{states['duplicate']}行完全重复＋{states['superseded']}行旧版本。
原值及选用版本见[处理后的表](cleaned.csv)，逐行处理见[row_handling.csv](row_handling.csv)，待核实问题见[issues.csv](issues.csv)。
同一工单可有多个问题，问题次数不等于不同工单数；不把按约定处理写成查实了原先缺失的真实值。

## 用途一：已服务且等待测量有效工单的平均等待

有效分母{len(waits)}张，平均{summary['served_wait']['mean_minutes']}分钟。
建议仅用于这个有效集合的描述，不称为全部工单或所有来访者的平均等待；缺测量或服务状态未知的工单不猜填为0。

## 用途二：当日办结比例与记录选择

| 条件 | 办结数 | 分母 | 比例 |
|---|---:|---:|---:|
| 仅要求办结状态有效 | {summary['completion']['completed']} | {summary['completion']['n']} | {percent(summary['completion']['rate'])} |
| 同时要求等待及单位、办结、窗口有效 | {summary['shared_three']['completed']} | {summary['shared_three']['n']} | {percent(summary['shared_three']['rate'])} |
| 再要求业务和放弃状态有效 | {summary['shared_five']['completed']} | {summary['shared_five']['n']} | {percent(summary['shared_five']['rate'])} |

主报告采用该指标本来能用的办结状态记录；另两行演示多指标共用记录的取舍，不因比例更高就替代主结果。
未知办结仍未知，不能将这几个比例称为全部工单的准确比例或数据清洗产生的管理改善。

## 用途三：各窗口已确认工单数

已确认数量见[summary.json](summary.json)的known_window_counts，窗口未知{summary['unknown_window_tickets']}张单列。
这些是登记数量，不是人员实际工作时长。优先核实未知窗口以决定窗口报告覆盖范围，核实缺失办结状态以补齐办结结果。
不因某用途缺字段而删除整张工单；是否限用应分别判断。

## 重新计算

使用Python标准库，无随机步骤。运行演练程序时显式传入学生数据根目录和输出目录；程序只生成上述结果，不改源CSV。
'''
    (output / "practice_report.md").write_text(report, encoding="utf-8")
    if hashes != {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in names}:
        raise RuntimeError("Input data changed")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    solve(args.student_root, args.output)


if __name__ == "__main__":
    main()
