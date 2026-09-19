"""Code regression checks using fictional edge cases and copied course data.

Run at the repository root: python -m pytest instructor-guide/tests/test_code_01_08.py -q
No student repository, production service or input CSV is modified.
"""
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


def reference(number):
    spec = importlib.util.spec_from_file_location(f"audit_l{number}", ROOT / f"instructor-guide/lesson-{number:02d}/reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L1, L5, L6, L7, L8 = (reference(n) for n in (1, 5, 6, 7, 8))


def ticket(tid="T1", **changes):
    return {"ticket_id": tid, "person_id": "P1", "date": "2026-04-13", "window_id": "A1",
            "center": "A", "business_code": "basic", "wait": 5., "completed": 1, "abandon": 0,
            "arrival_period": "上午", **changes}


def survey(tid="T1", **changes):
    return {"ticket_id": tid, "invited": "1", "score": "4", **changes}


def contact(tid="T1", cid="C1", **changes):
    return {"contact_id": cid, "ticket_id": tid, "contact_date": "2026-04-13", "staff_minutes": "2", **changes}


def staffing(day="2026-04-13", **changes):
    return {"date": day, "window_id": "A1", "staff_count": "1", "open_hours": "8", "absence_hours": "0", **changes}


def alert(rid="R1", **changes):
    return {"record_id": rid, "date": "2026-05-04", "device_id": rid, "device_class": "general",
            "score": 80., "label": 1, "miss_loss": 100., "inspection_cost": 3., **changes}


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_student(tmp_path, number, tables):
    """A standalone, single-lesson release with no helper files installed."""
    student = tmp_path / "student"
    lesson = student / f"lesson-{number:02d}"
    lesson.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / f"student-template/lesson-{number:02d}/analysis.py", lesson / "analysis.py")
    for name, rows, fields in tables:
        write_csv(student / "data" / name, rows, fields)
    result = subprocess.run([sys.executable, str(lesson / "analysis.py")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        return result, None
    output = json.loads((lesson / "artifacts/starting_overview.json").read_text(encoding="utf-8"))
    json.dumps(output, allow_nan=False)
    return result, output


def service_tables(rows, windows=None):
    raw = [{"ticket_id": r["ticket_id"], "window_id": r["window_id"], "wait_minutes": str(r["wait"]),
            "abandoned": "" if r["abandon"] is None else str(r["abandon"]),
            "completed_same_day": "" if r["completed"] is None else str(r["completed"]),
            "business_code": r["business_code"]} for r in rows]
    return [("service/tickets.csv", raw, ["ticket_id", "window_id", "wait_minutes", "abandoned", "completed_same_day", "business_code"]),
            ("service/windows.csv", windows if windows is not None else [{"window_id": "A1", "center": "A"}], ["window_id", "center"])]


@pytest.mark.parametrize("number", [1, 2, 4])
@pytest.mark.parametrize("rows", [[], [ticket(abandon=1)]], ids=["empty", "all-abandoned"])
def test_empty_served_group_outputs_null_not_zero(tmp_path, number, rows):
    result, output = run_student(tmp_path, number, service_tables(rows))
    assert result.returncode == 0, result.stderr
    group = output if number == 2 else output["centers" if number == 1 else "statistics"][0]
    assert group["n" if number == 2 else "served_n"] == 0
    assert group["served_wait_mean_minutes" if number == 1 else "mean"] is None


@pytest.mark.parametrize("number", [1, 2, 4])
@pytest.mark.parametrize("value", [math.nan, math.inf, -2])
def test_student_waits_reject_invalid_numbers(tmp_path, number, value):
    result, _ = run_student(tmp_path, number, service_tables([ticket(wait=value)]))
    assert result.returncode != 0 and "ValueError" in result.stderr


@pytest.mark.parametrize("number", [1, 4, 6])
def test_student_window_dictionary_rejects_duplicates(tmp_path, number):
    result, _ = run_student(tmp_path, number, service_tables([ticket()], [{"window_id": "A1", "center": "A"}] * 2))
    assert result.returncode != 0 and "重复" in result.stderr


@pytest.mark.parametrize("number", [1, 2, 4, 6])
def test_student_unknown_binary_status_is_not_silently_zero(tmp_path, number):
    result, _ = run_student(tmp_path, number, service_tables([ticket(abandon=None, completed=None)]))
    assert result.returncode != 0 and "状态" in result.stderr


def test_student_alert_empty_batch(tmp_path):
    result, output = run_student(tmp_path, 5, [
        ("alerts/development.csv", [], ["record_id", "date", "device_id", "risk_score"]),
        ("alerts/daily_capacity.csv", [], ["date", "max_reviews"])])
    assert result.returncode == 0, result.stderr
    assert output["device_days"] == 0 and output["score_min"] is None and output["score_max"] is None


@pytest.mark.parametrize("score,capacities", [("nan", [1]), ("50", [-1]), ("50", [1, 1]), ("50", [])])
def test_student_alert_invalid_scores_or_capacities(tmp_path, score, capacities):
    result, _ = run_student(tmp_path, 5, [
        ("alerts/development.csv", [{"record_id": "R1", "date": "2026-05-04", "device_id": "D1", "risk_score": score}], ["record_id", "date", "device_id", "risk_score"]),
        ("alerts/daily_capacity.csv", [{"date": "2026-05-04", "max_reviews": value} for value in capacities], ["date", "max_reviews"])])
    assert result.returncode != 0 and "ValueError" in result.stderr


def test_student_survey_whitespace_is_missing_and_unmatched_is_reported(tmp_path):
    result, output = run_student(tmp_path, 7, service_tables([ticket(), ticket("T2")]) + [
        ("service/satisfaction.csv", [survey(score="   ")], ["ticket_id", "invited", "score"])])
    assert result.returncode == 0, result.stderr
    assert output["responded"] == 0 and output["unmatched_tickets"] == 1


@pytest.mark.parametrize("surveys", [[survey(), survey()], [survey(score="6")], [survey(invited="0")]])
def test_student_survey_rejects_ambiguous_records(tmp_path, surveys):
    result, _ = run_student(tmp_path, 7, service_tables([ticket()]) + [
        ("service/satisfaction.csv", surveys, ["ticket_id", "invited", "score"])])
    assert result.returncode != 0 and "ValueError" in result.stderr


def test_alert_only_student_root(tmp_path):
    (tmp_path / "data/alerts").mkdir(parents=True)
    assert L1.student_root(["--student-root", str(tmp_path)], dataset="alerts") == tmp_path


def test_empty_replay_does_not_claim_zero_loss_per_day():
    output = L5.replay([], {}, lambda _: .1, "none")
    assert output["records"] == 0 and output["loss_per_day"] is None


@pytest.mark.parametrize("changes", [{"policy": "typo"}, {"capacity_multiplier": -1},
                                    {"capacity_multiplier": 1.1}, {"effectiveness": math.nan}, {"effectiveness": 1.1}])
def test_replay_rejects_invalid_policy_or_scenario(changes):
    args = {"policy": "score", **changes}
    with pytest.raises(ValueError):
        L5.replay([alert()], {"2026-05-04": 1}, lambda _: .1, **args)


@pytest.mark.parametrize("rows", [[alert(), alert(device_id="D2")], [alert(), alert("R2", device_id="R1")]])
def test_duplicate_record_or_device_day_cannot_bypass_review_capacity(rows):
    with pytest.raises(ValueError, match="duplicate"):
        L5.replay(rows, {"2026-05-04": 1}, lambda _: .1, "score")


@pytest.mark.parametrize("changes", [{"label": 2}, {"score": math.inf}, {"inspection_cost": -3}, {"miss_loss": math.nan}])
def test_replay_rejects_invalid_measurements(changes):
    with pytest.raises(ValueError):
        L5.replay([alert(**changes)], {"2026-05-04": 1}, lambda _: .1, "score")


def test_new_device_class_requires_an_explicit_estimation_assumption():
    p = L5.calibration([alert()])
    with pytest.raises(ValueError, match="No development"):
        p(alert(device_class="new"))


def test_replay_preserves_loss_formula_and_labels():
    rows = [alert("D1"), alert("D2", score=40, label=0), alert("D3", score=40), alert("D4", score=20, label=0)]
    output = L5.replay(rows, {"2026-05-04": 2}, lambda _: .1, "score")
    assert [output[key] for key in ("TP", "FP", "FN", "TN")] == [1, 1, 1, 1]
    assert output["total_loss"] == 121 and output["reviews"] == 2
    assert [r["label"] for r in rows] == [1, 0, 1, 0]


def test_missing_positive_weight_stratum_is_undefined_but_zero_weight_is_allowed():
    output = L6.build_result([ticket()])
    rows = {r["common_case_weight"]: r for r in output["standardized"]}
    assert output["centers"]["A"]["strata"]["case"]["rate"] is None
    assert rows[0]["rates"]["A"] == 1 and rows[.5]["rates"]["A"] is None
    assert rows[.5]["order_high_to_low"] == [] and output["simpson_A_B"] is None


def test_empty_comparison_and_exact_ties():
    assert L6.build_result([])["pooled_case_weight"] is None
    rows = [ticket(f"{c}-{s}", center=c, business_code=s) for c in "ABC" for s in ("basic", "case")]
    assert all(r["ties_high_to_low"] == [["A", "B", "C"]] for r in L6.build_result(rows)["standardized"])


def test_no_responses_keeps_unknown_range_instead_of_crashing():
    output = L7.build_result([ticket()], [survey(score=" ")])
    assert output["responded"] == 0 and output["respondent_satisfied_rate"] is None
    assert output["no_assumption_bounds"] == [0, 1] and output["stratum_adjusted_under_within_cell_MAR"] is None


def test_missing_invitation_and_survey_are_not_uninvited():
    output = L7.build_result([ticket(), ticket("T2"), ticket("T3")], [survey(invited="", score="4"), survey("T2")])
    assert output["unmatched_surveys"] == 1 and output["unknown_invitation"] == 1
    assert output["uninvited"] == 0 and output["invitation_rate"] is None
    assert output["response_among_invited"] == 1  # Not 2/1: the numerator has the same scope.


def test_empty_survey_target_has_no_rate_or_bounds():
    output = L7.build_result([], [])
    assert output["no_assumption_bounds"] == [None, None]
    assert output["invitation_rate"] is None and output["stratum_adjusted_under_within_cell_MAR"] is None


@pytest.mark.parametrize("surveys", [[survey(), survey()], [survey(score="nan")], [survey(invited="0")]])
def test_reference_survey_rejects_duplicates_invalid_scores_and_conflicts(surveys):
    with pytest.raises(ValueError):
        L7.build_result([ticket()], surveys)


def reconcile(tickets=None, contacts=None, surveys=None, plans=None):
    return L8.build_result(tickets if tickets is not None else [ticket()], contacts or [], surveys or [],
                           plans if plans is not None else [staffing()], [{"window_id": "A1", "center": "A"}], {})


def test_no_contacts_is_not_hidden_by_defaultdict_lookup():
    output = reconcile(surveys=[survey()])
    assert output["tickets_without_contacts"] == 1 and output["naive_contact_join_wait_mean"] is None


def test_missing_survey_does_not_drop_a_ticket_or_crash():
    output = reconcile(contacts=[contact()])
    assert output["tickets_without_survey"] == 1
    assert output["window_day_reports"][0]["tickets"] == 1
    assert output["window_day_reports"][0]["responses"] == 0


def test_cross_day_work_and_empty_staffed_day_are_preserved():
    output = reconcile(contacts=[contact(contact_date="2026-04-14", staff_minutes="60")],
                       plans=[staffing(), staffing("2026-04-14"), staffing("2026-04-15")])
    days = {r["date"]: r for r in output["window_day_reports"]}
    assert days["2026-04-13"]["tickets"] == 1 and days["2026-04-13"]["contacts"] == 0
    assert days["2026-04-14"]["tickets"] == 0 and days["2026-04-14"]["staff_minutes"] == 60
    assert days["2026-04-15"]["planned_person_hours"] == 8 and output["unique_planned_person_hours"] == 24
    assert output["cross_day_contacts"] == 1


def test_known_window_without_staffing_is_not_unknown_window_or_zero_hours():
    output = reconcile(contacts=[contact()], plans=[])
    assert output["unknown_window_tickets_quarantined_for_window_report"] == 0
    assert output["tickets_with_missing_staffing"] == 1
    assert output["window_day_reports"][0]["planned_person_hours"] is None


def test_unknown_window_and_orphan_contacts_keep_unassigned_totals():
    output = reconcile(tickets=[ticket(window_id="UNKNOWN")], contacts=[contact(), contact("ORPHAN", "C2", staff_minutes="3")])
    assert output["unknown_window_tickets_quarantined_for_window_report"] == 1
    assert output["contacts_without_ticket"] == 1 and output["unassigned_contact_rows"] == 2
    assert output["source_staff_minutes"] == output["unassigned_contact_staff_minutes"] == 5
    assert output["ticket_aggregated_staff_minutes"] + output["orphan_contact_staff_minutes"] == 5


@pytest.mark.parametrize("plans", [[staffing(), staffing()], [staffing(absence_hours="9")], [staffing(staff_count="1.5")], [staffing(open_hours="nan")]])
def test_invalid_staffing_cannot_enter_totals(plans):
    with pytest.raises(ValueError):
        reconcile(plans=plans)


@pytest.mark.parametrize("contacts", [[contact(), contact()], [contact(staff_minutes="nan")], [contact(contact_date="")]])
def test_invalid_contacts_cannot_enter_workload(contacts):
    with pytest.raises(ValueError):
        reconcile(contacts=contacts)


def file_hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*.csv")}


@pytest.mark.parametrize("number", range(1, 9))
def test_every_student_script_runs_from_two_directories_without_mutating_data(tmp_path, number):
    student = tmp_path / "student"
    for dataset in ("service", "alerts"):
        shutil.copytree(ROOT / f"student-template/data/{dataset}", student / f"data/{dataset}")
    lesson = student / f"lesson-{number:02d}"
    lesson.mkdir()
    shutil.copyfile(ROOT / f"student-template/lesson-{number:02d}/analysis.py", lesson / "analysis.py")
    before = file_hashes(student / "data")
    command = [sys.executable, str(lesson / "analysis.py")]
    first = subprocess.run(command, cwd=tmp_path, check=True, capture_output=True, timeout=30)
    result_path = lesson / "artifacts/starting_overview.json"
    result = result_path.read_bytes()
    second = subprocess.run(command, cwd=lesson, check=True, capture_output=True, timeout=30)
    assert first.stdout == second.stdout and result == result_path.read_bytes()
    json.dumps(json.loads(result), allow_nan=False)
    assert before == file_hashes(student / "data")


@pytest.mark.parametrize("number", range(1, 9))
def test_every_teacher_script_is_reproducible_and_read_only(tmp_path, number):
    student = tmp_path / "student"
    for dataset in ("service", "alerts"):
        shutil.copytree(ROOT / f"student-template/data/{dataset}", student / f"data/{dataset}")
    before = file_hashes(student / "data")
    command = [sys.executable, str(ROOT / f"instructor-guide/lesson-{number:02d}/reference.py"), "--student-root", str(student)]
    first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, timeout=30)
    second = subprocess.run(command, cwd=tmp_path, check=True, capture_output=True, timeout=30)
    assert first.stdout == second.stdout
    output = json.loads(first.stdout)
    json.dumps(output, allow_nan=False)
    assert before == file_hashes(student / "data")
    # Frozen numerical evidence from main@5c62512, not student project answers.
    if number == 5:
        assert output["selected_by_development_loss"] == "estimated_net_benefit"
        assert [r["total_loss"] for r in output["evaluation"]] == [1003000., 638490., 421800., 390650.]
        assert [r["reviews"] for r in output["evaluation"]] == [0, 260, 260, 260]
    elif number == 6:
        assert output["pooled_case_weight"] == pytest.approx(0.5061111111111111)
        assert output["simpson_A_B"] is True
    elif number == 7:
        assert [output[key] for key in ("target_tickets", "invited", "responded", "satisfied_respondents")] == [3600, 3199, 2099, 1856]
        assert output["no_assumption_bounds"] == pytest.approx([0.5155555555555555, 0.9325])
        assert output["stratum_adjusted_under_within_cell_MAR"] == pytest.approx(0.867349585182292)
    elif number == 8:
        assert output["input_unique_tickets"] == 4800 and output["contact_rows"] == 8921
        assert output["source_staff_minutes"] == pytest.approx(89466.8, abs=1e-6)
        assert output["unique_planned_person_hours"] == 2460
        assert output["unweighted_served_wait_mean"] == pytest.approx(13.189328151986183)
        assert output["unknown_window_tickets_quarantined_for_window_report"] == 7
        assert len(output["window_day_reports"]) == output["reported_window_days"] == 240
