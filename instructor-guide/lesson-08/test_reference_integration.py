"""Regression checks for L03/L08 integration; standard library and fictional data."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("reference08", Path(__file__).with_name("reference.py"))
reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference)


class ReferenceIntegrationTests(unittest.TestCase):
    def result(self, waits_and_states):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data/service"
            data.mkdir(parents=True)
            def write(name, rows):
                with (data / name).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
            write("windows.csv", [{"window_id": "A1", "center": "A"}])
            write("business_types.csv", [{"business_code": "basic", "reference_wait_minutes": "15"}])
            write("tickets_raw.csv", [
                {"ticket_id": f"T{i}", "export_revision": "1", "wait_minutes": str(wait),
                 "wait_unit": "minute", "window_id": "A1", "business_code": "basic",
                 "completed_same_day": "1", "abandoned": state, "date": "2026-04-13"}
                for i, (wait, state) in enumerate(waits_and_states)
            ])
            write("visits.csv", [{"contact_id": f"C{i}", "ticket_id": f"T{i}", "staff_minutes": "2"}
                                 for i in range(len(waits_and_states))])
            write("satisfaction.csv", [{"ticket_id": f"T{i}", "score": "4"}
                                       for i in range(len(waits_and_states))])
            write("staffing.csv", [{"date": "2026-04-13", "window_id": "A1",
                                   "staff_count": "1", "open_hours": "8", "absence_hours": "0"}])
            before = {p.name: p.read_bytes() for p in data.iterdir()}
            # Use the real L03 cleaner; the first-period table is intentionally empty.
            with patch.object(reference.u, "student_root", return_value=root), \
                 patch.object(reference.u, "baseline", return_value=[]), \
                 patch.object(reference.u, "emit") as emit:
                reference.main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in data.iterdir()})
            return emit.call_args.args[0]

    def test_unknown_abandonment_is_not_counted_as_served(self):
        result = self.result([(5, "0"), (60, "")])
        self.assertEqual(result["input_unique_tickets"], 2)
        self.assertEqual(result["raw_period_audit"]["missing_abandonment"], 1)
        self.assertEqual(result["unweighted_served_wait_mean"], 5)
        self.assertEqual(result["naive_contact_join_wait_mean"], 5)

    def test_all_unknown_states_produce_undefined_wait_not_zero(self):
        result = self.result([(60, "")])
        self.assertIsNone(result["unweighted_served_wait_mean"])
        self.assertIsNone(result["naive_contact_join_wait_mean"])
        json.dumps(result, allow_nan=False)

    def test_all_abandoned_produce_undefined_wait_not_zero(self):
        result = self.result([(60, "1")])
        self.assertIsNone(result["unweighted_served_wait_mean"])
        self.assertIsNone(result["naive_contact_join_wait_mean"])

    def test_observed_zero_wait_is_retained(self):
        result = self.result([(0, "0"), (60, "1")])
        self.assertEqual(result["unweighted_served_wait_mean"], 0)
        self.assertEqual(result["naive_contact_join_wait_mean"], 0)


if __name__ == "__main__":
    unittest.main()
