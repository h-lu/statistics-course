"""Regression checks for teacher references L01–04; standard library only.

Run from the repository root:
    python -m unittest discover -s instructor-guide/lesson-01 -p test_reference.py -v
Fixtures are fictional. Tests never write to the supplied course data.
"""
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

GUIDE = Path(__file__).resolve().parents[1]
ROOT = GUIDE.parent


def load(lesson):
    spec = importlib.util.spec_from_file_location(f"reference_l{lesson:02d}", GUIDE / f"lesson-{lesson:02d}" / "reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L1, L2, L3, L4 = (load(n) for n in range(1, 5))


def normalized(center="A", wait=5.0, abandon=0, business="basic", person="P1"):
    return {"center": center, "wait": wait, "abandon": abandon,
            "business_code": business, "person_id": person,
            "arrival_period": "上午", "completed": int(not abandon)}


def raw(tid="R1", revision="1", wait="120", unit="second", **changes):
    return {"ticket_id": tid, "export_revision": revision,
            "wait_minutes": wait, "wait_unit": unit,
            "window_id": "A1", "business_code": "basic",
            "completed_same_day": "1", "abandoned": "0", **changes}


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture(root, rows):
    directory = root / "data" / "service"
    write_csv(directory / "windows.csv", [{"window_id": "A1", "center": "A"}])
    write_csv(directory / "business_types.csv", [{"business_code": "basic", "reference_wait_minutes": "15"}])
    write_csv(directory / "tickets_raw.csv", rows, list(raw()))


class StatisticsTests(unittest.TestCase):
    def test_quantile_linear_and_endpoints(self):
        self.assertAlmostEqual(L1.quantile([31, 2, 4, 3], .9), 22.9)
        self.assertEqual(L1.quantile([2, 4], 0), 2)
        self.assertEqual(L1.quantile([2, 4], 1), 4)

    def test_empty_and_singleton(self):
        self.assertIsNone(L1.quantile([], .5))
        self.assertEqual(L1.describe([])["n"], 0)
        self.assertTrue(all(value is None for key, value in L1.describe([]).items() if key != "n"))
        self.assertEqual(L1.describe([7])["iqr"], 0)
        self.assertEqual(L1.describe([7])["std_n"], 0)

    def test_invalid_probability(self):
        for probability in (-.1, 1.1, math.nan, math.inf):
            with self.subTest(probability=probability), self.assertRaises(ValueError):
                L1.quantile([1, 2], probability)

    def test_nonfinite_values_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                L1.describe([1, value])
            with self.assertRaises(ValueError):
                L1.quantile([value], .5)

    def test_population_std_and_zero_denominator(self):
        self.assertEqual(L1.describe([0, 2])["std_n"], 1)
        self.assertIsNone(L1.rate(0, 0))
        self.assertEqual(L1.rate(0, 2), 0)

    def test_dictionary_keys_are_not_silently_overwritten(self):
        for rows in ([{"id": "A"}, {"id": "A"}], [{"id": ""}], [{"id": " "}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                L1.keyed(rows, "id")


class RootTests(unittest.TestCase):
    def test_monorepo_precedes_historical_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("student-template", "lesson-01-first-green", "course-student-template"):
                (root / name / "data" / "service").mkdir(parents=True)
            fake_script = root / "instructor-guide" / "lesson-01" / "reference.py"
            with patch.object(L1, "__file__", str(fake_script)):
                self.assertEqual(L1.student_root([]), root / "student-template")

    def test_historical_layouts_remain_supported(self):
        for name in ("lesson-01-first-green", "course-student-template"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / name / "data" / "service").mkdir(parents=True)
                with patch.object(L1, "__file__", str(root / "teacher" / "lesson-01" / "reference.py")):
                    self.assertEqual(L1.student_root([]), root / name)

    def test_explicit_invalid_root_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                L1.student_root(["--student-root", folder])

    def test_raw_only_root_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture(root, [raw()])
            self.assertEqual(L1.student_root(["--student-root", str(root)]), root)
            self.assertFalse((root / "data/service/tickets.csv").exists())
            run = subprocess.run([sys.executable, str(GUIDE / "lesson-03/reference.py"), "--student-root", str(root)], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(run.stdout)["audit"]["unique_tickets"], 1)


class Lesson01And02Tests(unittest.TestCase):
    def test_lesson01_worked_example(self):
        rows = [normalized(wait=value, abandon=int(i == 4), person=f"P{max(1, i)}")
                for i, value in enumerate([3, 4, 5, 8, 40])]
        result = L1.build_result(rows)
        center = result["centers"][0]
        self.assertEqual((result["registered_tickets"], result["unique_people_overall"]), (5, 4))
        self.assertEqual(center["served_wait"]["n"], 4)
        self.assertEqual(center["served_wait"]["mean"], 5)
        self.assertEqual(center["served_wait"]["median"], 4.5)
        self.assertEqual(center["abandon_rate"], .2)
        self.assertEqual(L1.describe([r["wait"] for r in rows])["mean"], 12)

    def test_person_counts_are_not_additive_across_centers(self):
        result = L1.build_result([normalized("A"), normalized("B")])
        self.assertEqual(result["unique_people_overall"], 1)
        self.assertEqual(sum(r["unique_people"] for r in result["centers"]), 2)

    def test_empty_centers_and_periods(self):
        result = L1.build_result([])
        self.assertIsNone(result["centers"][0]["same_day_rate"])
        self.assertEqual(result["served_wait_by_period"]["下午"]["n"], 0)
        json.dumps(result, allow_nan=False)

    def test_lesson02_worked_example(self):
        rows = [normalized("A", wait) for wait in [2, 3, 4, 31]]
        rows += [normalized("B", wait) for wait in [8, 9, 10, 13]]
        output = L2.build_result(rows)["comparisons"]
        served = next(r for r in output if r["scenario"] == "served_only")
        self.assertEqual(served["A_minus_B_mean"], 0)
        self.assertEqual(served["A_minus_B_median"], -6)
        self.assertAlmostEqual(served["A_minus_B_p90"], 10.8)

    def test_lesson02_empty_group_does_not_become_zero_effect(self):
        for comparison in L2.build_result([normalized("A")])["comparisons"]:
            self.assertIsNone(comparison["A_minus_B_mean"])
        self.assertIsNone(L2.difference(None, None))

    def test_baseline_rejects_ambiguous_or_invalid_data(self):
        windows = [{"window_id": "A1", "center": "A"}]
        valid = {"ticket_id": "T1", "window_id": "A1", "wait_minutes": "5",
                 "completed_same_day": "1", "abandoned": "0"}
        for changes in ({"window_id": "UNKNOWN"}, {"wait_minutes": "nan"},
                        {"wait_minutes": "-2"}, {"abandoned": ""}, {"completed_same_day": "2"}):
            with self.subTest(changes=changes), patch.object(L1, "read", side_effect=[windows, [{**valid, **changes}]]):
                with self.assertRaises(ValueError):
                    L1.baseline(Path("unused"))
        with patch.object(L1, "read", side_effect=[windows, [valid, valid]]):
            with self.assertRaises(ValueError):
                L1.baseline(Path("unused"))


class CleaningTests(unittest.TestCase):
    def clean(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture(root, rows)
            return L3.clean(root)

    def test_codes_are_recognized_before_unit_conversion(self):
        for sentinel in ("999", "-1"):
            self.assertEqual(L3.parse_wait(sentinel, "second"), (None, "wait_not_measured"))
        self.assertEqual(L3.parse_wait("180", "second"), (3, None))
        self.assertEqual(L3.parse_wait("60", "minute"), (60, None))
        self.assertEqual(L3.parse_wait("0", "minute"), (0, None))

    def test_missing_nonfinite_and_malformed_waits(self):
        for value in ("", "  ", None):
            self.assertEqual(L3.parse_wait(value, "minute"), (None, "wait_not_measured"))
        for value in ("NaN", "inf", "-inf", "bad", "-2"):
            self.assertEqual(L3.parse_wait(value, "minute"), (None, "wait_invalid"))
        self.assertEqual(L3.parse_wait("3", "hour"), (None, "wait_invalid"))

    def test_lesson03_worked_example_and_row_reconciliation(self):
        original = raw()
        rows, audit = self.clean([original, dict(original), raw(revision="2", wait="180"),
                                 raw("R2", wait="999", window_id="UNKNOWN"),
                                 raw("R3", wait="60", unit="minute", completed_same_day="0")])
        self.assertEqual(audit["raw_rows"], 5)
        self.assertEqual(audit["unique_tickets"], 3)
        self.assertEqual(audit["exact_duplicate_rows"], 1)
        self.assertEqual(audit["superseded_revision_rows"], 1)
        result = L3.build_result(rows, audit)
        self.assertEqual(result["served_valid_wait"]["mean"], 31.5)
        self.assertEqual(result["served_valid_wait"]["n"], 2)
        self.assertEqual(result["completion_specific_rate"], 2/3)
        self.assertEqual(result["complete_case_completion_rate"], 1/2)
        self.assertEqual(result["known_window_denominator"], 2)
        self.assertEqual(result["unknown_window_tickets"], 1)

    def test_cleaning_is_independent_of_file_order(self):
        rows = [raw(), raw(), raw(revision="2", wait="180"), raw("R2", wait="999")]
        expected = self.clean(rows)
        random.Random(31).shuffle(rows)
        self.assertEqual(expected, self.clean(rows))

    def test_conflicting_latest_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Conflicting latest revision"):
            self.clean([raw(revision="2", wait="120"), raw(revision="2", wait="180")])

    def test_empty_ticket_or_invalid_revision_is_rejected(self):
        for row in (raw(tid=""), raw(revision="zero"), raw(revision="0"), raw(revision="-1")):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.clean([row])

    def test_superseded_rows_are_not_revision_ticket_count(self):
        _, audit = self.clean([raw(), raw(revision="2", wait="180"), raw(revision="3", wait="240")])
        self.assertEqual(audit["tickets_with_revision"], 1)
        self.assertEqual(audit["superseded_revision_rows"], 2)

    def test_unknown_abandonment_is_not_served(self):
        rows, audit = self.clean([raw(abandoned="")])
        result = L3.build_result(rows, audit)
        self.assertEqual(result["served_valid_wait"]["n"], 0)
        self.assertEqual(result["completion_specific_denominator"], 1)
        self.assertIsNone(result["complete_case_completion_rate"])
        self.assertIn("missing_abandonment", result["unresolved_records"][0]["flags"])

    def test_empty_input_outputs_null_rates(self):
        rows, audit = self.clean([])
        result = L3.build_result(rows, audit)
        self.assertIsNone(result["completion_specific_rate"])
        self.assertIsNone(result["complete_case_completion_rate"])
        json.dumps(result, allow_nan=False)


class EvaluationTests(unittest.TestCase):
    def test_lesson04_worked_example(self):
        rows = [normalized("A", wait) for wait in [4, 5, 5, 6, 40]]
        rows += [normalized("B", wait) for wait in [8, 9, 10, 11, 12]]
        a, b, _ = L4.build_result(rows, {"basic": 15})["profiles"]
        self.assertEqual((a["mean"], a["median"], a["iqr"], a["served_over15"]), (12, 5, 1, .2))
        self.assertEqual((b["mean"], b["median"], b["iqr"], b["served_over15"]), (10, 10, 2, 0))

    def test_strict_threshold_and_union_without_double_count(self):
        rows = [normalized("A", 15), normalized("A", 30, business="case"),
                normalized("A", 40, abandon=1)]
        a = L4.build_result(rows, {"basic": 15, "case": 30})["profiles"][0]
        self.assertEqual(a["served_over_business_line_count"], 0)
        self.assertEqual(a["registered_bad_experience_count"], 1)
        self.assertEqual(a["registered_bad_experience"], 1/3)

    def test_all_abandoned_and_empty_centers_are_not_ranked_on_wait(self):
        result = L4.build_result([normalized("A", 40, abandon=1)], {"basic": 15})
        self.assertEqual(result["lower_is_better_tiers"]["mean"], [])
        self.assertEqual(result["undefined_centers"]["mean"], ["A", "B", "C"])
        self.assertEqual(result["profiles"][0]["registered_bad_experience"], 1)
        self.assertIsNone(result["profiles"][0]["served_over15"])
        json.dumps(result, allow_nan=False)

    def test_exact_ties_share_a_tier(self):
        result = L4.build_result([normalized(c) for c in "ABC"], {"basic": 15})
        self.assertEqual(result["lower_is_better_tiers"]["mean"], [["A", "B", "C"]])

    def test_thresholds_must_exist_and_be_finite(self):
        for thresholds in ({}, {"basic": math.nan}, {"basic": math.inf}, {"basic": -1}):
            with self.subTest(thresholds=thresholds), self.assertRaises(ValueError):
                L4.build_result([normalized()], thresholds)


class CourseDataRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = []
        data = ROOT / "student-template" / "data" / "service"
        paths = list(data.glob("*.csv"))
        if not paths:
            raise AssertionError("Run in the repository with student-template/data/service available")
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        for n in range(1, 5):
            script = GUIDE / f"lesson-{n:02d}" / "reference.py"
            command = [sys.executable, str(script)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
            second = subprocess.run(command, cwd=GUIDE, capture_output=True, text=True, check=True, timeout=30)
            explicit = subprocess.run(command + ["--student-root", str(ROOT / "student-template")], cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
            if first.stdout != second.stdout or first.stdout != explicit.stdout:
                raise AssertionError(f"L{n:02d}: output changed between invocations")
            result = json.loads(first.stdout)
            json.dumps(result, allow_nan=False)
            cls.results.append(result)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        if before != after:
            raise AssertionError("Reference changed supplied data")

    def test_lesson01_documented_baselines(self):
        result = self.results[0]
        self.assertEqual((result["registered_tickets"], result["unique_people_overall"]), (3600, 1986))
        for center, abandoned, mean in zip(result["centers"], [40, 22, 28], [13.4813, 11.4885, 12.6741]):
            self.assertEqual(center["registered"], 1200)
            self.assertEqual(center["abandoned"], abandoned)
            self.assertEqual(center["served_wait"]["n"], 1200-abandoned)
            self.assertAlmostEqual(center["served_wait"]["mean"], mean, places=4)

    def test_lesson02_documented_differences(self):
        rows = {r["scenario"]: r for r in self.results[1]["comparisons"]}
        for scenario, difference in [("served_only", 1.9928), ("served_basic", -2.8536), ("served_case", -6.3256)]:
            self.assertAlmostEqual(rows[scenario]["A_minus_B_mean"], difference, places=4)
        self.assertAlmostEqual(rows["served_afternoon"]["A_minus_B_p90"], -.509, places=3)

    def test_lesson03_documented_audit(self):
        result = self.results[2]
        for name, value in {"raw_rows": 1265, "unique_tickets": 1200, "exact_duplicate_rows": 39,
                            "superseded_revision_rows": 26, "tickets_with_revision": 26,
                            "converted_from_seconds": 42, "wait_not_measured": 19,
                            "unknown_window": 7, "unknown_business": 10, "missing_completion": 7}.items():
            self.assertEqual(result["audit"][name], value)
        self.assertEqual(result["completion_specific_denominator"], 1193)
        self.assertEqual(result["complete_case_denominator"], 1158)
        self.assertEqual(result["served_valid_wait"]["n"], 1122)
        self.assertAlmostEqual(result["served_valid_wait"]["mean"], 15.2114, places=4)
        self.assertEqual(len(result["unresolved_records"]), 1200-1158)

    def test_lesson04_documented_rules(self):
        result = self.results[3]
        self.assertEqual(result["lower_is_better_orders"]["served_over15"], ["B", "C", "A"])
        self.assertEqual(result["lower_is_better_orders"]["served_over_business_line"], ["A", "C", "B"])
        for row, count in zip(result["profiles"], [108, 151, 118]):
            self.assertEqual(row["registered_bad_experience_count"], count)
            self.assertEqual(row["registered_bad_experience"], count/1200)


if __name__ == "__main__":
    unittest.main()
