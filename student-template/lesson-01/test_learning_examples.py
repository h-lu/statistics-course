"""核算已发布的第1—8课学习例子；不检查或评价学生项目答案。

从学生仓库根目录运行：
    python -m unittest discover -s lesson-01 -p test_learning_examples.py -v
未发布的课次跳过；运行LEARN或experiments.py中的独立小例子，不读取项目CSV。
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
    8: {"duplication": [6, 4, 8, 16],
        "unmatched": {"counts": [3, 2, 1], "means": [[6, 6], [14, 6]]},
        "revision": {"R1": [10, "9", False, 8], "R2": [2, "2", True, None]},
        "staffing": {"hours": [16, 8], "minutes": 22,
                     "days": [[2, 16, 8, 16/60, 1/30],
                              [0, 0, 8, 0, 0], [1, 6, None, .1, None]]}},
}

# 第8课微例各自构造数据；复制脚本到无CSV的临时目录，调用函数而非项目入口。
EXPERIMENT_08 = '''import json, runpy
cases = runpy.run_path("experiments.py")
d = cases["duplication"]()
u = cases["unmatched"]()
r = cases["revision"]()
s = cases["staffing"]()
print(json.dumps({
    "duplication": [d["ticket_mean"], d["expanded_mean"],
                    d["expanded_sum_over_distinct_tickets"], d["staff_minutes"]],
    "unmatched": {"counts": [u["left_n"], u["inner_n"], len(u["unmatched"])],
                  "means": [[a["all_ticket_mean"], a["inner_join_mean"]]
                            for a in u["alternatives"]]},
    "revision": {a["ticket"]: [a["numeric_latest"], a["lexical_latest"],
                               a["conflict"], a["published_wait"]]
                 for a in r["selection"]},
    "staffing": {"hours": [s["known_plan_hours"], s["plan_hours_on_activity_days_only"]],
                 "minutes": s["source_staff_minutes"],
                 "days": [[a["tickets"], a["staff_minutes"], a["planned_person_hours"],
                           a["contact_person_hours"], a["recorded_work_over_plan"]]
                          for a in s["window_days"]]}
}, allow_nan=False))
'''


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
        elif isinstance(expected, bool):
            self.assertIs(actual, expected)
        elif isinstance(expected, (float, int)):
            self.assertIsInstance(actual, (float, int))
            self.assertTrue(math.isfinite(actual))
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10),
                            f"{actual} != {expected}")
        else:
            self.assertEqual(actual, expected)


def numeric_test(number):
    def test(self):
        directory = self.available(number)
        code = EXPERIMENT_08 if number == 8 else example_code(ROOT, number)
        # 在隔离临时目录运行，只允许例子通过标准输出给出核算值。
        with tempfile.TemporaryDirectory() as folder:
            files = []
            if number == 8:
                script = Path(folder) / "experiments.py"
                script.write_bytes((directory / "experiments.py").read_bytes())
                files = [script]
            process = subprocess.run([sys.executable, "-I", "-c", code], cwd=folder,
                                     capture_output=True, text=True, check=True, timeout=15)
            self.assertEqual(list(Path(folder).iterdir()), files)
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
        commands = {(action, int(lesson)) for action, lesson in re.findall(
            r"\bpython(?:3)?\s+scripts/course\.py\s+(run|check)\s+(\d+)\b", readme)}
        self.assertIn(("run", number), commands)
        self.assertIn(("check", number), commands)
        self.assertIn("教学合成", readme)
        for name, text in documents.items():
            with self.subTest(document=name):
                self.assertTrue(text.endswith("\n"))
                self.assertEqual(text.count("```") % 2, 0)
                for forbidden in ("instructor-guide/", "REFERENCE.md", "RUNBOOK.md",
                                  "question-bank/"):
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
