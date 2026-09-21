"""Course-wide student material contracts introduced after the L01-04 trial."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
STUDENT = ROOT / "student-template"


def test_all_lessons_have_support_and_three_levels() -> None:
    for number in range(1, 33):
        lesson = STUDENT / f"lesson-{number:02d}"
        readme = (lesson / "README.md").read_text(encoding="utf-8")
        support = (lesson / "SUPPORT.md").read_text(encoding="utf-8")

        assert "SUPPORT.md" in readme
        assert "LEARN.md" in readme
        for heading in (
            "基础练习（可信起点）",
            "标准任务（本课应完成）",
            "提高与拓展（提前完成后）",
        ):
            assert heading in readme
            assert heading in support

        for action in ("start", "run"):
            command = f"scripts/course.py {action} {number:02d}"
            assert command in support
        for required in ("成功信号", "卡住", "提交前自检"):
            assert required in support


def test_final_lesson_has_advance_plan_and_fallback_route() -> None:
    # 计划必须随L31发布，否则逐课发布时学生在L32开放前无法填写。
    plan = STUDENT / "lesson-31" / "LESSON_32_PLAN.md"
    assert plan.is_file()
    readme = (STUDENT / "lesson-32" / "README.md").read_text(encoding="utf-8")
    prior = (STUDENT / "lesson-31" / "README.md").read_text(encoding="utf-8")
    earlier = (STUDENT / "lesson-30" / "README.md").read_text(encoding="utf-8")
    assert "LESSON_32_PLAN.md" in readme
    assert "LESSON_32_PLAN.md" in prior
    assert "../lesson-32" not in earlier
    assert "默认路线" in readme
    for phrase in ("调查费用4", "延迟成本3", "0.70", "0.25"):
        assert phrase in readme
        assert phrase in plan.read_text(encoding="utf-8")
    assert "git add lesson-31/LESSON_32_PLAN.md" in prior


def test_student_markdown_relative_links_resolve() -> None:
    example_only = {("docs/READING_GUIDE.md", "artifacts/wait_summary.csv")}
    for document in STUDENT.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for match in re.finditer(r"\[[^]]+\]\(([^)]+)\)", text):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            relative_document = document.relative_to(STUDENT).as_posix()
            if (relative_document, target) in example_only:
                continue
            assert (document.parent / target).resolve().exists(), (
                f"{relative_document} links to missing {target}"
            )
