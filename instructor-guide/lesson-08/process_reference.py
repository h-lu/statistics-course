"""教师增强过程证据；完整计算只在教师目录。仅标准库。"""
from pathlib import Path
import importlib.util
import json
import math

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("student08", Path(__file__).with_name("exploratory_reference.py"))
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)


def build_result():
    data = {name: s.read(name) for name in s.TABLES}
    cleaned, audit = s.clean(data, "stop")
    config = {"revision_conflict": "stop", "window_join": "left", "metric_scope": "per_metric", "staffing_coverage": "union"}
    results = {}
    for name, update in [("main", {}), ("inner", {"window_join": "inner"}),
                         ("common", {"metric_scope": "common_complete"}),
                         ("activity", {"staffing_coverage": "activity_only"})]:
        choice = {**config, **update}
        joined, ja = s.join(cleaned, data, choice)
        metrics, days, reconciliation = s.indicators(joined, data, choice, ja)
        results[name] = {"choices": choice, "metrics": metrics, "join_audit": ja, "reconciliation": reconciliation}
    main = results["main"]
    if audit["combined_ids"] != 4800 or main["reconciliation"]["input_contact_n"] != 8921:
        raise RuntimeError("教学输入规模改变，请先核验来源")
    if not math.isclose(main["reconciliation"]["source_minutes"], 89466.8, abs_tol=1e-7):
        raise RuntimeError("接触工作量改变")
    return {"synthetic_data": True, "cleaning": audit, "comparisons": results}


if __name__ == "__main__":
    out = Path(__file__).with_name("process_results.json")
    out.write_text(json.dumps(build_result(), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(out.relative_to(ROOT))
