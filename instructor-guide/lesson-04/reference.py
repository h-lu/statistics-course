"""Competing evaluation profiles; no mandatory composite score."""
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

def main():
    root = u.student_root()
    rows = u.baseline(root)
    thresholds = {r["business_code"]: float(r["reference_wait_minutes"]) for r in u.read(root, "service/business_types.csv")}
    summary = []
    for c in "ABC":
        registered = [r for r in rows if r["center"] == c]
        served = [r for r in registered if not r["abandon"]]
        profile = u.describe([r["wait"] for r in served])
        profile.update({"center": c, "registered": len(registered), "abandon_rate": sum(r["abandon"] for r in registered) / len(registered), "served_over15": sum(r["wait"] > 15 for r in served) / len(served), "served_over_business_line": sum(r["wait"] > thresholds[r["business_code"]] for r in served) / len(served), "registered_bad_experience": sum(r["abandon"] or r["wait"] > thresholds[r["business_code"]] for r in registered) / len(registered), "case_share": sum(r["business_code"] == "case" for r in registered) / len(registered)})
        summary.append(profile)
    orders = {metric: [r["center"] for r in sorted(summary, key=lambda r: r[metric])] for metric in ("mean", "median", "p90", "served_over15", "served_over_business_line", "registered_bad_experience")}
    u.emit({"profiles": summary, "lower_is_better_orders": orders, "interpretation": "Orders encode different targets. Business-specific standards are a policy choice, not an automatic correction of quality or effort."})

if __name__ == "__main__":
    main()
