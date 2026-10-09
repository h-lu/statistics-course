"""Check authored student routes and ensure future placeholders stay inert."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STUDENT = ROOT / "student-template"
ACTIVE_LESSONS = tuple(range(1, 9))


def test_active_lessons_have_support_and_three_levels() -> None:
    for number in ACTIVE_LESSONS:
        lesson = STUDENT / f"lesson-{number:02d}"
        readme = (lesson / "README.md").read_text(encoding="utf-8")
        support = (lesson / "SUPPORT.md").read_text(encoding="utf-8")
        assert "SUPPORT.md" in readme and "LEARN.md" in readme
        for heading in ("基础练习（可信起点）", "标准任务（本课应完成）", "提高与拓展（提前完成后）"):
            assert heading in readme
        # SUPPORT是可选资源索引；不把标题、命令顺序或线性路线锁成教学方法。
        assert support.strip()
        for name in ("LEARN.md", "analysis.py", "report.md", "submission.json"):
            assert (lesson / name).is_file()


def test_future_lessons_have_no_executable_or_submission_content() -> None:
    for root in (STUDENT, ROOT / "instructor-guide"):
        for number in range(9, 33):
            directory = root / f"lesson-{number:02d}"
            paths = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
            assert paths == {"README.md"}
            assert "占位" in (directory / "README.md").read_text(encoding="utf-8")
    for name in ("inference", "experiments", "prediction", "policy"):
        assert not (STUDENT / "data" / name).exists()
        assert not (STUDENT / "scripts" / f"generate_{name}.py").exists()
    for name in ("service", "alerts"):
        assert (STUDENT / "data" / name).is_dir()


def test_student_markdown_relative_links_resolve() -> None:
    example_only = {("docs/READING_GUIDE.md", "artifacts/wait_summary.csv")}
    for document in STUDENT.rglob("*.md"):
        if "archive" in document.relative_to(STUDENT).parts:
            continue
        text = re.sub(r"```.*?```", "", document.read_text(encoding="utf-8"), flags=re.S)
        for match in re.finditer(r"\[[^]]+\]\(([^)]+)\)", text):
            target = match.group(1).strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "/")):
                continue
            relative_document = document.relative_to(STUDENT).as_posix()
            if (relative_document, target) in example_only:
                continue
            assert (document.parent / target).resolve().exists(), f"{relative_document} links to missing {target}"
