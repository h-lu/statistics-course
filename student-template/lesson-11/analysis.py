"""Run a separate small example and check public input, not the formal project."""
from pathlib import Path
import json
from sampling_tools import load_frame, response_mean, composition_estimate

HERE = Path(__file__).resolve().parent


def main():
    rows = [{"group": g, "answered": 1, "observed_need": int(i < yes)}
            for g, yes in (("A", 5), ("B", 9)) for i in range(10)]
    biased = [{"group": g, "answered": 1, "observed_need": int(i < yes)}
              for g, yes in (("A", 8), ("B", 9)) for i in range(10)]
    frame = load_frame()
    result = {"example_only": {"population_n": 100, "group_counts": {"A": 80, "B": 20},
                               "respondent_counts": {"A": 10, "B": 10},
                               "unweighted": response_mean(rows),
                               "composition_adjusted": composition_estimate(rows, {"A": 80, "B": 20}),
                               "biased_within_A_adjusted": composition_estimate(biased, {"A": 80, "B": 20}),
                               "missing_B_adjusted": composition_estimate([r for r in rows if r["group"] == "A"], {"A": 80, "B": 20})},
              "trace_example_only": [
                  {"person_id": "toy-offline", "in_frame": 0, "invited": 0, "answered": 0, "observed_need": None},
                  {"person_id": "toy-not-invited", "in_frame": 1, "invited": 0, "answered": 0, "observed_need": None},
                  {"person_id": "toy-no-response", "in_frame": 1, "invited": 1, "answered": 0, "observed_need": None},
                  {"person_id": "toy-response", "in_frame": 1, "invited": 1, "answered": 1, "observed_need": 1}],
              "public_input_check": {"population_n": len(frame),
                                     "group_counts": {g: sum(r["group"] == g for r in frame) for g in ("A", "B")},
                                     "web_frame_n": sum(r["online_frame"] for r in frame),
                                     "columns": list(frame[0]), "formal_acquisition_run": False}}
    destination = HERE / "artifacts"
    destination.mkdir(exist_ok=True)
    (destination / "example.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("这里只运行了另设100人小例和公开名册检查；正式方案、取得、比较与建议由你构建。")


if __name__ == "__main__":
    main()
