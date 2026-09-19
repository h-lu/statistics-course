"""Compare consequential definitions without declaring a unique target."""
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def difference(left, right):
    return None if left is None or right is None else left - right


def build_result(rows):
    scenarios = {
        "all_registered_elapsed": lambda r: True,
        "served_only": lambda r: r["abandon"] == 0,
        "served_basic": lambda r: r["abandon"] == 0 and r["business_code"] == "basic",
        "served_case": lambda r: r["abandon"] == 0 and r["business_code"] == "case",
        "served_morning": lambda r: r["abandon"] == 0 and r["arrival_period"] == "上午",
        "served_afternoon": lambda r: r["abandon"] == 0 and r["arrival_period"] == "下午",
    }
    definitions = {
        "all_registered_elapsed": "All registered tickets: elapsed time until service or departure, not time to service for everyone.",
        "served_only": "Reference population: all non-abandoned tickets in the first period.",
        "served_basic": "Restricts the reference population to basic business; changes the target population.",
        "served_case": "Restricts the reference population to complex cases; changes the target population.",
        "served_morning": "Restricts the reference population to morning arrivals.",
        "served_afternoon": "Restricts the reference population to afternoon arrivals.",
    }
    result = []
    for name, include in scenarios.items():
        summaries = {c: u.describe([r["wait"] for r in rows if r["center"] == c and include(r)])
                     for c in "ABC"}
        result.append({
            "scenario": name, "definition": definitions[name], "by_center": summaries,
            **{f"A_minus_B_{metric}": difference(summaries["A"][metric], summaries["B"][metric])
               for metric in ("mean", "median", "p90")},
        })
    return {
        "synthetic_data": True, "quantile_method": "linear (n-1)p", "difference_unit": "minutes",
        "comparisons": result,
        "warning": "These definitions answer related but not identical questions. Mean, median and P90 are different targets. Reusing this period for discovery and sensitivity is exploratory. Empty groups produce null differences, not zero effects.",
    }


def main():
    u.emit(build_result(u.baseline(u.student_root())))


if __name__ == "__main__":
    main()
