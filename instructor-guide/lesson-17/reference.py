from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"lesson-09"))
from reference_tools import *
paired=read("experiments","paired_study.csv");pairs=groups(paired,"person_id");d=np.array([float(next(r["minutes"] for r in rr if r["method"]=="B"))-float(next(r["minutes"] for r in rr if r["method"]=="A")) for rr in pairs.values()])
ind=read("experiments","independent_comparison.csv");repeat=read("experiments","repeated_measurements.csv")
person=[dict(arm=rr[0]["arm"],value=np.mean(arr(rr,"minutes"))) for rr in groups(repeat,"person_id").values()]
emit(dict(paired_difference_B_minus_A=ci_mean(d),paired_naively_independent=difference(arr([r for r in paired if r["method"]=="B"],"minutes"),arr([r for r in paired if r["method"]=="A"],"minutes")),independent_study=difference(arr([r for r in ind if r["arm"]=="B"],"minutes"),arr([r for r in ind if r["arm"]=="A"],"minutes")),repeated_person_mean=difference(arr([r for r in person if r["arm"]=="tool"],"value"),arr([r for r in person if r["arm"]=="usual"],"value")),repeated_naive_rows=difference(arr([r for r in repeat if r["arm"]=="tool"],"minutes"),arr([r for r in repeat if r["arm"]=="usual"],"minutes")),sequence_differences={seq:np.mean([float(next(r["minutes"] for r in rr if r["method"]=="B"))-float(next(r["minutes"] for r in rr if r["method"]=="A")) for rr in pairs.values() if rr[0]["sequence"]==seq]) for seq in ["AB","BA"]}))
