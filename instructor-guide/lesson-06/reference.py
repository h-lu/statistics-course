"""Marginal, stratified and directly standardized comparisons."""
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

def main():
    root = u.student_root()
    rows = u.baseline(root)
    groups = {}
    for c in "ABC":
        group = [r for r in rows if r["center"] == c]
        strata = {}
        for s in ("basic", "case"):
            values = [r["completed"] for r in group if r["business_code"] == s]
            strata[s] = {"n": len(values), "completed": sum(values), "rate": sum(values) / len(values)}
        groups[c] = {"n": len(group), "overall": sum(r["completed"] for r in group) / len(group), "case_share": strata["case"]["n"] / len(group), "strata": strata}
    pooled_case = sum(r["business_code"] == "case" for r in rows) / len(rows)
    standardized = []
    for w in sorted({0, .25, .5, .75, 1, pooled_case}):
        rates = {c: (1 - w) * groups[c]["strata"]["basic"]["rate"] + w * groups[c]["strata"]["case"]["rate"] for c in "ABC"}
        standardized.append({"common_case_weight": w, "rates": rates, "order_high_to_low": sorted(rates, key=rates.get, reverse=True)})
    a, b = groups["A"], groups["B"]
    simpson_ab = (a["overall"] - b["overall"]) * (a["strata"]["basic"]["rate"] - b["strata"]["basic"]["rate"]) < 0 and (a["overall"] - b["overall"]) * (a["strata"]["case"]["rate"] - b["strata"]["case"]["rate"]) < 0
    u.emit({"centers": groups, "pooled_case_weight": pooled_case, "standardized": standardized, "simpson_A_B": simpson_ab, "warning": "Rates describe supported strata; standardization is not an identified intervention effect."})

if __name__ == "__main__":
    main()
