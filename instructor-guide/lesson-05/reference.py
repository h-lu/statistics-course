"""Time-separated, capacity-feasible replay of alternative review policies."""
from pathlib import Path
from collections import defaultdict
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

def load(root, batch, devices):
    return [{**r, **devices[r["device_id"]], "score": float(r["risk_score"]), "label": int(r["failure_within_24h"])} for r in u.read(root, "alerts/" + batch + ".csv")]

def calibration(rows):
    bins, groups = defaultdict(list), defaultdict(list)
    for r in rows:
        bins[(r["device_class"], min(9, int(r["score"] // 10)))].append(r["label"])
        groups[r["device_class"]].append(r["label"])
    def probability(r):
        values = bins[(r["device_class"], min(9, int(r["score"] // 10)))]
        group = groups[r["device_class"]]
        prior = sum(group) / len(group)
        return (sum(values) + 20 * prior) / (len(values) + 20)
    return probability

def replay(rows, capacities, probability, policy, capacity_multiplier=1, effectiveness=.85):
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
                return probability(r) * effectiveness * r["miss_loss"] - r["inspection_cost"]
            return -1
        ordered = sorted(records, key=lambda r: (-gain(r), r["device_id"]))
        selected = {r["record_id"] for r in ordered[:k] if gain(r) > 0}
        assert len(selected) <= capacities[day]
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
    assert sum(counts.values()) == len(rows)
    return {"policy": policy, "records": len(rows), "days": len(days), "reviews": reviews, "available_slots": available, "capacity_violations": 0, **counts, "FPR": counts["FP"] / neg if neg else None, "FNR": counts["FN"] / pos if pos else None, "total_loss": round(total_loss, 4), "loss_per_day": total_loss / len(days), "missed_failure_loss": missed_loss, "by_group": dict(by_group)}

def main():
    root = u.student_root()
    devices = {}
    for d in u.read(root, "alerts/devices.csv"):
        devices[d["device_id"]] = {**d, "miss_loss": float(d["miss_loss"]), "inspection_cost": float(d["inspection_cost"])}
    capacities = {r["date"]: int(r["max_reviews"]) for r in u.read(root, "alerts/daily_capacity.csv")}
    dev, future = load(root, "development", devices), load(root, "evaluation", devices)
    probability = calibration(dev)
    policies = ("none", "score", "score_times_loss", "estimated_net_benefit")
    development = [replay(dev, capacities, probability, p) for p in policies]
    winner = min(development, key=lambda x: x["loss_per_day"])["policy"]
    evaluation = [replay(future, capacities, probability, p) for p in policies]
    sensitivity = []
    for mult, effect in ((.5, .85), (1, .5), (1, .95)):
        value = replay(future, capacities, probability, winner, mult, effect)
        sensitivity.append({"capacity_multiplier": mult, "assumed_effectiveness": effect, **value})
    u.emit({"development": development, "selected_by_development_loss": winner, "evaluation": evaluation, "evaluation_scenarios_not_new_validation": sensitivity, "warning": "Smoothed historical calibration is illustrative and not cross-validated inside development. Labels are never used to rank that day's records. Evaluation is a later period, not proof of future or causal effectiveness."})

if __name__ == "__main__":
    main()
