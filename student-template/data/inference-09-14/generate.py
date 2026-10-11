"""Deterministic teaching population, never real observations. Python 3.10+."""
import csv
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent

def generate(destination=HERE):
    rng = random.Random(20261011)
    rows = []
    for group, size, need_count, online_rate in [('A',3200,1120,.9),('B',800,520,.55)]:
        needs = [1]*need_count + [0]*(size-need_count)
        rng.shuffle(needs)
        for i, need in enumerate(needs,1):
            rows.append([f'{group}{i:04}',group,need,int(rng.random()<online_rate)])
    with (destination/'weekend_population.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,lineterminator="\n"); w.writerow(['person_id','group','need_weekend','online_frame']); w.writerows(rows)

if __name__ == '__main__':
    generate()
