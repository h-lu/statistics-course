"""Check L05–08 worked examples and existing reference results, not learning outcomes.

From repository root:
    python -m unittest discover -s instructor-guide/lesson-05 -p test_teaching_05_08.py -v
Uses only the standard library. Reads supplied CSVs; never regenerates them.
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "instructor-guide"
DATA = ROOT / "student-template" / "data"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def alert_reference():
    spec = importlib.util.spec_from_file_location("teaching_alert_reference", GUIDE / "lesson-05/reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ALERT = alert_reference()


def device(index, score, label):
    return {"record_id": f"day-D{index:03d}", "device_id": f"D{index:03d}",
            "date": "day", "score": score, "label": label,
            "device_class": f"group-{index}", "miss_loss": 100,
            "inspection_cost": 3}


def replay(rows, capacity, effectiveness=.85):
    return ALERT.replay(rows, {"day": capacity}, lambda r: 0, "score", effectiveness=effectiveness)


class WorkedExamples(unittest.TestCase):
    def test_05_ecdf_and_tied_threshold_capacity(self):
        scores = [80, 40, 40, 20]
        self.assertEqual(sum(x <= 40 for x in scores)/len(scores), .75)
        self.assertEqual(sum(x >= 40 for x in scores), 3)
        self.assertEqual(sum(x > 40 for x in scores), 1)

    def test_05_four_devices_loss_and_confusion(self):
        rows = [device(i, s, y) for i, (s, y) in enumerate([(80, 1), (40, 0), (40, 1), (20, 0)], 1)]
        result = replay(rows, 2)
        self.assertEqual([result[k] for k in ("TP", "FP", "FN", "TN")], [1, 1, 1, 1])
        self.assertEqual((result["FPR"], result["FNR"]), (.5, .5))
        self.assertEqual(result["total_loss"], 121)
        self.assertEqual(replay(rows, 0)["total_loss"], 200)
        self.assertEqual(200-result["total_loss"], 79)

    def test_05_fixed_tie_rule_is_label_independent(self):
        rows = [device(i, s, y) for i, (s, y) in enumerate([(80, 1), (40, 0), (40, 1), (20, 0)], 1)]
        before = replay(rows, 2)
        after = replay(list(reversed([{**r, "label": 1-r["label"]} for r in rows])), 2)
        picked = lambda result: {g for g, v in result["by_group"].items() if v["reviewed"]}
        self.assertEqual(picked(before), {"group-1", "group-2"})
        self.assertEqual(picked(before), picked(after))

    def test_05_hundred_records_and_two_effect_assumptions(self):
        rows = [device(i, 80 if i < 20 else 20, int(i < 6 or 20 <= i < 24)) for i in range(100)]
        result = replay(rows, 20)
        self.assertEqual([result[k] for k in ("TP", "FP", "FN", "TN")], [6, 14, 4, 76])
        self.assertAlmostEqual(result["FPR"], 14/90)
        self.assertEqual(result["FNR"], .4)
        self.assertNotEqual(result["FPR"], result["FP"]/result["reviews"])
        self.assertEqual(result["total_loss"], 550)
        self.assertEqual(replay(rows, 20, .8)["total_loss"], 580)

    def test_05_undefined_error_rates_are_not_zero(self):
        self.assertIsNone(replay([device(1, 80, 1)], 1)["FPR"])
        self.assertIsNone(replay([device(1, 80, 0)], 1)["FNR"])

    def test_06_marginal_stratified_reversal(self):
        self.assertEqual((18+48)/100, .66)
        self.assertEqual((64+10)/100, .74)
        self.assertGreater(18/20, 64/80)
        self.assertGreater(48/80, 10/20)
        self.assertLess((18+48)/100, (64+10)/100)

    def test_06_two_common_targets_and_whole_range(self):
        a = lambda w: (1-w)*.9+w*.6
        b = lambda w: (1-w)*.8+w*.5
        self.assertAlmostEqual(a(.5), .75)
        self.assertAlmostEqual(b(.5), .65)
        self.assertAlmostEqual(a(.75), .675)
        self.assertAlmostEqual(b(.75), .575)
        # The proof is linearity with equal endpoint differences; grid is an extra check.
        self.assertAlmostEqual(.9-.8, .6-.5)
        for w in (0, .1, .25, .5, .75, .9, 1):
            with self.subTest(w=w):
                self.assertAlmostEqual(a(w)-b(w), .1)

    def test_07_three_disjoint_groups_and_four_denominators(self):
        self.assertEqual(50+10+40, 100)
        self.assertEqual([50/100, 40/50, 40/100, 32/40], [.5, .8, .4, .8])

    def test_07_bounds_scenarios_and_threshold(self):
        proportion = lambda q: (32+60*q)/100
        for q, expected in [(0, .32), (.25, .47), (.5, .62), (.75, .77), (1, .92)]:
            with self.subTest(q=q):
                self.assertAlmostEqual(proportion(q), expected)
        critical = (70-32)/60
        self.assertAlmostEqual(proportion(critical), .70)
        self.assertLess(proportion(critical-.01), .70)

    def test_07_two_missingness_processes(self):
        proportion = lambda uninvited, nonresponse: (32+50*uninvited+10*nonresponse)/100
        self.assertEqual(proportion(.4, .8), .60)
        self.assertEqual(proportion(.8, .4), .76)
        self.assertAlmostEqual(proportion(.5, .8)-proportion(.4, .8), .05)
        self.assertAlmostEqual(proportion(.4, .9)-proportion(.4, .8), .01)

    def test_08_expansion_and_correct_aggregation(self):
        waits = {"T1": 2, "T2": 10}
        contacts = [("T1", 2), ("T1", 3), ("T1", 4), ("T2", 7)]
        expanded = [waits[ticket] for ticket, _ in contacts]
        self.assertEqual(sum(waits.values())/len(waits), 6)
        self.assertEqual(sum(expanded)/len(expanded), 4)
        self.assertEqual(sum(expanded)/len(waits), 8)
        self.assertEqual(sum(minutes for _, minutes in contacts), 16)
        self.assertEqual({ticket: sum(m for t, m in contacts if t == ticket) for ticket in waits}, {"T1": 9, "T2": 7})

    def test_08_staff_hours_are_not_additive_after_join(self):
        self.assertEqual(2*8, 16)
        self.assertEqual(4*8, 32)
        self.assertAlmostEqual(16/60, 4/15)
        # Two planned window-days remain even when only one has tickets.
        plans = {("W1", "day1"): 8, ("W1", "day2"): 8}
        active = {("W1", "day1")}
        self.assertEqual(sum(plans.values()), 16)
        self.assertEqual(sum(plans[k] for k in active), 8)

    def test_08_equal_means_do_not_prove_no_records_lost(self):
        all_waits, matched = [2, 10, 6], [2, 10]
        self.assertEqual(sum(all_waits)/len(all_waits), sum(matched)/len(matched))
        self.assertEqual(len(all_waits), len(matched)+1)
        self.assertEqual(21, 16+5)
        self.assertEqual(5, 4+1)


class SuppliedReferenceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(DATA.glob("service/*.csv"))+sorted(DATA.glob("alerts/*.csv"))
        if len(cls.paths) != 11:
            raise AssertionError("Run with all seven service and four alerts CSVs present")
        cls.before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}
        cls.results = {}
        for n in range(5, 9):
            command = [sys.executable, str(GUIDE/f"lesson-{n:02d}/reference.py"),
                       "--student-root", str(DATA.parent)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
            second = subprocess.run(command, cwd=GUIDE, capture_output=True, text=True, check=True, timeout=30)
            if first.stdout != second.stdout:
                raise AssertionError(f"L{n:02d}: output differs between repeated runs/directories")
            cls.results[n] = json.loads(first.stdout)
            json.dumps(cls.results[n], allow_nan=False)
        cls.after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}

    def test_data_unchanged_by_all_reference_runs(self):
        self.assertEqual(self.before, self.after)

    def test_05_development_and_later_period_sizes(self):
        result = self.results[5]
        for period, count, faults, days in [("development", 3780, 439, 42), ("evaluation", 1260, 166, 14)]:
            for row in result[period]:
                with self.subTest(period=period, policy=row["policy"]):
                    self.assertEqual((row["records"], row["TP"]+row["FN"], row["days"]), (count, faults, days))
                    self.assertEqual(sum(row[k] for k in ("TP", "FP", "FN", "TN")), count)
                    self.assertEqual(row["reviews"], row["TP"]+row["FP"])
                    self.assertEqual(row["capacity_violations"], 0)

    def test_05_reference_losses_and_group_coverage(self):
        result = {r["policy"]: r for r in self.results[5]["evaluation"]}
        for policy, expected in [("none", 1003000), ("score", 638490), ("score_times_loss", 421800), ("estimated_net_benefit", 390650)]:
            self.assertEqual(result[policy]["total_loss"], expected)
        net = result["estimated_net_benefit"]
        self.assertEqual([net[k] for k in ("TP", "FP", "FN", "TN")], [95, 165, 71, 929])
        self.assertEqual(net["by_group"]["一般"]["reviewed"], 0)
        self.assertAlmostEqual(net["FPR"], 165/1094)
        self.assertAlmostEqual(net["FNR"], 71/166)

    def test_05_scenarios_are_daily_rounded_and_not_new_data(self):
        rows = self.results[5]["evaluation_scenarios_not_new_validation"]
        self.assertEqual([(r["reviews"], r["total_loss"]) for r in rows], [(128, 616260), (260, 654450), (260, 315250)])
        self.assertEqual(rows[0]["available_slots"], 10*10+4*7)
        for row in rows:
            self.assertEqual(row["records"], 1260)

    def test_06_counts_and_common_weights(self):
        result = self.results[6]
        for name, expected in {"A": (238, 252, 697, 948), "B": (834, 935, 163, 265), "C": (529, 591, 414, 609)}.items():
            group = result["centers"][name]
            s = group["strata"]
            self.assertEqual((s["basic"]["completed"], s["basic"]["n"], s["case"]["completed"], s["case"]["n"]), expected)
            self.assertAlmostEqual(group["overall"], (expected[0]+expected[2])/1200)
        self.assertAlmostEqual(result["pooled_case_weight"], 1822/3600)

    def test_06_order_is_supported_by_both_strata(self):
        result = self.results[6]
        self.assertTrue(result["simpson_A_B"])
        for stratum in ("basic", "case"):
            rates = [result["centers"][c]["strata"][stratum]["rate"] for c in "ACB"]
            self.assertGreater(rates[0], rates[1])
            self.assertGreater(rates[1], rates[2])
        for row in result["standardized"]:
            self.assertEqual(row["order_high_to_low"], list("ACB"))
        pooled = next(r for r in result["standardized"] if r["common_case_weight"] == result["pooled_case_weight"])
        for center, expected in zip("ABC", [83.8560, 75.1844, 78.6132]):
            self.assertAlmostEqual(pooled["rates"][center]*100, expected, places=4)

    def test_07_funnel_and_four_rates(self):
        result = self.results[7]
        self.assertEqual([result[k] for k in ("target_tickets", "invited", "responded", "satisfied_respondents")], [3600, 3199, 2099, 1856])
        self.assertEqual(401+1100+result["responded"], result["target_tickets"])
        for name, value in [("invitation_rate", 3199/3600), ("response_among_invited", 2099/3199), ("response_among_all", 2099/3600), ("respondent_satisfied_rate", 1856/2099)]:
            self.assertEqual(result[name], value)

    def test_07_bounds_scenarios_and_eighty_percent_threshold(self):
        result = self.results[7]
        self.assertEqual(result["no_assumption_bounds"], [1856/3600, 3357/3600])
        for row in result["scenarios"]:
            self.assertEqual(row["overall_satisfied_rate"], (1856+1501*row["missing_satisfied_rate"])/3600)
        self.assertEqual((1856+1024)/3600, .8)
        self.assertAlmostEqual(1024/1501*100, 68.2212, places=4)

    def test_07_adjustment_uses_target_weights_and_flags_sparse_cell(self):
        result = self.results[7]
        estimate = sum(r["target_n"]/3600*r["observed_satisfied_rate"] for r in result["cells"])
        self.assertAlmostEqual(estimate, result["stratum_adjusted_under_within_cell_MAR"])
        self.assertAlmostEqual(estimate*100, 86.7350, places=4)
        sparse = next(r for r in result["cells"] if r["business"] == "basic" and r["abandoned"] == 1)
        self.assertEqual((sparse["target_n"], sparse["responded"]), (13, 3))
        self.assertEqual(result["target_units_in_zero_response_cells"], 0)

    def test_08_cardinality_and_preserved_totals(self):
        result = self.results[8]
        self.assertEqual((result["input_unique_tickets"], result["contact_rows"], result["staffing_unique_window_days"]), (4800, 8921, 240))
        self.assertEqual(result["unknown_window_tickets_quarantined_for_window_report"], 7)
        for key in ("contacts_without_ticket", "tickets_without_contacts", "tickets_without_survey"):
            self.assertEqual(result[key], 0)
        self.assertAlmostEqual(result["source_staff_minutes"], 89466.8)
        self.assertAlmostEqual(result["source_staff_minutes"], result["ticket_aggregated_staff_minutes"])

    def test_08_naive_join_changes_means_and_hours(self):
        result = self.results[8]
        self.assertAlmostEqual(result["unweighted_served_wait_mean"], 13.1893, places=4)
        self.assertAlmostEqual(result["naive_contact_join_wait_mean"], 14.8399, places=4)
        self.assertEqual(result["unique_planned_person_hours"], 2460)
        self.assertEqual(result["incorrect_hours_after_contact_join"], 91016)

    def test_08_current_same_day_assumption_not_a_future_guarantee(self):
        tickets = read_csv(DATA/"service/tickets.csv")+read_csv(DATA/"service/tickets_raw.csv")
        dates = {r["ticket_id"]: r["date"] for r in tickets}
        for row in read_csv(DATA/"service/visits.csv"):
            self.assertEqual(row["contact_date"], dates[row["ticket_id"]])
        self.assertEqual(self.results[8]["reported_window_days"], 240)
        self.assertEqual(len(self.results[8]["sample_window_day_reports"]), 6)


if __name__ == "__main__":
    unittest.main()
