"""The fifth-lesson wording revision keeps published questions and sessions intact."""

from hashlib import sha256
from pathlib import Path

import pytest

from app import db
from app.questions import BANKS, CURRENT_BANKS


PUBLISHED_R3_SHA256 = "b38a447a5a6ce188eabc8b4f530d7962c7c2a7bd46b57744dd44a1f9ddbd31c6"


def test_r4_is_current_while_r3_remains_unchanged():
    previous = BANKS["v2-l05-r3"]
    revised = BANKS["v2-l05-r4"]
    assert sha256(previous.path.read_bytes()).hexdigest() == PUBLISHED_R3_SHA256
    assert next(bank for bank in CURRENT_BANKS if bank.lesson_id.startswith("v2-l05")).lesson_id == revised.lesson_id
    assert previous.concept_ids == revised.concept_ids
    assert previous.durations == revised.durations
    for concept in previous.concept_ids:
        for phase in ("a", "b"):
            assert previous.question(concept, phase)["answer"] == revised.question(concept, phase)["answer"]

    teacher_copy = Path(__file__).resolve().parents[2] / "instructor-guide/knowledge-check/question-bank/lesson-v2r4-05.yml"
    if teacher_copy.is_file():
        assert revised.path.read_bytes() == teacher_copy.read_bytes()
    else:
        pytest.skip("standalone stat-check checkout has no teacher mirror")


def test_existing_r3_session_keeps_its_bank_when_r4_is_available(tmp_path):
    path = str(tmp_path / "lesson05.sqlite3")
    previous = BANKS["v2-l05-r3"]
    revised = BANKS["v2-l05-r4"]
    db.initialize(path, previous.lesson_id, previous.title)
    old_session = db.current_session(path)
    new_session = db.create_session(path, revised.lesson_id, revised.title)
    assert db.get_session(path, old_session["id"])["lesson_id"] == previous.lesson_id
    assert new_session["lesson_id"] == revised.lesson_id
