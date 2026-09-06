"""Generate fictional teaching records; no real institution or individual is represented."""
from pathlib import Path
import csv
import datetime as dt
import random

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'service'
SEED = 26090501

def write(name, rows):
    with (ROOT / name).open('w', newline='', encoding='utf-8') as f:
        out = csv.DictWriter(f, fieldnames=list(rows[0]))
        out.writeheader()
        out.writerows(rows)

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    days, d = [], dt.date(2026, 3, 2)
    while len(days) < 40:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)
    windows = [{'window_id': c + str(j), 'center': c, 'specialty': '综合业务', 'opened': '2025-09-01'} for c in 'ABC' for j in (1, 2)]
    write('windows.csv', windows)
    write('business_types.csv', [
        {'business_code': 'basic', 'name': '常规材料办理', 'complexity': '常规', 'reference_wait_minutes': 15},
        {'business_code': 'case', 'name': '复杂个案处理', 'complexity': '复杂', 'reference_wait_minutes': 30},
    ])
    tickets, surveys, visits, staffing = [], [], [], []
    for di, day in enumerate(days):
        for w in windows:
            staffing.append({'date': day, 'window_id': w['window_id'], 'staff_count': 2 if w['window_id'].endswith('1') else 1, 'open_hours': 7 if di % 10 else 6, 'absence_hours': 1 if rng.random() < .09 else 0})
        for center in 'ABC':
            for j in range(40):
                tid = f'T{len(tickets) + 1:05d}'
                code = 'case' if rng.random() < {'A': .78, 'B': .22, 'C': .50}[center] else 'basic'
                period = '上午' if rng.random() < .64 else '下午'
                appointment = int(rng.random() < (.57 if code == 'basic' else .24))
                base = {'A': 4.7, 'B': 6.8, 'C': 5.8}[center] * (2.65 if code == 'case' else 1)
                wait = rng.lognormvariate(0, .52) * base * (1.18 if period == '上午' else .80) * (.75 if appointment else 1.08)
                wait *= 1.25 if di >= 30 else 1
                if rng.random() < .025:
                    wait += rng.uniform(30, 85)
                abandoned = int(wait > 25 and rng.random() < .25)
                served = '' if abandoned else round(rng.gammavariate(3, 2.4 if code == 'basic' else 6), 2)
                success = {'A': (.96, .77), 'B': (.89, .64), 'C': (.93, .71)}[center][code == 'case']
                complete = 0 if abandoned else int(rng.random() < success)
                row = {'ticket_id': tid, 'person_id': f'P{rng.randrange(1, 2701):04d}', 'date': day, 'arrival_period': period, 'window_id': center + str(1 + j % 2), 'business_code': code, 'appointment': appointment, 'wait_minutes': round(wait, 2), 'service_minutes': served, 'abandoned': abandoned, 'completed_same_day': complete}
                tickets.append(row)
                latent_score = min(5, max(1, round(5.05 - wait / 18 + .25 * complete + rng.gauss(0, .95))))
                sent = int(rng.random() < (.50 if abandoned else .90))
                replied = sent and rng.random() < (.24 + .105 * latent_score - .07 * (code == 'case'))
                surveys.append({'survey_id': 'Q' + tid[1:], 'ticket_id': tid, 'invited': sent, 'score': latent_score if replied else '', 'response_days': rng.randrange(0, 5) if replied else ''})
                count = 1 + int(code == 'case') + int(not complete) + int(rng.random() < .15)
                for k in range(count):
                    visits.append({'contact_id': f'{tid}-{k+1}', 'ticket_id': tid, 'contact_sequence': k + 1, 'contact_type': '首次受理' if k == 0 else '补充沟通', 'contact_date': day, 'staff_minutes': round(rng.uniform(2, 11) * (1.8 if code == 'case' else 1), 2)})
    write('tickets.csv', tickets[:3600])
    raw = []
    for i, row in enumerate(tickets[3600:]):
        item = {**row, 'wait_unit': 'minute', 'export_revision': 1}
        if i % 29 == 0:
            item['wait_minutes'] = round(float(item['wait_minutes']) * 60, 2)
            item['wait_unit'] = 'second'
        if i % 113 == 5:
            item['wait_minutes'] = 999
        if i % 157 == 8:
            item['wait_minutes'] = -1
        if i % 197 == 2:
            item['window_id'] = 'UNKNOWN'
        if i % 131 == 7:
            item['business_code'] = ''
        if i % 173 == 4:
            item['completed_same_day'] = ''
        raw.append(item)
        if i % 31 == 0:
            raw.append(dict(item))
        if i % 47 == 3:
            revised = dict(item)
            revised['export_revision'] = 2
            if revised['wait_minutes'] not in (999, -1):
                revised['wait_minutes'] = round(float(revised['wait_minutes']) * .9, 2)
            raw.append(revised)
    write('tickets_raw.csv', raw)
    write('satisfaction.csv', surveys)
    write('visits.csv', visits)
    write('staffing.csv', staffing)
    print(f'service seed={SEED}: tickets=3600 raw_rows={len(raw)} raw_ticket_ids=1200 surveys={len(surveys)} contacts={len(visits)} staffing={len(staffing)}')

if __name__ == '__main__':
    main()
