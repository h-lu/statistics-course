"""V2 content must not reinterpret any legacy lesson or stored response."""
import hashlib
import json
from pathlib import Path

import pytest

from app import db
from app.questions import BANKS, CURRENT_BANKS, DEFAULT_BANK

LEGACY_DIGESTS = {
    "lesson-01.yml": "02b9fe1fa0aba5f7c87aa2458a45a55cc6ea916ea14d18c7ae24e24cb8e04aad",
    "lesson-02.yml": "9a0ce62eaf5aebe07001bd3a9378d7713abb78b203d16553597f2efb40018b1c",
    "lesson-03.yml": "cd271efb4d3802aaec631852d946bece941f3292c303171ae294587626b22904",
    "lesson-04.yml": "a9e2220263f57c71067e7eac62da5c76e20341d6f88ae2adc61f769b2ca2aa24",
    "lesson-05.yml": "d9c1f97ba64c6db0b760fd27ad6f20c5300e055639b891c1d3bcb4592ac8d0be",
    "lesson-06.yml": "d2145b320ef7f8d076e8b894e6e28f496875143423b68dea633fe395fc54b616",
}


def test_legacy_bank_bytes_are_unchanged():
    directory = Path(__file__).parents[1] / "app/question_bank"
    for name, expected in LEGACY_DIGESTS.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected


def test_current_catalog_is_v2_and_legacy_lookup_survives():
    assert len(CURRENT_BANKS) == 32
    assert DEFAULT_BANK.lesson_id == "v2-l01-r3"
    assert BANKS["bootcamp-01"].lesson_id == "bootcamp-01"
    assert BANKS["s04-grouped-comparison"].lesson_id == "s04-grouped-comparison"
    assert BANKS["v2-l01"].lesson_id == "v2-l01"


def test_published_v2_bank_bytes_are_unchanged():
    directory = Path(__file__).parents[1] / "app/question_bank"
    expected = json.loads(Path(__file__).with_name("published_v2_bank_hashes.json").read_text())
    assert len(expected) == 32
    for name, digest in expected.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest


def test_language_revision_preserves_question_structure_and_answer_keys():
    for number in range(1, 33):
        old = BANKS[f"v2-l{number:02d}"]
        revised = BANKS[f"v2-l{number:02d}-r1"]
        assert old.concept_ids == revised.concept_ids
        assert old.durations == revised.durations
        for concept in old.concept_ids:
            for phase in ("a", "b"):
                assert old.question(concept, phase)["answer"] == revised.question(concept, phase)["answer"]


@pytest.mark.parametrize("old_id", ["bootcamp-01", "v2-l01", "v2-l01-r1", "v2-l08-r1"])
def test_initialization_preserves_existing_legacy_responses(tmp_path, old_id):
    path = str(tmp_path / "legacy.sqlite3")
    old = BANKS[old_id]
    db.initialize(path, old.lesson_id, old.title)
    session = db.current_session(path)
    user = db.upsert_user(path, gitea_id=1, login="student", display_name="测试学生", role="student")
    concept = old.items[0]["concept_id"]
    db.save_response(path, session_id=session["id"], user_id=user["id"], concept_id=concept, phase="a", option_id=old.question(concept, "a")["answer"], confidence="sure", correct=True)
    db.initialize(path, DEFAULT_BANK.lesson_id, DEFAULT_BANK.title)
    after = db.current_session(path)
    assert dict(after) == dict(session)
    records = db.responses_for_user(path, session["id"], user["id"])
    assert len(records) == 1 and records[0]["concept_id"] == concept and records[0]["correct"] == 1
    new = db.create_session(path, DEFAULT_BANK.lesson_id, DEFAULT_BANK.title)
    assert new["id"] != session["id"]
    assert db.get_session(path, session["id"])["lesson_id"] == old.lesson_id
    assert len(db.responses_for_user(path, session["id"], user["id"])) == 1


def test_published_first_eight_r1_bank_bytes_are_unchanged():
    directory = Path(__file__).parents[1] / "app/question_bank"
    expected = json.loads(Path(__file__).with_name("published_r1_01_08_git_hashes.json").read_text())
    assert len(expected) == 8
    for name, digest in expected.items():
        content = (directory / name).read_bytes()
        git_blob = f"blob {len(content)}\0".encode() + content
        assert hashlib.sha1(git_blob).hexdigest() == digest
