"""Run the teaching example only; build your own formal comparison."""
from pathlib import Path
import json
from capacity_tools import load_scenario, exact_metrics, sample_demands, sample_metrics

HERE = Path(__file__).resolve().parent

def main():
    states = [(0, .2), (1, .5), (2, .3)]
    mean = sum(d * p for d, p in states)
    days = sample_demands(states, days=10000, seed=10)
    result = {
        "example_only": True,
        "mean_exact": mean,
        "variance_exact": sum(p * (d - mean) ** 2 for d, p in states),
        "capacity_1_exact": exact_metrics(states, 1, shortage_cost=12),
        "capacity_2_exact": exact_metrics(states, 2, shortage_cost=12),
        "capacity_1_simulated": sample_metrics(days, 1, shortage_cost=12),
        "simulation_seed": 10,
        "formal_inputs_checked": {
            name: {"states": len(load_scenario(HERE / "data/demand.csv", name)),
                   "probability_sum": sum(p for _, p in load_scenario(HERE / "data/demand.csv", name))}
            for name in ("base", "stress")
        },
    }
    out = HERE / "artifacts"
    out.mkdir(exist_ok=True)
    (out / "example.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("小例已运行。正式容量、比较目标和建议仍需你自己选择。")

if __name__ == "__main__":
    main()
