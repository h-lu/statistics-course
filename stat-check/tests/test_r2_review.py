"""PR #5 review: real HTTP flows, history isolation and explicit item contracts.

These tests use installed banks and temporary SQLite databases, not live accounts.
Text contracts guard reviewed examples; they do not prove equal A/B difficulty.
"""
import csv
from fractions import Fraction
from html import unescape
import io
import re
from pathlib import Path

import pytest

from app import db
from app.questions import BANKS, CURRENT_BANKS
from test_app import make_client, csrf_from, session_id_from, set_phase, create_session


def selected_text(lesson, concept, phase):
    question = BANKS[f"v2-l{lesson:02d}-r2"].question(concept, phase)
    return next(option["text"] for option in question["options"]
                if option["id"] == question["answer"])


def test_composite_pair_checks_equivalent_scales_in_both_forms():
    # Ten minutes is 600 seconds; the original normalized term must not change.
    assert Fraction(12, 10) == Fraction(12 * 60, 600)
    assert "600" in selected_text(4, "composite", "b")


def test_loss_pair_compares_total_loss_not_a_different_validation_concept():
    assert 40 + 200 == 240
    assert 40 + 2 * 60 == 160
    text = selected_text(5, "loss-action", "b")
    assert "160" in text and "240" in text


def test_table_operation_pair_distinguishes_appending_from_enrichment():
    text = selected_text(8, "cardinality", "b")
    assert "汇总" in text and "连接" in text


def test_work_hours_pair_keeps_one_total_per_window_day():
    assert 7 + 5 == 12
    text = selected_text(8, "reconciliation", "b")
    assert "12人时" in text and "日期" in text


def test_response_rate_numerical_distractors_are_distinct():
    question = BANKS["v2-l07-r2"].question("response-denominator", "a")
    rates = [re.search(r"＝(\d+)%", option["text"]).group(1)
             for option in question["options"]]
    assert len(set(rates)) == 4


def test_runtime_filenames_and_teacher_current_copies_agree():
    teacher = Path(__file__).resolve().parents[2] / "instructor-guide/knowledge-check/question-bank"
    if not teacher.is_dir():
        pytest.skip("Standalone Stat Check checkout has no teacher mirror")
    assert len(CURRENT_BANKS) == 32
    for bank in CURRENT_BANKS:
        match = re.fullmatch(r"v2-l(\d{2})-r(\d+)", bank.lesson_id)
        assert match is not None
        lesson, revision = match.groups()
        assert bank.path.name == f"lesson-v2r{revision}-{lesson}.yml"
        assert bank.path.read_bytes() == (teacher / bank.path.name).read_bytes()


@pytest.mark.parametrize("number", range(1, 9), ids=lambda n: f"L{n:02d}")
def test_each_r2_bank_http_a_learning_b_feedback_and_export(tmp_path, number):
    path = tmp_path / f"lesson-{number}.sqlite3"
    bank = BANKS[f"v2-l{number:02d}-r2"]
    with make_client(path, "teacher", "teacher") as teacher, make_client(path, "student", "review-student") as student:
        create_session(teacher, bank.lesson_id)
        session = db.current_session(str(path))
        assert session["lesson_id"] == bank.lesson_id
        submitted = {}
        for phase in ("a", "b"):
            set_phase(teacher, phase)
            for index, item in enumerate(bank.items):
                page = student.get("/stat-check/current")
                assert page.status_code == 200
                concept = re.search(r'name="concept_id" value="([^"]+)"', page.text).group(1)
                assert concept == item["concept_id"]
                question = bank.question(concept, phase)
                assert question["prompt"] in unescape(page.text)
                assert "参考答案：" not in page.text
                # Exercise both branches of actual HTTP grading, not pre-labelled rows.
                choice = question["answer"] if index else next(c for c in "ABCD" if c != question["answer"])
                submitted[(concept, phase)] = choice
                answer = student.post("/stat-check/answer", data={
                    "csrf_token": csrf_from(page), "session_id": session_id_from(page),
                    "concept_id": concept, "phase": phase,
                    "option_id": choice, "confidence": "unsure",
                }, follow_redirects=True)
                assert answer.status_code == 200
            if phase == "a":
                set_phase(teacher, "learn")
                page = student.get("/stat-check/current")
                learned = student.post("/stat-check/learn/complete", data={
                    "csrf_token": csrf_from(page), "session_id": session_id_from(page),
                }, follow_redirects=True)
                assert learned.status_code == 200
                assert "学习阶段已完成" in learned.text
        set_phase(teacher, "result")
        feedback = student.get("/stat-check/current")
        assert feedback.status_code == 200
        assert feedback.text.count("A：正确") == 4
        assert feedback.text.count("B：正确") == 4
        assert feedback.text.count("A：需复习") == 1
        assert feedback.text.count("B：需复习") == 1
        for item in bank.items:
            for phase in ("a", "b"):
                question = item["pair"][phase]
                assert question["prompt"] in unescape(feedback.text)
                assert question["explanation"] in unescape(feedback.text)
                for option in question["options"]:
                    assert option["text"] in unescape(feedback.text)
        with db.connect(str(path)) as connection:
            user_id = connection.execute("SELECT id FROM users WHERE login = 'review-student'").fetchone()[0]
        rows = db.responses_for_user(str(path), session["id"], user_id)
        assert len(rows) == 10
        for row in rows:
            key = (row["concept_id"], row["phase"])
            assert row["option_id"] == submitted[key]
            assert bool(row["correct"]) == (row["option_id"] == bank.question(*key)["answer"])
        export = teacher.get(f"/stat-check/teacher/export.csv?session_id={session['id']}")
        assert export.status_code == 200
        csv_rows = list(csv.DictReader(io.StringIO(export.text.lstrip("\ufeff"))))
        csv_row = next(r for r in csv_rows if r["gitea_login"] == "review-student")
        assert tuple(csv_row[k] for k in ("a_count", "a_correct", "b_count", "b_correct", "learned")) == ("5", "4", "5", "4", "1")
        row = next(r for r in db.export_rows(str(path), session["id"]) if r["login"] == "review-student")
        assert (row["a_count"], row["a_correct"], row["b_count"], row["b_correct"], row["learned"]) == (5, 4, 5, 4, 1)


def test_old_r1_answer_key_survives_http_restart_and_r2_session(tmp_path):
    path = tmp_path / "real-r1-history.sqlite3"
    old = BANKS["v2-l01-r1"]
    new = BANKS["v2-l01-r2"]
    assert old.question("unit", "a")["answer"] != new.question("unit", "a")["answer"]
    db.initialize(str(path), old.lesson_id, old.title)
    with make_client(path, "teacher", "teacher") as teacher, make_client(path, "student", "history-student") as student:
        old_session = db.current_session(str(path))
        assert old_session["lesson_id"] == old.lesson_id
        set_phase(teacher, "a")
        page = student.get("/stat-check/current")
        assert old.question("unit", "a")["prompt"] in unescape(page.text)
        payload = {"csrf_token": csrf_from(page), "session_id": session_id_from(page),
                   "concept_id": "unit", "phase": "a",
                   "option_id": new.question("unit", "a")["answer"], "confidence": "sure"}
        assert student.post("/stat-check/answer", data=payload).status_code == 200
        old_rows = [dict(r) for r in db.export_rows(str(path), old_session["id"])]
        student_row = next(r for r in old_rows if r["login"] == "history-student")
        assert (student_row["a_count"], student_row["a_correct"]) == (1, 0)
        set_phase(teacher, "result")
        feedback = student.get("/stat-check/current")
        for phase in ("a", "b"):
            assert old.question("unit", phase)["explanation"] in unescape(feedback.text)
        assert new.question("unit", "a")["explanation"] not in unescape(feedback.text)
        # Starting a new app must not silently replace the current session's bank.
        with make_client(path, "teacher", "teacher") as restarted:
            assert db.current_session(str(path))["lesson_id"] == old.lesson_id
            create_session(restarted, new.lesson_id)
            set_phase(restarted, "a")
        stale = student.post("/stat-check/answer", data=payload, follow_redirects=False)
        assert stale.status_code == 409
        page = student.get("/stat-check/current")
        assert new.question("unit", "a")["prompt"] in unescape(page.text)
        payload.update(csrf_token=csrf_from(page), session_id=session_id_from(page))
        assert student.post("/stat-check/answer", data=payload).status_code == 200
        current = db.current_session(str(path))
        new_row = next(r for r in db.export_rows(str(path), current["id"]) if r["login"] == "history-student")
        assert (new_row["a_count"], new_row["a_correct"]) == (1, 1)
        assert [dict(r) for r in db.export_rows(str(path), old_session["id"])] == old_rows
        old_csv = teacher.get(f"/stat-check/teacher/export.csv?session_id={old_session['id']}")
        assert old_csv.status_code == 200
        rows = list(csv.DictReader(io.StringIO(old_csv.text.lstrip("\ufeff"))))
        row = next(r for r in rows if r["gitea_login"] == "history-student")
        assert (row["a_count"], row["a_correct"]) == ("1", "0")


@pytest.mark.parametrize("lesson_id", ["v2-l01-r1", "v2-l08-r2"])
def test_feedback_preserves_unanswered_status_and_shows_both_explanations(tmp_path, lesson_id):
    path = tmp_path / "unanswered.sqlite3"
    bank = BANKS[lesson_id]
    with make_client(path, "teacher", "teacher") as teacher, make_client(path, "student", "unanswered-student") as student:
        create_session(teacher, bank.lesson_id)
        set_phase(teacher, "result")
        page = student.get("/stat-check/current")
        assert page.status_code == 200
        assert page.text.count("A：未完成") == 5
        assert page.text.count("B：未完成") == 5
        assert "A：需复习" not in page.text and "B：需复习" not in page.text
        for item in bank.items:
            for phase in ("a", "b"):
                assert item["pair"][phase]["explanation"] in unescape(page.text)
        with db.connect(str(path)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0
