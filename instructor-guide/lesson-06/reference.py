"""Marginal, stratified and directly standardized comparisons."""
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def standardized_rate(strata, case_weight):
    """A positive-weight missing stratum is unidentified; never fill it with 0."""
    total = 0.0
    for business, weight in (("basic", 1 - case_weight), ("case", case_weight)):
        if weight == 0:
            continue
        value = strata[business]["rate"]
        if value is None:
            return None
        total += weight * value
    return total


def build_result(rows):
    if any(r["center"] not in ("A", "B", "C") or r["business_code"] not in ("basic", "case")
           or r["completed"] not in (0, 1) for r in rows):
        raise ValueError("Unexpected center, business code or completion status")
    groups = {}
    for c in "ABC":
        group = [r for r in rows if r["center"] == c]
        strata = {}
        for s in ("basic", "case"):
            values = [r["completed"] for r in group if r["business_code"] == s]
            strata[s] = {"n": len(values), "completed": sum(values), "rate": u.rate(sum(values), len(values))}
        groups[c] = {"n": len(group), "overall": u.rate(sum(r["completed"] for r in group), len(group)),
                     "case_share": u.rate(strata["case"]["n"], len(group)), "strata": strata}
    pooled_case = u.rate(sum(r["business_code"] == "case" for r in rows), len(rows))
    weights = {0, .25, .5, .75, 1}
    if pooled_case is not None:
        weights.add(pooled_case)
    standardized = []
    for w in sorted(weights):
        rates = {c: standardized_rate(groups[c]["strata"], w) for c in "ABC"}
        ordered = sorted((c for c in rates if rates[c] is not None), key=rates.get, reverse=True)
        tiers = []
        for center in ordered:
            if not tiers or rates[center] != rates[tiers[-1][0]]:
                tiers.append([])
            tiers[-1].append(center)
        standardized.append({"common_case_weight": w, "rates": rates, "order_high_to_low": ordered,
                             "ties_high_to_low": tiers, "undefined_centers": [c for c in rates if rates[c] is None]})
    a, b = groups["A"], groups["B"]
    values = [g["overall"] for g in (a, b)] + [g["strata"][s]["rate"] for g in (a, b) for s in ("basic", "case")]
    simpson_ab = None
    if all(value is not None for value in values):
        overall_difference = a["overall"] - b["overall"]
        simpson_ab = all(overall_difference * (a["strata"][s]["rate"] - b["strata"][s]["rate"]) < 0
                         for s in ("basic", "case"))
    return {"centers": groups, "pooled_case_weight": pooled_case, "standardized": standardized,
            "simpson_A_B": simpson_ab,
            "warning": "A missing positive-weight stratum produces null, not zero. Zero-weight strata do not enter that target. Exact ties share a tier; order within a tier is not a ranking. Standardization is not an identified intervention effect."}


def main():
    u.emit(build_result(u.baseline(u.student_root())))


if __name__ == "__main__":
    main()
