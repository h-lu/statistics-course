from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gitea_id INTEGER NOT NULL UNIQUE,
    login TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'teacher')),
    last_login_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS course_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id TEXT NOT NULL,
    title TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('closed', 'a', 'learn', 'b', 'result')),
    phase_started_at TEXT,
    phase_ends_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES course_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('a', 'b')),
    option_id TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('guess', 'unsure', 'sure')),
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    submitted_at TEXT NOT NULL,
    UNIQUE(session_id, user_id, concept_id, phase)
);

CREATE TABLE IF NOT EXISTS learning_completions (
    session_id INTEGER NOT NULL REFERENCES course_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed_at TEXT NOT NULL,
    PRIMARY KEY(session_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_responses_session_phase
ON responses(session_id, phase);
"""


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat()


def connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize(database_path: str, lesson_id: str, title: str) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA journal_mode = WAL")
        existing = connection.execute(
            "SELECT id FROM course_sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO course_sessions
                    (lesson_id, title, phase, created_at)
                VALUES (?, ?, 'closed', ?)
                """,
                (lesson_id, title, iso_now()),
            )


def upsert_user(
    database_path: str,
    *,
    gitea_id: int,
    login: str,
    display_name: str,
    role: str,
) -> sqlite3.Row:
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users (gitea_id, login, display_name, role, last_login_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(gitea_id) DO UPDATE SET
                login = excluded.login,
                display_name = excluded.display_name,
                role = excluded.role,
                last_login_at = excluded.last_login_at
            """,
            (gitea_id, login, display_name, role, iso_now()),
        )
        return connection.execute(
            "SELECT * FROM users WHERE gitea_id = ?", (gitea_id,)
        ).fetchone()


def get_user(database_path: str, user_id: int) -> sqlite3.Row | None:
    with connect(database_path) as connection:
        return connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def current_session(database_path: str) -> sqlite3.Row:
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM course_sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise RuntimeError("course session is missing")
    return row


def get_session(database_path: str, session_id: int) -> sqlite3.Row | None:
    with connect(database_path) as connection:
        return connection.execute(
            "SELECT * FROM course_sessions WHERE id = ?", (session_id,)
        ).fetchone()


def session_history(database_path: str, limit: int = 12) -> list[sqlite3.Row]:
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT * FROM course_sessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def create_session(database_path: str, lesson_id: str, title: str) -> sqlite3.Row:
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO course_sessions
                (lesson_id, title, phase, created_at)
            VALUES (?, ?, 'closed', ?)
            """,
            (lesson_id, title, iso_now()),
        )
        session_id = int(cursor.lastrowid)
        return connection.execute(
            "SELECT * FROM course_sessions WHERE id = ?", (session_id,)
        ).fetchone()


def delete_session(database_path: str, session_id: int, force: bool = False) -> str | None:
    """Delete a closed session, optionally including its student records."""
    with connect(database_path) as connection:
        session = connection.execute(
            "SELECT id, lesson_id, title, phase FROM course_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session is None:
            return "场次不存在"
        if session["phase"] != "closed":
            return "只有尚未开始的场次可以删除"
        used = connection.execute(
            """
            SELECT EXISTS(SELECT 1 FROM responses WHERE session_id = ?)
                OR EXISTS(SELECT 1 FROM learning_completions WHERE session_id = ?)
            """,
            (session_id, session_id),
        ).fetchone()[0]
        if used and not force:
            return "已有学生记录的场次不能删除"
        connection.execute("DELETE FROM course_sessions WHERE id = ?", (session_id,))
        total = connection.execute("SELECT COUNT(*) FROM course_sessions").fetchone()[0]
        if total == 0:
            connection.execute(
                "INSERT INTO course_sessions (lesson_id, title, phase, created_at) VALUES (?, ?, 'closed', ?)",
                (session["lesson_id"], session["title"], iso_now()),
            )
    return None


def set_phase(
    database_path: str,
    session_id: int,
    phase: str,
    duration_seconds: int | None,
) -> None:
    now = utc_now()
    ends_at = (
        (now + timedelta(seconds=duration_seconds)).isoformat()
        if duration_seconds
        else None
    )
    with connect(database_path) as connection:
        connection.execute(
            """
            UPDATE course_sessions
            SET phase = ?, phase_started_at = ?, phase_ends_at = ?
            WHERE id = ?
            """,
            (phase, now.isoformat(), ends_at, session_id),
        )


def responses_for_user(
    database_path: str, session_id: int, user_id: int
) -> list[sqlite3.Row]:
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT * FROM responses
            WHERE session_id = ? AND user_id = ?
            ORDER BY id
            """,
            (session_id, user_id),
        ).fetchall()


def response_for(
    database_path: str,
    session_id: int,
    user_id: int,
    concept_id: str,
    phase: str,
) -> sqlite3.Row | None:
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT * FROM responses
            WHERE session_id = ? AND user_id = ? AND concept_id = ? AND phase = ?
            """,
            (session_id, user_id, concept_id, phase),
        ).fetchone()


def save_response(
    database_path: str,
    *,
    session_id: int,
    user_id: int,
    concept_id: str,
    phase: str,
    option_id: str,
    confidence: str,
    correct: bool,
) -> None:
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO responses
                (session_id, user_id, concept_id, phase, option_id,
                 confidence, correct, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                concept_id,
                phase,
                option_id,
                confidence,
                int(correct),
                iso_now(),
            ),
        )


def mark_learning_complete(
    database_path: str, session_id: int, user_id: int
) -> None:
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO learning_completions (session_id, user_id, completed_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, user_id) DO NOTHING
            """,
            (session_id, user_id, iso_now()),
        )


def learning_complete(
    database_path: str, session_id: int, user_id: int
) -> bool:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT 1 FROM learning_completions
            WHERE session_id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()
    return row is not None


def dashboard_summary(
    database_path: str, session_id: int, item_count: int
) -> dict:
    with connect(database_path) as connection:
        students = connection.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'student'"
        ).fetchone()["n"]
        completed = {}
        for phase in ("a", "b"):
            completed[phase] = connection.execute(
                """
                SELECT COUNT(*) AS n FROM (
                    SELECT r.user_id FROM responses r
                    JOIN users u ON u.id = r.user_id
                    WHERE r.session_id = ? AND r.phase = ? AND u.role = 'student'
                    GROUP BY r.user_id HAVING COUNT(*) = ?
                )
                """,
                (session_id, phase, item_count),
            ).fetchone()["n"]
        completed["learn"] = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM learning_completions lc
            JOIN users u ON u.id = lc.user_id
            WHERE lc.session_id = ? AND u.role = 'student'
            """,
            (session_id,),
        ).fetchone()["n"]
        aggregates = connection.execute(
            """
            SELECT r.concept_id, r.phase, COUNT(*) AS answered,
                   SUM(r.correct) AS correct_count
            FROM responses r
            JOIN users u ON u.id = r.user_id
            WHERE r.session_id = ? AND u.role = 'student'
            GROUP BY r.concept_id, r.phase
            """,
            (session_id,),
        ).fetchall()
    return {
        "students": students,
        "completed": completed,
        "aggregates": aggregates,
    }


def export_rows(database_path: str, session_id: int) -> list[sqlite3.Row]:
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT u.login, u.display_name,
                   SUM(CASE WHEN r.phase = 'a' THEN 1 ELSE 0 END) AS a_count,
                   SUM(CASE WHEN r.phase = 'a' THEN r.correct ELSE 0 END) AS a_correct,
                   SUM(CASE WHEN r.phase = 'b' THEN 1 ELSE 0 END) AS b_count,
                   SUM(CASE WHEN r.phase = 'b' THEN r.correct ELSE 0 END) AS b_correct,
                   CASE WHEN lc.user_id IS NULL THEN 0 ELSE 1 END AS learned
            FROM users u
            LEFT JOIN responses r
                ON r.user_id = u.id AND r.session_id = ?
            LEFT JOIN learning_completions lc
                ON lc.user_id = u.id AND lc.session_id = ?
            WHERE u.role = 'student'
            GROUP BY u.id, lc.user_id
            ORDER BY u.login
            """,
            (session_id, session_id),
        ).fetchall()
