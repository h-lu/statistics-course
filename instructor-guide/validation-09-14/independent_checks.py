"""Independent review calculations: no toolkit/reference-suite imports.

Run from any directory with Python 3.10+ (standard library only).
Writes only independent_checks_result.json next to this script.
"""
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / 'student-template/data/inference-09-14'


def read(name):
    with (DATA / name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def interval(k, n, method):
    p = k / n
    z = 1.959963984540054
    if method == 'wald':
        half = z * math.sqrt(p * (1 - p) / n)
        return p - half, p + half
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0, center - half), min(1, center + half)


def run():
    population = read('weekend_population.csv')
    N = len(population)
    K = sum(int(row['need_weekend']) for row in population)
    truth = K / N
    assert (N, K) == (4000, 1640)
    coverage = []
    for n in (80, 200):
        denominator = math.comb(N, n)
        for method in ('wilson', 'wald'):
            probability_sum = covered = width = 0.0
            for k in range(max(0, n - (N - K)), min(n, K) + 1):
                probability = math.comb(K, k) * math.comb(N - K, n - k) / denominator
                lo, hi = interval(k, n, method)
                probability_sum += probability
                covered += probability * (lo <= truth <= hi)
                width += probability * (hi - lo)
            assert math.isclose(probability_sum, 1.0, abs_tol=1e-12)
            coverage.append({'n': n, 'method': method,
                             'exact_hypergeometric_coverage': covered,
                             'exact_mean_width': width})
    simple_se = [{'n': n, 'finite_population_SE':
                  math.sqrt((1 - n / N) * truth * (1 - truth) * N / (N - 1) / n)}
                 for n in (80, 200, 800)]
    strata = {}
    for group in ('A', 'B'):
        values = [int(row['need_weekend']) for row in population if row['group'] == group]
        size = len(values)
        p = sum(values) / size
        strata[group] = (size, p * (1 - p) * size / (size - 1))
    allocations = []
    for a, b in ((168, 24), (136, 34), (96, 48), (100, 25), (72, 36)):
        variance = sum((size / N) ** 2 * (1 - n / size) * s2 / n
                       for (size, s2), n in zip(strata.values(), (a, b)))
        size, s2 = strata['B']
        allocations.append({'A': a, 'B': b, 'cost': a + 3 * b,
                            'overall_SE': math.sqrt(variance),
                            'B_SE': math.sqrt((1 - b / size) * s2 / b)})
    demand = read('demand.csv')
    capacity_results = []
    for scenario in ('base', 'stress'):
        states = [(int(row['demand']), float(row['probability']))
                  for row in demand if row['scenario'] == scenario]
        assert math.isclose(sum(p for _, p in states), 1)
        for shortage_cost in (8, 12, 20):
            costs = {c: sum(p * (2 * c + shortage_cost * max(0, d - c))
                            for d, p in states) for c in range(121)}
            best = min(costs.values())
            capacity_results.append({'scenario': scenario, 'shortage_cost': shortage_cost,
                                     'minimum_expected_cost': best,
                                     'minimizing_integer_capacities':
                                     [c for c, cost in costs.items() if math.isclose(cost, best)],
                                     'cost_at_80': costs[80], 'cost_at_120': costs[120],
                                     'maximum_shortage_at_80': max(d for d, _ in states) - 80,
                                     'maximum_shortage_at_120': max(d for d, _ in states) - 120})
    return {'population_N': N, 'population_K': K, 'truth': truth,
            'online_frame_N': sum(int(row['online_frame']) for row in population),
            'coverage': coverage, 'simple_random_sample_SE': simple_se,
            'stratified_allocations': allocations, 'all_integer_capacity_search': capacity_results,
            'scope': 'Exact model/design calculations; not a classroom trial or HTTP test.'}


if __name__ == '__main__':
    output = HERE / 'independent_checks_result.json'
    output.write_text(json.dumps(run(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output)
