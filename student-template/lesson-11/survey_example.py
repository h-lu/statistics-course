"""Run two surveys of the lesson's fixed synthetic population, then audit later."""
import argparse
import csv
import json
from pathlib import Path

from sampling_tools import (OBSERVATION_FIELDS, audit_population,
                            composition_estimate, load_frame, make_request,
                            read_observations, response_mean, run_request,
                            write_request)

MECHANISMS = ("register_ordinary", "web_voluntary")
LABELS = ("完整名册普通联系", "网上邀请、自愿回答")
METRICS = (
    ("抽样框人数", "frame_n"), ("邀请人数", "invited_n"),
    ("回答人数", "responded_n"), ("A组回答人数", "responded_A"),
    ("B组回答人数", "responded_B"), ("A组有需求回答人数", "need_A"),
    ("B组有需求回答人数", "need_B"), ("A组需求比例", "rate_A"),
    ("B组需求比例", "rate_B"), ("直接比例", "direct_rate"),
    ("0.8/0.2构成比例", "composition_rate"),
    ("邀请费用（仅邀请，单位）", "invitation_cost_units"),
)


def known(value):
    """Use 未知 in readable outputs; raw observations keep the API's blanks."""
    if isinstance(value, dict):
        return {key: known(item) for key, item in value.items()}
    return "未知" if value is None else value


def write_json(path, value):
    payload = json.dumps(known(value), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    with path.open("xb") as handle:
        handle.write(payload.encode("utf-8"))


def summarize(rows, counts):
    result = {"frame_n": sum(row["in_frame"] for row in rows),
              "invited_n": sum(row["invited"] for row in rows),
              "responded_n": sum(row["answered"] for row in rows),
              "direct_rate": response_mean(rows),
              "composition_rate": composition_estimate(rows, counts),
              "invitation_cost_units": sum(row["invitation_cost_units"] for row in rows)}
    for group in ("A", "B"):
        respondents = [row for row in rows if row["group"] == group and row["answered"]]
        result["responded_" + group] = len(respondents)
        result["need_" + group] = sum(row["observed_need"] for row in respondents)
        result["rate_" + group] = response_mean(rows, group)
    return result


def population_counts(frame):
    return {group: sum(row["group"] == group for row in frame) for group in ("A", "B")}


def write_samples(output, rows):
    categories = (
        ("框外", lambda row: not row["in_frame"]),
        ("未邀请", lambda row: row["in_frame"] and not row["invited"]),
        ("未回答", lambda row: row["invited"] and not row["answered"]),
        ("明确0", lambda row: row["answered"] and row["observed_need"] == 0),
        ("明确1", lambda row: row["answered"] and row["observed_need"] == 1),
    )
    with (output / "sample-records.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["类别", *OBSERVATION_FIELDS], lineterminator="\n")
        writer.writeheader()
        for label, matches in categories:
            row = next((row for row in rows if matches(row)), None)
            if row is not None:
                writer.writerow(known({"类别": label, **row}))


def survey(args):
    frame = load_frame()
    requests = {mechanism: make_request(frame, mechanism, args.n,
                                       args.selection_seed, args.response_seed)
                for mechanism in MECHANISMS}
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    # Save every comparison plan before the first acquisition.
    for mechanism, request in requests.items():
        write_request(request, output / "plans" / (mechanism + ".json"))
    print("两份方案均已保存；现在分别取得回答。", flush=True)
    for mechanism, request in requests.items():
        run_request(request, output / mechanism)

    observations = {mechanism: read_observations(output / mechanism / "observations.csv")
                    for mechanism in MECHANISMS}
    estimates = {mechanism: summarize(rows, population_counts(frame))
                 for mechanism, rows in observations.items()}
    write_json(output / "estimates.json", estimates)
    with (output / "comparison.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["指标", *LABELS])
        for label, key in METRICS:
            writer.writerow([label, *(known(estimates[mechanism][key]) for mechanism in MECHANISMS)])
    write_samples(output, observations["web_voluntary"])
    print("已保存 estimates.json、comparison.csv 和 sample-records.csv。", flush=True)
    if args.audit:
        audit(output)
    else:
        print("尚未进行总体审计；形成估计后可使用 audit 子命令。")


def audit(output):
    if not (output / "comparison.csv").is_file():
        raise ValueError("先运行 survey 并保存比较，再进行总体审计。")
    if (output / "audit.json").exists():
        raise FileExistsError("audit.json 已存在；保留原审计，不能覆盖。")
    saved_estimates = json.loads((output / "estimates.json").read_text(encoding="utf-8"))
    counts = population_counts(load_frame())
    requests = {}
    for mechanism in MECHANISMS:
        requests[mechanism] = json.loads(
            (output / "plans" / (mechanism + ".json")).read_text(encoding="utf-8"))
        rows = read_observations(output / mechanism / "observations.csv")
        if known(summarize(rows, counts)) != saved_estimates[mechanism]:
            raise ValueError("保存的估计与观测不一致，请先核对文件。")
    results = {mechanism: audit_population(requests[mechanism], output / mechanism)
               for mechanism in MECHANISMS}
    write_json(output / "audit.json", results)
    print("已核对已存方案和观测，保存总体审计 audit.json。")


def main():
    parser = argparse.ArgumentParser(
        description="在原4000人合成总体上比较两种调查：先保存方案、取得并估计，再另行审计。")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("survey", help="取得两种调查并保存比较；默认不审计")
    collect.add_argument("--n", type=int, required=True, help="两种方式相同的邀请人数")
    collect.add_argument("--selection-seed", type=int, required=True, help="自行选定的邀请种子")
    collect.add_argument("--response-seed", type=int, required=True, help="自行选定的回答种子")
    collect.add_argument("--output", type=Path, required=True, help="尚不存在的输出目录；保留之前的结果")
    collect.add_argument("--audit", action="store_true", help="估计及比较保存后再审计，供一次完整复现使用")
    inspect = commands.add_parser("audit", help="核对已取得的方案、观测和估计，再保存总体审计")
    inspect.add_argument("--output", type=Path, required=True, help="已完成survey的同一个目录")
    args = parser.parse_args()
    try:
        survey(args) if args.command == "survey" else audit(args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"无法完成：{error}\n")


if __name__ == "__main__":
    main()
