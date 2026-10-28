"""Lesson 14 arithmetic: small independent examples, no chosen project solution."""
import importlib.util
import math
import itertools
import statistics
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('stratified_tools', Path(__file__).parents[1] / 'lesson-14/stratified_tools.py')
tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tools)


class StratifiedTests(unittest.TestCase):
    def test_teaching_sample(self):
        r = tools.sample_inference({'A': 800, 'B': 200}, {'A': 160, 'B': 40}, {'A': 68, 'B': 23})
        self.assertAlmostEqual(r['estimate'], .455)
        self.assertAlmostEqual(r['estimated_se'], .03142341578356069)
        self.assertAlmostEqual(r['lower'], .3934101050642211)
        self.assertAlmostEqual(r['upper'], .516589894935779)
        self.assertEqual(r['warnings'], [])

    def test_known_planning_example(self):
        N = {'A': 800, 'B': 200}
        p = {'A': .4, 'B': .6}
        a = tools.planning_precision(N, {'A': 160, 'B': 40}, p)
        b = tools.planning_precision(N, {'A': 100, 'B': 60}, p)
        self.assertAlmostEqual(a['planning_se'], math.sqrt(.64*.24/160*640/799+.04*.24/40*160/199))
        self.assertGreater(b['planning_se'], a['planning_se'])
        self.assertLess(b['stratum_planning_se']['B'], a['stratum_planning_se']['B'])

    def test_estimated_variance_unbiased_by_complete_enumeration(self):
        population = {'A': [0, 0, 1, 1], 'B': [0, 1, 1]}
        N, n = {'A': 4, 'B': 3}, {'A': 2, 'B': 2}
        estimates, variance_estimates = [], []
        for a in itertools.combinations(population['A'], 2):
            for b in itertools.combinations(population['B'], 2):
                result = tools.sample_inference(N, n, {'A': sum(a), 'B': sum(b)})
                estimates.append(result['estimate'])
                variance_estimates.append(result['estimated_se'] ** 2)
        actual = statistics.pvariance(estimates)
        theoretical = tools.planning_precision(N, n, {'A': .5, 'B': 2/3})['planning_se'] ** 2
        self.assertAlmostEqual(actual, theoretical)
        self.assertAlmostEqual(actual, statistics.mean(variance_estimates))

    def test_conservative_bound_for_fixed_allocation(self):
        N, n = {'A': 90, 'B': 30}, {'A': 12, 'B': 8}
        bound = tools.planning_precision(N, n, {'A': .5, 'B': .5})['planning_se']
        for a in (0, .1, .4, .5, .9, 1):
            for b in (0, .2, .5, .8, 1):
                self.assertLessEqual(tools.planning_precision(N, n, {'A': a, 'B': b})['planning_se'], bound)

    def test_census_zero_sampling_variance(self):
        r = tools.sample_inference({'A': 4, 'B': 2}, {'A': 4, 'B': 2}, {'A': 2, 'B': 0})
        self.assertEqual(r['estimated_se'], 0)
        self.assertEqual(r['lower'], r['estimate'])
        self.assertEqual(r['warnings'], [])

    def test_zero_sample_rate_warns_not_certifies(self):
        r = tools.sample_inference({'A': 100}, {'A': 10}, {'A': 0})
        self.assertEqual(r['estimated_se'], 0)
        self.assertTrue(r['warnings'])

    def test_untruncated_interval_and_small_count_warning(self):
        r = tools.sample_inference({'A': 100}, {'A': 2}, {'A': 1})
        self.assertLess(r['lower'], 0)
        self.assertGreater(r['upper'], 1)
        self.assertTrue(r['warnings'])

    def test_weights_use_population_not_sample_mix(self):
        r = tools.sample_inference({'A': 80, 'B': 20}, {'A': 10, 'B': 10}, {'A': 5, 'B': 9})
        self.assertAlmostEqual(r['estimate'], .58)
        self.assertNotEqual(r['estimate'], .7)

    def test_bad_sizes(self):
        for N, n in [({}, {}), ({'A': 10}, {'B': 2}), ({'A': 10}, {'A': 1}), ({'A': 10}, {'A': 11}), ({'A': 10}, {'A': 2.0}), ({'A': True}, {'A': 2})]:
            with self.subTest(N=N, n=n), self.assertRaises(ValueError):
                tools.sample_inference(N, n, {'A': 1})

    def test_bad_counts(self):
        for y in [-1, 3, 1.0, True]:
            with self.subTest(y=y), self.assertRaises(ValueError):
                tools.sample_inference({'A': 10}, {'A': 2}, {'A': y})
        with self.assertRaises(ValueError):
            tools.sample_inference({'A': 10}, {'A': 2}, {'B': 1})

    def test_bad_assumptions(self):
        for p in [float('nan'), float('inf'), -.1, 1.1, True, '.5']:
            with self.subTest(p=p), self.assertRaises(ValueError):
                tools.planning_precision({'A': 10}, {'A': 2}, {'A': p})
        with self.assertRaises(ValueError):
            tools.planning_precision({'A': 10}, {'A': 2}, {'B': .5})


if __name__ == '__main__':
    unittest.main()
