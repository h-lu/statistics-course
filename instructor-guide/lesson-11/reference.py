"""Teacher mechanism checks, not a required student solution or chosen optimum."""
from pathlib import Path
import json
import shutil
from statistics import mean, stdev
import sys
import tempfile

HERE = Path(__file__).resolve().parent
LESSON = HERE.parents[1] / "student-template/lesson-11"
sys.path.insert(0, str(LESSON))
import sampling_tools as tools


def describe(rows):
    group_counts = {g: sum(r["answered"] for r in rows if r["group"] == g) for g in ("A", "B")}
    return {"invited_n": sum(r["invited"] for r in rows),
            "answered_n": sum(r["answered"] for r in rows),
            "respondent_group_counts": group_counts,
            "respondent_rate": tools.response_mean(rows),
            "composition_adjusted_rate": tools.composition_estimate(rows, {"A": 3200, "B": 800}),
            "invitation_cost_units": sum(r["invitation_cost_units"] for r in rows)}


def build_reference(repetitions=100, snapshot_dir=None):
    frame = tools.load_frame()
    mechanisms = ["register_ordinary", "web_voluntary", "register_complete"]
    # Save all three plans before any acquisition/audit in the worked comparison.
    plans = {mode: tools.make_request(frame, mode, 200, 11, 11) for mode in mechanisms}
    examples = {}
    with tempfile.TemporaryDirectory(prefix="lesson11-reference-") as temporary:
        temporary = Path(temporary)
        for mode, plan in plans.items():
            tools.write_request(plan, temporary / f"plan-{mode}.json")
        for mode, plan in plans.items():
            rows, receipt = tools.run_request(plan, temporary / mode)
            traces = {name: next((r for r in rows if condition(r)), None) for name, condition in {
                "outside_frame": lambda r: not r["in_frame"],
                "in_frame_not_invited": lambda r: r["in_frame"] and not r["invited"],
                "invited_not_answered": lambda r: r["invited"] and not r["answered"],
                "answered": lambda r: r["answered"]}.items()}
            examples[mode] = {"request_sha256": tools.request_hash(plan), "summary": describe(rows),
                              "trace": traces, "receipt": receipt,
                              "post_plan_audit": tools.audit_population(plan, temporary / mode)}
            if snapshot_dir is not None:
                source = temporary / mode
                target = Path(snapshot_dir) / mode
                if target.exists():
                    expected = {p.name: p.read_bytes() for p in source.iterdir()}
                    current = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
                    if current != expected:
                        raise ValueError("Existing teacher audit snapshot differs; keep it and choose a new versioned location")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(source, target)
        truth = examples["register_ordinary"]["post_plan_audit"]["population_rate"]
        repeated = {}
        for mode in mechanisms:
            results = []
            for index in range(repetitions):
                plan = tools.make_request(frame, mode, 200, 1000 + index, 2000 + index)
                rows, _ = tools.run_request(plan, temporary / f"{mode}-{index}")
                results.append(describe(rows))
            estimates = [r["composition_adjusted_rate"] for r in results if r["composition_adjusted_rate"] is not None]
            raw = [r["respondent_rate"] for r in results if r["respondent_rate"] is not None]
            repeated[mode] = {"repetitions": repetitions, "invitation_count_each": 200,
                               "mean_respondents": mean(r["answered_n"] for r in results),
                               "mean_invitation_cost": mean(r["invitation_cost_units"] for r in results),
                               "mean_raw_respondent_rate": mean(raw),
                               "mean_adjusted_rate": mean(estimates) if estimates else None,
                               "adjusted_bias_against_fixed_truth": mean(estimates) - truth if estimates else None,
                               "adjusted_repeated_sample_sd": stdev(estimates) if len(estimates) >= 2 else None,
                               "undefined_adjusted_samples": repetitions - len(estimates)}
    return {"scope": "Teacher mechanism demonstration; not a prescribed student plan or optimal survey",
            "population_id": tools.POPULATION_ID, "population_n": 4000,
            "truth": truth, "toy_example_is_different_population": True,
            "same_invitation_count_does_not_fix_cost_or_respondents": True,
            "worked_single_acquisitions": examples, "repeated_mechanism_checks": repeated,
            "interpretation": [
                "One acquisition is not proof of bias or of its absence; the fixed response rules explain the mechanism.",
                "Composition correction assumes respondents can represent their group; the web need-dependent rule violates it.",
                "The repeated-sample SD is dispersion of estimates, not the SD divided by sqrt(repetitions).",
                "Complete response is an ideal benchmark, not a promise it costs only the listed invitations."
            ]}


if __name__ == "__main__":
    result = build_reference(snapshot_dir=HERE / "audit/reference-seed11")
    (HERE / "reference_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"truth": result["truth"], "single_acquisition_summaries": {
        key: value["summary"] for key, value in result["worked_single_acquisitions"].items()},
        "repeated_mechanism_checks": result["repeated_mechanism_checks"]}, ensure_ascii=False, indent=2))
