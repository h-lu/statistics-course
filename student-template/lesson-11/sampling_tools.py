"""Local acquisition tools, not a completed survey comparison.

Choose invitations from frame.csv only. The simulator reads latent outcomes to
generate responses; its public result exposes an outcome only for respondents.
The local population file is an audit input, not an access-control boundary.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import random
from statistics import mean

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
POPULATION_ID = "weekend-4000-20261011-v1"
PROTOCOL = "lesson11-acquisition-v1"
MECHANISMS = {"register_ordinary", "register_complete", "web_voluntary"}
FRAME_FIELDS = {"person_id", "group", "online_frame"}
OBSERVATION_FIELDS = ["person_id", "group", "in_frame", "invited", "answered",
                      "invite_probability", "observed_need", "invitation_cost_units"]
REQUEST_FIELDS = {"protocol", "population_id", "mechanism", "n", "selection_seed",
                  "response_seed", "frame_sha256", "invited_ids"}


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def request_hash(request):
    """Fingerprint the actual plan, including its seeds and invitation IDs."""
    return _sha(_json_bytes(request))


def _integer(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")


def _check_frame(frame):
    if not frame or any(set(row) != FRAME_FIELDS for row in frame):
        raise ValueError("Planning accepts only person_id, group, online_frame; no outcome columns")
    if len({row["person_id"] for row in frame}) != len(frame):
        raise ValueError("Frame person IDs must be unique")
    if any(not row["person_id"] or row["group"] not in {"A", "B"}
           or row["online_frame"] not in {0, 1} for row in frame):
        raise ValueError("Invalid frame record")


def load_frame(path=DATA / "frame.csv"):
    """Read the public contact frame. This function never reads latent outcomes."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != FRAME_FIELDS:
            raise ValueError("Use frame.csv for planning, not the simulator population")
        rows = [{**row, "online_frame": int(row["online_frame"])} for row in reader]
    _check_frame(rows)
    return rows


def choose_invites(frame, n, seed, mechanism):
    """Equal-probability sampling without replacement in the chosen frame."""
    _check_frame(frame)
    _integer(n, "n", 1)
    _integer(seed, "selection seed")
    if mechanism not in MECHANISMS:
        raise ValueError("Unknown acquisition mechanism")
    eligible = frame if mechanism != "web_voluntary" else [r for r in frame if r["online_frame"]]
    if n > len(eligible):
        raise ValueError("Invitation count exceeds the selected frame")
    return sorted(random.Random(seed).sample([r["person_id"] for r in eligible], n))


def make_request(frame, mechanism, n, selection_seed, response_seed):
    """Create a reproducible plan before acquisition; does not open the population."""
    _integer(response_seed, "response seed")
    public = load_frame()
    if frame != public:
        raise ValueError("Formal requests must use this lesson's unchanged public frame")
    invited = choose_invites(frame, n, selection_seed, mechanism)
    return {"protocol": PROTOCOL, "population_id": POPULATION_ID, "mechanism": mechanism,
            "n": n, "selection_seed": selection_seed, "response_seed": response_seed,
            "frame_sha256": _sha((DATA / "frame.csv").read_bytes()), "invited_ids": invited}


def validate_request(request):
    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise ValueError("Request fields do not match the acquisition contract")
    expected = make_request(load_frame(), request["mechanism"], request["n"],
                            request["selection_seed"], request["response_seed"])
    if request != expected:
        raise ValueError("Plan, frame identity or invitation list was changed")


def write_request(request, path):
    """Save a plan without replacing a previously written plan."""
    validate_request(request)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(_json_bytes(request))
    return request_hash(request)


def _population():
    # Internal simulation/audit input: never used by choose_invites/make_request.
    provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    expected = provenance["files_sha256"]["simulator/weekend_population.csv"]
    if _sha((DATA / "simulator/weekend_population.csv").read_bytes()) != expected:
        raise ValueError("Keep the fixed simulator population unchanged")
    with (DATA / "simulator/weekend_population.csv").open(encoding="utf-8", newline="") as handle:
        rows = [{**r, "need_weekend": int(r["need_weekend"]), "online_frame": int(r["online_frame"])}
                for r in csv.DictReader(handle)]
    if [{k: r[k] for k in FRAME_FIELDS} for r in rows] != load_frame():
        raise ValueError("Simulator population and public frame disagree")
    if any(r["need_weekend"] not in {0, 1} for r in rows):
        raise ValueError("Simulator need values must be binary")
    return rows


def _costs():
    with (DATA / "strata.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    costs = {r["group"]: int(r["invitation_cost_units"]) for r in rows}
    if set(costs) != {"A", "B"} or any(value < 0 for value in costs.values()):
        raise ValueError("Invalid group invitation costs")
    return costs


def run_request(request, output_dir):
    """Simulate one chosen acquisition; write raw observations, not a recommendation.

    All comparison plans should already be saved. Keep the returned directory;
    re-running uses a fresh directory and never replaces earlier observations.
    """
    validate_request(request)
    population = _population()
    mechanism = request["mechanism"]
    invited = set(request["invited_ids"])
    eligible_count = sum(mechanism != "web_voluntary" or r["online_frame"] for r in population)
    rng = random.Random(request["response_seed"])
    costs = _costs()
    observations = []
    for row in population:
        eligible = mechanism != "web_voluntary" or bool(row["online_frame"])
        selected = row["person_id"] in invited
        # Do not return individual response probabilities: for web responses
        # they would disclose an otherwise unobserved latent need value.
        probability = ((.85 if row["need_weekend"] else .25) if mechanism == "web_voluntary"
                       else 1.0 if mechanism == "register_complete" else {"A": .8, "B": .6}[row["group"]])
        answered = selected and rng.random() < probability
        observations.append({"person_id": row["person_id"], "group": row["group"],
                             "in_frame": int(eligible), "invited": int(selected), "answered": int(answered),
                             "invite_probability": request["n"] / eligible_count if eligible else 0,
                             "observed_need": row["need_weekend"] if answered else None,
                             "invitation_cost_units": costs[row["group"]] if selected else 0})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / "request.json").write_bytes(_json_bytes(request))
    observations_path = output / "observations.csv"
    with observations_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OBSERVATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(observations)
    receipt = {"protocol": PROTOCOL, "population_id": POPULATION_ID,
               "request_sha256": request_hash(request), "frame_sha256": request["frame_sha256"],
               "observations_sha256": _sha(observations_path.read_bytes()),
               "mechanism": mechanism, "invited": len(invited),
               "responded": sum(r["answered"] for r in observations),
               "invitation_cost_units": sum(r["invitation_cost_units"] for r in observations),
               "cost_scope": "Invitations only; response counts and follow-up costs are not guaranteed",
               "audit_released": False, "synthetic_teaching_data": True}
    (output / "receipt.json").write_bytes(_json_bytes(receipt))
    return observations, receipt


def read_observations(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != OBSERVATION_FIELDS:
            raise ValueError("Observation columns do not match this lesson's contract")
        rows = []
        for raw in reader:
            row = dict(raw)
            for key in ("in_frame", "invited", "answered", "invitation_cost_units"):
                row[key] = int(row[key])
            row["invite_probability"] = float(row["invite_probability"])
            row["observed_need"] = None if row["observed_need"] == "" else int(row["observed_need"])
            if any(row[key] not in {0, 1} for key in ("in_frame", "invited", "answered")):
                raise ValueError("Frame, invitation and response flags must be binary")
            if (row["answered"] and row["observed_need"] not in {0, 1}) or (not row["answered"] and row["observed_need"] is not None):
                raise ValueError("An outcome is observed exactly when the person answers")
            if row["answered"] and not row["invited"]:
                raise ValueError("An uninvited person cannot answer this acquisition")
            rows.append(row)
    return rows


def response_mean(rows, group=None):
    """Descriptive proportion among respondents; no representativeness claim."""
    values = [r["observed_need"] for r in rows if r["answered"] and (group is None or r["group"] == group)]
    return mean(values) if values else None


def composition_estimate(rows, population_counts):
    """Adjust group shares only. Missing response groups return undefined/None."""
    if not population_counts or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0
                                    for n in population_counts.values()):
        raise ValueError("Population group counts must be positive integers")
    rates = {g: response_mean(rows, g) for g in population_counts}
    if any(rate is None for rate in rates.values()):
        return None
    total = sum(population_counts.values())
    return sum(population_counts[g] / total * rates[g] for g in population_counts)


def audit_population(request, output_dir):
    """Post-plan teaching audit of a completed acquisition, separate from planning.

    This checks the saved request/observation fingerprints. It is a transparent
    classroom protocol, not a claim that the local input file is inaccessible.
    """
    validate_request(request)
    output = Path(output_dir)
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    if receipt["request_sha256"] != request_hash(request):
        raise ValueError("The acquired plan differs from the plan supplied for audit")
    if json.loads((output / "request.json").read_text(encoding="utf-8")) != request:
        raise ValueError("Saved request was changed")
    if _sha((output / "observations.csv").read_bytes()) != receipt["observations_sha256"]:
        raise ValueError("Saved observations were changed")
    population = _population()
    return {"purpose": "Post-plan audit of a fixed synthetic population, not a second sample",
            "population_id": POPULATION_ID, "request_sha256": request_hash(request),
            "population_n": len(population), "population_need_n": sum(r["need_weekend"] for r in population),
            "population_rate": mean(r["need_weekend"] for r in population),
            "group_rates": {g: mean(r["need_weekend"] for r in population if r["group"] == g) for g in ("A", "B")},
            "simulator_input_sha256": _sha((DATA / "simulator/weekend_population.csv").read_bytes())}
