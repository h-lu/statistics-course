"""Optional arithmetic for a student-chosen stratified design, not a survey solver.

Inputs are explicit stratum counts/assumptions. No population file is read,
no allocation is selected, and no official comparison is run.
Independent within-stratum SRSWOR and full response are required.
"""
import math


def _sizes(population_sizes, sample_sizes):
    if not population_sizes or set(population_sizes) != set(sample_sizes):
        raise ValueError('Use the same nonempty strata in N and n')
    for h, N in population_sizes.items():
        n = sample_sizes[h]
        if type(N) is not int or type(n) is not int or not 2 <= n <= N:
            raise ValueError('Each stratum requires integer 2 <= n <= N')
    total = sum(population_sizes.values())
    return {h: N / total for h, N in population_sizes.items()}


def sample_inference(population_sizes, sample_sizes, successes):
    """Estimated SE and untruncated approximate 95% Wald CI from ONE sample.

The warning is a screening reminder, not a certification of normality.
A census stratum has zero sampling variance even with all-zero outcomes.
"""
    W = _sizes(population_sizes, sample_sizes)
    if set(successes) != set(W):
        raise ValueError('Supply observed successes for every stratum')
    rates, variances, warnings = {}, {}, []
    for h, N in population_sizes.items():
        n, y = sample_sizes[h], successes[h]
        if type(y) is not int or not 0 <= y <= n:
            raise ValueError('Successes must be integer counts between 0 and n')
        rates[h] = y / n
        variances[h] = (1 - n / N) * rates[h] * (1 - rates[h]) / (n - 1)
        if n < N and min(y, n - y) < 5:
            warnings.append(f'{h}: few successes/failures; normal CI may be unreliable')
    estimate = sum(W[h] * rates[h] for h in W)
    se = math.sqrt(sum(W[h] ** 2 * variances[h] for h in W))
    return dict(estimate=estimate, estimated_se=se,
                lower=estimate - 1.96 * se, upper=estimate + 1.96 * se,
                stratum_estimated_se={h: math.sqrt(v) for h, v in variances.items()},
                warnings=warnings,
                note='Approximate normal interval, not exact 95%; excludes nonresponse/coverage bias')


def planning_precision(population_sizes, sample_sizes, assumed_proportions):
    """Conditional planning SE; assumptions are NOT observed sample estimates.

The caller chooses allocations and assumptions. 0.5 in every stratum gives
an upper variance bound for a fixed allocation, not an optimal allocation.
"""
    W = _sizes(population_sizes, sample_sizes)
    if set(assumed_proportions) != set(W):
        raise ValueError('Supply an assumption for every stratum')
    variances = {}
    for h, N in population_sizes.items():
        n, p = sample_sizes[h], assumed_proportions[h]
        if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('Assumed proportions must be finite numbers in [0,1]')
        variances[h] = p * (1 - p) / n * (N - n) / (N - 1)
    return dict(planning_se=math.sqrt(sum(W[h] ** 2 * variances[h] for h in W)),
                stratum_planning_se={h: math.sqrt(v) for h, v in variances.items()})
