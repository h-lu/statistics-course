"""Competing evaluation profiles; no mandatory composite score."""
from pathlib import Path
import importlib.util
import math

spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def metric_tiers(profiles, metric):
    """Exact ties share a tier; undefined metrics are not assigned a rank."""
    tiers = []
    previous = None
    for row in sorted((r for r in profiles if r[metric] is not None), key=lambda r: r[metric]):
        if not tiers or row[metric] != previous:
            tiers.append([])
        tiers[-1].append(row["center"])
        previous = row[metric]
    return tiers


def build_result(rows, thresholds):
    if any(not math.isfinite(value) or value < 0 for value in thresholds.values()):
        raise ValueError("Business thresholds must be finite and nonnegative")
    unknown = {r["business_code"] for r in rows} - thresholds.keys()
    if unknown:
        raise ValueError(f"Missing business thresholds: {sorted(unknown)}")
    summary = []
    for center in "ABC":
        registered = [r for r in rows if r["center"] == center]
        served = [r for r in registered if r["abandon"] == 0]
        over15 = sum(r["wait"] > 15 for r in served)
        over_business = sum(r["wait"] > thresholds[r["business_code"]] for r in served)
        bad = sum(bool(r["abandon"]) or r["wait"] > thresholds[r["business_code"]] for r in registered)
        profile = u.describe([r["wait"] for r in served])
        profile.update({
            "center": center, "registered": len(registered),
            "abandon_rate": u.rate(sum(r["abandon"] for r in registered), len(registered)),
            "served_over15_count": over15, "served_over15": u.rate(over15, len(served)),
            "served_over_business_line_count": over_business,
            "served_over_business_line": u.rate(over_business, len(served)),
            "registered_bad_experience_count": bad,
            "registered_bad_experience": u.rate(bad, len(registered)),
            "case_share": u.rate(sum(r["business_code"] == "case" for r in registered), len(registered)),
        })
        summary.append(profile)
    metrics = ("mean", "median", "p90", "served_over15", "served_over_business_line", "registered_bad_experience")
    tiers = {metric: metric_tiers(summary, metric) for metric in metrics}
    return {
        "synthetic_data": True, "profiles": summary,
        "lower_is_better_orders": {metric: [c for tier in groups for c in tier] for metric, groups in tiers.items()},
        "lower_is_better_tiers": tiers,
        "undefined_centers": {metric: [r["center"] for r in summary if r[metric] is None] for metric in metrics},
        "rule_definitions": {
            "served_over15": "wait > 15 among non-abandoned tickets; equality is not over the line.",
            "served_over_business_line": "wait > the stated business threshold among non-abandoned tickets.",
            "business_thresholds_minutes": thresholds,
            "registered_bad_experience": "abandoned OR over the business line, counted once per registered ticket; a declared composite, not all aspects of experience.",
        },
        "interpretation": "Orders encode different targets. Business-specific standards are a policy choice, not an automatic correction of quality or effort. Exact ties share a tier; within-tier display order is not a preference. These descriptive tiers carry no significance claim.",
    }


def main():
    root = u.student_root()
    business = u.keyed(u.read(root, "service/business_types.csv"), "business_code")
    thresholds = {code: float(row["reference_wait_minutes"]) for code, row in business.items()}
    u.emit(build_result(u.baseline(root), thresholds))


if __name__ == "__main__":
    main()
