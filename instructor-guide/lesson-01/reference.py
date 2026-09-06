"""Reference evidence, not a unique recommended conclusion. Standard library only."""
from pathlib import Path
import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict

def student_root():
    p = argparse.ArgumentParser()
    p.add_argument("--student-root", type=Path)
    args = p.parse_args()
    if args.student_root:
        root = args.student_root.resolve()
    else:
        workspace = Path(__file__).resolve().parents[2]
        root = workspace / "lesson-01-first-green"
        if not root.is_dir():
            root = workspace / "course-student-template"
    if not (root / "data" / "service" / "tickets.csv").is_file():
        raise FileNotFoundError("Pass --student-root pointing at the V2 student repository")
    return root

def read(root, name):
    with (root / "data" / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def quantile(values, p):
    if not values:
        return None
    x = sorted(values)
    h = (len(x) - 1) * p
    lo = int(h)
    return x[lo] + (h - lo) * (x[min(lo + 1, len(x) - 1)] - x[lo])

def describe(values):
    if not values:
        return {"n": 0, "mean": None, "median": None, "p90": None, "iqr": None, "std_n": None}
    return {"n": len(values), "mean": statistics.mean(values), "median": statistics.median(values), "p90": quantile(values, .9), "iqr": quantile(values, .75) - quantile(values, .25), "std_n": statistics.pstdev(values)}

def baseline(root):
    windows = {r["window_id"]: r["center"] for r in read(root, "service/windows.csv")}
    return [{**r, "center": windows[r["window_id"]], "wait": float(r["wait_minutes"]), "completed": int(r["completed_same_day"]), "abandon": int(r["abandoned"])} for r in read(root, "service/tickets.csv")]

def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))

def main():
    root = student_root()
    rows = baseline(root)
    centers = []
    for center in "ABC":
        group = [r for r in rows if r["center"] == center]
        served = [r for r in group if not r["abandon"]]
        centers.append({"center": center, "registered": len(group), "unique_people": len({r["person_id"] for r in group}), "abandoned": sum(r["abandon"] for r in group), "case_share": sum(r["business_code"] == "case" for r in group) / len(group), "served_wait": describe([r["wait"] for r in served]), "same_day_rate": statistics.mean(r["completed"] for r in group)})
    periods = {period: describe([r["wait"] for r in rows if r["arrival_period"] == period and not r["abandon"]]) for period in ("上午", "下午")}
    emit({"registered_tickets": len(rows), "unique_people_overall": len({r["person_id"] for r in rows}), "centers": centers, "served_wait_by_period": periods, "interpretation": "These are descriptive baselines; center, appointment, business mix and time can coexist. No causal conclusion is encoded."})

if __name__ == "__main__":
    main()
