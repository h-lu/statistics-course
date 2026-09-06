"""Fictional device-day alerts, with fully observed retrospective labels."""
from pathlib import Path
import csv
import datetime as dt
import random

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'alerts'
SEED = 26090505

def write(name, rows):
    with (ROOT / name).open('w', newline='', encoding='utf-8') as f:
        out = csv.DictWriter(f, fieldnames=list(rows[0]))
        out.writeheader()
        out.writerows(rows)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    devices = []
    for i in range(90):
        group = ['一般', '重要', '关键'][i % 3]
        devices.append({'device_id': f'D{i+1:03d}', 'campus': ['东区', '西区', '南区'][(i // 3) % 3], 'device_class': group, 'miss_loss': {'一般': 800, '重要': 3000, '关键': 10000}[group], 'inspection_cost': {'一般': 40, '重要': 70, '关键': 120}[group], 'prevention_fraction': .85})
    write('devices.csv', devices)
    partitions, capacities = {'development': [], 'evaluation': []}, []
    for di in range(56):
        day = (dt.date(2026, 5, 4) + dt.timedelta(days=di)).isoformat()
        batch = 'development' if di < 42 else 'evaluation'
        capacities.append({'date': day, 'batch': batch, 'max_reviews': 15 if dt.date.fromisoformat(day).weekday() >= 5 else 20})
        for device in devices:
            group = device['device_class']
            p = {'一般': .06, '重要': .12, '关键': .16}[group] + (.055 if batch == 'evaluation' and device['campus'] == '南区' else 0)
            failure = int(rng.random() < p)
            score = rng.triangular(22, 100, 74) if failure else rng.triangular(0, 91, 21)
            score += {'一般': 4, '重要': 0, '关键': -5}[group]
            if batch == 'evaluation' and device['campus'] == '南区':
                score -= 8
            score = round(min(100, max(0, score)), 1)
            partitions[batch].append({'record_id': f'{day}-{device["device_id"]}', 'date': day, 'device_id': device['device_id'], 'risk_score': score, 'failure_within_24h': failure})
    for batch, rows in partitions.items():
        write(batch + '.csv', rows)
    write('daily_capacity.csv', capacities)
    print(f'alerts seed={SEED}: development={len(partitions["development"])} evaluation={len(partitions["evaluation"])} devices=90 days=56')

if __name__ == '__main__':
    main()
