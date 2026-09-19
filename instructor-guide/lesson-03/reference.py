"""Version-aware cleaning reference; every unique ticket remains represented."""
from pathlib import Path
from collections import Counter, defaultdict
import importlib.util
import math

spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def parse_wait(raw_value, unit):
    """Recognize missing codes before conversion; never pass NaN/Inf into JSON."""
    if raw_value is None or not raw_value.strip():
        return None, "wait_not_measured"
    try:
        value = float(raw_value)
    except ValueError:
        return None, "wait_invalid"
    if value in (999, -1):
        return None, "wait_not_measured"
    if not math.isfinite(value) or value < 0 or unit not in ("minute", "second"):
        return None, "wait_invalid"
    return (value / 60 if unit == "second" else value), None


def clean(root):
    raw = u.read(root, "service/tickets_raw.csv")
    windows = u.keyed(u.read(root, "service/windows.csv"), "window_id")
    business = u.keyed(u.read(root, "service/business_types.csv"), "business_code")
    groups = defaultdict(list)
    for row in raw:
        tid = row.get("ticket_id")
        if not tid or not tid.strip():
            raise ValueError("Empty ticket_id: the analysis unit cannot be determined")
        try:
            revision = int(row["export_revision"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid export_revision: {tid}") from error
        if revision < 1:
            raise ValueError(f"Invalid export_revision: {tid}")
        groups[tid].append(row)
    result, counts = [], Counter()
    for tid, candidates in sorted(groups.items()):
        unique = {tuple(sorted(r.items())) for r in candidates}
        counts["exact_duplicate_rows"] += len(candidates) - len(unique)
        version = max(int(r["export_revision"]) for r in candidates)
        latest = [r for r in candidates if int(r["export_revision"]) == version]
        if len({tuple(sorted(r.items())) for r in latest}) != 1:
            raise ValueError(f"Conflicting latest revision: {tid}")
        counts["superseded_revision_rows"] += len(unique) - 1
        counts["tickets_with_revision"] += int(version > 1)
        r = dict(latest[0])
        flags = []
        wait, wait_flag = parse_wait(r.get("wait_minutes"), r.get("wait_unit"))
        if wait_flag:
            flags.append(wait_flag)
        else:
            counts["converted_from_seconds"] += int(r["wait_unit"] == "second")
        window = windows.get(r["window_id"])
        center = window["center"] if window else None
        if not center:
            center = None
            flags.append("unknown_window")
        if r["business_code"] not in business:
            flags.append("unknown_business")
        completed = int(r["completed_same_day"]) if r.get("completed_same_day") in ("0", "1") else None
        if completed is None:
            flags.append("missing_completion")
        abandon = int(r["abandoned"]) if r.get("abandoned") in ("0", "1") else None
        if abandon is None:
            flags.append("missing_abandonment")
        counts.update(flags)
        result.append({**r, "wait": wait, "center": center, "completed": completed,
                       "abandon": abandon, "quality_flags": flags})
    # Decomposition counts rows, unlike tickets_with_revision, which counts tickets.
    if len(raw) != len(result) + counts["exact_duplicate_rows"] + counts["superseded_revision_rows"]:
        raise RuntimeError("Raw-row reconciliation failed")
    return result, {"raw_rows": len(raw), "unique_tickets": len(groups), **dict(counts)}


def build_result(rows, audit):
    valid_wait = [r for r in rows if r["wait"] is not None and r["abandon"] == 0]
    valid_completion = [r for r in rows if r["completed"] is not None]
    complete_case = [r for r in rows if not r["quality_flags"]]
    successes = sum(r["completed"] for r in valid_completion)
    cc_successes = sum(r["completed"] for r in complete_case)
    unresolved = [{"ticket_id": r["ticket_id"], "flags": r["quality_flags"]}
                  for r in rows if r["quality_flags"]]
    by_window = Counter(r["window_id"] for r in rows if r["center"] is not None)
    return {
        "synthetic_data": True, "audit": audit,
        "served_valid_wait": u.describe([r["wait"] for r in valid_wait]),
        "completion_specific_denominator": len(valid_completion), "completion_successes": successes,
        "completion_specific_rate": u.rate(successes, len(valid_completion)),
        "complete_case_denominator": len(complete_case), "complete_case_successes": cc_successes,
        "complete_case_completion_rate": u.rate(cc_successes, len(complete_case)),
        "complete_case_served_wait": u.describe([r["wait"] for r in complete_case if r["abandon"] == 0]),
        "window_ticket_counts": dict(sorted(by_window.items())),
        "known_window_denominator": sum(by_window.values()),
        "unknown_window_tickets": len(rows) - sum(by_window.values()),
        "unresolved_examples": unresolved[:10], "unresolved_records": unresolved,
        "warning": "Different purposes can retain different valid subsets. Neither deletion nor imputation creates observed truth. Window ticket counts are not staff effort. Unknown abandonment is not evidence of service. null rates have zero denominators.",
    }


def main():
    u.emit(build_result(*clean(u.student_root())))


if __name__ == "__main__":
    main()
