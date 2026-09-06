from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("course", Path(__file__).parents[1] / "scripts/course.py")
course = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(course)


class CourseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lesson = self.root / "lesson-01"
        self.lesson.mkdir()
        (self.lesson / "artifacts").mkdir()
        (self.lesson / "report.md").write_text("# 一个统计报告\n结论有证据，含适用范围。", encoding="utf-8")
        (self.lesson / "artifacts/evidence.json").write_text('{"count": 10}\n', encoding="utf-8")
        self.obj = {
            "lesson": "lesson-01", "status": "not_started",
            "report": "lesson-01/report.md", "artifacts": [],
            "run": ["python", "lesson-01/analysis.py"],
        }
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        (self.lesson / "submission.json").write_text(json.dumps(self.obj), encoding="utf-8")

    def finish(self):
        self.obj.update(status="complete", artifacts=["lesson-01/artifacts/evidence.json"])
        self.save()

    def test_initial_template_is_not_complete(self):
        with self.assertRaisesRegex(ValueError, "complete"):
            course.check(self.root, "lesson-01")

    def test_start_does_not_claim_completion(self):
        course.start(self.root, "lesson-01")
        self.assertEqual(course.manifest(self.root, "lesson-01")["status"], "in_progress")

    def test_complete_accepts_open_evidence_interface(self):
        self.finish()
        self.assertEqual(course.check(self.root, "lesson-01")["status"], "complete")

    def test_empty_artifact_list_is_not_delivery(self):
        self.obj["status"] = "complete"
        self.save()
        with self.assertRaisesRegex(ValueError, "结果文件"):
            course.check(self.root, "lesson-01")

    def test_nonexistent_evidence_rejected(self):
        self.finish()
        self.obj["artifacts"] = ["lesson-01/artifacts/missing.csv"]
        self.save()
        with self.assertRaisesRegex(ValueError, "不存在"):
            course.check(self.root, "lesson-01")

    def test_report_cannot_be_its_own_evidence(self):
        self.finish()
        self.obj["artifacts"] = [self.obj["report"]]
        self.save()
        with self.assertRaisesRegex(ValueError, "报告本身"):
            course.check(self.root, "lesson-01")

    def test_paths_stay_in_repository(self):
        for path in ["../outside.txt", "/tmp/outside.txt", ""]:
            with self.assertRaises(ValueError):
                course.inside(self.root, path)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                course.inside(self.root, "escape/outside.txt")

    def test_lesson_range_and_tag_format(self):
        self.assertEqual(course.lesson_name("lesson-03"), "lesson-03")
        self.assertIsNotNone(course.TAG.fullmatch("v2-l32-revision-1"))
        for value in [0, 33, "../01"]:
            with self.assertRaises(ValueError):
                course.lesson_name(value)

    @patch.object(course, "run")
    def test_reproducibility_detects_changed_evidence(self, run):
        self.finish()
        def alter(root, lesson):
            (root / lesson / "artifacts/evidence.json").write_text('{"count": 11}\n')
        run.side_effect = alter
        with self.assertRaisesRegex(ValueError, "已提交文件不同"):
            course.reproduce(self.root, "lesson-01")

    @patch.object(course, "run")
    def test_reproducible_evidence_accepted(self, run):
        self.finish()
        run.side_effect = lambda root, lesson: (root / lesson / "artifacts/evidence.json").write_text('{"count": 10}\n')
        course.reproduce(self.root, "lesson-01")
        run.assert_called_once()

    @patch.object(course, "run")
    def test_noop_does_not_reuse_submitted_outputs(self, run):
        self.finish()
        with self.assertRaisesRegex(ValueError, "不存在"):
            course.reproduce(self.root, "lesson-01")
        self.assertEqual((self.lesson / "artifacts/evidence.json").read_text(), '{"count": 10}\n')

    def make_remaining_manifests(self):
        for n in range(2, 33):
            lesson = f"lesson-{n:02d}"
            (self.root / lesson).mkdir()
            obj = dict(self.obj, lesson=lesson, status="not_started", artifacts=[])
            (self.root / lesson / "submission.json").write_text(json.dumps(obj))

    @patch.object(course, "reproduce")
    @patch.object(course, "run")
    def test_final_tag_checks_only_selected_lesson(self, run, reproduce):
        self.finish()
        self.make_remaining_manifests()
        course.ci(self.root, "refs/tags/v2-l01-final")
        reproduce.assert_called_once_with(self.root, "lesson-01")
        run.assert_not_called()

    def test_final_tag_cannot_claim_unstarted_lesson(self):
        self.make_remaining_manifests()
        with self.assertRaisesRegex(ValueError, "complete"):
            course.ci(self.root, "refs/tags/v2-l02-final")

    def test_real_subprocess_rebuilds_evidence_for_final_tag(self):
        self.finish()
        self.make_remaining_manifests()
        (self.lesson / "analysis.py").write_text(
            "from pathlib import Path\n"
            "Path('lesson-01/artifacts/evidence.json').write_text('{\"count\": 10}\\n')\n"
        )
        course.ci(self.root, "refs/tags/v2-l01-final")


if __name__ == "__main__":
    unittest.main()
