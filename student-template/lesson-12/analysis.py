"""Enumerate the six samples in the four-person teaching example."""
from pathlib import Path
from itertools import combinations
import json,math

def main():
    values=[2,4,6,8];samples=list(combinations(values,2));means=[sum(s)/2 for s in samples];mu=sum(values)/4
    obj={'population':values,'population_mean':mu,'population_sd':math.sqrt(sum((v-mu)**2 for v in values)/4),'samples':[{'values':list(s),'mean':m} for s,m in zip(samples,means)],'all_means':means,'mean_of_means':sum(means)/6,'exact_se':math.sqrt(sum((m-mu)**2 for m in means)/6)}
    p=Path(__file__).parent/'artifacts/example.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(json.dumps(obj,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
