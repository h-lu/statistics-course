"""第31课数据读取与描述统计示例；请据分析任务扩展。"""
from pathlib import Path
import csv,json,statistics
ROOT=Path(__file__).resolve().parents[1]
LESSON=ROOT/"lesson-31"
DATA=ROOT/"data"/"policy"/"decision_options.csv"
def main():
    with DATA.open(encoding="utf-8",newline="") as handle:
        rows=list(csv.DictReader(handle))
    summary={"purpose":"数据结构与描述统计示例；请按本课任务继续完成分析",
             "synthetic_data":True,"source":str(DATA.relative_to(ROOT)),"rows":len(rows),"groups":{}}
    for group in sorted({row["action"] for row in rows}):
        subset=[row for row in rows if row["action"]==group]
        stats={"n":len(subset)}
        for field in ["loss"]:
            values=[float(row[field]) for row in subset if row[field]!=""]
            stats[field]={"observed_n":len(values),"missing_n":len(subset)-len(values),
              "mean":statistics.fmean(values) if values else None,
              "min":min(values) if values else None,"max":max(values) if values else None}
        summary["groups"][group]=stats
    out=LESSON/"artifacts";out.mkdir(exist_ok=True)
    (out/"starting_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"数据概况已生成：{out/'starting_summary.json'}；接下来按README完成分析任务并撰写报告。")
if __name__=="__main__":main()
