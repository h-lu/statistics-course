"""Reference evidence, not a unique recommended conclusion. Standard library only."""
from pathlib import Path
import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict


def student_root(argv=None):
    """Find the monorepo data first; keep the two historical layouts usable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student-root", type=Path)
    args = parser.parse_args(argv)
    workspace = Path(__file__).resolve().parents[2]
    candidates = ([args.student_root] if args.student_root is not None else [
        workspace / "student-template",
        workspace / "lesson-01-first-green",
        workspace / "course-student-template",
    ])
    for candidate in candidates:
        root = candidate.resolve()
        if (root / "data" / "service").is_dir():
            return root
    # L03 may use only the raw export: do not require tickets.csv for all lessons.
    raise FileNotFoundError(
        "Service data directory not found. Pass --student-root pointing at the "
        "student repository containing data/service. Checked: "
        + ", ".join(str(path) for path in candidates)
    )


def read(root, name):
    with (root / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def keyed(rows, key):
    """Reject ambiguous dictionary keys instead of silently overwriting rows."""
    result = {}
    for row in rows:
        value = row.get(key)
        if not value or not value.strip() or value in result:
            raise ValueError(f"Empty or duplicate {key}: {value!r}")
        result[value] = row
    return result


def quantile(values, p):
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Quantile probability must be in [0, 1]")
    if not values:
        return None
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Quantile values must be finite")
    x = sorted(values)
    h = (len(x) - 1) * p
    lo = int(h)
    return x[lo] + (h - lo) * (x[min(lo + 1, len(x) - 1)] - x[lo])


def describe(values):
    if not values:
        return {"n": 0, "mean": None, "median": None, "p90": None, "iqr": None, "std_n": None}
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Descriptive values must be finite")
    return {"n": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values), "p90": quantile(values, .9),
            "iqr": quantile(values, .75) - quantile(values, .25),
            "std_n": statistics.pstdev(values)}


def rate(numerator, denominator):
    """A zero denominator is undefined, not a zero observed rate."""
    return numerator / denominator if denominator else None


def baseline(root):
    windows = keyed(read(root, "service/windows.csv"), "window_id")
    tickets = keyed(read(root, "service/tickets.csv"), "ticket_id")
    rows = []
    for tid, row in tickets.items():
        window = windows.get(row["window_id"])
        if window is None or window["center"] not in "ABC" or len(window["center"]) != 1:
            raise ValueError(f"Unknown window or center: {tid}")
        wait = float(row["wait_minutes"])
        if not math.isfinite(wait) or wait < 0:
            raise ValueError(f"Invalid baseline waiting time: {tid}")
        if row["abandoned"] not in ("0", "1") or row["completed_same_day"] not in ("0", "1"):
            raise ValueError(f"Invalid baseline binary status: {tid}")
        rows.append({**row, "center": window["center"], "wait": wait,
                     "completed": int(row["completed_same_day"]),
                     "abandon": int(row["abandoned"])})
    return rows


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def build_result(rows):
    centers = []
    for center in "ABC":
        group = [r for r in rows if r["center"] == center]
        served = [r for r in group if r["abandon"] == 0]
        abandoned = sum(r["abandon"] for r in group)
        completed = sum(r["completed"] for r in group)
        centers.append({
            "center": center, "registered": len(group),
            "unique_people": len({r["person_id"] for r in group}),
            "abandoned": abandoned, "abandon_rate": rate(abandoned, len(group)),
            "case_share": rate(sum(r["business_code"] == "case" for r in group), len(group)),
            "served_wait": describe([r["wait"] for r in served]),
            "same_day_completed": completed, "same_day_rate": rate(completed, len(group)),
        })
    periods = {period: describe([r["wait"] for r in rows
                                if r["arrival_period"] == period and r["abandon"] == 0])
               for period in ("上午", "下午")}
    return {
        "synthetic_data": True, "quantile_method": "linear (n-1)p",
        "registered_tickets": len(rows),
        "unique_people_overall": len({r["person_id"] for r in rows}),
        "centers": centers, "served_wait_by_period": periods,
        "denominator_notes": {
            "served_wait": "Non-abandoned tickets; n is not a count of unique people.",
            "same_day_rate": "Same-day completed tickets / all registered tickets.",
            "unique_people": "Distinct within each center; center counts need not add to the overall count.",
            "std_n": "Describes observed values with divisor n; not a standard error.",
        },
        "interpretation": "These are descriptive baselines; center, appointment, business mix and time can coexist. No causal conclusion is encoded.",
    }


def main():
    emit(build_result(baseline(student_root())))


if __name__ == "__main__":
    main()
