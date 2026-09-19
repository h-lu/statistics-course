"""PR #6 follow-up regressions; fictional inputs and temporary files only."""
import csv
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_reference(number):
    spec = importlib.util.spec_from_file_location(
        f"pr6_reference_{number}", ROOT / f"instructor-guide/lesson-{number:02d}/reference.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L5, L7 = load_reference(5), load_reference(7)
BAD_DATES = ("20260504", "2026-5-04", "2026-02-30", "not-a-date")


def alert(rid="R1", day="2026-05-04"):
    return {"record_id": rid, "date": day, "device_id": "D1", "device_class": "general",
            "score": 80., "label": 1, "miss_loss": 100., "inspection_cost": 3.}


@pytest.mark.parametrize("day", BAD_DATES)
def test_replay_rejects_noncanonical_or_impossible_dates(day):
    with pytest.raises(ValueError, match="date|Date|YYYY"):
        L5.replay([alert(day=day)], {day: 1}, lambda _: .5, "score")


def test_same_calendar_day_cannot_receive_two_separate_quotas():
    rows = [alert(), alert("R2", "20260504")]
    with pytest.raises(ValueError, match="date|Date|YYYY"):
        L5.replay(rows, {"2026-05-04": 1, "20260504": 1}, lambda _: .5, "score")


def test_valid_leap_date_and_zero_capacity_remain_supported():
    output = L5.replay([alert(day="2028-02-29")], {"2028-02-29": 0}, lambda _: .5, "score")
    assert output["days"] == 1 and output["reviews"] == 0
    assert output["FN"] == 1 and output["total_loss"] == 100


def test_date_alias_cannot_make_an_earlier_evaluation_look_later(monkeypatch):
    def source(day, rid):
        return {"date": day, "record_id": rid, "device_id": "D1",
                "risk_score": "80", "failure_within_24h": "1"}
    tables = {
        "alerts/devices.csv": [{"device_id": "D1", "device_class": "general",
                                "miss_loss": "100", "inspection_cost": "3"}],
        "alerts/daily_capacity.csv": [{"date": "2026-12-01", "max_reviews": "1"},
                                      {"date": "20260601", "max_reviews": "1"}],
        "alerts/development.csv": [source("2026-12-01", "R1")],
        "alerts/evaluation.csv": [source("20260601", "R2")],
    }
    monkeypatch.setattr(L5.u, "student_root", lambda **kwargs: Path("unused"))
    monkeypatch.setattr(L5.u, "read", lambda root, name: tables[name])
    with pytest.raises(ValueError, match="date|Date|YYYY"):
        L5.main()


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("day", BAD_DATES)
def test_single_lesson_student_release_rejects_bad_dates(tmp_path, day):
    root = tmp_path / "student"
    lesson = root / "lesson-05"
    lesson.mkdir(parents=True)
    shutil.copyfile(ROOT / "student-template/lesson-05/analysis.py", lesson / "analysis.py")
    write_csv(root / "data/alerts/development.csv", [{"record_id": "R1", "date": day,
              "device_id": "D1", "risk_score": "80"}])
    write_csv(root / "data/alerts/daily_capacity.csv", [{"date": day, "max_reviews": "1"}])
    result = subprocess.run([sys.executable, str(lesson / "analysis.py")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and "ValueError" in result.stderr
    assert not (lesson / "artifacts/starting_overview.json").exists()


@pytest.mark.parametrize("invited", [0, "0"])
def test_numeric_zero_invitation_is_not_coerced_to_unknown(invited):
    source = [{"ticket_id": "T1", "invited": invited, "score": None}]
    records = L7.attach_surveys([{"ticket_id": "T1"}], source)
    assert records[0]["invited"] == 0 and records[0]["score"] is None
    assert source[0]["invited"] == invited  # Parsing must not edit source data.


@pytest.mark.parametrize("score", [0, "0"])
def test_zero_is_an_invalid_score_not_a_missing_score(score):
    with pytest.raises(ValueError, match="score"):
        L7.attach_surveys([{"ticket_id": "T1"}], [{"ticket_id": "T1", "invited": 1, "score": score}])


def test_missing_invitation_and_valid_numeric_rating_remain_separate():
    record = L7.attach_surveys([{"ticket_id": "T1"}],
        [{"ticket_id": "T1", "invited": None, "score": 4}])[0]
    assert record["invited"] is None and record["score"] == 4


def test_lesson08_reference_describes_current_code_not_removed_behavior():
    text = (ROOT / "instructor-guide/lesson-08/REFERENCE.md").read_text(encoding="utf-8")
    assert "参考按工单日期归集接触不会造成跨日错配" not in text
    assert "实际统计找不到对应排班键的工单" not in text
    assert "只从有工单的键构建" not in text
    assert "程序使用断言检查" not in text
    assert "window_day_reports" in text and "tickets_with_missing_staffing" in text
