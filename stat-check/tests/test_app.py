from __future__ import annotations

import re
from collections import Counter
from datetime import timedelta

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import Settings
from app import db
from app.main import create_app
from app.questions import BANK, BANKS, CURRENT_BANKS, QUESTION_BANKS, QuestionBank


def make_client(database_path, role: str, login: str) -> TestClient:
    settings = Settings(
        database_path=str(database_path),
        session_secret="test-secret-that-is-long-enough",
        gitea_base_url="https://gitea.example",
        gitea_client_id="client",
        gitea_client_secret="secret",
        public_base_url="https://course.example/stat-check",
        teacher_logins=frozenset({"teacher"}),
        secure_cookie=False,
        testing=True,
    )
    client = TestClient(create_app(settings))
    response = client.get(
        f"/stat-check/test-login?login={login}&role={role}",
        follow_redirects=True,
    )
    assert response.status_code == 200
    return client


def csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def session_id_from(response) -> int:
    match = re.search(r'name="session_id" value="(\d+)"', response.text)
    assert match
    return int(match.group(1))


def set_phase(client: TestClient, phase: str) -> None:
    page = client.get("/stat-check/teacher")
    response = client.post(
        "/stat-check/teacher/phase",
        data={
            "csrf_token": csrf_from(page),
            "session_id": session_id_from(page),
            "phase": phase,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert f"当前阶段：" in response.text


def answer_all(client: TestClient, phase: str, bank=BANK) -> None:
    for _ in bank.items:
        page = client.get("/stat-check/current")
        concept_match = re.search(r'name="concept_id" value="([^"]+)"', page.text)
        assert concept_match
        concept_id = concept_match.group(1)
        answer = str(bank.question(concept_id, phase)["answer"])
        response = client.post(
            "/stat-check/answer",
            data={
                "csrf_token": csrf_from(page),
                "session_id": session_id_from(page),
                "concept_id": concept_id,
                "phase": phase,
                "option_id": answer,
                "confidence": "sure",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200


def create_session(client: TestClient, lesson_id: str) -> None:
    page = client.get("/stat-check/teacher")
    response = client.post(
        "/stat-check/teacher/session",
        data={"csrf_token": csrf_from(page), "lesson_id": lesson_id},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_complete_classroom_flow(tmp_path) -> None:
    database_path = tmp_path / "flow.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    student = make_client(database_path, "student", "student01")

    set_phase(teacher, "a")
    first_page = student.get("/stat-check/current")
    assert "A 版基础题" in first_page.text
    assert "AI 全程可以使用" in first_page.text
    answer_all(student, "a")
    assert "A 版基础题已完成" in student.get("/stat-check/current").text

    set_phase(teacher, "learn")
    learn_page = student.get("/stat-check/current")
    assert "借助 AI 理解概念" in learn_page.text
    learned = student.post(
        "/stat-check/learn/complete",
        data={
            "csrf_token": csrf_from(learn_page),
            "session_id": session_id_from(learn_page),
        },
        follow_redirects=True,
    )
    assert "学习阶段已完成" in learned.text


def test_teacher_can_delete_unused_closed_session_but_not_used_session(tmp_path) -> None:
    database_path = tmp_path / "delete-session.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    create_session(teacher, "v2-l02-r1")
    page = teacher.get("/stat-check/teacher")
    session_id = session_id_from(page)
    deleted = teacher.post(
        "/stat-check/teacher/session/delete",
        data={"csrf_token": csrf_from(page), "session_id": session_id},
        follow_redirects=True,
    )
    assert deleted.status_code == 200
    assert f"#{session_id}" not in deleted.text

    create_session(teacher, "v2-l01-r1")
    student = make_client(database_path, "student", "student01")
    set_phase(teacher, "a")
    answer_all(student, "a")
    set_phase(teacher, "closed")
    page = teacher.get("/stat-check/teacher")
    blocked = teacher.post(
        "/stat-check/teacher/session/delete",
        data={"csrf_token": csrf_from(page), "session_id": session_id_from(page)},
    )
    assert blocked.status_code == 409
    assert "已有学生记录" in blocked.text

    set_phase(teacher, "b")
    answer_all(student, "b")
    assert "B 版变式题已完成" in student.get("/stat-check/current").text

    set_phase(teacher, "result")
    result = student.get("/stat-check/current")
    assert result.status_code == 200
    assert result.text.count("A：正确") == len(BANK.items)
    assert result.text.count("B：正确") == len(BANK.items)

    dashboard = teacher.get("/stat-check/teacher")
    assert "A 版完成" in dashboard.text
    assert "100%" in dashboard.text
    export = teacher.get("/stat-check/teacher/export.csv")
    assert export.status_code == 200
    assert "student01" in export.text
    set_phase(teacher, "closed")
    force_page = teacher.get("/stat-check/teacher")
    force_deleted = teacher.post(
        "/stat-check/teacher/session/delete",
        data={
            "csrf_token": csrf_from(force_page),
            "session_id": session_id_from(force_page),
            "force": "true",
        },
        follow_redirects=True,
    )
    assert force_deleted.status_code == 200
    assert "已有学生记录的场次不能删除" not in force_deleted.text


def test_teacher_can_delete_only_unused_session_and_gets_empty_replacement(tmp_path) -> None:
    database_path = tmp_path / "delete-only-session.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    page = teacher.get("/stat-check/teacher")
    session_id = session_id_from(page)
    deleted = teacher.post(
        "/stat-check/teacher/session/delete",
        data={"csrf_token": csrf_from(page), "session_id": session_id},
        follow_redirects=True,
    )
    assert deleted.status_code == 200
    replacement_id = session_id_from(deleted)
    assert replacement_id != session_id
    assert f"#{session_id}" not in deleted.text


def test_repeated_answer_submit_is_idempotent_and_first_answer_stays_locked(tmp_path) -> None:
    database_path = tmp_path / "locked.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    student = make_client(database_path, "student", "student02")
    set_phase(teacher, "a")

    page = student.get("/stat-check/current")
    concept_id = re.search(
        r'name="concept_id" value="([^"]+)"', page.text
    ).group(1)
    payload = {
        "csrf_token": csrf_from(page),
        "session_id": session_id_from(page),
        "concept_id": concept_id,
        "phase": "a",
        "option_id": str(BANK.question(concept_id, "a")["answer"]),
        "confidence": "unsure",
    }
    assert student.post("/stat-check/answer", data=payload).status_code == 200
    duplicate = student.post(
        "/stat-check/answer", data=payload, follow_redirects=False
    )
    assert duplicate.status_code == 303
    assert duplicate.headers["location"] == "/stat-check/current"
    saved = db.responses_for_user(database_path, session_id_from(page), 2)
    assert len(saved) == 1
    assert saved[0]["option_id"] == payload["option_id"]


def test_student_cannot_open_teacher_dashboard(tmp_path) -> None:
    student = make_client(tmp_path / "permission.sqlite3", "student", "student03")
    assert student.get("/stat-check/teacher").status_code == 403


def test_question_bank_directory_and_answer_positions() -> None:
    assert [bank.path.name for bank in QUESTION_BANKS] == [
        f"lesson-{number:02d}.yml" for number in range(1, 7)
    ] + [f"lesson-v2-{number:02d}.yml" for number in range(1, 33)] + [
        f"lesson-v2r1-{number:02d}.yml" for number in range(1, 33)
    ]
    assert len({bank.lesson_id for bank in QUESTION_BANKS}) == 70
    assert [bank.lesson_id for bank in CURRENT_BANKS] == [f"v2-l{n:02d}-r1" for n in range(1, 33)]
    assert BANK.lesson_id == "v2-l01-r1"
    for bank in QUESTION_BANKS:
        assert len(bank.items) == 5
        answers = Counter(
            str(item["pair"][phase]["answer"])
            for item in bank.items
            for phase in ("a", "b")
        )
        for item in bank.items:
            for phase in ("a", "b"):
                assert [
                    str(option["id"])
                    for option in item["pair"][phase]["options"]
                ] == ["A", "B", "C", "D"]
        assert set(answers) == {"A", "B", "C", "D"}
        assert max(answers.values()) <= 4


def test_question_bank_rejects_duplicate_concept_ids(tmp_path) -> None:
    duplicate_bank = tmp_path / "duplicate.yml"
    source = yaml.safe_load(BANK.path.read_text(encoding="utf-8"))
    source["items"][1]["concept_id"] = source["items"][0]["concept_id"]
    duplicate_bank.write_text(yaml.safe_dump(source, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate concept_id"):
        QuestionBank(duplicate_bank)


def test_new_session_uses_selected_bank_and_preserves_history(tmp_path) -> None:
    database_path = tmp_path / "sessions.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    student = make_client(database_path, "student", "student04")

    set_phase(teacher, "a")
    first_page = student.get("/stat-check/current")
    first_concept = re.search(
        r'name="concept_id" value="([^"]+)"', first_page.text
    ).group(1)
    first_answer = str(BANK.question(first_concept, "a")["answer"])
    student.post(
        "/stat-check/answer",
        data={
            "csrf_token": csrf_from(first_page),
            "session_id": session_id_from(first_page),
            "concept_id": first_concept,
            "phase": "a",
            "option_id": first_answer,
            "confidence": "sure",
        },
    )
    old_session = db.current_session(str(database_path))

    create_session(teacher, "bootcamp-02")
    new_session = db.current_session(str(database_path))
    assert new_session["id"] != old_session["id"]
    assert new_session["phase"] == "closed"
    assert new_session["lesson_id"] == "bootcamp-02"
    assert len(db.session_history(str(database_path))) == 2

    waiting = student.get("/stat-check/current")
    assert BANKS["bootcamp-02"].title in waiting.text
    assert 'data-state-watch' in waiting.text
    state = student.get("/stat-check/state").json()
    assert state["session_id"] == new_session["id"]
    assert state["phase"] == "closed"

    second_bank = BANKS["bootcamp-02"]
    set_phase(teacher, "a")
    answer_all(student, "a", second_bank)
    assert "A 版基础题已完成" in student.get("/stat-check/current").text
    set_phase(teacher, "learn")
    learn_page = student.get("/stat-check/current")
    student.post(
        "/stat-check/learn/complete",
        data={
            "csrf_token": csrf_from(learn_page),
            "session_id": session_id_from(learn_page),
        },
    )
    set_phase(teacher, "b")
    answer_all(student, "b", second_bank)
    set_phase(teacher, "result")
    second_result = student.get("/stat-check/current")
    assert second_result.text.count("A：正确") == len(second_bank.items)
    assert second_result.text.count("B：正确") == len(second_bank.items)
    dashboard = teacher.get("/stat-check/teacher")
    assert second_bank.title in dashboard.text

    old_export = teacher.get(
        f"/stat-check/teacher/export.csv?session_id={old_session['id']}"
    )
    assert old_export.status_code == 200
    assert "student04" in old_export.text
    assert ",1,1," in old_export.text


def test_stale_student_forms_cannot_write_to_new_session(tmp_path) -> None:
    database_path = tmp_path / "stale-student.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    student = make_client(database_path, "student", "student07")

    set_phase(teacher, "a")
    stale_answer_page = student.get("/stat-check/current")
    stale_concept = re.search(
        r'name="concept_id" value="([^"]+)"', stale_answer_page.text
    ).group(1)

    create_session(teacher, BANK.lesson_id)
    set_phase(teacher, "a")
    answer_session = db.current_session(str(database_path))
    stale_answer = student.post(
        "/stat-check/answer",
        data={
            "csrf_token": csrf_from(stale_answer_page),
            "session_id": session_id_from(stale_answer_page),
            "concept_id": stale_concept,
            "phase": "a",
            "option_id": str(BANK.question(stale_concept, "a")["answer"]),
            "confidence": "sure",
        },
        follow_redirects=False,
    )
    assert stale_answer.status_code == 409
    with db.connect(str(database_path)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM responses WHERE session_id = ?",
            (answer_session["id"],),
        ).fetchone()[0] == 0

    set_phase(teacher, "learn")
    stale_learn_page = student.get("/stat-check/current")
    create_session(teacher, BANK.lesson_id)
    set_phase(teacher, "learn")
    learn_session = db.current_session(str(database_path))
    stale_learning = student.post(
        "/stat-check/learn/complete",
        data={
            "csrf_token": csrf_from(stale_learn_page),
            "session_id": session_id_from(stale_learn_page),
        },
        follow_redirects=False,
    )
    assert stale_learning.status_code == 409
    with db.connect(str(database_path)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_completions WHERE session_id = ?",
            (learn_session["id"],),
        ).fetchone()[0] == 0


def test_stale_teacher_page_cannot_advance_new_session(tmp_path) -> None:
    database_path = tmp_path / "stale-teacher.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    stale_teacher_page = teacher.get("/stat-check/teacher")

    create_session(teacher, BANK.lesson_id)
    new_session = db.current_session(str(database_path))
    stale_phase = teacher.post(
        "/stat-check/teacher/phase",
        data={
            "csrf_token": csrf_from(stale_teacher_page),
            "session_id": session_id_from(stale_teacher_page),
            "phase": "a",
        },
        follow_redirects=False,
    )

    assert stale_phase.status_code == 409
    current = db.current_session(str(database_path))
    assert current["id"] == new_session["id"]
    assert current["phase"] == "closed"


def test_expired_phases_reject_answer_and_learning_submit(tmp_path) -> None:
    database_path = tmp_path / "expired.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    student = make_client(database_path, "student", "student05")

    set_phase(teacher, "a")
    question_page = student.get("/stat-check/current")
    concept_id = re.search(
        r'name="concept_id" value="([^"]+)"', question_page.text
    ).group(1)
    with db.connect(str(database_path)) as connection:
        connection.execute(
            "UPDATE course_sessions SET phase_ends_at = ? WHERE id = ?",
            (
                (db.utc_now() - timedelta(seconds=1)).isoformat(),
                db.current_session(str(database_path))["id"],
            ),
        )

    expired_page = student.get("/stat-check/current")
    assert "计时已结束" in expired_page.text
    assert "data-state-watch" in expired_page.text
    late_answer = student.post(
        "/stat-check/answer",
        data={
            "csrf_token": csrf_from(question_page),
            "session_id": session_id_from(question_page),
            "concept_id": concept_id,
            "phase": "a",
            "option_id": str(BANK.question(concept_id, "a")["answer"]),
            "confidence": "sure",
        },
        follow_redirects=False,
    )
    assert late_answer.status_code == 409

    set_phase(teacher, "learn")
    learn_page = student.get("/stat-check/current")
    assert "data-state-watch" in learn_page.text
    assert "data-reload-on-deadline" in learn_page.text
    with db.connect(str(database_path)) as connection:
        connection.execute(
            "UPDATE course_sessions SET phase_ends_at = ? WHERE id = ?",
            (
                (db.utc_now() - timedelta(seconds=1)).isoformat(),
                db.current_session(str(database_path))["id"],
            ),
        )
    late_learning = student.post(
        "/stat-check/learn/complete",
        data={
            "csrf_token": csrf_from(learn_page),
            "session_id": session_id_from(learn_page),
        },
        follow_redirects=False,
    )
    assert late_learning.status_code == 409


def test_refresh_markers_are_present(tmp_path) -> None:
    database_path = tmp_path / "refresh.sqlite3"
    teacher = make_client(database_path, "teacher", "teacher")
    student = make_client(database_path, "student", "student06")

    closed_page = student.get("/stat-check/current")
    assert 'data-state-watch' in closed_page.text
    assert '/stat-check/state' in closed_page.text

    teacher_page = teacher.get("/stat-check/teacher")
    assert 'data-auto-reload="15000"' in teacher_page.text
    assert "新建本课自查（暂不开放）" in teacher_page.text
    assert 'value="v2-l01-r1"' in teacher_page.text
    assert 'value="v2-l01"' not in teacher_page.text
    assert 'value="bootcamp-01"' not in teacher_page.text

    set_phase(teacher, "a")
    attempt_page = student.get("/stat-check/current")
    assert 'data-state-watch' in attempt_page.text
    assert 'data-reload-on-deadline' in attempt_page.text
    assert '/stat-check/state' in attempt_page.text

    set_phase(teacher, "learn")
    learn_page = student.get("/stat-check/current")
    assert 'data-state-watch' in learn_page.text
    assert 'data-reload-on-deadline' in learn_page.text
