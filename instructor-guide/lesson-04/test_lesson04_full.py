"""L04 cold-read arithmetic, code contracts, worked project and submission checks.

Use temporary copies, never student accounts, production services or source CSV edits.
Run: python -m pytest instructor-guide/lesson-04/test_lesson04_full.py -q
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
LESSON = ROOT / "student-template/lesson-04"


def load(path):
    spec = importlib.util.spec_from_file_location("review_" + path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


REF = load(Path(__file__).with_name("reference.py"))
WORK = load(Path(__file__).with_name("walkthrough.py"))
START = load(LESSON / "analysis.py")


def learning():
    text = (LESSON / "LEARN.md").read_text(encoding="utf-8")
    code = re.search(r"```python\n(# learning-example.*?)```", text, re.S).group(1)
    scope = {}
    with contextlib.redirect_stdout(io.StringIO()) as output:
        exec(compile(code, "lesson04-learning", "exec"), scope)
    json.loads(output.getvalue())
    return scope


def ticket(tid="T1", **changes):
    return {"ticket_id": tid, "date": "2026-03-02", "window_id": "A1", "business_code": "basic",
            "wait_minutes": "5", "abandoned": "0", **changes}


WINDOWS = [{"window_id": "A1", "center": "A"}, {"window_id": "B1", "center": "B"}]
BUSINESS = [{"business_code": "basic", "reference_wait_minutes": "15"},
            {"business_code": "case", "reference_wait_minutes": "30"}]


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*.csv"))}


def test_original_worked_results_and_deletion_warning():
    result = learning()["result"]
    assert result["x"] == {"mean": 12, "median": 5, "iqr": 1, "over15": .2}
    assert result["y"] == {"mean": 10, "median": 10, "iqr": 2, "over15": 0}
    assert result["x_mean_after_exclusion"] == 5 and result["x_over15_after_exclusion"] == 0


@pytest.mark.parametrize("values,iqr", [([0, 10], 5), ([7], 0), ([1, 2, 4, 8, 16, 32], 11.5)])
def test_learning_iqr_handles_other_sample_sizes(values, iqr):
    # For six values: Q1=2+0.25*(4-2)=2.5; Q3=8+0.75*(16-8)=14.
    assert learning()["profile"](values)["iqr"] == iqr


def test_learning_empty_group_and_nonfinite_input():
    scope = learning()
    assert all(value is None for value in scope["profile"]([]).values())
    with pytest.raises(ValueError):
        scope["profile"]([math.inf])


def test_tail_change_and_strict_threshold_practice():
    scope = learning()
    after = scope["profile"]([4, 5, 5, 6, 80])
    assert after["median"] == 5 and after["iqr"] == 1 and after["mean"] == 20
    assert sum([4, 5, 5, 6, 80]) - sum(scope["x"]) == 40
    values = [15, 15, 16] + [4] * 7
    assert sum(v > 15 for v in values) / len(values) == .1
    assert not (sum(v > 15 for v in values) / len(values) > .1)


def test_composite_example_units_and_proportion_scale():
    assert 12 / 10 + .1 == 720 / 600 + .1 == 1.3
    assert 720 / 10 + .1 != 1.3
    assert 12 / 10 + 10 != 1.3


@pytest.mark.parametrize("changes", [{"center": "D"}, {"abandon": 2}, {"abandon": None},
                                    {"wait": math.nan}, {"wait": math.inf}, {"wait": -1}, {"wait": None}])
def test_reference_reuse_rejects_invalid_input_before_counting(changes):
    row = {"center": "A", "business_code": "basic", "wait": 5., "abandon": 0, **changes}
    with pytest.raises(ValueError):
        REF.build_result([row], {"basic": 15})


def test_student_import_needs_no_data_and_writes_no_file(tmp_path):
    script = tmp_path / "lesson-04/analysis.py"
    script.parent.mkdir()
    shutil.copyfile(LESSON / "analysis.py", script)
    load(script)
    assert sorted(p.name for p in script.parent.iterdir() if p.name != "__pycache__") == ["analysis.py"]


def test_student_empty_and_all_abandoned_groups_are_undefined():
    for rows in ([], [ticket(abandoned="1")]):
        result = START.build_overview(rows, WINDOWS)
        for group in result["statistics"]:
            assert group["served_n"] == 0
            assert all(group[key] is None for key in ("mean", "median", "maximum"))


def test_student_build_does_not_mutate_inputs():
    rows, windows = [ticket()], copy.deepcopy(WINDOWS)
    before = copy.deepcopy((rows, windows))
    START.build_overview(rows, windows)
    assert (rows, windows) == before


def test_student_missing_header_has_a_clear_error(tmp_path, monkeypatch):
    data = tmp_path / "data/service"
    data.mkdir(parents=True)
    (data / "tickets.csv").write_text("ticket_id\nT1\n", encoding="utf-8")
    monkeypatch.setattr(START, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="缺少必要列"):
        START.read("service/tickets.csv", ("ticket_id", "abandoned"))


def test_walkthrough_equality_overlap_and_empty_center():
    rows = [ticket("T1", wait_minutes="15"), ticket("T2", wait_minutes="30", business_code="case"),
            ticket("T3", wait_minutes="40", abandoned="1")]
    summary, details = WORK.analyze(rows, WINDOWS, BUSINESS)
    a, b = summary["profiles"]
    assert a["over15_count"] == 1 and a["over_business_count"] == 0
    assert a["registered_event_count"] == 1  # Both abandonment and over-line, counted once.
    assert b["registered"] == 0 and b["over15_rate"] is None
    assert all(r["investigate_long_wait"] is None for r in summary["decisions"] if r["center"] == "B")
    assert len(details) == 3 and summary["registered_total"] == 3


@pytest.mark.parametrize("rows", [[ticket(), ticket()], [ticket(abandoned="2")],
                                 [ticket(window_id="UNKNOWN")], [ticket(wait_minutes="nan")]])
def test_walkthrough_does_not_silently_drop_bad_records(rows):
    with pytest.raises(ValueError):
        WORK.analyze(rows, WINDOWS, BUSINESS)


def test_walkthrough_disallows_writing_into_source_data():
    student = ROOT / "student-template"
    with pytest.raises(ValueError, match="separate output"):
        WORK.run(student, student / "data/service")


def test_actual_project_matches_reference_and_is_reproducible(tmp_path):
    student = ROOT / "student-template"
    before = hashes(student / "data/service")
    result = WORK.run(student, tmp_path / "work")
    reference = REF.build_result(REF.u.baseline(student), {"basic": 15, "case": 30})
    mappings = {"served": "n", "over15_count": "served_over15_count", "over15_rate": "served_over15",
                "over_business_count": "served_over_business_line_count", "over_business_rate": "served_over_business_line",
                "registered_event_count": "registered_bad_experience_count", "registered_event_rate": "registered_bad_experience"}
    for actual, expected in zip(result["profiles"], reference["profiles"]):
        for key in ("center", "registered", "mean", "median", "p90", "case_share", "abandon_rate"):
            assert actual[key] == expected[key]
        for key, target in mappings.items():
            assert actual[key] == expected[target]
    assert result["registered_total"] == 3600
    for rule, trigger, expected in [("uniform_15_minutes", .1, ["A", "B", "C"]),
                                    ("business_15_30_minutes", .1, ["B"]),
                                    ("business_15_30_minutes", .12, [])]:
        selected = [r["center"] for r in result["decisions"] if r["rule"] == rule and r["trigger"] == trigger and r["investigate_long_wait"]]
        assert selected == expected
    first = {p.name: p.read_bytes() for p in (tmp_path / "work").iterdir()}
    WORK.run(student, tmp_path / "work")
    assert first == {p.name: p.read_bytes() for p in (tmp_path / "work").iterdir()}
    assert hashes(student / "data/service") == before


def test_student_saved_overview_matches_execution(tmp_path):
    student = tmp_path / "student"
    shutil.copytree(ROOT / "student-template/data/service", student / "data/service")
    shutil.copytree(LESSON, student / "lesson-04")
    subprocess.run([sys.executable, str(student / "lesson-04/analysis.py")], cwd=tmp_path,
                   check=True, capture_output=True, timeout=30)
    assert (student / "lesson-04/artifacts/starting_overview.json").read_bytes() == (LESSON / "artifacts/starting_overview.json").read_bytes()


def test_simulated_submission_rebuilds_deleted_artifacts_without_touching_template(tmp_path):
    course = load(ROOT / "student-template/scripts/course.py")
    before_manifest = (LESSON / "submission.json").read_bytes()
    student = tmp_path / "student"
    lesson = student / "lesson-04"
    lesson.mkdir(parents=True)
    shutil.copytree(ROOT / "student-template/data/service", student / "data/service")
    shutil.copyfile(Path(__file__).with_name("walkthrough.py"), lesson / "analysis.py")
    WORK.run(student, lesson / "artifacts")
    shutil.copyfile(lesson / "artifacts/practice_report.md", lesson / "report.md")
    evidence = [f"lesson-04/artifacts/{name}" for name in ("profiles.csv", "ticket_checks.csv", "summary.json", "practice_report.md")]
    manifest = {"lesson": "lesson-04", "status": "complete", "report": "lesson-04/report.md",
                "artifacts": evidence,
                "run": ["python", "lesson-04/analysis.py", "--student-root", ".", "--output", "lesson-04/artifacts"]}
    (lesson / "submission.json").write_text(json.dumps(manifest), encoding="utf-8")
    course.check(student, "lesson-04")
    course.ci(student, "refs/tags/v2-l04-final")
    assert (LESSON / "submission.json").read_bytes() == before_manifest
    assert json.loads(before_manifest)["status"] == "not_started"
