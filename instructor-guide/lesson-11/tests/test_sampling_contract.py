"""Independent tests of L11's public planning/acquisition/audit contract.

All writes stay in TemporaryDirectory. No application, database, production bank,
student repository or real course source is modified. Run with python3 -B.
"""
from __future__ import annotations

from collections import Counter
from contextlib import redirect_stdout
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
LESSON = ROOT / "student-template/lesson-11"
DATA = LESSON / "data"
TOOLS_PATH = LESSON / "sampling_tools.py"
ANALYSIS_PATH = LESSON / "analysis.py"
BUILD_PATH = ROOT / "instructor-guide/lesson-11/build_data.py"
TASK_ROOT = ROOT.parents[1]
TEMP_ROOT = TASK_ROOT / "audit" / "tmp"
EXPECTED_HASHES = {
    "frame.csv": "5461f03ae642b151920364b5aa8db4f960e2587f1038d044047924d329a33a55",
    "strata.csv": "bc63a744116d2f862372b4f2dbc7cad051fdbfcdd18da3b523ad5da73f951c64",
    "simulator/weekend_population.csv": "1230ee05eb580a93061adc71a7c0d87a867471cb7519962cb4c4a3099bbb3f24",
}
REAL_RANDOM = random.Random


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tools = load_module("l11_contract_sampling_tools", TOOLS_PATH)
builder = load_module("l11_contract_build_data", BUILD_PATH)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_rows():
    return [
        {"group": group, "answered": 1, "observed_need": int(i < yes)}
        for group, yes in (("A", 5), ("B", 9)) for i in range(10)
    ]


class SamplingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        cls.protected = [TOOLS_PATH, ANALYSIS_PATH, BUILD_PATH,
                         DATA / "provenance.json",
                         *(DATA / name for name in EXPECTED_HASHES)]
        cls.before_hashes = {str(p): sha(p) for p in cls.protected}
        cls.frame = tools.load_frame()
        with (DATA / "simulator/weekend_population.csv").open(
                encoding="utf-8", newline="") as handle:
            cls.population = list(csv.DictReader(handle))

    @classmethod
    def tearDownClass(cls):
        after = {str(p): sha(p) for p in cls.protected}
        if after != cls.before_hashes:
            raise AssertionError("Tests changed protected source/data bytes")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="l11-contract-",
                                                dir=TEMP_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)

    def request(self, mode="register_ordinary", n=200):
        return tools.make_request(self.frame, mode, n, 47, 991)

    def test_historical_population_counts_and_truth(self):
        self.assertEqual(len(self.population), 4000)
        self.assertEqual(Counter(r["group"] for r in self.population),
                         {"A": 3200, "B": 800})
        yes = Counter(r["group"] for r in self.population
                      if r["need_weekend"] == "1")
        self.assertEqual(yes, {"A": 1120, "B": 520})
        self.assertEqual(sum(yes.values()), 1640)
        self.assertEqual(1640 / 4000, .41)
        self.assertEqual(len({r["person_id"] for r in self.population}), 4000)

    def test_provenance_preserves_historical_identity_and_exact_hashes(self):
        provenance = json.loads((DATA / "provenance.json").read_text())
        self.assertEqual(provenance["origin_commit"],
                         "ce955719b68991166c86fbb1ecae1d203e7a0671")
        self.assertEqual(provenance["population_seed"], 20261011)
        self.assertEqual(provenance["population_id"],
                         "weekend-4000-20261011-v1")
        self.assertEqual(provenance["files_sha256"], EXPECTED_HASHES)
        self.assertEqual({name: sha(DATA / name) for name in EXPECTED_HASHES},
                         EXPECTED_HASHES)
        self.assertEqual(provenance["acquisition_rules"]["web_response_given_need"], .85)
        self.assertEqual(provenance["acquisition_rules"]["web_response_given_no_need"], .25)
        self.assertTrue(provenance["acquisition_rules"]["ordinary_within_group_independent_of_need"])

    def test_generator_rebuilds_all_data_and_provenance_exactly(self):
        generated = self.scratch / "rebuilt"
        builder.build(generated)
        for name in (*EXPECTED_HASHES, "provenance.json"):
            with self.subTest(file=name):
                self.assertEqual((generated / name).read_bytes(),
                                 (DATA / name).read_bytes())

    def test_public_frame_is_exact_outcome_free_projection(self):
        self.assertEqual(len(self.frame), 4000)
        self.assertTrue(all(set(row) == {"person_id", "group", "online_frame"}
                            for row in self.frame))
        expected = [{key: int(row[key]) if key == "online_frame" else row[key]
                     for key in ("person_id", "group", "online_frame")}
                    for row in self.population]
        self.assertEqual(self.frame, expected)
        self.assertEqual(Counter(r["group"] for r in self.frame if r["online_frame"]),
                         {"A": 2861, "B": 444})

    def test_load_frame_accepts_only_public_columns(self):
        public_copy = self.scratch / "frame.csv"
        public_copy.write_bytes((DATA / "frame.csv").read_bytes())
        self.assertEqual(tools.load_frame(public_copy), self.frame)
        with self.assertRaises(ValueError):
            tools.load_frame(DATA / "simulator/weekend_population.csv")
        contaminated = [dict(row, need_weekend=0) for row in self.frame]
        with self.assertRaises(ValueError):
            tools.choose_invites(contaminated, 5, 47, "register_ordinary")

    def test_planning_never_calls_latent_population_reader(self):
        with mock.patch.object(tools, "_population",
                               side_effect=AssertionError("latent read during design")) as latent:
            for mode in sorted(tools.MECHANISMS):
                invited = tools.choose_invites(self.frame, 31, 47, mode)
                request = tools.make_request(self.frame, mode, 31, 47, 991)
                self.assertEqual(invited, request["invited_ids"])
                tools.validate_request(request)
            latent.assert_not_called()

    def test_each_mode_invites_unique_eligible_ids_within_bounds(self):
        for mode in sorted(tools.MECHANISMS):
            eligible = {r["person_id"] for r in self.frame
                        if mode != "web_voluntary" or r["online_frame"]}
            for n in (1, len(eligible)):
                with self.subTest(mode=mode, n=n):
                    invited = tools.choose_invites(self.frame, n, 47, mode)
                    self.assertEqual(len(invited), n)
                    self.assertEqual(len(set(invited)), n)
                    self.assertTrue(set(invited) <= eligible)
            with self.assertRaises(ValueError):
                tools.choose_invites(self.frame, len(eligible) + 1, 47, mode)
        for invalid in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                tools.choose_invites(self.frame, invalid, 47, "register_ordinary")

    def test_request_identity_validation_rejects_changed_or_duplicate_ids(self):
        original = self.request()
        for field, value in (
                ("population_id", "other-population"), ("frame_sha256", "0" * 64),
                ("protocol", "other-protocol"),
                ("invited_ids", original["invited_ids"][:-1] + original["invited_ids"][:1])):
            with self.subTest(field=field):
                changed = dict(original, **{field: value})
                with self.assertRaises(ValueError):
                    tools.validate_request(changed)

    def test_invitation_probabilities_match_selected_frames(self):
        for mode in sorted(tools.MECHANISMS):
            request = self.request(mode, 73)
            observations, receipt = tools.run_request(request, self.scratch / mode)
            frame_n = 3305 if mode == "web_voluntary" else 4000
            for row, public in zip(observations, self.frame):
                eligible = mode != "web_voluntary" or bool(public["online_frame"])
                self.assertEqual(row["in_frame"], int(eligible))
                self.assertEqual(row["invite_probability"], 73 / frame_n if eligible else 0)
                self.assertFalse(row["invited"] and not eligible)
            self.assertEqual(sum(row["invited"] for row in observations), 73)
            self.assertEqual(receipt["invited"], 73)

    def test_unobserved_values_remain_none_in_memory_and_csv_readback(self):
        observations, _ = tools.run_request(self.request(), self.scratch / "run")
        self.assertTrue(any(r["invited"] and not r["answered"] for r in observations))
        self.assertTrue(any(not r["invited"] for r in observations))
        for row in observations:
            if row["answered"]:
                self.assertIn(row["observed_need"], (0, 1))
            else:
                self.assertIsNone(row["observed_need"])
            self.assertNotIn("need_weekend", row)
            self.assertNotIn("response_probability", row)
        path = self.scratch / "run/observations.csv"
        self.assertEqual(tools.read_observations(path), observations)
        with path.open(encoding="utf-8", newline="") as handle:
            for raw in csv.DictReader(handle):
                if raw["answered"] == "0":
                    self.assertEqual(raw["observed_need"], "")

    def constant_uniform_run(self, mode, value, name):
        n = 3305 if mode == "web_voluntary" else 4000
        request = self.request(mode, n)
        def factory(seed):
            return SimpleNamespace(random=lambda: value) if seed == 991 else REAL_RANDOM(seed)
        with mock.patch.object(tools.random, "Random", side_effect=factory):
            return tools.run_request(request, self.scratch / name)[0]

    def test_ordinary_response_thresholds_are_group_based_not_need_based(self):
        # A=0.8 and B=0.6, strict '<'. Same uniform value within each group
        # gives identical response flags for latent need 0 and 1.
        for value, expected in (
                (.59, {"A": 3200, "B": 800}),
                (.6, {"A": 3200}),
                (.79, {"A": 3200}),
                (.8, {})):
            with self.subTest(uniform=value):
                rows = self.constant_uniform_run("register_ordinary", value,
                                                 f"ordinary-{value}")
                self.assertEqual(Counter(r["group"] for r in rows if r["answered"]),
                                 expected)
                for group in ("A", "B"):
                    flags = {r["answered"] for r in rows if r["group"] == group}
                    self.assertEqual(len(flags), 1)

    def test_web_response_preserves_point85_point25_thresholds(self):
        # All online-frame units are invited; offline units cannot answer.
        need_by_id = {r["person_id"]: int(r["need_weekend"]) for r in self.population}
        for value in (.249, .25, .849, .85):
            with self.subTest(uniform=value):
                rows = self.constant_uniform_run("web_voluntary", value,
                                                 f"web-{value}")
                for row in rows:
                    need = need_by_id[row["person_id"]]
                    expected = bool(row["in_frame"]) and value < (.85 if need else .25)
                    self.assertEqual(bool(row["answered"]), expected)

    def test_complete_means_all_invited_reply_not_all_population(self):
        rows, receipt = tools.run_request(self.request("register_complete", 31),
                                          self.scratch / "complete")
        self.assertEqual(sum(r["answered"] for r in rows), 31)
        self.assertEqual(receipt["responded"], 31)
        self.assertEqual(sum(r["observed_need"] is None for r in rows), 3969)

    def test_same_request_and_seeds_reproduce_exact_output_bytes(self):
        request = self.request("web_voluntary", 137)
        tools.run_request(request, self.scratch / "one")
        tools.run_request(request, self.scratch / "two")
        for name in ("request.json", "observations.csv", "receipt.json"):
            self.assertEqual((self.scratch / "one" / name).read_bytes(),
                             (self.scratch / "two" / name).read_bytes())

    def test_request_and_run_never_overwrite_previous_output(self):
        request = self.request()
        request_path = self.scratch / "plan.json"
        tools.write_request(request, request_path)
        old_request = request_path.read_bytes()
        with self.assertRaises(FileExistsError):
            tools.write_request(request, request_path)
        self.assertEqual(request_path.read_bytes(), old_request)
        tools.run_request(request, self.scratch / "acquired")
        before = {p.name: p.read_bytes() for p in (self.scratch / "acquired").iterdir()}
        with self.assertRaises(FileExistsError):
            tools.run_request(request, self.scratch / "acquired")
        self.assertEqual({p.name: p.read_bytes() for p in (self.scratch / "acquired").iterdir()},
                         before)

    def test_postplan_audit_validates_completed_acquisition_and_fixed_truth(self):
        request = self.request()
        output = self.scratch / "run"
        _, receipt = tools.run_request(request, output)
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        audit = tools.audit_population(request, output)
        self.assertEqual((audit["population_n"], audit["population_need_n"],
                          audit["population_rate"]), (4000, 1640, .41))
        self.assertEqual(audit["group_rates"], {"A": .35, "B": .65})
        self.assertEqual(audit["request_sha256"], receipt["request_sha256"])
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)

    def test_postplan_audit_rejects_changed_supplied_request(self):
        request = self.request()
        output = self.scratch / "run"
        tools.run_request(request, output)
        changed = tools.make_request(self.frame, "register_ordinary", 200, 48, 991)
        with self.assertRaises(ValueError):
            tools.audit_population(changed, output)

    def test_postplan_audit_rejects_changed_saved_request(self):
        request = self.request()
        output = self.scratch / "run"
        tools.run_request(request, output)
        changed = dict(request, response_seed=992)
        (output / "request.json").write_text(json.dumps(changed))
        with self.assertRaises(ValueError):
            tools.audit_population(request, output)

    def test_postplan_audit_rejects_changed_observation_bytes(self):
        request = self.request()
        output = self.scratch / "run"
        tools.run_request(request, output)
        path = output / "observations.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            tools.audit_population(request, output)

    def test_small_example_hand_calculation_and_missing_group(self):
        rows = fixture_rows()
        biased = [{"group": g, "answered": 1, "observed_need": int(i < yes)}
                  for g, yes in (("A", 8), ("B", 9)) for i in range(10)]
        self.assertEqual(tools.response_mean(rows), .7)
        self.assertAlmostEqual(tools.composition_estimate(rows, {"A": 80, "B": 20}), .58)
        self.assertAlmostEqual(tools.composition_estimate(biased, {"A": 80, "B": 20}), .82)
        self.assertIsNone(tools.composition_estimate(
            [r for r in rows if r["group"] == "A"], {"A": 80, "B": 20}))
        self.assertIsNone(tools.response_mean([], "B"))
        self.assertIsNone(tools.composition_estimate([], {"A": 80, "B": 20}))

    def test_analysis_only_runs_toy_example_and_public_frame_check(self):
        with mock.patch.dict(sys.modules, {"sampling_tools": tools}):
            analysis = load_module("l11_contract_analysis", ANALYSIS_PATH)
        with mock.patch.object(analysis, "HERE", self.scratch), \
             mock.patch.object(tools, "_population",
                               side_effect=AssertionError("base analysis read truth")), \
             mock.patch.object(tools, "run_request",
                               side_effect=AssertionError("base analysis acquired formal data")), \
             redirect_stdout(io.StringIO()):
            analysis.main()
        result = json.loads((self.scratch / "artifacts/example.json").read_text())
        toy = result["example_only"]
        self.assertEqual(toy["population_n"], 100)
        self.assertEqual(toy["group_counts"], {"A": 80, "B": 20})
        self.assertEqual(toy["unweighted"], .7)
        self.assertAlmostEqual(toy["composition_adjusted"], .58)
        self.assertAlmostEqual(toy["biased_within_A_adjusted"], .82)
        self.assertIsNone(toy["missing_B_adjusted"])
        self.assertEqual(result["public_input_check"]["population_n"], 4000)
        self.assertFalse(result["public_input_check"]["formal_acquisition_run"])
        self.assertEqual(result["trace_example_only"][2]["observed_need"], None)

    def test_readback_rejects_unanswered_outcome_or_uninvited_answer(self):
        output = self.scratch / "run"
        tools.run_request(self.request(), output)
        with (output / "observations.csv").open(encoding="utf-8", newline="") as handle:
            original = list(csv.DictReader(handle))
        for field, value, select in (
                ("observed_need", "0", lambda r: r["answered"] == "0"),
                ("invited", "0", lambda r: r["answered"] == "1")):
            with self.subTest(field=field):
                rows = [dict(r) for r in original]
                row = next(r for r in rows if select(r))
                row[field] = value
                fixture = self.scratch / f"bad-{field}.csv"
                with fixture.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=tools.OBSERVATION_FIELDS)
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaises(ValueError):
                    tools.read_observations(fixture)


if __name__ == "__main__":
    unittest.main()
