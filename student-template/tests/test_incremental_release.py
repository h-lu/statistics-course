"""Check partial releases using temporary repositories; no network or student work."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("release_course", Path(__file__).parents[1] / "scripts/course.py")
course = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(course)


def make_lesson(root, number=1, status="complete"):
    name = f"lesson-{number:02d}"
    folder = root / name
    folder.mkdir()
    (folder / "artifacts").mkdir()
    (folder / "report.md").write_text("分析报告", encoding="utf-8")
    (folder / "artifacts/result.txt").write_text("5\n", encoding="utf-8")
    (folder / "analysis.py").write_text(
        f"from pathlib import Path\nPath('{name}/artifacts/result.txt').write_text('5\\n')\n",
        encoding="utf-8",
    )
    (folder / "submission.json").write_text(json.dumps({
        "lesson": name, "status": status, "report": f"{name}/report.md",
        "artifacts": [f"{name}/artifacts/result.txt"], "run": ["python", f"{name}/analysis.py"]
    }), encoding="utf-8")
    return folder


class PartialCITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_single_final_tag_reproduces_and_preserves_source(self):
        make_lesson(self.root)
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        course.ci(self.root, "refs/tags/v2-l01-final")
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_single_revision_tag(self):
        make_lesson(self.root)
        course.ci(self.root, "refs/tags/v2-l01-revision-1")

    def test_branch_checks_only_existing_lessons(self):
        make_lesson(self.root, 1)
        make_lesson(self.root, 2, "in_progress")
        make_lesson(self.root, 8, "not_started")
        with patch.object(course, "reproduce") as reproduce, patch.object(course, "run") as run:
            course.ci(self.root, "refs/heads/main")
        reproduce.assert_called_once_with(self.root, "lesson-01")
        run.assert_called_once_with(self.root, "lesson-02")

    def test_final_tag_does_not_parse_unrelated_bad_manifest(self):
        make_lesson(self.root)
        other = make_lesson(self.root, 2)
        (other / "submission.json").write_text("not json")
        course.ci(self.root, "refs/tags/v2-l01-final")

    def test_missing_target_still_fails(self):
        make_lesson(self.root)
        with self.assertRaises((OSError, ValueError)):
            course.ci(self.root, "refs/tags/v2-l02-final")

    def test_invalid_and_unstarted_tags_fail(self):
        make_lesson(self.root, status="not_started")
        for ref in ("refs/tags/v2-l01-final", "refs/tags/v2-l33-final", "refs/tags/v2-l01-revision-0"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                course.ci(self.root, ref)

    def test_existing_directory_missing_manifest_is_not_skipped(self):
        (self.root / "lesson-01").mkdir()
        with self.assertRaises(OSError):
            course.ci(self.root)

    def test_empty_pre_release_repository(self):
        with patch.object(course, "run") as run, patch.object(course, "reproduce") as reproduce:
            course.ci(self.root)
        run.assert_not_called()
        reproduce.assert_not_called()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


class ReadingGuideSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source, self.target = base / "release", base / "student"
        for root in (self.source, self.target):
            root.mkdir()
            git(root, "init", "-b", "main")
            git(root, "config", "user.name", "Local test")
            git(root, "config", "user.email", "test@example.invalid")
        make_lesson(self.source)
        (self.source / "docs").mkdir()
        (self.source / "docs/READING_GUIDE.md").write_text("新阅读指南\n", encoding="utf-8")
        (self.source / "docs/WORKFLOW.md").write_text("不要自动覆盖旧说明\n", encoding="utf-8")
        self.publish()
        git(self.target, "remote", "add", "course-release", str(self.source))

    def publish(self):
        git(self.source, "add", ".")
        git(self.source, "commit", "--allow-empty", "-m", "test release")

    def test_new_lesson_receives_guide_and_is_staged(self):
        course.sync(self.target)
        self.assertEqual((self.target / "docs/READING_GUIDE.md").read_text(), "新阅读指南\n")
        paths = git(self.target, "diff", "--cached", "--name-only").splitlines()
        self.assertIn("docs/READING_GUIDE.md", paths)
        self.assertIn("lesson-01/report.md", paths)
        self.assertFalse((self.target / "docs/WORKFLOW.md").exists())

    def test_existing_guide_and_student_lesson_are_not_overwritten(self):
        make_lesson(self.target)
        (self.target / "lesson-01/report.md").write_text("学生作品", encoding="utf-8")
        (self.target / "docs").mkdir()
        (self.target / "docs/READING_GUIDE.md").write_text("学生批注", encoding="utf-8")
        course.sync(self.target)
        self.assertEqual((self.target / "lesson-01/report.md").read_text(), "学生作品")
        self.assertEqual((self.target / "docs/READING_GUIDE.md").read_text(), "学生批注")

    def test_missing_guide_is_added_without_new_lesson(self):
        make_lesson(self.target)
        course.sync(self.target)
        self.assertTrue((self.target / "docs/READING_GUIDE.md").is_file())

    def test_old_release_without_guide_still_syncs(self):
        (self.source / "docs/READING_GUIDE.md").unlink()
        self.publish()
        course.sync(self.target)
        self.assertTrue((self.target / "lesson-01").is_dir())
        self.assertFalse((self.target / "docs/READING_GUIDE.md").exists())

    def test_external_docs_symlink_is_rejected(self):
        outside = self.target.parent / "outside"
        outside.mkdir()
        (self.target / "docs").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            course.sync(self.target)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
