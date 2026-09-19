"""核对第1—8课精修中的小例子和说明，不评价学生理解或正式作业。

在完整课程仓库根目录运行：
python -m unittest discover -s instructor-guide/lesson-01 -p test_student_reading_clarifications.py -v

只用标准库；在空临时目录执行讲义片段，不读取项目数据、不访问网络。
"""
import ast
from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
STUDENT = ROOT / "student-template"


def text(number, name="LEARN.md"):
    return (STUDENT / f"lesson-{number:02d}" / name).read_text(encoding="utf-8")


def snippet(number, marker):
    found = re.findall(r"```python\n(# " + re.escape(marker) + r"\n.*?)\n```",
                       text(number), re.S)
    if len(found) != 1:
        raise ValueError(f"第{number}课应有一段{marker}代码")
    return found[0]


def replace_input(code, variable, value):
    """仅替换讲义片段中的一处输入赋值；执行原有判断和输出代码。"""
    nodes = [node for node in ast.parse(code).body
             if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == variable
                     for target in node.targets)]
    if len(nodes) != 1:
        raise ValueError(f"输入赋值不唯一：{variable}")
    node = nodes[0]
    lines = code.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [f"{variable} = {value!r}\n"]
    return "".join(lines)


def run_code(code):
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run([sys.executable, "-I", "-c", code], cwd=directory,
                                capture_output=True, text=True, timeout=15)
        if list(Path(directory).iterdir()):
            raise AssertionError("学习片段不应创建文件")
    return result


class ExecutedExampleTests(unittest.TestCase):
    def test_id_count_changes_with_actual_input(self):
        code = snippet(8, "cold-read-check")
        for size in (0, 1, 2, 3, 10):
            with self.subTest(records=size):
                changed = replace_input(code, "ticket_ids", [f"T{i}" for i in range(size)])
                result = run_code(changed)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(),
                                 f"编号检查通过：{size}张工单没有重复编号")

    def test_duplicate_ids_fail_instead_of_printing_success(self):
        code = snippet(8, "cold-read-check")
        for ids in (["T1", "T1"], ["T1", "T2", "T1"]):
            with self.subTest(ids=ids):
                result = run_code(replace_input(code, "ticket_ids", ids))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("工单编号重复", result.stderr)
                self.assertNotIn("检查通过", result.stdout)

    def test_same_ranking_rule_can_select_different_devices(self):
        code = snippet(5, "learning-example")
        original = run_code(code)
        changed = run_code(replace_input(code, "rows",
                           [("D1", 10, 1), ("D2", 20, 0),
                            ("D3", 90, 1), ("D4", 80, 0)]))
        for result in (original, changed):
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(original.stdout)["selected"], ["D1", "D2"])
        self.assertEqual(json.loads(changed.stdout)["selected"], ["D3", "D4"])
        self.assertIn("10、20、90、80", text(5))
        self.assertIn("同一排序规则就会选D3、D4", text(5))

    def test_ranking_does_not_change_when_only_labels_change(self):
        code = snippet(5, "learning-example")
        result = run_code(replace_input(code, "rows",
                          [("D1", 80, 0), ("D2", 40, 1),
                           ("D3", 40, 0), ("D4", 20, 1)]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["selected"], ["D1", "D2"])

    def test_common_weight_direction_and_magnitude_are_distinct(self):
        # 核算正文另设的层内差值；不是对正式项目中心排序的测试。
        first, second = Fraction(20, 100), Fraction(5, 100)
        difference = lambda w: (1-w)*first+w*second
        self.assertEqual(difference(Fraction(1, 2)), Fraction(125, 1000))
        self.assertEqual(difference(Fraction(3, 4)), Fraction(875, 10000))
        for weight in (Fraction(0), Fraction(1, 2), Fraction(3, 4), Fraction(1)):
            self.assertGreater(difference(weight), 0)
        self.assertIn("12.5个百分点", text(6))
        self.assertIn("8.75个百分点", text(6))

    def test_two_time_periods_are_appended_not_inner_joined(self):
        # 另设最小表核算两种操作，不是验收学生的正式连接程序。
        first = [{"ticket_id": "J1", "wait": 2}, {"ticket_id": "J2", "wait": 4}]
        second = [{"ticket_id": "J3", "wait": 6}]
        appended = first + second
        common = [left for left in first for right in second
                  if left["ticket_id"] == right["ticket_id"]]
        self.assertEqual(len(appended), 3)
        self.assertEqual(len(common), 0)
        self.assertEqual(sum(row["wait"] for row in appended)/len(appended), 4)
        self.assertEqual(3600+1200, 4800)
        self.assertIn("3,600＋1,200＝4,800", text(8))


class WordingConsistencyTests(unittest.TestCase):
    def test_l01_prompts_are_conditional_on_chosen_analysis(self):
        report = text(1, "report.md")
        for phrase in ("研究等待时间时", "使用满意度资料时", "若使用分位数", "图表或分组表"):
            self.assertIn(phrase, report)
        self.assertIn("至少一种合理的替代解释或统计口径", report)

    def test_l02_reasons_precede_results_without_banning_exploration(self):
        self.assertIn("它为什么与问题有关", text(2))
        self.assertIn("计算后发现的新问题", text(2))
        self.assertIn("两到三种", text(2, "README.md"))
        self.assertIn("使用者的问题", text(2, "report.md"))

    def test_l03_completeness_summary_matches_definition(self):
        self.assertIn("本次分析所需字段", text(3))
        self.assertIn("分别按每项指标所需字段选择完整记录", text(3))
        self.assertIn("统一使用等待、办结和窗口都完整的记录", text(3))
        self.assertNotIn("按指标选择记录与完整案例分析", text(3))

    def test_l04_thresholds_have_different_units_and_declared_basis(self):
        for phrase in ("15分钟用来判断一张工单", "10%用来判断一组工单", "管理假设", "评价没有改变也有意义"):
            self.assertIn(phrase, text(4))
        self.assertIn("题目给定要求和自行提出的假设", text(4, "report.md"))

    def test_l05_optional_probability_model_and_fixed_rule_align(self):
        self.assertIn("不要求先建立故障概率模型", text(5))
        self.assertIn("若另外估计故障概率", text(5, "README.md"))
        self.assertIn("名单仍可随当日分数和名额变化", text(5, "README.md"))
        self.assertIn("同一规则", text(5, "report.md"))

    def test_l07_mechanism_is_an_assumption_not_an_entry_requirement(self):
        self.assertIn("不要求先确定真实的缺失机制", text(7))
        self.assertIn("无法验证的假设要保留为使用条件", text(7))
        self.assertIn("至少两种不同的缺失评价假设", text(7, "README.md"))
        self.assertIn("不要求实际联系任何人", text(7, "README.md"))

    def test_dictionary_distinguishes_identifier_and_missing_ratings(self):
        dictionary = (STUDENT / "data/service/README.md").read_text(encoding="utf-8")
        for phrase in ("整理后的工单表中，ticket_id可作主键", "原始导出允许同一工单",
                       "空白表示没有取得评价", "0表示未受邀", "1表示受邀后无回答", "单列待核实"):
            self.assertIn(phrase, dictionary)
        self.assertNotIn("空白表示没有回答", dictionary)

    def test_l08_append_is_named_in_all_three_documents(self):
        for name in ("README.md", "LEARN.md", "report.md"):
            with self.subTest(file=name):
                self.assertIn("按行追加", text(8, name))
                self.assertIn("连接", text(8, name))
        self.assertIn("不检查编号是否缺失", text(8))

    def test_l08_revision_plan_is_conditional(self):
        self.assertIn("若计划修订", text(8, "README.md"))
        self.assertIn("若计划修订", text(8, "report.md"))
        self.assertIn("不修订时说明保留原版即可", text(8, "report.md"))
        self.assertIn("第3—8课选择一件", text(8, "README.md"))

    def test_assessment_does_not_add_unlearned_methods(self):
        assessment = (STUDENT / "docs/ASSESSMENT.md").read_text(encoding="utf-8")
        self.assertIn("不表示前8课每份报告都必须加入置信区间或显著性检验", assessment)
        self.assertIn("结果核对仍须完成", assessment)
        self.assertIn("项目：0.8分", assessment)
        self.assertIn("每项最高1分", assessment)

    def test_knowledge_check_preserves_ungraded_intro_lessons(self):
        guide = (STUDENT / "docs/KNOWLEDGE_CHECK.md").read_text(encoding="utf-8")
        self.assertIn("第1、2课仍须完成自查，但不计分", guide)
        self.assertIn("从第3课起", guide)
        self.assertIn("ASSESSMENT.md", guide)
        self.assertIn("正确率和信心只用于反馈", guide)


if __name__ == "__main__":
    unittest.main()
