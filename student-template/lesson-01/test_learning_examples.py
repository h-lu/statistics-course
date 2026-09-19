"""核算已发布的第1—8课学习例子；不检查或评价学生项目答案。

从学生仓库根目录运行：
    python -m unittest discover -s lesson-01 -p test_learning_examples.py -v
未发布的课次跳过；仅运行LEARN中的独立小例子，不读取项目CSV。
"""
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = re.compile(r"```python\n(# learning-example\n.*?)\n```", re.S)
EXPECTED = {
    1: {"tickets": 5, "people": 4, "all_mean": 12, "all_median": 5,
        "served_n": 4, "served_mean": 5, "served_median": 4.5, "abandon_rate": .2},
    2: {"mean_difference": 0, "median_difference": -6,
        "p90_x": 22.9, "p90_y": 12.1, "p90_difference": 10.8},
    3: {"target_n": 3, "wait_n": 2, "wait_mean": 31.5,
        "completion_rate": 2/3, "complete_case_rate": .5, "known_window_n": 2},
    4: {"x": {"mean": 12, "median": 5, "iqr": 1, "over15": .2},
        "y": {"mean": 10, "median": 10, "iqr": 2, "over15": 0},
        "x_mean_after_exclusion": 5, "x_over15_after_exclusion": 0},
    5: {"selected": ["D1", "D2"], "ecdf40": .75,
        "counts": {"TP": 1, "FP": 1, "FN": 1, "TN": 1}, "loss85": 121,
        "large_fpr": 14/90, "large_list_nonfault": .7,
        "large_loss80": 580, "large_loss85": 550},
    6: {"actual": {"A": .66, "B": .74}, "w50": {"A": .75, "B": .65},
        "w75": {"A": .675, "B": .575}, "endpoint_differences": [.1, .1]},
    7: {"invitation": .5, "response_invited": .8, "response_all": .4,
        "happy_respondents": .8, "bounds": [.32, .92],
        "scenarios": [.47, .62, .77], "q_for70": 38/60, "two_process": [.60, .76]},
    8: {"ticket_mean": 6, "expanded_mean": 4, "wrong_sum_over_distinct": 8,
        "contact_minutes": 16, "planned_day_hours": 8, "wrong_ticket_hours": 16,
        "wrong_contact_hours": 32, "all_mean_with_unknown": 6,
        "all_minutes_with_unknown": 21, "two_day_plan": 16},
}


def published(root):
    """只枚举已发布目录；目录存在而学习文件缺失时不应静默跳过。"""
    return [n for n in range(1, 9) if (root / f"lesson-{n:02d}").is_dir()]


def example_code(root, number):
    path = root / f"lesson-{number:02d}" / "LEARN.md"
    snippets = EXAMPLE.findall(path.read_text(encoding="utf-8"))
    if len(snippets) != 1:
        raise ValueError(f"{path}: 应有且仅有一段标记的学习核算代码")
    return snippets[0]


def reject_constant(value):
    raise ValueError(f"非有限JSON数值：{value}")


class LearningExamples(unittest.TestCase):
    def available(self, number):
        if number not in published(ROOT):
            self.skipTest(f"第{number}课尚未发布")
        return ROOT / f"lesson-{number:02d}"

    def assert_values(self, actual, expected):
        if isinstance(expected, dict):
            self.assertIsInstance(actual, dict)
            self.assertEqual(set(actual), set(expected))
            for key, value in expected.items():
                with self.subTest(field=key):
                    self.assert_values(actual[key], value)
        elif isinstance(expected, list):
            self.assertIsInstance(actual, list)
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.assert_values(left, right)
        elif isinstance(expected, (float, int)):
            self.assertIsInstance(actual, (float, int))
            self.assertTrue(math.isfinite(actual))
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10),
                            f"{actual} != {expected}")
        else:
            self.assertEqual(actual, expected)


def numeric_test(number):
    def test(self):
        self.available(number)
        code = example_code(ROOT, number)
        # 在空临时目录运行，只允许例子通过标准输出给出核算值。
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.run([sys.executable, "-I", "-c", code], cwd=folder,
                                     capture_output=True, text=True, check=True, timeout=15)
            self.assertEqual(list(Path(folder).iterdir()), [])
        result = json.loads(process.stdout, parse_constant=reject_constant)
        self.assert_values(result, EXPECTED[number])
    return test


def material_test(number):
    def test(self):
        directory = self.available(number)
        documents = {name: (directory / name).read_text(encoding="utf-8")
                     for name in ("README.md", "LEARN.md", "report.md")}
        readme = documents["README.md"]
        self.assertIn(f"# 第{number}课", readme)
        self.assertIn(f"python scripts/course.py run {number:02d}", readme)
        self.assertIn(f"python scripts/course.py check {number:02d}", readme)
        self.assertIn(f"v2-l{number:02d}-final", readme)
        self.assertIn("check` 只检查", readme)
        self.assertIn("不会重新运行分析", readme)
        self.assertIn("教学合成数据", readme)
        self.assertIn("不是已完成报告", documents["report.md"])
        for name, text in documents.items():
            with self.subTest(document=name):
                self.assertTrue(text.endswith("\n"))
                self.assertEqual(text.count("```") % 2, 0)
                for forbidden in ("instructor-guide/", "REFERENCE.md", "RUNBOOK.md",
                                  "question-bank/", "后台审核", "教师参考答案"):
                    self.assertNotIn(forbidden, text)
    return test


for number in range(1, 9):
    setattr(LearningExamples, f"test_example_{number:02d}", numeric_test(number))
    setattr(LearningExamples, f"test_material_{number:02d}", material_test(number))


class PublishedSubsetTests(unittest.TestCase):
    def test_one_lesson_does_not_require_future_lessons(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lesson-01").mkdir()
            self.assertEqual(published(root), [1])
            self.assertFalse((root / "lesson-02").exists())

    def test_existing_lesson_with_missing_material_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lesson-01").mkdir()
            with self.assertRaises(FileNotFoundError):
                example_code(root, 1)


if __name__ == "__main__":
    unittest.main()
