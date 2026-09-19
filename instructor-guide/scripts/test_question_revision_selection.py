"""Check the teacher validator's bank choice without running course projects."""
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("course_validator", Path(__file__).with_name("validate_course.py"))
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def touch(root, *names):
    for name in names:
        (root / name).write_text("fixture", encoding="utf-8")


def test_partial_r2_upgrade_is_per_lesson(tmp_path):
    touch(tmp_path, "lesson-v2r1-01.yml", "lesson-v2r2-01.yml", "lesson-v2r1-09.yml")
    assert validator.current_bank_spec(tmp_path, 1) == (tmp_path / "lesson-v2r2-01.yml", "v2-l01-r2")
    assert validator.current_bank_spec(tmp_path, 9) == (tmp_path / "lesson-v2r1-09.yml", "v2-l09-r1")


def test_revisions_are_numeric(tmp_path):
    touch(tmp_path, "lesson-v2r2-01.yml", "lesson-v2r9-01.yml", "lesson-v2r10-01.yml")
    assert validator.current_bank_spec(tmp_path, 1)[1] == "v2-l01-r10"


def test_unversioned_bank_remains_a_fallback(tmp_path):
    touch(tmp_path, "lesson-v2-02.yml")
    assert validator.current_bank_spec(tmp_path, 2) == (tmp_path / "lesson-v2-02.yml", "v2-l02")


def test_missing_lesson_is_not_replaced_with_other_lesson(tmp_path):
    touch(tmp_path, "lesson-v2r2-01.yml")
    path, identifier = validator.current_bank_spec(tmp_path, 2)
    assert identifier == "v2-l02-r1" and not path.exists()
