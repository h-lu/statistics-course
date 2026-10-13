"""Small, explicit tools for one capacity choice; no automatic recommendation."""
import csv
import math
import random
from collections import defaultdict

def _states(states):
    values = [(float(d), float(p)) for d, p in states]
    if not values or any(not math.isfinite(d) or d < 0 or not d.is_integer()
                         or not math.isfinite(p) or p < 0 for d, p in values):
        raise ValueError("Demand must be a nonnegative integer; probability must be finite and nonnegative.")
    total = math.fsum(p for _, p in values)
    if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-10):
        raise ValueError("Probabilities in one scenario must sum to 1.")
    return [(int(d), p / total) for d, p in values if p > 0]

def _settings(capacity, booking_cost, shortage_cost, quantile):
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise ValueError("Capacity must be a nonnegative integer.")
    if any(not math.isfinite(v) or v < 0 for v in (booking_cost, shortage_cost)):
        raise ValueError("Costs must be finite and nonnegative.")
    if not math.isfinite(quantile) or not 0 < quantile <= 1:
        raise ValueError("Quantile level must be in (0, 1].")

def load_scenario(path, scenario):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return _states([(float(r["demand"]), float(r["probability"]))
                    for r in rows if r["scenario"] == scenario])

def exact_metrics(states, capacity, booking_cost=2., shortage_cost=8., quantile=.95):
    states = _states(states)
    _settings(capacity, booking_cost, shortage_cost, quantile)
    outcomes = defaultdict(float)
    for demand, probability in states:
        outcomes[max(0, demand - capacity)] += probability
    mean_shortage = math.fsum(s * p for s, p in outcomes.items())
    cumulative = 0.
    q = max(outcomes)
    for shortage, probability in sorted(outcomes.items()):
        cumulative += probability
        if cumulative >= quantile - 1e-12:
            q = shortage
            break
    return {
        "capacity": capacity,
        "booking_cost": booking_cost * capacity,
        "mean_total_cost": booking_cost * capacity + shortage_cost * mean_shortage,
        "shortage_probability": math.fsum(p for s, p in outcomes.items() if s > 0),
        "mean_shortage": mean_shortage,
        "shortage_quantile_level": quantile,
        "shortage_quantile": q,
        "max_possible_shortage": max(outcomes),
    }

def sample_demands(states, days=10000, seed=10):
    states = _states(states)
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("days must be a positive integer.")
    rng = random.Random(seed)
    return rng.choices([d for d, _ in states],
                       weights=[p for _, p in states], k=days)

def sample_metrics(demands, capacity, booking_cost=2., shortage_cost=8., quantile=.95):
    _settings(capacity, booking_cost, shortage_cost, quantile)
    demands = list(demands)
    if not demands or any(not math.isfinite(d) or d < 0 or int(d) != d for d in demands):
        raise ValueError("Need nonempty nonnegative integer daily demands.")
    shortages = sorted(max(0, int(d) - capacity) for d in demands)
    n = len(shortages)
    mean_shortage = math.fsum(shortages) / n
    return {
        "capacity": capacity, "days": n,
        "booking_cost": booking_cost * capacity,
        "mean_total_cost": booking_cost * capacity + shortage_cost * mean_shortage,
        "shortage_probability": sum(s > 0 for s in shortages) / n,
        "mean_shortage": mean_shortage,
        "shortage_quantile_level": quantile,
        "shortage_quantile": shortages[math.ceil(quantile * n) - 1],
        "max_observed_shortage": shortages[-1],
    }
