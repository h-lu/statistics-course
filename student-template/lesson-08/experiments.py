"""教学构造的反例；从学生仓库根运行，不读取或改动正式CSV。"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent


def unique_index(rows, field):
    index = {}
    for row in rows:
        key = row.get(field)
        if not key or key in index:
            raise ValueError(f"缺键或重复键 {field}: {key!r}")
        index[key] = row
    return index


def average(values):
    return mean(values) if values else None


def duplication():
    tickets = [{"ticket": "T1", "wait": 2}, {"ticket": "T2", "wait": 10}]
    contacts = [{"contact": "C1", "ticket": "T1", "minutes": 2},
                {"contact": "C2", "ticket": "T1", "minutes": 3},
                {"contact": "C3", "ticket": "T1", "minutes": 4},
                {"contact": "C4", "ticket": "T2", "minutes": 7}]
    ti = unique_index(tickets, "ticket")
    unique_index(contacts, "contact")
    expanded = [ti[r["ticket"]]["wait"] for r in contacts]
    totals = defaultdict(lambda: {"contacts": 0, "minutes": 0})
    for row in contacts:
        totals[row["ticket"]]["contacts"] += 1
        totals[row["ticket"]]["minutes"] += row["minutes"]
    return {"synthetic_microcase": True, "tickets": tickets, "contacts": contacts,
            "ticket_mean": average([r["wait"] for r in tickets]),
            "expanded_mean": average(expanded),
            "expanded_sum_over_distinct_tickets": sum(expanded) / len(tickets),
            "contact_aggregates": dict(totals),
            "staff_minutes": sum(r["minutes"] for r in contacts),
            "question": "三个等待均值的分子与分母分别是什么？哪一个回答每张工单的平均等待？"}


def unmatched():
    # 均值相同并不能证明覆盖相同；改变未知工单值后结论还可能改变。
    windows = {"A1"}
    tickets = [{"ticket": "T1", "window": "A1", "wait": 2},
               {"ticket": "T2", "window": "A1", "wait": 10},
               {"ticket": "T3", "window": "UNKNOWN", "wait": 6}]
    unique_index(tickets, "ticket")
    matched = [r for r in tickets if r["window"] in windows]
    unknown = [r for r in tickets if r["window"] not in windows]
    alternatives = []
    for changed_wait in (6, 30):
        values = [r["wait"] for r in matched] + [changed_wait]
        alternatives.append({"unknown_wait": changed_wait,
                             "all_ticket_mean": average(values),
                             "inner_join_mean": average([r["wait"] for r in matched])})
    return {"synthetic_microcase": True, "left_n": len(tickets), "inner_n": len(matched),
            "unmatched": unknown, "alternatives": alternatives,
            "question": "窗口报告与全体工单报告分别保留谁？哪些未匹配信息仍有效？"}


def revision():
    records = [{"ticket": "R1", "revision": "9", "wait": 40},
               {"ticket": "R1", "revision": "10", "wait": 8},
               {"ticket": "R2", "revision": "2", "wait": 12},
               {"ticket": "R2", "revision": "2", "wait": 20}]
    groups = defaultdict(list)
    for row in records:
        groups[row["ticket"]].append(row)
    output = []
    for ticket, rows in groups.items():
        version = max(int(r["revision"]) for r in rows)
        latest = [r for r in rows if int(r["revision"]) == version]
        # 不能用排序最后一行消解冲突，更不能平均两条互相冲突的测量。
        signatures = {json.dumps(r, sort_keys=True) for r in latest}
        output.append({"ticket": ticket, "numeric_latest": version,
                       "lexical_latest": max(r["revision"] for r in rows),
                       "latest_records": latest,
                       "conflict": len(signatures) != 1,
                       "published_wait": latest[0]["wait"] if len(signatures) == 1 else None})
    return {"synthetic_microcase": True, "raw": records, "selection": output,
            "question": "最新版本存在冲突时，哪些指标需要暂缓使用？哪些已知信息仍可保留？说明不同处理下结果的适用范围。"}


def staffing():
    # 日期+窗口是联合键；排班与业务集合的并集保留三种覆盖状态。
    plan = {( "2026-04-13", "A1"): 8, ("2026-04-14", "A1"): 8}
    activity = {( "2026-04-13", "A1"): {"tickets": 2, "staff_minutes": 16},
                ( "2026-04-15", "A1"): {"tickets": 1, "staff_minutes": 6}}
    reports = []
    for key in sorted(set(plan) | set(activity)):
        observed = activity.get(key, {"tickets": 0, "staff_minutes": 0})
        minutes = observed["staff_minutes"]
        hours = plan.get(key)
        reports.append({"date": key[0], "window": key[1], **observed,
                        "planned_person_hours": hours,
                        "contact_person_hours": minutes / 60,
                        "recorded_work_over_plan": minutes / 60 / hours if hours else None,
                        "coverage": "plan_and_activity" if key in plan and key in activity
                        else "plan_without_recorded_activity" if key in plan else "activity_without_plan"})
    return {"synthetic_microcase": True, "window_days": reports,
            "known_plan_hours": sum(plan.values()),
            "plan_hours_on_activity_days_only": sum(v for k, v in plan.items() if k in activity),
            "source_staff_minutes": sum(r["staff_minutes"] for r in activity.values()),
            "question": "哪一天的计数为0，哪一天的计划量为null？缺排班时完整时期的比值能否计算？"}


CASES = {"duplication": duplication, "unmatched": unmatched,
         "revision": revision, "staffing": staffing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    args = parser.parse_args()
    result = CASES[args.case]()
    target = HERE / "artifacts" / ("experiment_" + args.case + ".json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(target.relative_to(HERE.parent))


if __name__ == "__main__":
    main()
