"""Test local publication in disposable directories, without network or deployment."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("publish_student_lesson.py")


class PublishStudentLessonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.target = root / "template", root / "student"
        (self.source / "lesson-01").mkdir(parents=True)
        (self.source / "lesson-01/README.md").write_text("第1课", encoding="utf-8")
        (self.source / "docs").mkdir()
        (self.source / "docs/READING_GUIDE.md").write_text("阅读指南\n", encoding="utf-8")
        (self.target / ".git").mkdir(parents=True)

    def publish(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--source", str(self.source),
                               "--destination", str(self.target), "--lesson", "1"],
                              capture_output=True, text=True, timeout=15)

    def test_new_lesson_includes_missing_guide(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / "docs/READING_GUIDE.md").read_bytes(),
                         (self.source / "docs/READING_GUIDE.md").read_bytes())
        self.assertTrue((self.target / "lesson-01/README.md").is_file())

    def test_existing_guide_is_not_overwritten(self):
        (self.target / "docs").mkdir()
        (self.target / "docs/READING_GUIDE.md").write_text("个人批注", encoding="utf-8")
        self.assertEqual(self.publish().returncode, 0)
        self.assertEqual((self.target / "docs/READING_GUIDE.md").read_text(), "个人批注")

    def test_existing_student_lesson_aborts_without_copying(self):
        (self.target / "lesson-01").mkdir()
        (self.target / "lesson-01/report.md").write_text("学生报告", encoding="utf-8")
        self.assertNotEqual(self.publish().returncode, 0)
        self.assertEqual((self.target / "lesson-01/report.md").read_text(), "学生报告")
        self.assertFalse((self.target / "docs").exists())

    def test_old_template_without_guide_still_works(self):
        (self.source / "docs/READING_GUIDE.md").unlink()
        self.assertEqual(self.publish().returncode, 0)
        self.assertTrue((self.target / "lesson-01").is_dir())

    def test_destination_outside_symlink_rejected_before_copy(self):
        outside = self.target.parent / "outside"
        outside.mkdir()
        (self.target / "docs").symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.publish().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.target / "lesson-01").exists())

    def test_source_guide_symlink_rejected(self):
        guide = self.source / "docs/READING_GUIDE.md"
        guide.unlink()
        guide.symlink_to(self.source / "lesson-01/README.md")
        self.assertNotEqual(self.publish().returncode, 0)
        self.assertFalse((self.target / "lesson-01").exists())


if __name__ == "__main__":
    unittest.main()
