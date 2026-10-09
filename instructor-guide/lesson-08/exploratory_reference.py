"""教师参考计算的一种路线。仅由教师process_reference调用，不属于学生起始程序。"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date
import argparse
import csv
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[2] / "student-template"
HERE = ROOT / "lesson-08"
TABLES = {"tickets.csv": ("ticket_id",), "tickets_raw.csv": ("ticket_id",),
          "satisfaction.csv": ("ticket_id",), "visits.csv": ("contact_id",),
          "windows.csv": ("window_id",), "business_types.csv": ("business_code",),
          "staffing.csv": ("date", "window_id")}


def read(name):
    with (ROOT / "data/service" / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def keyed(rows, field):
    result = {}
    for row in rows:
        value = row.get(field)
        if not value or not value.strip() or value in result:
            raise ValueError(f"缺失或重复主键 {field}: {value!r}")
        result[value] = row
    return result


def number(value, label):
    x = float(value)
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"{label} 必须为非负有限数")
    return x


def binary(value):
    return int(value) if value in ("0", "1") else None


def ratio(a, b):
    return a / b if b else None


def day(value):
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("日期须为YYYY-MM-DD")
    return value


def wait(value, unit):
    if not value or value in ("999", "-1"):
        return None
    try:
        x = float(value)
    except ValueError:
        return None
    if x in (999, -1) or not math.isfinite(x) or x < 0 or unit not in ("minute", "second"):
        return None
    return x / 60 if unit == "second" else x


def clean(data, policy):
    windows = keyed(data["windows.csv"], "window_id")
    business = keyed(data["business_types.csv"], "business_code")
    groups = defaultdict(list)
    audit = Counter()
    for row in data["tickets_raw.csv"]:
        tid = row.get("ticket_id")
        if not tid or not tid.strip():
            raise ValueError("缺失ticket_id，无法确定工单单位")
        version = int(row["export_revision"])
        if version < 1:
            raise ValueError("revision必须为正整数")
        groups[tid].append(row)
    selected = []
    for tid, candidates in sorted(groups.items()):
        signatures = {tuple(sorted(r.items())) for r in candidates}
        audit["exact_duplicate_rows"] += len(candidates) - len(signatures)
        latest_version = max(int(r["export_revision"]) for r in candidates)
        latest = [r for r in candidates if int(r["export_revision"]) == latest_version]
        distinct = {tuple(sorted(r.items())) for r in latest}
        audit["superseded_revision_rows"] += len(signatures) - len(distinct)
        if len(distinct) > 1:
            audit["conflicting_latest_tickets"] += 1
            if policy == "stop":
                raise ValueError(f"{tid}最新版本冲突；先核实或声明quarantine规则")
            # 隔离冲突字段，保留每条最新记录中一致的信息，不猜真值。
            record = {k: latest[0][k] if len({r.get(k) for r in latest}) == 1 else "" for k in latest[0]}
            record["revision_conflict"] = True
        else:
            record = dict(latest[0])
            record["revision_conflict"] = False
        record["period"] = "second"
        selected.append(record)
    baseline = [dict(r, period="first", wait_unit="minute", revision_conflict=False) for r in data["tickets.csv"]]
    keyed(baseline, "ticket_id")
    if set(r["ticket_id"] for r in baseline) & set(groups):
        raise ValueError("两期工单ID重叠，不能直接追加")
    rows = []
    flags_count = Counter()
    for raw in baseline + selected:
        row = dict(raw)
        row["date"] = day(row["date"]) if row["date"] else None
        row["wait"] = wait(row.get("wait_minutes"), row.get("wait_unit"))
        row["abandon"] = binary(row.get("abandoned"))
        row["completed"] = binary(row.get("completed_same_day"))
        row["center"] = windows.get(row.get("window_id"), {}).get("center")
        row["business_known"] = row.get("business_code") in business
        flags = []
        for condition, flag in [(row["wait"] is None, "wait_unknown"),
                                (row["abandon"] is None, "abandon_unknown"),
                                (row["completed"] is None, "completion_unknown"),
                                (row["center"] is None, "window_unknown"),
                                (not row["business_known"], "business_unknown"),
                                (row["revision_conflict"], "revision_conflict"),
                                (row["date"] is None, "date_unknown")]:
            if condition:
                flags.append(flag)
        row["quality_flags"] = flags
        flags_count.update(flags)
        rows.append(row)
    keyed(rows, "ticket_id")
    audit.update({"raw_rows": len(data["tickets_raw.csv"]), "second_period_ids": len(groups),
                  "first_period_ids": len(baseline), "combined_ids": len(rows)})
    if audit["raw_rows"] != len(selected) + audit["exact_duplicate_rows"] + audit["superseded_revision_rows"] + sum(
            len({tuple(sorted(r.items())) for r in candidates if int(r["export_revision"]) == max(int(x["export_revision"]) for x in candidates)}) - 1
            for candidates in groups.values()):
        raise RuntimeError("原始行分解不守恒")
    return rows, {**dict(audit), "field_flags": dict(flags_count), "revision_conflict_rule": policy}


def join(rows, data, config):
    index = keyed(rows, "ticket_id")
    surveys = keyed(data["satisfaction.csv"], "ticket_id")
    keyed(data["visits.csv"], "contact_id")
    aggregates = defaultdict(lambda: {"contact_count": 0, "contact_minutes": 0.0})
    orphan = []
    for contact in data["visits.csv"]:
        minutes = number(contact["staff_minutes"], "staff_minutes")
        day(contact["contact_date"])
        if contact["ticket_id"] not in index:
            orphan.append(contact)
        totals = aggregates[contact["ticket_id"]]
        totals["contact_count"] += 1
        totals["contact_minutes"] += minutes
    output = []
    for row in rows:
        survey = surveys.get(row["ticket_id"])
        invitation = (survey or {}).get("invited", "")
        score = (survey or {}).get("score", "")
        if invitation not in ("", "0", "1") or score not in ("", "1", "2", "3", "4", "5"):
            raise ValueError("调查状态或评分不合法")
        if invitation == "0" and score:
            raise ValueError("未受邀却有评分，需核实")
        status = "missing_registration" if survey is None else "unknown_invitation" if invitation == "" else "not_invited" if invitation == "0" else "no_response" if not score else "responded"
        output.append({**row, **aggregates.get(row["ticket_id"], {"contact_count": 0, "contact_minutes": 0.0}),
                       "survey_status": status, "score": int(score) if score else None,
                       "invited": int(invitation) if invitation else None})
    kept = [r for r in output if config["window_join"] == "left" or r["center"] is not None]
    return kept, {"input_ticket_n": len(output), "joined_ticket_n": len(kept),
                  "unknown_window_n": sum(r["center"] is None for r in output),
                  "excluded_ticket_ids": [r["ticket_id"] for r in output if r not in kept],
                  "survey_status_all": dict(Counter(r["survey_status"] for r in output)),
                  "orphan_contact_n": len(orphan), "orphan_contact_minutes": sum(float(r["staff_minutes"]) for r in orphan),
                  "contacts_missing_on_ticket_n": sum(r["contact_count"] == 0 for r in output),
                  "unmatched_survey_rows": len(set(surveys) - set(index)),
                  "source_contact_minutes": sum(float(r["staff_minutes"]) for r in data["visits.csv"]),
                  "aggregated_contact_minutes": sum(a["contact_minutes"] for a in aggregates.values())}


def indicators(rows, data, config, join_audit):
    selected = rows if config["metric_scope"] == "per_metric" else [r for r in rows if not r["quality_flags"]]
    waits = [r for r in selected if r["wait"] is not None and r["abandon"] == 0]
    completions = [r for r in selected if r["completed"] is not None]
    responses = [r for r in selected if r["score"] is not None]
    expanded = [r["wait"] for r in waits for _ in range(r["contact_count"])]
    metrics = {"ticket_scope_n": len(rows), "metric_base_n": len(selected),
               "common_complete_required_fields": ["wait/unit", "abandonment", "completion", "window", "business", "registration_date", "revision_consistency"],
               "served_wait_n": len(waits), "served_wait_mean": statistics.mean([r["wait"] for r in waits]) if waits else None,
               "completion_n": len(completions), "completed_n": sum(r["completed"] for r in completions),
               "completion_rate": ratio(sum(r["completed"] for r in completions), len(completions)),
               "response_n": len(responses), "satisfied_n": sum(r["score"] >= 4 for r in responses),
               "satisfied_among_responses": ratio(sum(r["score"] >= 4 for r in responses), len(responses)),
               "contact_weighted_wait_mean": statistics.mean(expanded) if expanded else None,
               "scope_contact_n": sum(r["contact_count"] for r in rows),
               "scope_contact_minutes": sum(r["contact_minutes"] for r in rows),
               "not_measured_personal_productivity": True}
    plan = {}
    windows = keyed(data["windows.csv"], "window_id")
    for record in data["staffing.csv"]:
        key = (day(record["date"]), record["window_id"])
        if key in plan or key[1] not in windows:
            raise ValueError("排班联合键重复或窗口未知")
        count = number(record["staff_count"], "staff_count")
        if not count.is_integer():
            raise ValueError("staff_count须为整数")
        total = count * number(record["open_hours"], "open_hours")
        absence = number(record["absence_hours"], "absence_hours")
        if absence > total or not math.isfinite(total):
            raise ValueError("排班有效人时不合法")
        plan[key] = total - absence
    activity = defaultdict(lambda: {"ticket_n": 0, "contact_n": 0, "staff_minutes": 0.0})
    scope_index = keyed(rows, "ticket_id")
    for row in rows:
        if row["center"] is not None and row["date"] is not None:
            activity[(row["date"], row["window_id"])]["ticket_n"] += 1
    unassigned_n, unassigned_minutes, cross_day = 0, 0.0, 0
    for contact in data["visits.csv"]:
        row = scope_index.get(contact["ticket_id"])
        if row is None or row["center"] is None:
            unassigned_n += 1
            unassigned_minutes += float(contact["staff_minutes"])
            continue
        key = (day(contact["contact_date"]), row["window_id"])
        activity[key]["contact_n"] += 1
        activity[key]["staff_minutes"] += float(contact["staff_minutes"])
        cross_day += row["date"] is not None and contact["contact_date"] != row["date"]
    keys = set(activity) | set(plan) if config["staffing_coverage"] == "union" else set(activity)
    reports = []
    for key in sorted(keys):
        values = activity.get(key, {"ticket_n": 0, "contact_n": 0, "staff_minutes": 0.0})
        hours = plan.get(key)
        reports.append({"date": key[0], "window_id": key[1], **values,
                        "planned_person_hours": hours, "contact_person_hours": values["staff_minutes"] / 60,
                        "recorded_contact_hours_over_plan": ratio(values["staff_minutes"] / 60, hours) if hours is not None else None,
                        "coverage": "plan_and_activity" if key in plan and key in activity else "plan_without_recorded_activity" if key in plan else "activity_without_plan"})
    assigned_minutes = sum(r["staff_minutes"] for r in reports)
    source_minutes = join_audit["source_contact_minutes"]
    check = math.isclose(assigned_minutes + unassigned_minutes, source_minutes, rel_tol=1e-12, abs_tol=1e-7)
    if not check:
        raise RuntimeError("接触分钟差额无法解释")
    reconciliation = {"input_contact_n": len(data["visits.csv"]),
                      "assigned_contact_n": sum(r["contact_n"] for r in reports), "unassigned_contact_n": unassigned_n,
                      "source_minutes": source_minutes, "assigned_minutes": assigned_minutes,
                      "unassigned_minutes": unassigned_minutes, "minutes_reconciled": check,
                      "unique_plan_window_days": len(plan), "reported_window_days": len(reports),
                      "unassigned_ticket_n": len(rows) - sum(r["ticket_n"] for r in reports),
                      "unknown_registration_date_ticket_n": sum(r["date"] is None for r in rows),
                      "known_plan_person_hours_all": sum(plan.values()),
                      "known_plan_person_hours_in_report": sum(r["planned_person_hours"] for r in reports if r["planned_person_hours"] is not None),
                      "plan_days_without_recorded_activity": len(set(plan) - set(activity)),
                      "activity_days_without_plan": len(set(activity) - set(plan)), "cross_day_contacts": cross_day,
                      "proxy_window_assignment": "contact window is not observed; use ticket window explicitly",
                      "zero_activity_limitation": "no input rows does not prove complete source coverage",
                      "partial_plan_limitation": "known plan total is incomplete if activity days lack plan"}
    return metrics, reports, reconciliation


# 本模块只提供教师参考的一种计算流程，入口为同目录process_reference.py。
