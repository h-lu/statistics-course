"""核对第1—8课冷读修订中的算例、入口和原始示例输出。

从资料库根目录运行：
python -m unittest discover -s instructor-guide/lesson-01 -p test_student_cold_read_01_08.py -v

这些测试不测量学生阅读能力，不评价学生答案，不修改原始数据。
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
STUDENT = ROOT / "student-template"


def learn(number):
    return (STUDENT / f"lesson-{number:02d}" / "LEARN.md").read_text(encoding="utf-8")


class AddedExamplesTests(unittest.TestCase):
    def test_l01_quartiles_and_nonoverlapping_bins(self):
        waits = [3, 4, 5, 8, 40]
        q1, _, q3 = statistics.quantiles(waits, n=4, method="inclusive")
        self.assertEqual((q1, q3, q3-q1), (4, 8, 4))
        counts = [sum(low <= value < low+10 for value in waits) for low in range(0, 50, 10)]
        self.assertEqual(counts, [4, 0, 0, 0, 1])
        self.assertEqual(sum(counts), len(waits))
        self.assertIn("4、0、0、0、1", learn(1))

    def test_l02_standard_deviation_and_sign(self):
        self.assertAlmostEqual(statistics.pstdev([2, 4, 6]), (8/3)**.5)
        self.assertEqual(statistics.stdev([2, 4, 6]), 2)
        self.assertEqual(statistics.median([2, 3, 4, 31])-statistics.median([8, 9, 10, 13]), -6)
        self.assertIn("1.633分钟", learn(2))
        self.assertIn("同一个插值位置", learn(2))

    def test_l03_completeness_is_relative_to_required_fields(self):
        rows = [(3, 1, "A1"), (None, 1, None), (60, 0, "A1")]
        completion_only = [r for r in rows if r[1] is not None]
        all_three = [r for r in rows if all(v is not None for v in r)]
        self.assertEqual(sum(r[1] for r in completion_only)/len(completion_only), 2/3)
        self.assertEqual(sum(r[1] for r in all_three)/len(all_three), .5)
        self.assertIn("已确认2张", learn(3))
        self.assertIn("另一组字段要求", learn(3))

    def test_l04_two_executable_rules_have_different_purposes(self):
        data = {"X": [4, 5, 5, 6, 40], "Y": [8, 9, 10, 11, 12]}
        self.assertEqual(sorted(data, key=lambda g: statistics.median(data[g])), ["X", "Y"])
        flagged = [g for g, values in data.items() if sum(v > 15 for v in values)/len(values) > .1]
        self.assertEqual(flagged, ["X"])
        self.assertIn("10%是本例另设的管理要求", learn(4))

    def test_l05_loss_scenario_does_not_rewrite_historical_labels(self):
        rows = [("D1", 80, 1), ("D2", 40, 0), ("D3", 40, 1), ("D4", 20, 0)]
        before = copy.deepcopy(rows)
        selected = {r[0] for r in sorted(rows, key=lambda r: (-r[1], r[0]))[:2]}
        loss = sum(3+label*100*.15 if device in selected else label*100 for device, _, label in rows)
        self.assertEqual((selected, loss, rows), ({"D1", "D2"}, 121, before))
        self.assertIn("减少的是损失", learn(5))
        self.assertIn("两次复核", learn(5))

    def test_l06_pooled_weight_not_average_center_percentages(self):
        self.assertEqual((80+60)/(100+300), .35)
        self.assertEqual((.8+.2)/2, .5)
        self.assertEqual((80+20)/(100+100), .5)
        self.assertIn("＝35%", learn(6))

    def test_l07_group_adjustment_targets_all_tickets(self):
        self.assertAlmostEqual((8+12)/(10+20), 2/3)
        self.assertAlmostEqual((20/100)*(8/10)+(80/100)*(12/20), .64)
        self.assertIn("即64%", learn(7))
        self.assertIn("不是这些人会回答的概率", learn(7))

    def test_l08_person_hours_and_total_absence(self):
        self.assertEqual(2*4, 8)
        self.assertEqual(2*4-1, 7)  # Absence is already total person-hours.
        self.assertIn("不要再乘一次人数", learn(8))

    def test_l08_check_accepts_unique_ids_and_rejects_duplicates(self):
        snippets = re.findall(r"```python\n(# cold-read-check\n.*?)\n```", learn(8), re.S)
        self.assertEqual(len(snippets), 1)
        with tempfile.TemporaryDirectory() as folder:
            good = subprocess.run([sys.executable, "-I", "-c", snippets[0]], cwd=folder, capture_output=True, text=True, timeout=15)
            bad_code = snippets[0].replace('["T1", "T2"]', '["T1", "T1"]')
            self.assertNotEqual(snippets[0], bad_code)
            bad = subprocess.run([sys.executable, "-I", "-c", bad_code], cwd=folder, capture_output=True, text=True, timeout=15)
        self.assertEqual(good.returncode, 0)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("工单编号重复", bad.stderr)


class MaterialGuidanceTests(unittest.TestCase):
    def test_all_lessons_link_guide_and_explain_starter_output(self):
        for number in range(1, 9):
            with self.subTest(lesson=number):
                text = (STUDENT / f"lesson-{number:02d}" / "README.md").read_text(encoding="utf-8")
                self.assertIn("../docs/READING_GUIDE.md", text)
                self.assertIn("artifacts/starting_overview.json", text)
                self.assertIn("仅提交这个概览还没有完成作业", text)
                self.assertIn(f"v2-l{number:02d}-final", text)

    def test_reading_guide_differentiates_terminal_paths_and_lists(self):
        text = (STUDENT / "docs/READING_GUIDE.md").read_text(encoding="utf-8")
        for phrase in ("终端", ">>>", "不是分析报告", "不是一个整句字符串", "只有本地提交还没有上传"):
            self.assertIn(phrase, text)
        command = re.search(r'`(\["python", "lesson-01/analysis.py"\])`', text).group(1)
        self.assertEqual(json.loads(command), ["python", "lesson-01/analysis.py"])

    def test_root_ai_guidance_allows_candidates(self):
        text = (STUDENT / "README.md").read_text(encoding="utf-8")
        self.assertIn("AI 可以提出分析对象、问题和方法的候选方案", text)
        self.assertNotIn("不能替你决定分析对象", text)

    def test_current_submission_configs_remain_unfinished(self):
        for number in range(1, 9):
            value = json.loads((STUDENT / f"lesson-{number:02d}/submission.json").read_text())
            self.assertEqual(value["status"], "not_started")
            self.assertEqual(value["artifacts"], [])


class StarterRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.scratch = Path(cls.temp.name)
        cls.hashes = {}
        for group in ("service", "alerts"):
            source = STUDENT / "data" / group
            shutil.copytree(source, cls.scratch / "data" / group)
            for path in source.glob("*.csv"):
                cls.hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        for number in range(1, 9):
            folder = cls.scratch / f"lesson-{number:02d}"
            folder.mkdir()
            shutil.copy2(STUDENT / folder.name / "analysis.py", folder / "analysis.py")

    @classmethod
    def tearDownClass(cls):
        for path, digest in cls.hashes.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise AssertionError(f"原始数据被改动：{path}")


def starter_test(number):
    def test(self):
        directory = self.scratch / f"lesson-{number:02d}"
        outputs = []
        for cwd in (self.scratch, directory):
            run = subprocess.run([sys.executable, str(directory / "analysis.py")], cwd=cwd,
                                 capture_output=True, text=True, check=True, timeout=30)
            self.assertEqual(run.stdout.strip(), f"{directory.name}/artifacts/starting_overview.json")
            outputs.append((directory / "artifacts/starting_overview.json").read_bytes())
        expected = (STUDENT / directory.name / "artifacts/starting_overview.json").read_bytes()
        self.assertEqual(outputs, [expected, expected])
        json.dumps(json.loads(outputs[0]), allow_nan=False)
    return test


for number in range(1, 9):
    setattr(StarterRegressionTests, f"test_starter_{number:02d}", starter_test(number))


if __name__ == "__main__":
    unittest.main()
