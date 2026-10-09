"""重现基准和一个竞争方案；先在报告说明规则选择。"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-config", type=Path, default=HERE / "config.json")
    parser.add_argument("--alternative-config", type=Path, default=HERE / "config-alternative.json")
    parser.add_argument("--experiment", action="append", choices=("duplication", "unmatched", "revision", "staffing"), default=[])
    args = parser.parse_args()
    configs = [json.loads(p.read_text(encoding="utf-8")) for p in (args.main_config, args.alternative_config)]
    keys = ("revision_conflict", "window_join", "metric_scope", "staffing_coverage")
    if sum(configs[0][k] != configs[1][k] for k in keys) != 1:
        raise ValueError("本次控制比较请只改变一个规则，并在报告说明理由")
    for config, label in ((args.main_config,"main"),(args.alternative_config,"alternative")):
        subprocess.run([sys.executable, str(HERE / "analysis.py"), "--stage", "indicators", "--config", str(config),
                        "--output", str(HERE / "artifacts" / label)], check=True)
    for case in dict.fromkeys(args.experiment):
        subprocess.run([sys.executable, str(HERE / "experiments.py"), case], check=True)


if __name__ == "__main__":
    main()
