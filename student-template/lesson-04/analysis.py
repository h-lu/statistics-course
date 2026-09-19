"""读取第一期数据并生成概览；评价规则、比较与建议需要另行完成。"""
from pathlib import Path
import csv
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(relative, required_fields):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(required_fields) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{relative} 缺少必要列：{', '.join(sorted(missing))}")
        return list(reader)


def build_overview(rows, window_rows):
    # 使用已整理的第一期数据；异常状态须核对，不猜成0。
    if any(row.get("abandoned") not in ("0", "1") for row in rows):
        raise ValueError("abandoned 应为0或1；未知或异常状态须先核对。")
    ids = [row.get("ticket_id") for row in rows]
    if any(not isinstance(value, str) or not value.strip() for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("第一期工单编号为空或重复，请先核对。")
    windows = {}
    for row in window_rows:
        key, center = row.get("window_id"), row.get("center")
        if not isinstance(key, str) or not key.strip() or key in windows:
            raise ValueError("窗口编号为空或重复，请先核对 windows.csv。")
        if not isinstance(center, str) or not center.strip():
            raise ValueError("窗口缺少所属中心，请先核对 windows.csv。")
        windows[key] = center
    if any(row.get("window_id") not in windows for row in rows):
        raise ValueError("有工单未匹配到窗口，请先核对，不能直接删去未匹配工单。")

    summary = []
    for center in sorted(set(windows.values())):
        selected = [row for row in rows if windows[row["window_id"]] == center and row["abandoned"] == "0"]
        try:
            waits = [float(row["wait_minutes"]) for row in selected]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("已服务等待无法读取为数值，请核对原始记录。") from error
        if any(not math.isfinite(value) or value < 0 for value in waits):
            raise ValueError("已服务等待须为有限的非负数，请核对原始记录。")
        # null表示没有可用结果，不能将空组评为等待0分钟的最佳中心。
        summary.append({"center": center, "served_n": len(waits),
                        "mean": statistics.mean(waits) if waits else None,
                        "median": statistics.median(waits) if waits else None,
                        "maximum": max(waits) if waits else None})
    return {"statistics": summary, "scope": "第一期已服务工单；未形成评价规则",
            "note": "请自行说明评价目标、长等待的判断规则及另一套办法，不能直接把该表当排名。"}


def main():
    rows = read("service/tickets.csv", ("ticket_id", "window_id", "wait_minutes", "abandoned"))
    windows = read("service/windows.csv", ("window_id", "center"))
    output = build_overview(rows, windows)
    path = HERE / "artifacts" / "starting_overview.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
