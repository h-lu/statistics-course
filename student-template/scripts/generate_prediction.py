"""Generate the explicitly synthetic prediction teaching dataset; stdlib only."""
from pathlib import Path
import csv, math, random
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"prediction"
SEED=2026090521
def write(name, rows, lineterminator="\r\n"):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator=lineterminator);w.writeheader();w.writerows(rows)
def main():
    OUT.mkdir(parents=True,exist_ok=True);rng=random.Random(SEED);rows=[]
    for entity in range(240):
        region=["east","west","north"][entity%3]
        age=rng.uniform(1,15);frailty=rng.gauss(0,2)
        first=0 if entity<200 else 12
        for month in range(first,24):
            complex_case=int(rng.random()<(.35 if month<20 else .55))
            backlog=max(0,rng.gauss(14+month*.22+(region=="west")*3,5))
            workload=max(1,rng.gauss(8+backlog*.25,2))
            failures=max(0,int(rng.expovariate(.9)))
            staffing=workload*.85+rng.gauss(0,.65)
            quality=rng.uniform(.3,1)
            duration=max(2,12+1.1*backlog+1.6*workload+9*complex_case+
                         .055*(backlog-15)**2+frailty+rng.gauss(0,3+backlog*.14))
            logit=-5+.055*backlog+.11*workload+.65*complex_case+.45*failures+.035*age
            if region=="west":logit+=.035*backlog
            if month>=20:logit+=.6
            escalated=int(rng.random()<1/(1+math.exp(-logit)))
            rows.append(dict(record_id=f"R{entity:03d}-{month:02d}",entity_id=f"E{entity:03d}",
                month=month,region=region,backlog=round(backlog,2),workload=round(workload,2),
                complexity="complex" if complex_case else "standard",prior_failures=failures,
                age_years=round(age,2),staffing_index=round(staffing,2),
                sensor_quality="" if month>=20 and rng.random()<.25 else round(quality,3),
                resolution_minutes=round(duration,2),escalated=escalated,
                after_close_minutes=round(duration+rng.gauss(0,.5),2),
                satisfaction_after=max(1,min(5,5-escalated-rng.randint(0,2)))))
    write("requests.csv",rows)
    specs=[
      ("record_id","工单登记时","记录标识，不作为预测变量"),("entity_id","工单登记时","重复观测的设备标识；用于分组划分数据和聚类分析"),
      ("month","工单登记时","0—23的顺序月份；20起为后续环境"),
      ("region","工单登记时","服务地区east/west/north"),
      ("backlog","工单登记时","当前积压件数；可含平均化后的小数"),
      ("workload","工单登记时","当日每人预计工单负荷"),
      ("complexity","工单登记时","初始复杂程度，不是事后难度"),
      ("prior_failures","工单登记时","该设备此前已发生的故障次数"),
      ("age_years","工单登记时","设备年限，年"),
      ("staffing_index","工单登记时","与负荷相关的排班指数，不等于随机处理"),
      ("sensor_quality","工单登记时","0—1质量评分；后期存在缺失"),
      ("resolution_minutes","工单办结后","连续预测目标，分钟"),
      ("escalated","工单办结后","是否升级处理，0/1预测目标"),
      ("after_close_minutes","工单办结后","工单办结后登记时长，可能造成数据泄漏的字段"),
      ("satisfaction_after","工单办结后","事后满意度；不能用于工单登记时预测")]
    write("feature_availability.csv",[dict(field=a,available_at=b,meaning=c) for a,b,c in specs],lineterminator="\n")
    print(f"prediction: {len(rows)} synthetic rows; seed={SEED}")
if __name__=="__main__":main()
