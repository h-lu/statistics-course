"""查看第二期原始导出的行数和编码；本程序尚未完成数据清洗。"""
from collections import Counter
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(relative):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ticket_id", "wait_minutes", "wait_unit", "export_revision"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("原始导出缺少字段：" + ", ".join(sorted(missing)))
        return list(reader)


def build_overview(rows):
    # 这里数的是导出行。重复行和旧版本尚未处理，不能当成最终工单统计。
    ids = [row["ticket_id"] for row in rows]
    known_ids = {value for value in ids if value is not None and value.strip()}
    return {
        "raw_rows": len(rows),
        "unique_ticket_ids": len(known_ids),
        "blank_ticket_id_rows": sum(value is None or not value.strip() for value in ids),
        "wait_units": dict(Counter(row["wait_unit"] for row in rows)),
        "revision_counts": dict(Counter(row["export_revision"] for row in rows)),
        # 只检查这两个原文编码，不是所有空白或无效等待的总数。
        "missing_wait_code_rows": sum(
            (row["wait_minutes"] or "").strip() in ("999", "-1") for row in rows
        ),
        "note": "这些计数按原始导出行统计；尚未处理重复、修订、缺失或单位，不能直接当作工单质量报告。",
    }


def main():
    output = build_overview(read("service/tickets_raw.csv"))
    (HERE / "artifacts").mkdir(exist_ok=True)
    path = HERE / "artifacts" / "starting_overview.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
