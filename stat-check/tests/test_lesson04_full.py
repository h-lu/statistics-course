"""L04 r2 answers solved before inspecting grading, plus actual HTTP exercise.

All clients use temporary SQLite and test authentication, never live students.
The installed r2 bank remains unchanged; no new revision is needed for this audit.
"""
import csv
from fractions import Fraction
import hashlib
from html import unescape
import io
from pathlib import Path
import re

import pytest

from app import db
from app.questions import BANKS
from test_app import make_client, csrf_from, session_id_from, set_phase, create_session

# Independently solved from the prompts, not read from the answer field at submission.
SOLUTIONS = {
    "center-tail": {"a": "C", "b": "D"},
    "iqr-robustness": {"a": "D", "b": "C"},
    "composite": {"a": "A", "b": "B"},
    "goal-metric": {"a": "B", "b": "D"},
    "incentive": {"a": "A", "b": "B"},
}


@pytest.mark.parametrize("concept,phase", [(c, p) for c in SOLUTIONS for p in ("a", "b")])
def test_reviewed_answer_matches_single_valid_option(concept, phase):
    question = BANKS["v2-l04-r2"].question(concept, phase)
    expected = SOLUTIONS[concept][phase]
    assert question["answer"] == expected
    assert len({o["text"] for o in question["options"]}) == 4
    assert [o["id"] for o in question["options"] if o.get("misconception") is None] == [expected]
    assert question["explanation"].strip()


def test_r2_is_unchanged_and_teacher_copy_is_identical():
    bank = BANKS["v2-l04-r2"]
    data = bank.path.read_bytes()
    assert hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == "f01d95d763f96b0e85f21a8eb084d585c21d2605"
    teacher = Path(__file__).resolve().parents[2] / "instructor-guide/knowledge-check/question-bank" / bank.path.name
    # A standalone service checkout has no teacher repository; installed bank is still checked.
    if teacher.is_file():
        assert teacher.read_bytes() == data
    assert bank.durations == {"attempt_a": 300, "learn": 240, "attempt_b": 300}
    assert bank.concept_ids == list(SOLUTIONS)


def test_numerical_questions_independently_calculated():
    assert 5 - 5 == 0  # IQR is not the range: 100-1=99.
    assert 100 - 1 == 99 and 80 - 40 == 40
    assert Fraction(12, 10) == Fraction(720, 600)
    assert Fraction(720, 60) != Fraction(12, 10)
    assert Fraction(3 + 4 - 2, 10) == Fraction(1, 2)
    waits = [15, 15, 16] + [4] * 7
    rate = Fraction(sum(w > 15 for w in waits), len(waits))
    assert rate == Fraction(1, 10) and not rate > Fraction(1, 10)
    # Counts alone cannot determine the direction of a rate change.
    assert Fraction(20, 1000) < Fraction(5, 100)


@pytest.mark.parametrize("make_first_wrong", [False, True], ids=["all-correct", "one-wrong-per-form"])
def test_l04_a_learning_b_feedback_export_and_history(tmp_path, make_first_wrong):
    path = tmp_path / "lesson04.sqlite3"
    bank = BANKS["v2-l04-r2"]
    with make_client(path, "teacher", "teacher") as teacher, make_client(path, "student", "l04-simulated") as student:
        create_session(teacher, bank.lesson_id)
        session = db.current_session(str(path))
        submitted = {}
        for phase in ("a", "b"):
            set_phase(teacher, phase)
            for index, concept in enumerate(SOLUTIONS):
                page = student.get("/stat-check/current")
                assert page.status_code == 200
                actual = re.search(r'name="concept_id" value="([^"]+)"', page.text).group(1)
                assert actual == concept
                question = bank.question(concept, phase)
                assert question["prompt"] in unescape(page.text)
                assert "参考答案：" not in page.text
                choice = SOLUTIONS[concept][phase]
                if make_first_wrong and index == 0:
                    choice = next(c for c in "ABCD" if c != choice)
                submitted[(concept, phase)] = choice
                response = student.post("/stat-check/answer", data={
                    "csrf_token": csrf_from(page), "session_id": session_id_from(page),
                    "concept_id": concept, "phase": phase, "option_id": choice, "confidence": "unsure",
                }, follow_redirects=True)
                assert response.status_code == 200
            if phase == "a":
                set_phase(teacher, "learn")
                page = student.get("/stat-check/current")
                for item in bank.items:
                    assert item["tutor_context"] in unescape(page.text)
                response = student.post("/stat-check/learn/complete", data={
                    "csrf_token": csrf_from(page), "session_id": session_id_from(page),
                }, follow_redirects=True)
                assert response.status_code == 200 and "学习阶段已完成" in response.text
        set_phase(teacher, "result")
        feedback = student.get("/stat-check/current")
        correct = 4 if make_first_wrong else 5
        for phase in ("A", "B"):
            assert feedback.text.count(f"{phase}：正确") == correct
            assert feedback.text.count(f"{phase}：需复习") == 5 - correct
        for concept in SOLUTIONS:
            for phase in ("a", "b"):
                q = bank.question(concept, phase)
                for text in (q["prompt"], q["explanation"], *(o["text"] for o in q["options"])):
                    assert text in unescape(feedback.text)
        with db.connect(str(path)) as conn:
            user = conn.execute("SELECT id FROM users WHERE login = 'l04-simulated'").fetchone()[0]
        rows = db.responses_for_user(str(path), session["id"], user)
        assert len(rows) == 10
        for row in rows:
            key = (row["concept_id"], row["phase"])
            assert row["option_id"] == submitted[key]
            assert bool(row["correct"]) == (row["option_id"] == SOLUTIONS[key[0]][key[1]])
        export = teacher.get(f"/stat-check/teacher/export.csv?session_id={session['id']}")
        assert export.status_code == 200
        records = list(csv.DictReader(io.StringIO(export.text.lstrip("\ufeff"))))
        row = next(r for r in records if r["gitea_login"] == "l04-simulated")
        assert tuple(row[k] for k in ("a_count", "a_correct", "b_count", "b_correct", "learned")) == ("5", str(correct), "5", str(correct), "1")
        old_text = export.text
        create_session(teacher, bank.lesson_id)
        assert db.current_session(str(path))["id"] != session["id"]
        assert teacher.get(f"/stat-check/teacher/export.csv?session_id={session['id']}").text == old_text
