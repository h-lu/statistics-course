from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import course_status
except ImportError:
    import course_status


class CourseStatusTests(unittest.TestCase):
    def test_roster_requires_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roster.csv"
            path.write_text(
                "student_id,gitea_login,repo_owner,repo_name\n"
                "1,s01,s01,statistics-2026\n",
                encoding="utf-8",
            )
            self.assertEqual(course_status.read_roster(path)[0]["gitea_login"], "s01")

    @patch.object(course_status, "api_get")
    def test_green_requires_signed_complete_and_success_status(self, api_get) -> None:
        signed = base64.b64encode(
            json.dumps({"status": "complete"}).encode("utf-8")
        ).decode("ascii")
        api_get.side_effect = [
            (200, {"name": "statistics-2026"}),
            (200, [{"ref": "refs/tags/s01-final"}]),
            (200, {"content": signed}),
            (200, {"state": "success", "sha": "1234567890abcdef"}),
        ]
        result = course_status.status_for(
            "https://example.test/gitea",
            "token",
            {"repo_owner": "s01", "repo_name": "statistics-2026"},
            "s01-final",
        )
        self.assertEqual(result["light"], "GREEN")
        self.assertEqual(result["signed"], "complete")
        self.assertEqual(result["sha"], "1234567890abcdef")

    def test_v2_mapping_covers_whole_semester(self):
        self.assertEqual(len(course_status.TAG_BY_LESSON), 32)
        self.assertEqual(course_status.TAG_BY_LESSON["lesson-32"], "v2-l32-final")

    @patch.object(course_status, "api_get")
    def test_v2_wrong_lesson_cannot_be_green(self, api_get):
        signed = base64.b64encode(json.dumps({"status": "complete", "lesson": "lesson-01"}).encode()).decode()
        api_get.side_effect = [(200, {}), (200, [{}]), (200, {"content": signed}), (200, {"state": "success", "sha": "abc"})]
        result = course_status.status_for("https://example.test", "token", {"repo_owner": "s01", "repo_name": "course"}, "v2-l32-final")
        self.assertEqual(result["light"], "RED")
        self.assertEqual(result["signed"], "wrong_lesson")

    @patch.object(course_status, "api_get")
    def test_green_ci_is_red_when_tag_is_not_signed_complete(self, api_get) -> None:
        unsigned = base64.b64encode(
            json.dumps({"status": "in_progress"}).encode("utf-8")
        ).decode("ascii")
        api_get.side_effect = [
            (200, {"name": "statistics-2026"}),
            (200, [{"ref": "refs/tags/s01-final"}]),
            (200, {"content": unsigned}),
            (200, {"state": "success", "sha": "1234567890abcdef"}),
        ]
        result = course_status.status_for(
            "https://example.test/gitea",
            "token",
            {"repo_owner": "s01", "repo_name": "statistics-2026"},
            "s01-final",
        )
        self.assertEqual(result["light"], "RED")
        self.assertEqual(result["signed"], "in_progress")

    @patch.object(course_status, "api_get")
    def test_missing_tag_is_red(self, api_get) -> None:
        api_get.side_effect = [(200, {}), (404, None)]
        result = course_status.status_for(
            "https://example.test/gitea",
            "token",
            {"repo_owner": "s01", "repo_name": "statistics-2026"},
            "s01-final",
        )
        self.assertEqual(result["light"], "RED")

    @patch.object(course_status, "api_get")
    def test_missing_repo_has_complete_output_shape(self, api_get) -> None:
        api_get.return_value = (404, None)
        result = course_status.status_for(
            "https://example.test/gitea",
            "token",
            {"repo_owner": "s01", "repo_name": "statistics-2026"},
            "s01-final",
        )
        self.assertEqual(result["light"], "RED")
        self.assertEqual(result["signed"], "-")


if __name__ == "__main__":
    unittest.main()
