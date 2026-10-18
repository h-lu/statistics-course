"""Rebuild the historical fixed synthetic population and its public projection."""
from pathlib import Path
import csv
import hashlib
import io
import json
import random

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "student-template/lesson-11/data"
SEED = 20261011
SOURCE_COMMIT = "ce955719b68991166c86fbb1ecae1d203e7a0671"


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def build(destination=DATA):
    destination = Path(destination)
    (destination / "simulator").mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    population = []
    for group, size, need_count, online_rate in [("A", 3200, 1120, .9), ("B", 800, 520, .55)]:
        needs = [1] * need_count + [0] * (size - need_count)
        rng.shuffle(needs)
        for i, need in enumerate(needs, 1):
            population.append([f"{group}{i:04}", group, need, int(rng.random() < online_rate)])
    population_bytes = csv_bytes(["person_id", "group", "need_weekend", "online_frame"], population)
    frame_bytes = csv_bytes(["person_id", "group", "online_frame"], [[r[0], r[1], r[3]] for r in population])
    strata_bytes = csv_bytes(["group", "population_count", "online_count", "invitation_cost_units", "ordinary_response_probability"],
                            [[g, sum(r[1] == g for r in population), sum(r[1] == g and r[3] for r in population), cost, response]
                             for g, cost, response in [("A", 1, .8), ("B", 3, .6)]])
    payloads = {"frame.csv": frame_bytes, "strata.csv": strata_bytes,
                "simulator/weekend_population.csv": population_bytes}
    for relative, content in payloads.items():
        (destination / relative).write_bytes(content)
    hashes = {relative: hashlib.sha256(content).hexdigest() for relative, content in payloads.items()}
    provenance = {
        "population_id": "weekend-4000-20261011-v1",
        "kind": "teaching_synthetic_fixed_finite_population",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "population_seed": SEED,
        "population_n": 4000,
        "group_counts": {"A": 3200, "B": 800},
        "origin_commit": SOURCE_COMMIT,
        "origin_path": "student-template/data/inference-09-14/weekend_population.csv",
        "generation": "The same fixed historical population, not a new population per acquisition",
        "files_sha256": hashes,
        "public_planning_columns": ["person_id", "group", "online_frame"],
        "simulator_only_column": "need_weekend",
        "column_roles": {
            "person_id": "Unique invented unit ID; not a real person",
            "group": "Teaching contact group A/B, not a protected attribute or causal factor",
            "online_frame": "Fixed membership in the online contact frame",
            "need_weekend": "Fixed latent binary need for the same specified weekend; simulation and post-plan audit input"
        },
        "acquisition_rules": {
            "register": "Equal-probability invitations without replacement among all 4000",
            "register_ordinary_response": {"A": .8, "B": .6},
            "ordinary_within_group_independent_of_need": True,
            "register_complete": "Ideal full response; separate comparison, not default reality",
            "web": "Equal-probability invitations without replacement among online_frame=1 only",
            "web_response_given_need": .85,
            "web_response_given_no_need": .25
        },
        "invitation_cost": "Teaching units A=1/B=3 per invitation in every mechanism; excludes follow-up and response costs",
        "audit_protocol": "Choose and save all compared plans from frame.csv before acquisition; inspect simulator outcomes only for post-plan audit. Local file readability is not technical access prevention.",
        "scope": "Synthetic teaching exercise; no real survey observations, personal data, consent records or institutional effects"
    }
    (destination / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return provenance


if __name__ == "__main__":
    result = build()
    print(json.dumps({"population_n": result["population_n"], "population_id": result["population_id"],
                      "files_sha256": result["files_sha256"]}, ensure_ascii=False, indent=2))
