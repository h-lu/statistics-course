"""L21: example code for reading data and computing descriptive statistics."""
from pathlib import Path
import csv,json,statistics
ROOT=Path(__file__).resolve().parents[1]
LESSON=ROOT/"lesson-21"
DATA=ROOT/"data"/"prediction"/"requests.csv"
def main():
    with DATA.open(encoding="utf-8",newline="") as handle:
        rows=list(csv.DictReader(handle))
    rows=[row for row in rows if int(row["month"])<16]  # development only; preserve future outcomes
    summary={"purpose":"数据读取示例；请按分析要求扩展分析，不代表已完成项目",
             "synthetic_data":True,"source":str(DATA.relative_to(ROOT)),"rows":len(rows),"groups":{}}
    for group in sorted({row["region"] for row in rows}):
        subset=[row for row in rows if row["region"]==group]
        stats={"n":len(subset)}
        for field in ["backlog","resolution_minutes"]:
            values=[float(row[field]) for row in subset if row[field]!=""]
            stats[field]={"observed_n":len(values),"missing_n":len(subset)-len(values),
              "mean":statistics.fmean(values) if values else None,
              "min":min(values) if values else None,"max":max(values) if values else None}
        summary["groups"][group]=stats
    out=LESSON/"artifacts";out.mkdir(exist_ok=True)
    (out/"starting_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"示例统计结果已生成：{out/'starting_summary.json'}；接下来按README完成正式成果。")
if __name__=="__main__":main()
