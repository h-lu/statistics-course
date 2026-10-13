"""Lesson10 source fidelity and HTTP flow using temporary synthetic databases."""
from fractions import Fraction
import hashlib
from html import unescape
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

from app import db
from app.questions import (
    ACTIVE_LESSONS, BANKS, CURRENT_BANKS, CURRENT_BANK_OVERRIDES,
    V2_LESSON_ID, bank_for_lesson, select_current_banks,
)
from test_app import make_client, csrf_from, session_id_from, set_phase, create_session


LESSON_ID = "v2-l10-r3-20261013"
SOURCE_SHA256 = "4897f57a3c6df300529977e94697997f44f12b57e0ea4fac4d424eea7130a598"
BANK = BANKS[LESSON_ID]
SOLUTIONS = {"a": ("A", "B", "B", "D", "C"), "b": ("C", "D", "C", "A", "B")}
PREVIOUS_CURRENT = tuple(
    f"v2-l{n:02d}-r{5 if n == 5 else 4 if n <= 8 else 2}" for n in range(1, 10)
)


def test_source_id_bytes_mirrors_and_only_lesson10_default_added():
    root = Path(__file__).resolve().parents[2]
    draft = root / "instructor-guide/knowledge-check/drafts/lesson10-20261013" / BANK.path.name
    formal = root / "instructor-guide/knowledge-check/question-bank" / BANK.path.name
    if draft.is_file():
        assert draft.read_bytes() == formal.read_bytes() == BANK.path.read_bytes()
    assert hashlib.sha256(BANK.path.read_bytes()).hexdigest() == SOURCE_SHA256
    assert [b.lesson_id for b in CURRENT_BANKS] == [*PREVIOUS_CURRENT, LESSON_ID]
    assert ACTIVE_LESSONS == tuple(range(1, 11))
    assert CURRENT_BANK_OVERRIDES == {10: LESSON_ID}
    assert BANK.durations == {"attempt_a": 300, "learn": 240, "attempt_b": 300}
    assert BANK.concept_ids == [f"l10-r3-20261013-c{i}" for i in range(1, 6)]
    assert len(BANK.items) == 5
    assert bank_for_lesson("v2-l10-r1").lesson_id == "v2-l10-r1"
    assert bank_for_lesson("v2-l10").lesson_id == "v2-l10"


@pytest.mark.parametrize("phase,index", [(p, i) for p in ("a", "b") for i in range(5)])
def test_ten_independently_reviewed_answers_formats_and_feedback(phase, index):
    question = BANK.items[index]["pair"][phase]
    assert question["answer"] == SOLUTIONS[phase][index]
    assert [o["id"] for o in question["options"]] == list("ABCD")
    assert len({o["text"] for o in question["options"]}) == 4
    assert [o["id"] for o in question["options"] if o["misconception"] is None] == [question["answer"]]
    assert question["prompt"] and question["explanation"]
    assert not {"points", "score", "weight"}.intersection(question)


def test_calculations_and_quantile_convention_independent_of_answer_keys():
    assert 1 * Fraction(3, 4) + 3 * Fraction(1, 4) == Fraction(3, 2)
    assert 23 // 3 == 7 and 7 * 3 <= 23 < 8 * 3
    assert 4 * 2 + (6 - 4) * 7 == 22
    assert Fraction(1, 4) == Fraction(25, 100)
    assert Fraction(sum((0, 0, 0, 4)), 4) == 1
    assert Fraction(80, 100) < Fraction(95, 100) <= Fraction(80 + 15, 100)


def test_dated_release_preserves_capture_groups_and_override_respects_active_scope():
    match = V2_LESSON_ID.fullmatch(LESSON_ID)
    assert match and match.groups() == ("10", "3")
    assert V2_LESSON_ID.fullmatch("v2-l10-r3-2026101") is None
    stubs = tuple(SimpleNamespace(lesson_id=i) for i in ("v2-l09-r2", "v2-l10-r99", LESSON_ID, "v2-l11-r1"))
    assert [b.lesson_id for b in select_current_banks(stubs)] == ["v2-l09-r2", LESSON_ID]
    assert [b.lesson_id for b in select_current_banks(stubs, active_lessons=(9,))] == ["v2-l09-r2"]
    assert [b.lesson_id for b in select_current_banks(stubs[:-2])] == ["v2-l09-r2", "v2-l10-r99"]


def assert_public_question(page, question):
    assert page.status_code == 200
    body = unescape(page.text)
    assert question["prompt"] in body
    assert all(option["text"] in body for option in question["options"])
    assert not any(item["pair"][phase]["explanation"] in body
                   for item in BANK.items for phase in ("a", "b"))
    assert all(item["tutor_context"] not in body for item in BANK.items)
    assert "参考答案：" not in body and "正确选项：" not in body
    assert not re.search(r'name="(?:answer|correct)"|data-(?:answer|correct)', body)
    assert "AI 全程可以使用" in body


@pytest.mark.parametrize("one_error", [False, True], ids=["all-correct", "one-wrong-per-phase"])
def test_lesson10_teacher_selector_complete_http_flow_scoring_and_answer_visibility(tmp_path, one_error):
    path = tmp_path / "lesson10-synthetic.sqlite3"
    with make_client(path, "teacher", "teacher") as teacher, make_client(path, "student", "lesson10-fixture") as student:
        page = teacher.get("/stat-check/teacher")
        options = re.findall(r'<option value="([^"]+)"', page.text)
        assert options == [*PREVIOUS_CURRENT, LESSON_ID]
        create_session(teacher, LESSON_ID)
        session = db.current_session(str(path))
        assert session["lesson_id"] == LESSON_ID and session["phase"] == "closed"
        assert student.get("/stat-check/teacher").status_code == 403
        for phase in ("a", "b"):
            set_phase(teacher, phase)
            for index, item in enumerate(BANK.items):
                page = student.get("/stat-check/current")
                question = item["pair"][phase]
                assert_public_question(page, question)
                assert f'name="concept_id" value="{item["concept_id"]}"' in page.text
                option = SOLUTIONS[phase][index]
                if one_error and index == 0:
                    option = next(o["id"] for o in question["options"] if o["id"] != option)
                answer = {"csrf_token": csrf_from(page), "session_id": session_id_from(page),
                          "concept_id": item["concept_id"], "phase": phase,
                          "option_id": option, "confidence": "sure"}
                result = student.post("/stat-check/answer", data=answer, follow_redirects=False)
                assert result.status_code == 303
                # A repeat cannot overwrite the saved correctness or answer.
                if index == 0:
                    answer["option_id"] = SOLUTIONS[phase][index]
                    assert student.post("/stat-check/answer", data=answer, follow_redirects=False).status_code == 303
            if phase == "a":
                set_phase(teacher, "learn")
                learning = student.get("/stat-check/current")
                assert "借助 AI 理解概念" in learning.text
                completed = student.post("/stat-check/learn/complete", data={
                    "csrf_token": csrf_from(learning), "session_id": session_id_from(learning)}, follow_redirects=True)
                assert "学习阶段已完成" in completed.text
        set_phase(teacher, "result")
        feedback = student.get("/stat-check/current")
        assert feedback.status_code == 200
        expected_count = 4 if one_error else 5
        assert feedback.text.count("A：正确") == feedback.text.count("B：正确") == expected_count
        assert feedback.text.count("参考答案：") == 10
        assert all(item["pair"][phase]["explanation"] in unescape(feedback.text)
                   for item in BANK.items for phase in ("a", "b"))
        responses = db.responses_for_user(str(path), session["id"], 2)
        assert len(responses) == 10
        assert [row["correct"] for row in responses].count(0) == (2 if one_error else 0)
        exported = db.export_rows(str(path), session["id"])[0]
        assert (exported["a_count"], exported["b_count"], exported["a_correct"], exported["b_correct"], exported["learned"]) == (5, 5, expected_count, expected_count, 1)


def test_installation_restart_and_new_session_keep_old_lesson10_record(tmp_path):
    path = str(tmp_path / "old-lesson10-synthetic.sqlite3")
    old_bank = BANKS["v2-l10-r1"]
    db.initialize(path, old_bank.lesson_id, old_bank.title)
    old_session = dict(db.current_session(path))
    user = db.upsert_user(path, gitea_id=101, login="old-fixture", display_name="合成测试", role="student")
    concept = old_bank.concept_ids[0]
    db.save_response(path, session_id=old_session["id"], user_id=user["id"], concept_id=concept,
                     phase="a", option_id="A", confidence="unsure", correct=False)
    db.mark_learning_complete(path, old_session["id"], user["id"])
    before = [dict(r) for r in db.responses_for_user(path, old_session["id"], user["id"])]
    with make_client(path, "teacher", "teacher") as teacher:
        assert dict(db.current_session(path)) == old_session
        create_session(teacher, LESSON_ID)
        assert db.current_session(path)["lesson_id"] == LESSON_ID
        assert [dict(r) for r in db.responses_for_user(path, old_session["id"], user["id"])] == before
        assert db.learning_complete(path, old_session["id"], user["id"])
        assert db.get_session(path, old_session["id"])["lesson_id"] == old_bank.lesson_id
        history = teacher.get(f"/stat-check/teacher?session_id={old_session['id']}")
        assert history.status_code == 200 and old_bank.title in unescape(history.text)

