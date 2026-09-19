"""Reconcile tickets, contacts and window-days without dropping unknown records."""
from pathlib import Path
from collections import defaultdict
from datetime import date
import importlib.util
import math


def module(number):
    spec = importlib.util.spec_from_file_location("reference_" + number, Path(__file__).resolve().parents[1] / ("lesson-" + number) / "reference.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


u, quality, response = module("01"), module("03"), module("07")


def nonnegative(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field}: {value!r}") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return number


def checked_date(value, field):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Missing or invalid {field}: {value!r}") from error
    if parsed.isoformat() != value:
        raise ValueError(f"Use YYYY-MM-DD for {field}")
    return value


def empty_day():
    return {"tickets": 0, "contacts": 0, "staff_minutes": 0,
            "completion_known": 0, "completed": 0, "responses": 0, "satisfied": 0}


def build_result(tickets, contacts, surveys, staffing, windows, audit):
    ticket_index = u.keyed(tickets, "ticket_id")
    u.keyed(contacts, "contact_id")
    window_index = u.keyed(windows, "window_id")
    tickets = response.attach_surveys(tickets, surveys)
    ids = set(ticket_index)
    by_ticket = defaultdict(list)
    for row in contacts:
        by_ticket[row["ticket_id"]].append(row)
    staff = {}
    for row in staffing:
        key = (checked_date(row.get("date"), "staffing date"), row["window_id"])
        if key in staff or row["window_id"] not in window_index:
            raise ValueError(f"Duplicate or unknown staffing window/date: {key}")
        count = nonnegative(row["staff_count"], "staff_count")
        if not count.is_integer():
            raise ValueError("staff_count must be an integer")
        planned = count * nonnegative(row["open_hours"], "open_hours")
        absence = nonnegative(row["absence_hours"], "absence_hours")
        if not math.isfinite(planned) or absence > planned:
            raise ValueError(f"Invalid planned hours or absence exceeds planned hours: {key}")
        staff[key] = planned - absence

    valid_wait = [r for r in tickets if r["wait"] is not None and r["abandon"] == 0]
    true_mean = u.describe([r["wait"] for r in valid_wait])["mean"]
    # .get() does not create empty entries, so later missing-contact counts stay valid.
    duplicated = [r["wait"] for r in valid_wait for _ in by_ticket.get(r["ticket_id"], ())]
    joined_mean = u.describe(duplicated)["mean"]
    # Begin with every planned window-day, including days without recorded activity.
    window_days = {key: empty_day() for key in staff}
    unknown_window, missing_ticket_staffing, naive_staff_hours = 0, 0, 0
    for row in tickets:
        key = (checked_date(row.get("date"), "ticket date"), row["window_id"])
        if row["window_id"] not in window_index:
            unknown_window += 1
            continue
        if key not in staff:
            missing_ticket_staffing += 1
        group = window_days.setdefault(key, empty_day())
        group["tickets"] += 1
        group["completion_known"] += row["completed"] is not None
        group["completed"] += row["completed"] if row["completed"] is not None else 0
        group["responses"] += row["score"] is not None
        group["satisfied"] += row["score"] is not None and row["score"] >= 4
        # Deliberately incorrect join example, not the published plan total.
        naive_staff_hours += len(by_ticket.get(row["ticket_id"], ())) * staff.get(key, 0)

    source_minutes, ticket_minutes, unassigned_minutes, orphan_minutes = 0.0, 0.0, 0.0, 0.0
    orphan_contacts, unassigned_contacts, missing_contact_staffing, cross_day_contacts = 0, 0, 0, 0
    for contact in contacts:
        minutes = nonnegative(contact["staff_minutes"], "staff_minutes")
        contact_date = checked_date(contact.get("contact_date"), "contact_date")
        source_minutes += minutes
        ticket = ticket_index.get(contact["ticket_id"])
        if ticket is None:
            orphan_contacts += 1
            orphan_minutes += minutes
        else:
            ticket_minutes += minutes
            cross_day_contacts += contact_date != ticket["date"]
        if ticket is None or ticket["window_id"] not in window_index:
            unassigned_contacts += 1
            unassigned_minutes += minutes
            continue
        # Work belongs to the contact's date, not to the ticket's registration date.
        key = (contact_date, ticket["window_id"])
        if key not in staff:
            missing_contact_staffing += 1
        group = window_days.setdefault(key, empty_day())
        group["contacts"] += 1
        group["staff_minutes"] += minutes

    assigned_minutes = sum(g["staff_minutes"] for g in window_days.values())
    if not math.isclose(source_minutes, ticket_minutes + orphan_minutes, rel_tol=1e-12, abs_tol=1e-6):
        raise RuntimeError("Contact-to-ticket minutes do not reconcile")
    if not math.isclose(source_minutes, assigned_minutes + unassigned_minutes, rel_tol=1e-12, abs_tol=1e-6):
        raise RuntimeError("Assigned and unassigned contact minutes do not reconcile")
    if len(tickets) != sum(g["tickets"] for g in window_days.values()) + unknown_window:
        raise RuntimeError("Ticket counts do not reconcile")
    if len(contacts) != sum(g["contacts"] for g in window_days.values()) + unassigned_contacts:
        raise RuntimeError("Contact counts do not reconcile")
    reports = [{"date": key[0], "window_id": key[1], "planned_person_hours": staff.get(key), **group}
               for key, group in sorted(window_days.items())]
    return {
        "input_unique_tickets": len(tickets), "raw_period_audit": audit, "contact_rows": len(contacts),
        "contacts_without_ticket": orphan_contacts,
        "tickets_without_contacts": sum(not by_ticket.get(tid) for tid in ids),
        "tickets_without_survey": sum(not r["survey_matched"] for r in tickets),
        "unknown_window_tickets_quarantined_for_window_report": unknown_window,
        "tickets_with_missing_staffing": missing_ticket_staffing,
        "contacts_with_missing_staffing": missing_contact_staffing,
        "cross_day_contacts": cross_day_contacts,
        "staffing_unique_window_days": len(staff), "reported_window_days": len(window_days),
        "source_staff_minutes": source_minutes, "ticket_aggregated_staff_minutes": ticket_minutes,
        "orphan_contact_staff_minutes": orphan_minutes,
        "window_assigned_staff_minutes": assigned_minutes,
        "unassigned_contact_rows": unassigned_contacts, "unassigned_contact_staff_minutes": unassigned_minutes,
        "unweighted_served_wait_mean": true_mean, "naive_contact_join_wait_mean": joined_mean,
        "unique_planned_person_hours": sum(staff.values()), "incorrect_hours_after_contact_join": naive_staff_hours,
        "sample_window_day_reports": reports[:6], "window_day_reports": reports,
        "warning": "Contact work is grouped by contact_date; assigning its window from the ticket is an explicit proxy because actual contact window is not recorded. Unknown windows and orphan contacts stay in unassigned totals. Known-window activity without staffing is retained with planned_person_hours=null, not zero. Zero activity means no records in these inputs, not proof of complete coverage. Planned hours are not measured effort; satisfaction uses valid responses only.",
    }


def main():
    root = u.student_root()
    extra, audit = quality.clean(root)
    u.emit(build_result(u.baseline(root) + extra,
                        u.read(root, "service/visits.csv"), u.read(root, "service/satisfaction.csv"),
                        u.read(root, "service/staffing.csv"), u.read(root, "service/windows.csv"), audit))


if __name__ == "__main__":
    main()
