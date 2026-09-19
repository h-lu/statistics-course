"""Time-separated, capacity-feasible replay of alternative review policies."""
from pathlib import Path
from collections import defaultdict
from datetime import date
import importlib.util
import math
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def checked_date(value):
    """Reject date aliases before grouping quotas or comparing time periods."""
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid date: {value!r}; use YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise ValueError(f"Use YYYY-MM-DD for date: {value!r}")
    return value


def load(root, batch, devices):
    rows = [{**r, **devices[r["device_id"]], "score": float(r["risk_score"]), "label": int(r["failure_within_24h"])} for r in u.read(root, "alerts/" + batch + ".csv")]
    validate_rows(rows)
    return rows


def validate_rows(rows):
    u.keyed(rows, "record_id")
    device_days = set()
    for row in rows:
        key = (checked_date(row["date"]), row["device_id"])
        if any(not str(value).strip() for value in key) or key in device_days:
            raise ValueError("Empty or duplicate device/date")
        device_days.add(key)
        if not str(row["device_class"]).strip():
            raise ValueError("Missing device class")
        if not math.isfinite(row["score"]) or not 0 <= row["score"] <= 100:
            raise ValueError("Risk score must be finite and in [0, 100]")
        if row["label"] not in (0, 1):
            raise ValueError("Failure label must be 0 or 1")
        for field in ("miss_loss", "inspection_cost"):
            if not math.isfinite(row[field]) or row[field] < 0:
                raise ValueError(f"{field} must be finite and nonnegative")


def calibration(rows):
    validate_rows(rows)
    if not rows:
        raise ValueError("Cannot calibrate risk without development records")
    bins, groups = defaultdict(list), defaultdict(list)
    for r in rows:
        bins[(r["device_class"], min(9, int(r["score"] // 10)))].append(r["label"])
        groups[r["device_class"]].append(r["label"])
    def probability(r):
        values = bins[(r["device_class"], min(9, int(r["score"] // 10)))]
        group = groups.get(r["device_class"])
        if not group:
            raise ValueError(f"No development observations for device class: {r['device_class']}")
        prior = sum(group) / len(group)
        return (sum(values) + 20 * prior) / (len(values) + 20)
    return probability

def replay(rows, capacities, probability, policy, capacity_multiplier=1, effectiveness=.85):
    validate_rows(rows)
    if policy not in {"none", "score", "score_times_loss", "estimated_net_benefit"}:
        raise ValueError(f"Unknown policy: {policy}")
    # This argument reduces the supplied capacity; increased capacity requires
    # an explicitly changed capacity table, not silently borrowing future slots.
    if not math.isfinite(capacity_multiplier) or not 0 <= capacity_multiplier <= 1:
        raise ValueError("capacity_multiplier must be in [0, 1]")
    if not math.isfinite(effectiveness) or not 0 <= effectiveness <= 1:
        raise ValueError("effectiveness must be in [0, 1]")
    for day, capacity in capacities.items():
        checked_date(day)
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
            raise ValueError(f"Capacity must be a nonnegative integer: {day}")
    for day in {r["date"] for r in rows}:
        if day not in capacities:
            raise ValueError(f"Missing capacity for date: {day}")
    days = defaultdict(list)
    for r in rows:
        days[r["date"]].append(r)
    counts = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    total_loss, reviews, missed_loss, available = 0.0, 0, 0.0, 0
    by_group = defaultdict(lambda: {"n": 0, "reviewed": 0, "faults": 0, "missed": 0, "loss": 0.0})
    for day, records in sorted(days.items()):
        k = int(capacities[day] * capacity_multiplier)
        available += k
        def gain(r):
            if policy == "score":
                return r["score"]
            if policy == "score_times_loss":
                return r["score"] / 100 * effectiveness * r["miss_loss"] - r["inspection_cost"]
            if policy == "estimated_net_benefit":
                p = probability(r)
                if not math.isfinite(p) or not 0 <= p <= 1:
                    raise ValueError("Estimated probability must be in [0, 1]")
                return p * effectiveness * r["miss_loss"] - r["inspection_cost"]
            return -1
        gains = {r["record_id"]: gain(r) for r in records}
        ordered = sorted(records, key=lambda r: (-gains[r["record_id"]], r["device_id"]))
        selected = {r["record_id"] for r in ordered[:k] if gains[r["record_id"]] > 0}
        if len(selected) > k:
            raise RuntimeError("Daily capacity reconciliation failed")
        reviews += len(selected)
        for r in records:
            review = r["record_id"] in selected
            label = r["label"]
            key = "TP" if review and label else "FP" if review else "FN" if label else "TN"
            counts[key] += 1
            loss = r["inspection_cost"] + label * r["miss_loss"] * (1 - effectiveness) if review else label * r["miss_loss"]
            total_loss += loss
            missed_loss += (not review) * label * r["miss_loss"]
            g = by_group[r["device_class"]]
            g["n"] += 1
            g["reviewed"] += review
            g["faults"] += label
            g["missed"] += (not review) * label
            g["loss"] += loss
    neg = counts["FP"] + counts["TN"]
    pos = counts["FN"] + counts["TP"]
    if sum(counts.values()) != len(rows) or counts["TP"] + counts["FP"] != reviews:
        raise RuntimeError("Review counts do not reconcile")
    return {"policy": policy, "records": len(rows), "days": len(days), "reviews": reviews, "available_slots": available, "capacity_violations": 0, **counts, "FPR": counts["FP"] / neg if neg else None, "FNR": counts["FN"] / pos if pos else None, "total_loss": round(total_loss, 4), "loss_per_day": u.rate(total_loss, len(days)), "missed_failure_loss": missed_loss, "by_group": dict(by_group)}

def main():
    root = u.student_root(dataset="alerts")
    devices = {}
    for d in u.keyed(u.read(root, "alerts/devices.csv"), "device_id").values():
        devices[d["device_id"]] = {**d, "miss_loss": float(d["miss_loss"]), "inspection_cost": float(d["inspection_cost"])}
    capacities = {checked_date(r["date"]): int(r["max_reviews"]) for r in u.keyed(u.read(root, "alerts/daily_capacity.csv"), "date").values()}
    dev, future = load(root, "development", devices), load(root, "evaluation", devices)
    if not future:
        raise ValueError("Evaluation batch is empty; no later-period performance can be reported")
    if not dev or max(r["date"] for r in dev) >= min(r["date"] for r in future):
        raise ValueError("Evaluation dates must be strictly after the development period")
    probability = calibration(dev)
    policies = ("none", "score", "score_times_loss", "estimated_net_benefit")
    development = [replay(dev, capacities, probability, p) for p in policies]
    winner = min(development, key=lambda x: x["loss_per_day"])["policy"]
    evaluation = [replay(future, capacities, probability, p) for p in policies]
    sensitivity = []
    for mult, effect in ((.5, .85), (1, .5), (1, .95)):
        value = replay(future, capacities, probability, winner, mult, effect)
        sensitivity.append({"capacity_multiplier": mult, "assumed_effectiveness": effect, **value})
    u.emit({"development": development, "selected_by_development_loss": winner, "evaluation": evaluation, "evaluation_scenarios_not_new_validation": sensitivity, "warning": "Smoothed historical calibration is illustrative and not cross-validated inside development. Development calibration uses all development labels and is in-sample. Evaluation labels are not used to rank evaluation records. Evaluation is a later period, not proof of future or causal effectiveness."})

if __name__ == "__main__":
    main()
