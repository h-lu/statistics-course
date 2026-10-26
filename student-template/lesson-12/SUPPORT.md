# 从一轮调查，到重复抽样

命令均在学生仓库根目录运行，Python标准库即可。第11课的名册和数据仍放在 `lesson-11/data/`，本课只新增程序与结果。

## 1. 先核对小例

```sh
python3 scripts/course_l12.py start 12
python3 lesson-12/analysis.py
```

打开 `lesson-12/artifacts/example.json`，核对六个样本及均值。这里穷尽全部六种等可能抽法，标准误是 $\sqrt{5/3}$ ，不再对这六个结果使用分母5。

## 2. 运行一个正式数据上的基准条件

`config-example.json`明确写了：完整名册、完全回答、每次80人、直接比例、重复500次、总种子1201。打开配置先确认这些值，再运行：

```sh
python3 lesson-12/repeat.py --config lesson-12/config-example.json --output lesson-12/artifacts/reference-80
```

这只完成一个条件，用来理解工具。正式任务还需根据自己的问题选对照、检查模拟稳定性并提出建议。

|输出|每行或内容是什么|
|---|---|
|`plan.json`|本次运行前保存的条件|
|`first_observations.csv`|第一轮中4000人各自的框、邀请、回答与已观察需求|
|`trials.csv`|一行是一轮调查，500行就是500个独立模拟重复|
|`summary.json`|同一条件下的平均估计、偏差、标准误等|

总种子只在开始设置一次，程序为每轮生成新的邀请种子与回答种子；它们也保存在trials中。每轮从相同固定总体重新抽样，不是把总体重新生成，也不是每轮重新设置同一个邀请种子。

## 3. 读第一轮，再读500轮

示范第一轮邀请并收到80份回答：A组65份中24人有需求，B组15份中9人有需求。

**这一轮估计＝ $(24+9)/80=0.4125$ ，即41.25%**。

邀请费用为 $65\times 1+15\times 3=110$ 。这个费用只计邀请，不包括促成完全回答的额外成本。

这只是 `trials.csv` 的第1行。对500轮汇总，指定配置实际得到：

- `mean_estimate`＝0.4102。
- `bias`＝ $0.4102-0.41=0.0002$ ，即0.02个百分点。
- `estimated_se`≈0.056223，即5.6223个百分点。
- `monte_carlo_se_of_mean`≈0.002514，约为 $\frac{0.056223}{\sqrt{500}}$ 。它描述500个估计的平均数的模拟误差，不是单次调查的波动。

完整回答基准的精确标准误约0.054443；500次模拟估出的0.056223与它不完全相同，是有限重复的波动，不应人为改成精确值。

若某轮没有回答，raw估计留空；poststrat还要求两组都有回答。summary报告未定义次数。出现未定义轮次时，其均值和标准误仅针对可计算的那些轮，不能忽略这一条件。

## 4. 画的是什么分布？

```sh
python3 lesson-12/plot_distribution.py --run lesson-12/artifacts/reference-80
```

打开生成的 `distribution.svg`。横轴是每轮调查的估计比例，纵轴是落入相应区间的轮数，虚线是41%的总体真值。它没有把每个人的0/1需求画成直方图。

先看中心是否靠近虚线，再看分散程度，最后看形状。图形看起来较集中，不等于中心没有偏离。

## 5. 设置你自己的比较

把示范配置复制成例如 `lesson-12/plan-a.json` 和 `plan-b.json`。先选要改变的一项，再运行到不同目录：

```sh
python3 lesson-12/repeat.py --config lesson-12/plan-a.json --output lesson-12/artifacts/plan-a
python3 lesson-12/repeat.py --config lesson-12/plan-b.json --output lesson-12/artifacts/plan-b
```

|字段|可用值与含义|
|---|---|
|mechanism|register_complete：从完整名册抽人，抽中者全部回答；register_ordinary：从完整名册抽人，但有人不回答；web_voluntary：从网上可联系名单邀请，由受邀者自愿回答|
|n|每轮邀请人数；名册方式不超过4000，网上方式不超过3305|
|estimator|raw：回答者直接比例；poststrat：按全体A/B的0.8/0.2构成加权|
|repetitions|重复次数，至少2；可从500开始|
|seed|固定的非负整数总种子，用于复现这次模拟|

所有机制与第11课相同。同一总种子使比较能复现，但不代表不同机制一定邀请到相同的人。

比如比较样本量，就保持机制和估计方法相同；比较估计方法，可用相同的机制、人数、种子，使两种算法处理相同的调查。选择有实际理由，不把每一项都同时改变。

## 6. 如何判断模拟是否稳定

保留第一次配置与输出，再增加重复次数或另选种子，查看平均、偏差和标准误是否有足以改变建议的变化。输出目录必须用新名字。增加重复次数只减少模拟本身的不确定性，不是多调查一次就能修复选择偏差。

## 7. 把自己的方案写进复现命令

基础小例不替代正式分析。可以在 `lesson-12/my_study.py` 保存自己的重建脚本。下面仅示范如何运行你已经确定的两份配置，不替你选择方案或写结论：

```python
from pathlib import Path
import json
import shutil
import tempfile
from repeat import run
from plot_distribution import draw

here = Path(__file__).resolve().parent
files = ("plan.json", "first_observations.csv", "trials.csv",
         "summary.json", "distribution.svg")
with tempfile.TemporaryDirectory(prefix="lesson12-") as temporary:
    for name in ("plan-a", "plan-b"):
        config = json.loads((here / f"{name}.json").read_text(encoding="utf-8"))
        fresh = Path(temporary) / name
        run(config, fresh)
        draw(fresh)
        destination = here / "artifacts" / "rebuild" / name
        destination.mkdir(parents=True, exist_ok=True)
        for filename in files:
            shutil.copyfile(fresh / filename, destination / filename)
```

脚本先在临时新目录计算，再更新专用rebuild目录中的已知文件；不删除第一次实验结果。两份输入配置须事先保存，仍由你决定比较因素。它同时生成两幅分布图。

连续运行两次：

```sh
python3 lesson-12/my_study.py
python3 lesson-12/my_study.py
```

固定数据、配置和环境时，两次输出应一致。可以逐项核对summary数值；正式复现检查会重建登记的文件。

在submission中把run设为 `["python3", "lesson-12/my_study.py"]`，artifacts列出两方案各5个文件，共10个产物。下面代码可以列出示例清单，检查后填入该字段：

```python
import json
names = ["plan.json", "first_observations.csv", "trials.csv",
         "summary.json", "distribution.svg"]
paths = [f"lesson-12/artifacts/rebuild/{case}/{name}"
         for case in ("plan-a", "plan-b") for name in names]
print(json.dumps(paths, ensure_ascii=False, indent=2))
```

不把输入配置和报告列作生成产物。若增加了模拟稳定性条件或其他必要输出，也应让脚本重建并登记，而不是只交这两个示例条件。完成报告后设complete，运行 `python3 scripts/course_l12.py check 12`，再按[提交流程](../docs/WORKFLOW.md)提交。

重建检查在临时副本中清除已登记输出再运行，不删除原作业。上述脚本可在本地连续重建；前面独立运行repeat的命令仍用于新实验，应使用新目录，避免覆盖第一次结果。


已完成结果如何安全重建并核对产物清单，见[第1—12课重建检查](../docs/REBUILD_CHECK.md)。本课的新实验仍保留新目录，不删除原证据。
