"""Archived future lessons remain usable for history, never for new sessions."""
from pathlib import Path
import re

from app import db
from app.questions import ACTIVE_LESSONS, BANKS, CURRENT_BANKS, QUESTION_BANKS, bank_for_lesson
from test_app import csrf_from, make_client


def test_all_archived_future_versions_and_teacher_copies_are_preserved():
    teacher = Path(__file__).resolve().parents[2] / "instructor-guide/knowledge-check/question-bank"
    archived = []
    for bank in QUESTION_BANKS:
        match = re.fullmatch(r"v2-l(\d{2})(?:-r\d+)?", bank.lesson_id)
        if match and int(match.group(1)) >= 9:
            archived.append(bank)
            assert bank.path.parent.name == "redesign-2026-10-09"
            relative = bank.path.relative_to(Path(__file__).parents[1] / "app/question_bank")
            assert bank.path.read_bytes() == (teacher / relative).read_bytes()
            assert bank_for_lesson(bank.lesson_id) is bank
    assert len(archived) == 48
    assert [int(re.search(r"l(\d{2})", b.lesson_id).group(1)) for b in CURRENT_BANKS] == list(ACTIVE_LESSONS)
    assert len(BANKS) == 87


def test_future_existing_session_and_response_survive_app_restart(tmp_path):
    path = tmp_path / "old-future.sqlite3"
    bank = BANKS["v2-l09-r1"]
    db.initialize(str(path), bank.lesson_id, bank.title)
    session = db.current_session(str(path))
    user = db.upsert_user(str(path), gitea_id=1, login="synthetic-history", display_name="合成测试用户", role="student")
    concept = bank.concept_ids[0]
    db.save_response(str(path), session_id=session["id"], user_id=user["id"], concept_id=concept,
                     phase="a", option_id=bank.question(concept, "a")["answer"], confidence="sure", correct=True)
    before_responses = [dict(r) for r in db.responses_for_user(str(path), session["id"], user["id"])]
    with make_client(path, "teacher", "teacher") as client:
        assert client.get("/stat-check/healthz").json() == {"status": "ok"}
        assert dict(db.current_session(str(path))) == dict(session)
        page = client.get("/stat-check/teacher")
        assert 'value="v2-l09-r1"' not in page.text
        rejected = client.post("/stat-check/teacher/session", data={"csrf_token": csrf_from(page), "lesson_id": bank.lesson_id})
        assert rejected.status_code == 400
        assert dict(db.current_session(str(path))) == dict(session)
        assert [dict(r) for r in db.responses_for_user(str(path), session["id"], user["id"])] == before_responses
