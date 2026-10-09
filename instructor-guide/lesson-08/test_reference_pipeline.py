"""第8课教师参考流程的统计边界；不以正式答案替代方法检查。"""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("student08", Path(__file__).with_name("exploratory_reference.py"))
s = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)
CONFIG = {"revision_conflict": "stop", "window_join": "left", "metric_scope": "per_metric", "staffing_coverage": "union"}


def fixture():
    return {
        "tickets.csv": [dict(ticket_id=f"T{i}", date="2026-04-13", window_id="A1", business_code="basic",
                             wait_minutes=str(w), abandoned="0", completed_same_day="1") for i,w in ((1,2),(2,10))],
        "tickets_raw.csv": [],
        "windows.csv": [{"window_id":"A1", "center":"A"}],
        "business_types.csv": [{"business_code":"basic"}],
        "satisfaction.csv": [{"ticket_id":"T1", "invited":"1", "score":""}],
        "visits.csv": [dict(contact_id=f"C{i}", ticket_id=t, staff_minutes=str(m), contact_date="2026-04-13")
                       for i,t,m in ((1,"T1",2),(2,"T1",3),(3,"T1",4),(4,"T2",7))],
        "staffing.csv": [dict(date=d, window_id="A1", staff_count="1", open_hours="8", absence_hours="0")
                         for d in ("2026-04-13","2026-04-14")],
    }


def run(data, config=CONFIG):
    rows, ca = s.clean(data, config["revision_conflict"])
    joined, ja = s.join(rows, data, config)
    metrics, days, ra = s.indicators(joined, data, config, ja)
    return rows, ca, joined, ja, metrics, days, ra


class StudentPipelineTests(unittest.TestCase):
    def test_unit_and_survey_status_and_source_preserved(self):
        data=fixture(); before=copy.deepcopy(data)
        rows,_,joined,ja,m,days,ra=run(data)
        self.assertEqual(data,before)
        self.assertEqual(m["served_wait_mean"],6)
        self.assertEqual(m["contact_weighted_wait_mean"],4)
        self.assertEqual(ja["survey_status_all"],{"no_response":1,"missing_registration":1})
        self.assertIsNone(m["satisfied_among_responses"])
        self.assertEqual(ra["source_minutes"],16)
        self.assertEqual(ra["known_plan_person_hours_in_report"],16)
        self.assertEqual(ra["plan_days_without_recorded_activity"],1)

    def test_unknown_abandonment_is_not_served_and_empty_is_null(self):
        data=fixture()
        for r in data["tickets.csv"]: r["abandoned"]=""
        *_,m,days,ra=run(data)
        self.assertEqual(m["served_wait_n"],0)
        self.assertIsNone(m["served_wait_mean"])

    def test_cross_day_and_missing_plan_not_zero(self):
        data=fixture();data["visits.csv"][0]["contact_date"]="2026-04-15"
        *_,m,days,ra=run(data)
        late=next(d for d in days if d["date"]=="2026-04-15")
        self.assertEqual(late["staff_minutes"],2)
        self.assertIsNone(late["planned_person_hours"])
        self.assertIsNone(late["recorded_contact_hours_over_plan"])
        self.assertEqual(ra["cross_day_contacts"],1)
        self.assertEqual(ra["activity_days_without_plan"],1)

    def test_orphan_and_unknown_window_minutes_reconcile(self):
        data=fixture();data["tickets.csv"][1]["window_id"]="UNKNOWN"
        data["visits.csv"].append(dict(contact_id="C5",ticket_id="ORPHAN",staff_minutes="5",contact_date="2026-04-13"))
        *_,ja,m,days,ra=run(data)
        self.assertEqual(ja["orphan_contact_n"],1)
        self.assertEqual(ra["unassigned_contact_n"],2)
        self.assertEqual(ra["unassigned_minutes"],12)
        self.assertEqual(ra["assigned_minutes"]+ra["unassigned_minutes"],21)
        self.assertTrue(ra["minutes_reconciled"])

    def test_revision_numeric_and_conflict_quarantine_consensus(self):
        data=fixture();r=dict(data["tickets.csv"][0]);r["ticket_id"]="R1";r["wait_unit"]="minute"
        data["tickets_raw.csv"]=[dict(r,export_revision="9",wait_minutes="40"),dict(r,export_revision="10",wait_minutes="8")]
        rows,ca,*_=run(data)
        self.assertEqual(next(x for x in rows if x["ticket_id"]=="R1")["wait"],8)
        data["tickets_raw.csv"].append(dict(r,export_revision="10",wait_minutes="20",date="2026-04-14"))
        with self.assertRaises(ValueError): run(data)
        rows,ca,joined,ja,m,days,ra=run(data,{**CONFIG,"revision_conflict":"quarantine"})
        conflict=next(x for x in rows if x["ticket_id"]=="R1")
        self.assertIsNone(conflict["wait"])
        self.assertIsNone(conflict["date"])
        self.assertEqual(conflict["completed"],1)
        self.assertEqual(ra["unknown_registration_date_ticket_n"],1)

    def test_duplicate_keys_fail_without_overwriting(self):
        data=fixture();data["visits.csv"].append(dict(data["visits.csv"][0]))
        with self.assertRaises(ValueError): run(data)
        data=fixture();data["staffing.csv"].append(dict(data["staffing.csv"][0]))
        with self.assertRaises(ValueError): run(data)

    def test_activity_scope_changes_known_plan_range(self):
        data=fixture()
        *_,m,days,ra=run(data,{**CONFIG,"staffing_coverage":"activity_only"})
        self.assertEqual(ra["known_plan_person_hours_all"],16)
        self.assertEqual(ra["known_plan_person_hours_in_report"],8)
        self.assertEqual(ra["source_minutes"],16)


if __name__=="__main__":
    unittest.main()
