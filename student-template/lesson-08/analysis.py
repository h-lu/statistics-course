"""七表读取概览与通用核算函数。正式问题、规则和分析由你决定。"""
from pathlib import Path
from collections import defaultdict
import csv
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
KEYS = {"tickets.csv": ("ticket_id",), "tickets_raw.csv": ("ticket_id",),
        "satisfaction.csv": ("ticket_id",), "visits.csv": ("contact_id",),
        "windows.csv": ("window_id",), "business_types.csv": ("business_code",),
        "staffing.csv": ("date", "window_id")}


def read(relative):
    with (ROOT / "data" / relative).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def unique_index(rows, fields):
    """通用键检查。对原始修订表不要直接要求ticket_id唯一。"""
    if isinstance(fields,str): fields=(fields,)
    result={}
    for row in rows:
        key=tuple(row.get(k) for k in fields)
        if any(v is None or not str(v).strip() for v in key) or key in result:
            raise ValueError(f"缺失或重复键 {fields}: {key}")
        result[key]=row
    return result


def group_totals(rows, fields, value_field):
    """按自己指定的字段分组求和；字段有效性和用途仍由分析者选择。"""
    if isinstance(fields,str): fields=(fields,)
    groups=defaultdict(lambda:{"rows":0,"sum":0.0})
    for row in rows:
        value=float(row[value_field])
        if not math.isfinite(value): raise ValueError(f"非有限数值: {value_field}")
        key=tuple(row[k] for k in fields)
        groups[key]["rows"]+=1
        groups[key]["sum"]+=value
    return dict(groups)


def inventory():
    summary=[]
    for filename,key in KEYS.items():
        rows=read("service/"+filename)
        summary.append({"file":filename,"rows":len(rows),"proposed_key":list(key),
                        "unique_keys":len({tuple(r[k] for k in key) for r in rows})})
    return {"inventory":summary,"note":"仅为读入概览，未清洗、连接、选择指标或形成发布判断。"}


def main():
    target=HERE/"artifacts/starting_overview.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(inventory(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(target.relative_to(ROOT))


if __name__=="__main__":
    main()
