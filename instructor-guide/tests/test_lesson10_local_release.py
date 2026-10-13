"""Real local Git fixtures; preserve old lessons and never contact student servers."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

TEMPLATE = Path(__file__).resolve().parents[2] / "student-template"
PUBLISHER = TEMPLATE.parent / "instructor-guide/scripts/publish_student_lesson.py"
SHELL_PUBLISHER = PUBLISHER.with_name("publish-statistics-lesson.sh")
SPEC = importlib.util.spec_from_file_location("course_l10_release_tests", TEMPLATE / "scripts/course.py")
course = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(course)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.DEVNULL).decode()


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


class Lesson10LocalReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.target = root / "release", root / "student"
        shutil.copytree(TEMPLATE, self.source,
                        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        self.target.mkdir()
        for folder in (self.source, self.target):
            git(folder, "init", "-b", "main")
            git(folder, "config", "user.name", "Isolated test fixture")
            git(folder, "config", "user.email", "fixture@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "isolated local release")
        git(self.target, "remote", "add", "course-release", str(self.source))
        for number in range(1, 10):
            lesson = self.target / f"lesson-{number:02d}"
            lesson.mkdir()
            for name in ("README.md", "LEARN.md", "analysis.py", "report.md", "submission.json"):
                (lesson / name).write_text(f"student-owned {number} {name}\n", encoding="utf-8")
        (self.target / "scripts").mkdir()
        old = (TEMPLATE / "scripts/course.py").read_bytes().replace(
            b"ACTIVE_LESSONS = tuple(range(1, 11))", b"ACTIVE_LESSONS = tuple(range(1, 10))"
        )
        (self.target / "scripts/course.py").write_bytes(old + b"\n# student local annotation\n")
        (self.target / "docs").mkdir()
        (self.target / "docs/READING_GUIDE.md").write_text("student annotations\n")
        (self.target / "data/service").mkdir(parents=True)
        (self.target / "data/service/tickets.csv").write_text("student-owned data\n")
        git(self.target, "add", ".")
        git(self.target, "commit", "-m", "isolated student originals")
        (self.target / "lesson-03/report.md").write_text("uncommitted student revision\n")
        (self.target / "lesson-09/custom.txt").write_text("untracked student result\n")
        self.before = snapshot(self.target)

    def assert_originals_unchanged(self):
        after = snapshot(self.target)
        self.assertEqual(self.before, {p: after[p] for p in self.before})
        for n in range(1, 10):
            prefix = f"lesson-{n:02d}/"
            self.assertEqual({p: h for p, h in self.before.items() if p.startswith(prefix)},
                             {p: h for p, h in after.items() if p.startswith(prefix)})

    def invoke_runner(self, action):
        return subprocess.run([sys.executable, "scripts/course_l10.py", action, "10"],
                              cwd=self.target, capture_output=True, text=True, timeout=30)

    def test_sync_adds10_dependencies_and_second_sync_skips_the_entire_lesson(self):
        course.sync(self.target)
        self.assert_originals_unchanged()
        self.assertTrue((self.target / "lesson-10/data/demand.csv").is_file())
        self.assertTrue((self.target / "lesson-10/capacity_tools.py").is_file())
        self.assertTrue((self.target / "scripts/course_l10.py").is_file())
        self.assertFalse((self.target / "lesson-11").exists())
        for action in ("start", "run"):
            result = self.invoke_runner(action)
            self.assertEqual(result.returncode, 0, result.stderr)
        # This is a synthetic delivery-interface test, not a completed student project.
        meta = self.target / "lesson-10/submission.json"
        obj = json.loads(meta.read_text())
        obj.update(status="complete", artifacts=["lesson-10/artifacts/example.json"])
        meta.write_text(json.dumps(obj))
        (self.target / "lesson-10/report.md").write_text("synthetic interface fixture\n")
        result = self.invoke_runner("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_originals_unchanged()
        old_cli = subprocess.run([sys.executable, "scripts/course.py", "run", "10"],
                                 cwd=self.target, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(old_cli.returncode, 0)
        (self.target / "lesson-10/README.md").write_text("student lesson 10 edits\n")
        (self.target / "lesson-10/capacity_tools.py").unlink()
        before_second = snapshot(self.target)
        index_before = git(self.target, "diff", "--cached", "--binary")
        course.sync(self.target)
        self.assertEqual(snapshot(self.target), before_second)
        self.assertEqual(git(self.target, "diff", "--cached", "--binary"), index_before)
        self.assertFalse((self.target / "lesson-10/capacity_tools.py").exists())

    def test_shared_code_conflict_fails_before_any_file_or_index_change(self):
        (self.target / "scripts/course_l10.py").write_text("student incompatible implementation\n")
        before, staged = snapshot(self.target), git(self.target, "diff", "--cached", "--binary")
        with self.assertRaisesRegex(ValueError, "共享代码与发布版本不兼容"):
            course.sync(self.target)
        self.assertEqual(snapshot(self.target), before)
        self.assertEqual(git(self.target, "diff", "--cached", "--binary"), staged)
        self.assertFalse((self.target / "lesson-10").exists())

    def test_missing_released_dependency_fails_without_partial_sync(self):
        (self.source / "scripts/course_l10.py").unlink()
        git(self.source, "add", "-u")
        git(self.source, "commit", "-m", "isolated missing dependency")
        before, staged = snapshot(self.target), git(self.target, "diff", "--cached", "--binary")
        with self.assertRaisesRegex(ValueError, "缺少发布依赖"):
            course.sync(self.target)
        self.assertEqual(snapshot(self.target), before)
        self.assertEqual(git(self.target, "diff", "--cached", "--binary"), staged)
        self.assertFalse((self.target / "lesson-10").exists())

    def test_existing10_adds_missing_support_without_repairing_lesson_files(self):
        (self.target / "lesson-10").mkdir()
        (self.target / "lesson-10/report.md").write_text("existing partial student lesson\n")
        course.sync(self.target)
        self.assert_originals_unchanged()
        self.assertEqual((self.target / "scripts/course_l10.py").read_bytes(),
                         (self.source / "scripts/course_l10.py").read_bytes())
        self.assertEqual({p.name for p in (self.target / "lesson-10").iterdir()}, {"report.md"})

    def test_existing10_still_rejects_conflicting_shared_code_without_writes(self):
        (self.target / "lesson-10").mkdir()
        (self.target / "lesson-10/report.md").write_text("student partial work\n")
        (self.target / "scripts/course_l10.py").write_text("student incompatible runtime\n")
        before, staged = snapshot(self.target), git(self.target, "diff", "--cached", "--binary")
        with self.assertRaisesRegex(ValueError, "共享代码与发布版本不兼容"):
            course.sync(self.target)
        self.assertEqual(snapshot(self.target), before)
        self.assertEqual(git(self.target, "diff", "--cached", "--binary"), staged)

    def test_tmp_bootstrap_sync_destination_and_repeat_preserve_old_client(self):
        bootstrap = '''set -eu
git fetch course-release main
lesson10_bootstrap=$(mktemp "${TMPDIR:-/tmp}/course-l10.XXXXXX")
trap 'rm -f "$lesson10_bootstrap"' EXIT
git show FETCH_HEAD:scripts/course_l10.py > "$lesson10_bootstrap"
python3 "$lesson10_bootstrap" sync --destination "$PWD"
'''
        for _ in range(2):
            result = subprocess.run(["sh", "-c", bootstrap], cwd=self.target,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_originals_unchanged()
            if _ == 0:
                (self.target / "lesson-10/README.md").write_text("student current lesson edits\n")
                self.after_first = snapshot(self.target)
            else:
                self.assertEqual(snapshot(self.target), self.after_first)
        self.assertEqual(self.invoke_runner("start").returncode, 0)
        self.assertEqual(self.invoke_runner("run").returncode, 0)
        rejected = subprocess.run([sys.executable, "scripts/course_l10.py", "run", "10",
                                   "--destination", str(self.target)], cwd=self.target,
                                  capture_output=True, text=True, timeout=15)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("仅用于sync", rejected.stderr)

    def test_local_publisher_and_shell_dry_run_keep_old_lessons(self):
        args = ["--source", str(self.source), "--destination", str(self.target), "--lesson", "10"]
        dry = subprocess.run(["sh", str(SHELL_PUBLISHER), "--dry-run", *args],
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(snapshot(self.target), self.before)
        result = subprocess.run([sys.executable, str(PUBLISHER), *args],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("course_l10.py", result.stdout)
        self.assert_originals_unchanged()
        self.assertEqual(self.invoke_runner("start").returncode, 0)
        self.assertEqual(self.invoke_runner("run").returncode, 0)
        before_second = snapshot(self.target)
        (self.source / "lesson-10/new-source-only.txt").write_text("do not fill existing lesson\n")
        result = subprocess.run([sys.executable, str(PUBLISHER), *args],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot(self.target), before_second)

    def test_local_publisher_shared_conflict_has_no_partial_copy(self):
        (self.target / "scripts/course_l10.py").write_text("incompatible local code\n")
        before = snapshot(self.target)
        result = subprocess.run([sys.executable, str(PUBLISHER), "--source", str(self.source),
                                 "--destination", str(self.target), "--lesson", "10"],
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("共享代码与发布版本不兼容", result.stderr)
        self.assertEqual(snapshot(self.target), before)

    def test_local_publisher_existing10_adds_missing_runtime_only(self):
        (self.target / "lesson-10").mkdir()
        (self.target / "lesson-10/report.md").write_text("student partial work\n")
        result = subprocess.run([sys.executable, str(PUBLISHER), "--source", str(self.source),
                                 "--destination", str(self.target), "--lesson", "10"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_originals_unchanged()
        self.assertTrue((self.target / "scripts/course_l10.py").is_file())
        self.assertEqual({p.name for p in (self.target / "lesson-10").iterdir()}, {"report.md"})


if __name__ == "__main__":
    unittest.main()
