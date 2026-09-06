"""Reconcile ticket, contact and window-day grains before publishing."""
from pathlib import Path
from collections import defaultdict
import importlib.util

def module(number):
    spec = importlib.util.spec_from_file_location("reference_" + number, Path(__file__).resolve().parents[1] / ("lesson-" + number) / "reference.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

u, quality = module("01"), module("03")

def main():
    root = u.student_root()
    extra, audit = quality.clean(root)
    tickets = u.baseline(root) + extra
    assert len({r["ticket_id"] for r in tickets}) == len(tickets)
    ids = {r["ticket_id"] for r in tickets}
    contacts = u.read(root, "service/visits.csv")
    surveys = u.read(root, "service/satisfaction.csv")
    staffing = u.read(root, "service/staffing.csv")
    assert len({r["contact_id"] for r in contacts}) == len(contacts)
    assert len({r["ticket_id"] for r in surveys}) == len(surveys)
    assert len({(r["date"], r["window_id"]) for r in staffing}) == len(staffing)
    by_ticket = defaultdict(list)
    for r in contacts:
        by_ticket[r["ticket_id"]].append(r)
    staff = {(r["date"], r["window_id"]): float(r["staff_count"]) * float(r["open_hours"]) - float(r["absence_hours"]) for r in staffing}
    survey = {r["ticket_id"]: r for r in surveys}
    valid_wait = [r for r in tickets if r["wait"] is not None and not r["abandon"]]
    true_mean = sum(r["wait"] for r in valid_wait) / len(valid_wait)
    duplicated = [r["wait"] for r in valid_wait for _ in by_ticket[r["ticket_id"]]]
    joined_mean = sum(duplicated) / len(duplicated)
    windows_days = defaultdict(lambda: {"tickets": 0, "contacts": 0, "staff_minutes": 0, "completion_known": 0, "completed": 0, "responses": 0, "satisfied": 0})
    unknown_window = 0
    naive_staff_hours = 0
    for r in tickets:
        key = (r["date"], r["window_id"])
        cs = by_ticket[r["ticket_id"]]
        if key not in staff:
            unknown_window += 1
            continue
        g = windows_days[key]
        g["tickets"] += 1
        g["contacts"] += len(cs)
        g["staff_minutes"] += sum(float(c["staff_minutes"]) for c in cs)
        g["completion_known"] += r["completed"] is not None
        g["completed"] += r["completed"] or 0
        score = survey[r["ticket_id"]]["score"]
        g["responses"] += bool(score)
        g["satisfied"] += bool(score) and int(score) >= 4
        naive_staff_hours += len(cs) * staff[key]
    source_minutes = sum(float(r["staff_minutes"]) for r in contacts)
    aggregated_minutes = sum(sum(float(c["staff_minutes"]) for c in by_ticket[tid]) for tid in ids)
    assert abs(source_minutes - aggregated_minutes) < 1e-6
    assert len(tickets) == sum(g["tickets"] for g in windows_days.values()) + unknown_window
    u.emit({"input_unique_tickets": len(tickets), "raw_period_audit": audit, "contact_rows": len(contacts), "contacts_without_ticket": sum(r["ticket_id"] not in ids for r in contacts), "tickets_without_contacts": sum(tid not in by_ticket for tid in ids), "tickets_without_survey": sum(tid not in survey for tid in ids), "unknown_window_tickets_quarantined_for_window_report": unknown_window, "staffing_unique_window_days": len(staff), "reported_window_days": len(windows_days), "source_staff_minutes": source_minutes, "ticket_aggregated_staff_minutes": aggregated_minutes, "unweighted_served_wait_mean": true_mean, "naive_contact_join_wait_mean": joined_mean, "unique_planned_person_hours": sum(staff.values()), "incorrect_hours_after_contact_join": naive_staff_hours, "sample_window_day_reports": [{"date": key[0], "window_id": key[1], "planned_person_hours": staff[key], **g} for key, g in sorted(windows_days.items())][:6], "warning": "Window publication excludes unresolved window identities but retains them in global reconciliation. Planned hours are not measured effort; satisfaction denominators remain respondents."})

if __name__ == "__main__":
    main()
