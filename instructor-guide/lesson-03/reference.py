"""Version-aware cleaning reference; every unique ticket remains represented."""
from pathlib import Path
from collections import Counter, defaultdict
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

def clean(root):
    raw = u.read(root, "service/tickets_raw.csv")
    windows = {r["window_id"]: r["center"] for r in u.read(root, "service/windows.csv")}
    business = {r["business_code"] for r in u.read(root, "service/business_types.csv")}
    groups = defaultdict(list)
    for row in raw:
        groups[row["ticket_id"]].append(row)
    result, counts = [], Counter()
    for tid, candidates in sorted(groups.items()):
        unique = {tuple(sorted(r.items())) for r in candidates}
        counts["exact_duplicate_rows"] += len(candidates) - len(unique)
        version = max(int(r["export_revision"]) for r in candidates)
        latest = [r for r in candidates if int(r["export_revision"]) == version]
        if len({tuple(sorted(r.items())) for r in latest}) != 1:
            raise ValueError(f"Conflicting latest revision: {tid}")
        counts["tickets_with_revision"] += int(version > 1)
        r = dict(latest[0])
        flags = []
        value = float(r["wait_minutes"])
        if value in (999, -1):
            wait = None
            flags.append("wait_not_measured")
        elif r["wait_unit"] not in ("minute", "second") or value < 0:
            wait = None
            flags.append("wait_invalid")
        else:
            wait = value / 60 if r["wait_unit"] == "second" else value
            counts["converted_from_seconds"] += int(r["wait_unit"] == "second")
        center = windows.get(r["window_id"])
        if center is None:
            flags.append("unknown_window")
        if r["business_code"] not in business:
            flags.append("unknown_business")
        completed = int(r["completed_same_day"]) if r["completed_same_day"] in ("0", "1") else None
        if completed is None:
            flags.append("missing_completion")
        counts.update(flags)
        result.append({**r, "wait": wait, "center": center, "completed": completed, "abandon": int(r["abandoned"]), "quality_flags": flags})
    assert len(result) == len(groups)
    return result, {"raw_rows": len(raw), "unique_tickets": len(groups), **dict(counts)}

def main():
    root = u.student_root()
    rows, audit = clean(root)
    valid_wait = [r for r in rows if r["wait"] is not None and not r["abandon"]]
    valid_completion = [r for r in rows if r["completed"] is not None]
    complete_case = [r for r in rows if not r["quality_flags"]]
    all_rate = sum(r["completed"] for r in valid_completion) / len(valid_completion)
    cc_rate = sum(r["completed"] for r in complete_case) / len(complete_case)
    u.emit({"audit": audit, "served_valid_wait": u.describe([r["wait"] for r in valid_wait]), "completion_specific_denominator": len(valid_completion), "completion_specific_rate": all_rate, "complete_case_denominator": len(complete_case), "complete_case_completion_rate": cc_rate, "complete_case_served_wait": u.describe([r["wait"] for r in complete_case if not r["abandon"]]), "unresolved_examples": [{"ticket_id": r["ticket_id"], "flags": r["quality_flags"]} for r in rows if r["quality_flags"]][:10], "warning": "Different purposes can retain different valid subsets. Neither deletion nor imputation creates observed truth."})

if __name__ == "__main__":
    main()
