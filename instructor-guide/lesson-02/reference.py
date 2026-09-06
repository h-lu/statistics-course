"""Compare consequential definitions without declaring a unique target."""
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

def main():
    root = u.student_root()
    rows = u.baseline(root)
    scenarios = {
        "all_registered_elapsed": lambda r: True,
        "served_only": lambda r: not r["abandon"],
        "served_basic": lambda r: not r["abandon"] and r["business_code"] == "basic",
        "served_case": lambda r: not r["abandon"] and r["business_code"] == "case",
        "served_morning": lambda r: not r["abandon"] and r["arrival_period"] == "上午",
        "served_afternoon": lambda r: not r["abandon"] and r["arrival_period"] == "下午",
    }
    result = []
    for name, include in scenarios.items():
        summaries = {c: u.describe([r["wait"] for r in rows if r["center"] == c and include(r)]) for c in "ABC"}
        result.append({"scenario": name, "by_center": summaries, "A_minus_B_mean": summaries["A"]["mean"] - summaries["B"]["mean"], "A_minus_B_median": summaries["A"]["median"] - summaries["B"]["median"], "A_minus_B_p90": summaries["A"]["p90"] - summaries["B"]["p90"]})
    u.emit({"quantile_method": "linear (n-1)p", "comparisons": result, "warning": "These definitions answer related but not identical questions. Reusing this period for discovery and sensitivity is exploratory."})

if __name__ == "__main__":
    main()
