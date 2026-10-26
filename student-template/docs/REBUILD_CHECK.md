# 第1—12课：从结果文件到安全重建

本页只帮助核对已完成作品，不新增一份作业，也不替你决定分析方案。

## 一条结果怎样接到报告

按这个顺序检查：输入与配置 → 程序 → 明细与汇总 → 报告中的数字。

例如，自建程序输出两方案的明细和比较汇总，报告引用其中一行。明细至少能找到工单编号、纳入条件、指标分子与分母、结果及单位；汇总要写评价对象、人数和计算方法。文件名由你的程序决定，不要求改成统一名字。

打开报告中的一个数字，回到对应结果文件，再找到参与计算的明细或输入。两个方案应能按同一编号或同一评价范围对齐；不要只对比截图里的两个总数。

## 提交清单各项负责什么

- `run`：从学生仓库根目录执行的完整命令，必须能生成登记结果。
- `artifacts`：该命令生成、用于支持报告的文件；每个路径从仓库根目录写起。
- `report`：自己的报告路径。输入配置、原始数据、程序与报告不是生成产物，不放进artifacts。

例如，若你的程序实际保存了两方案明细与比较表，应登记这三份结果，而不是仍只登记默认起点的sample或summary。名单、字段和文件数量以本课任务及你的实际程序为准；不要把不存在的示例文件名填进去。

完成报告和必要结果后才将status设为complete。`check`检查清单与文件；它不证明统计解释或模型结论正确。

## 新实验与重建不是一回事

新实验改变配置或种子时，使用新目录，保留原计划和结果。已完成作品的重建，是用保存的相同输入、配置和程序重新计算，应得到相同的确定性产物。

某些工具拒绝覆盖已有目录，这是保护证据，不必为重跑而删除历史实验。可以使用各课SUPPORT中的临时目录脚本；也可以通过下面的CI入口，在一次性副本中重建已登记产物。

## 连续检查两次，不覆盖原作业

将以下代码保存为学生仓库根目录的 `check_rebuild.py`，把lesson改为已完成的课次。它先检查该课，再连续两次调用仅针对该课的复现检查。

```python
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
lesson = "01"  # 改为本次已完成的课次，01至12。
number = int(lesson)
if not 1 <= number <= 12:
    raise ValueError("This guide covers lessons 01 to 12")
lesson = f"{number:02d}"
entry = {11: "scripts/course_l11.py", 12: "scripts/course_l12.py"}.get(number, "scripts/course.py")
subprocess.run([sys.executable, entry, "check", lesson], cwd=ROOT, check=True)
env = dict(os.environ, GITHUB_REF=f"refs/tags/v2-l{lesson}-final")
for _ in range(2):
    subprocess.run([sys.executable, entry, "ci"], cwd=ROOT, env=env, check=True)
```

运行 `python3 check_rebuild.py`。这里的GITHUB_REF只告诉检查器选哪课，不会创建或推送Git标签，不改变成绩。

检查器复制作品，在副本中移除登记输出，再执行submission中的run，逐文件比较内容；原作业保留。不要将check_rebuild.py本身登记为run，否则会递归调用检查器。run仍指向生成分析结果的程序。

第13、14课使用各自SUPPORT的独立检查入口，不套用本页的课次范围。

## 失败时从哪查

1. 文件不存在：核对运行目录、实际输出名和artifacts路径。
2. 复现后仍缺文件：run是否只生成默认起点，而报告引用了另一个程序的结果？
3. 输出不同：核对输入版本、配置、随机种子、模型和计算环境；时间戳等每次变化的运行日志另存，不冒充确定性分析产物。
4. 输出目录冲突：不要删除原证据，检查临时副本是否遗漏了本应登记的生成文件；必要时采用本课的临时目录重建骨架。
5. 检查通过但报告数字对不上：仍需逐条追踪计算，检查不会替你判断结论。

如果曾按结果挑选种子或改方案，应如实保留首次记录和修改理由；重建一致不会让事后选择变成事先计划。
