"""数据读取与概览示例，尚未完成本课要求的分析和方案比较。"""
from pathlib import Path
import csv,json,statistics
ROOT=Path(__file__).resolve().parents[1]
LESSON=Path(__file__).resolve().parent
FILES=["demand_history.csv","capacity_options.csv"]
def main():
    summaries=[]
    for filename in FILES:
        path=ROOT/"data"/"inference"/filename
        with path.open(encoding="utf-8",newline="") as f:
            reader=csv.DictReader(f);rows=list(reader);columns=reader.fieldnames or []
        numeric={}
        for column in columns:
            vals=[]
            for row in rows:
                try:vals.append(float(row[column]))
                except (TypeError,ValueError):pass
            if vals and len(vals)>=len(rows)*.8:
                numeric[column]={"numeric_n":len(vals),"mean":statistics.mean(vals),"min":min(vals),"max":max(vals)}
        summaries.append({"file":"data/inference/"+filename,"rows":len(rows),"columns":columns,"missing":{c:sum(r[c]=="" for r in rows) for c in columns},"pooled_numeric_description":numeric})
    target=LESSON/"artifacts";target.mkdir(exist_ok=True)
    (target/"starting_inventory.json").write_text(json.dumps({"purpose":"数据读取与描述性统计概览；尚未完成本课的分组分析、方案设计、推断或方案比较","tables":summaries},ensure_ascii=False,indent=2),encoding="utf-8")
    print("已读取数据，概览结果保存在 lesson-10/artifacts/starting_inventory.json。请据此继续完成本课分析。")
if __name__=="__main__":main()
