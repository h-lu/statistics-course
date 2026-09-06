"""第22课数据读取与描述统计示例；请据分析任务扩展。"""
from pathlib import Path
import csv,json,statistics
ROOT=Path(__file__).resolve().parents[1]
LESSON=ROOT/"lesson-22"
DATA=ROOT/"data"/"prediction"/"requests.csv"
def main():
    with DATA.open(encoding="utf-8",newline="") as handle:
        rows=list(csv.DictReader(handle))
    rows=[row for row in rows if int(row["month"])<16]  # 仅使用开发阶段数据；保留后续月份用于评价
    summary={"purpose":"数据结构与描述统计示例；请按本课任务继续完成分析",
             "synthetic_data":True,"source":str(DATA.relative_to(ROOT)),"rows":len(rows),"groups":{}}
    for group in sorted({row["complexity"] for row in rows}):
        subset=[row for row in rows if row["complexity"]==group]
        stats={"n":len(subset)}
        for field in ["workload","resolution_minutes"]:
            values=[float(row[field]) for row in subset if row[field]!=""]
            stats[field]={"observed_n":len(values),"missing_n":len(subset)-len(values),
              "mean":statistics.fmean(values) if values else None,
              "min":min(values) if values else None,"max":max(values) if values else None}
        summary["groups"][group]=stats
    out=LESSON/"artifacts";out.mkdir(exist_ok=True)
    (out/"starting_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"数据概况已生成：{out/'starting_summary.json'}；接下来按README完成分析任务并撰写报告。")
if __name__=="__main__":main()
