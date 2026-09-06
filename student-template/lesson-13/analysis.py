"""Example code for reading data and computing basic descriptive summaries."""
from pathlib import Path
import csv,json,statistics
ROOT=Path(__file__).resolve().parents[1]
LESSON=Path(__file__).resolve().parent
FILES=["decision_sample.csv","estimation_populations.csv"]
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
    (target/"starting_inventory.json").write_text(json.dumps({"purpose":"数据读取与合并描述统计示例；未完成分组、设计、推断或政策比较","tables":summaries},ensure_ascii=False,indent=2),encoding="utf-8")
    print("已读取数据；示例统计结果位于 lesson-13/artifacts/starting_inventory.json。请继续完成本课分析任务。")
if __name__=="__main__":main()
