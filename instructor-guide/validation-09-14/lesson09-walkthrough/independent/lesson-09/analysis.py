"""Student policy comparison. Deterministic expectations; no sampling seed needed."""
import csv
import json
import math
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'data' / 'inference-09-14'))
import toolkit as t

# Rules fixed before evaluating scenarios. Reserve 30 gives routine one third
# of review capacity when there are enough positives, then rank remaining slots.
POLICIES = {
    'S_reserve30': ({'routine': 'sensitive', 'priority': 'sensitive'}, 30),
    'S_loss': ({'routine': 'sensitive', 'priority': 'sensitive'}, 0),
    'mixed_loss': ({'routine': 'sensitive', 'priority': 'precise'}, 0),
}

def evaluate(scenario, policy):
    methods, reserve = POLICIES[policy]
    tests = {r['method']: r for r in t.table('screening.csv')}
    rows = []
    for g in t.table('alert_groups.csv'):
        method = tests[methods[g['group']]]
        n, p, loss = int(g['daily_devices']), float(g[scenario]), float(g['miss_cost'])
        f = t.natural_frequencies(n, p, float(method['sensitivity']), float(method['specificity']))
        rows.append(dict(scenario=scenario, policy=policy, group=g['group'], method=method['method'],
                         devices=n, base_rate=p, fault_total=n*p, miss_cost=loss,
                         screen_cost=n*float(method['cost_per_device']), **f,
                         review_cap=math.floor(f['positive'] + 1e-9), reviews=0))
    budget = 90
    for r in rows:
        if r['group'] == 'routine':
            r['reviews'] = min(reserve, r['review_cap'], budget)
            budget -= r['reviews']
    for r in sorted(rows, key=lambda x: (-(x['positive_predictive_value'] or 0)*x['miss_cost'], x['group'])):
        add = min(budget, r['review_cap'] - r['reviews'])
        r['reviews'] += add
        budget -= add
    for r in rows:
        r['detected'] = r['reviews'] * (r['positive_predictive_value'] or 0)
        r['unreviewed_positive_faults'] = r['true_positive'] - r['detected']
        r['undetected'] = r['fault_total'] - r['detected']
        r['undetected_loss'] = r['undetected'] * r['miss_cost']
        r['review_cost'] = 3*r['reviews']
        assert 0 <= r['reviews'] <= r['positive'] + 1e-9
        assert abs(r['undetected'] - r['missed'] - r['unreviewed_positive_faults']) < 1e-8
    assert sum(r['screen_cost'] for r in rows) <= 2000
    assert sum(r['reviews'] for r in rows) <= 90
    total = {k: sum(r[k] for r in rows) for k in ['screen_cost','reviews','review_cost','undetected','undetected_loss']}
    total.update(scenario=scenario, policy=policy)
    total['combined_cost'] = total['screen_cost'] + total['review_cost'] + total['undetected_loss']
    return rows, total

def main():
    out = HERE / 'artifacts'
    out.mkdir(exist_ok=True)
    details, totals = [], []
    for scenario in ['base_low', 'base', 'base_high']:
        for policy in POLICIES:
            rows, total = evaluate(scenario, policy)
            details.extend(rows)
            totals.append(total)
    for name, rows in [('comparison.csv',details), ('totals.csv',totals)]:
        with (out/name).open('w',encoding='utf-8',newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    example = t.natural_frequencies(1000,.01,.9,.95)
    assert abs(example['positive_predictive_value'] - 9/58.5) < 1e-12
    (out/'example.json').write_text(json.dumps(example,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(totals,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
