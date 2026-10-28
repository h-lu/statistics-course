# 第14课｜运行帮助

这是可选帮助：基础小例用于建立可信起点，标准任务仍由你决定规划依据、精度优先级与分配方案，提高问题见EXERCISES第四部分。遇到文件问题时，可按“核对配置→追踪一轮→重复重建→提交”排查。沿用前课Python环境，所有命令在学生仓库根目录执行。

## 一、先算预算，再运行

默认 `lesson-14/config.json` 为：

```json
{
  "n_A": 128,
  "n_B": 32,
  "repetitions": 500,
  "seed": 1401,
  "budget": 240
}
```

|字段|含义|核对什么|
|---|---|---|
|`n_A`、`n_B`|一次调查各层人数|整数，各层至少2人，不超过3200、800|
|`repetitions`|重复调查次数|即 $R$ ，至少2；不是一次调查人数|
|`seed`|抽样种子|非负整数，固定以便复算|
|`budget`|邀请费用上限|需要满足 $n_A+3n_B\le\mathrm{budget}$ |

默认费用 $128+3\times32=224$ ，不是240。`budget` 只作上限检查，不会自动优化人数，也不表示实际花掉了全部预算。

## 二、第一次运行与文件顺序

```sh
python3 lesson-14/analysis.py
```

默认结果在 `lesson-14/artifacts/baseline/`。已有同名目录时程序拒绝覆盖；可以直接读取旧结果，或另选新目录做新实验。

|文件|内容|推荐读法|
|---|---|---|
|`plan.json`|完整配置|先核人数、轮数、预算|
|`first_sample.csv`|第一轮受访者，一行一人|按group数人数和有需求人数|
|`trials.csv`|重复调查，一行一轮|对照组内、加权及直接合并估计|
|`summary.json`|精度、费用与设计汇总|最后比较总体和B组的SE|

从 `first_sample.csv` 按 `group` 数样本人数和 `observed_need=1` 的人数，自己计算两组比例、加权总体比例和直接合并比例。再对照 `trials.csv` 第一行：`estimate` 是加权总体估计，`B_estimate` 是B组估计，`pooled` 是直接合并比例，`cost` 是费用。

**一轮推断的成功信号**：两组人数与配置一致，手算点估计与首行一致；用同一轮样本算出的估计SE和区间有明确输入与条件。`trials.csv` 保留基础输出，不自动完成你的区间解释。下列可选工具只演示另设的小样本，不读取正式数据、不选择正式方案。

```python
# 在学生仓库根目录执行，或保存为自己的演示脚本。
import sys
sys.path.insert(0, "lesson-14")
from stratified_tools import sample_inference, planning_precision
N = {"A": 800, "B": 200}
n = {"A": 160, "B": 40}
print(sample_inference(N, n, {"A": 68, "B": 23}))
print(planning_precision(N, n, {"A": 0.5, "B": 0.5}))
```

第一项应给出点估计0.455、估计SE约0.0314234、区间约0.393410—0.516590；第二项是保守假设下的规划SE，不是同一批样本的估计SE。工具返回未截断的正态区间，小计数会提示警告；没有警告也不是覆盖率保证。把区间端点截到0和1之间，不能解决近似失效。

正式追踪时，需要你从样本获得计数，并指定正确名册人数和样本人数；不能把模拟真值传入 `successes`（它要求观察到的整数计数）。规划函数则需要明确假设比例，不读取完整总体，不自动推荐分配。

`summary.json` 的主要字段：

- `total`：总体估计的模拟平均值、偏差及 `empirical_se`。
- `B`：B组估计的相同统计量。
- `pooled`：未加权合并估计的表现，用于检查样本构成的影响。
- `allocation`：每层总体人数、样本量、总体份额、包含概率、设计权重和单价。
- `design_se_exact`：利用教学总体真值计算的理论总体SE，用于核对模拟。
- `design_effect_same_n`：以同总人数简单随机抽样为参照的方差比，不是同预算比较。

`empirical_se` 来自500轮估计值的样本标准差。它与理论SE接近但不必相等；总体真值用于课堂审核，不是现实调查前必然已知的信息。

### 从输出数字写出判断

先在同一行记录实际费用、`design_se_exact`、`total.empirical_se` 和 `B.empirical_se`。比例单位的SE乘100后才是百分点，例如0.031表示3.1个百分点，不是“误差已知为3.1%”。

比较时先核费用是否相同，再问总体SE和B组SE分别怎样改变。用各层人数和总体份额解释取舍，最后根据调查目标作选择。不要因为某轮估计更靠近真值，就断言整个方案更稳定。

知识讲解的1000人小例只用于理解计算；本脚本固定使用4000人正式名册，输出数值不应与小例强行相等。`design_se_exact` 是模拟中用完整总体计算的理论评价值，不是某次真实调查已知的误差。

## 三、保存自己的方案

先写比较计划，再复制默认配置到自己选择的文件名。根据调查用途自主确定预算240下的比例分配方案、另一可行方案，以及预算180下的新方案；检查人数和实际费用，不照搬教学小例的预算280。

可把文件命名为 `plan-proportional.json`、`plan-alternative.json`、`plan-budget180.json`。它们沿用第一节五个字段，根据调查目标自行填写人数；可先用费用不等式列出可行人数，再按总体与B组的精度优先级筛选。

先用 `planning_precision` 或LEARN公式比较你自己的分配在两组合理比例设定下的表现，再运行教学总体模拟。保留两种证据的区别：前者是条件规划，后者是这个合成总体下的评价。不要把改变需求比例的压力情景声称为原模拟器已运行的结果。

单独运行一个新方案可用：

```sh
python3 lesson-14/analysis.py --config lesson-14/plan-alternative.json --output lesson-14/artifacts/alternative-first
```

比较时保持总体、重复次数和评价口径一致，列出实际成本。同一种子便于复算，不意味着不同分配下各组抽中的人完全相同。预算下降的比较同时涉及可用资源变化，要与同预算分配比较分开解释。

## 四、可重复执行的重建脚本

默认入口保护已有目录，直接把它重复指向旧目录会报错。正式重建可先在临时新目录计算，再复制确定的产物到自己专用的重建目录，不删除原始数据或历史实验。

将以下保存为 `lesson-14/my-analysis.py`，先确认第三节的配置文件已经存在：

```python
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "lesson-14"
CASES = {
    "proportional": "plan-proportional.json",
    "alternative": "plan-alternative.json",
    "budget180": "plan-budget180.json",
}
FILES = ("plan.json", "first_sample.csv", "trials.csv", "summary.json")

for name, config_name in CASES.items():
    destination = LESSON / "artifacts" / "rebuild" / name
    with tempfile.TemporaryDirectory(prefix="lesson14-") as temporary:
        fresh = Path(temporary) / "result"
        subprocess.run(
            [sys.executable, str(LESSON / "analysis.py"),
             "--config", str(LESSON / config_name),
             "--output", str(fresh)],
            cwd=ROOT, check=True,
        )
        destination.mkdir(parents=True, exist_ok=True)
        for filename in FILES:
            shutil.copyfile(fresh / filename, destination / filename)
```

该脚本会更新 `artifacts/rebuild/` 下你登记的方案的四个产物。这个目录专用于重建；要保留旧比较，先另存到其他目录。自己的方案可替换配置内容或增减 `CASES`，不要求采用某个固定人数。

连续运行两次：

```sh
python3 lesson-14/my-analysis.py
python3 lesson-14/my-analysis.py
```

两次都应成功，配置与输入不变时产物内容应相同。随后用 `ci` 作正式字节核对。

## 五、汇总比较与登记提交

建议表中至少列：预算、两层人数、总人数、实际费用、总体SE、B组SE。另保留首轮加权估计、估计SE、近似区间与条件判断，以及规划假设敏感性的记录；不要只比较平均估计谁更接近真值，因为单次模拟也有随机波动。

完成报告后，`lesson-14/submission.json` 可按以下结构填写。若改了目录或方案，要同步修改路径。

```json
{
  "lesson": "lesson-14",
  "status": "complete",
  "run": ["python3", "lesson-14/my-analysis.py"],
  "artifacts": [
    "lesson-14/artifacts/rebuild/proportional/plan.json",
    "lesson-14/artifacts/rebuild/proportional/first_sample.csv",
    "lesson-14/artifacts/rebuild/proportional/trials.csv",
    "lesson-14/artifacts/rebuild/proportional/summary.json",
    "lesson-14/artifacts/rebuild/alternative/plan.json",
    "lesson-14/artifacts/rebuild/alternative/first_sample.csv",
    "lesson-14/artifacts/rebuild/alternative/trials.csv",
    "lesson-14/artifacts/rebuild/alternative/summary.json",
    "lesson-14/artifacts/rebuild/budget180/plan.json",
    "lesson-14/artifacts/rebuild/budget180/first_sample.csv",
    "lesson-14/artifacts/rebuild/budget180/trials.csv",
    "lesson-14/artifacts/rebuild/budget180/summary.json"
  ],
  "report": "lesson-14/report.md"
}
```

```sh
python3 scripts/course_l1314.py check 14
python3 scripts/course_l1314.py ci 14
```

检查会在临时副本重建登记产物并核对字节，不修改原作业。检查通过后，仍需确认报告中的解释与自己的证据一致；标签沿用 `v2-l14-final`。

## 六、常见问题

|现象|怎样检查|
|---|---|
|预算改为180后报错|重新计算两层人数对应的费用；只改budget不会调整人数|
|输出目录已存在|新实验另取目录；重复重建使用第四节脚本|
|组人数报错|检查整数、至少2人及对应总体上限|
|加权与直接合并不同|先核总体份额0.8/0.2与样本份额，不先认定代码错|
|设计效应小但费用更高|参照是同人数；另做同费用比较|
|模拟SE不等于理论SE|有限轮数有模拟误差；先核方法与配置，再增加轮数核查|
|复现检查产物不一致|检查配置、种子与输入是否固定，避免手改输出或写入运行时间|
|不知道怎样写联系计划|写明名册、抽取方法、人数、费用、未回答记录与追访安排|

真实无回答会改变实际取得的数据。不要把方便联系到的人随意补入样本，或直接把未回答者当作无需求。
