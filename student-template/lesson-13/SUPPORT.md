# 第13课｜运行帮助

本页按“首次运行→读懂结果→比较条件→重复重建→提交检查”的顺序使用。所有命令均在学生仓库根目录执行，沿用前课的Python环境。

## 一、运行前确认配置

原始数据位于 `lesson-11/data/`，本课使用其中4000人的教学合成总体，不需要重新下载数据。默认 `lesson-13/config.json` 为：

```json
{
  "n": 80,
  "repetitions": 500,
  "seed": 1301,
  "method": "wilson",
  "decision_threshold": 0.4
}
```

|字段|作用|本课注意事项|
|---|---|---|
|`n`|一次调查人数|整数，至少2，不超过总体人数|
|`repetitions`|调查重复次数|即 $R$，至少2；用于评价方法|
|`seed`|抽样种子|非负整数；固定后便于复算|
|`method`|区间方法|`wilson`、`wald_fpc` 或 `bootstrap`|
|`decision_threshold`|行动门槛|0到1之间，运行前确定|
|`bootstrap_draws`|每轮内部重抽次数|即 $B$，默认500；使用bootstrap时至少100|

Wilson与普通百分位自助区间在这里作为低抽样比例近似；`wald_fpc` 是带有限总体修正的正态近似。三者都不是任意样本下精确95%的保证，因此还要评价覆盖表现。

## 二、首次运行并读懂结果

```sh
python3 lesson-13/analysis.py
```

默认输出到 `lesson-13/artifacts/baseline/`。程序会保护已有输出，不覆盖同名目录。如果已经运行过，直接读原结果，或在下一次指定一个新的输出目录。

|文件|一行或一个文件代表什么|先看什么|
|---|---|---|
|`plan.json`|本次完整设置|方法、人数、轮数、种子、门槛|
|`first_sample.csv`|一行是一名第一轮受访者|`observed_need` 为0或1|
|`trials.csv`|一行是一轮调查|估计、上下限、宽度、覆盖与行动判断|
|`summary.json`|全部调查的汇总|覆盖率、平均宽度、模拟标准误|

先从第一轮样本开始。默认80人中36人的 `observed_need` 为1，因此样本比例为 $36/80=0.45$。在 `trials.csv` 第一行核对：

- `estimate` 为0.45；`lower` 约0.3458，`upper` 约0.5588。
- `width` 为上限减下限，约0.2130。
- `covered=1` 表示区间覆盖教学总体真值0.41；0表示未覆盖。
- `decision=uncertain` 表示区间跨过门槛0.40。另两种取值是 `support_above` 和 `support_below`。

最后读汇总：默认500轮有482轮覆盖，`observed_coverage` 为0.964，`coverage_mc_se` 约0.00833，`average_width` 约0.2094。`nominal_coverage=0.95` 是目标水平，不是强制输出的数值。总体真值 `truth_for_audit_only` 只用于评价覆盖，不参与区间计算。

可用下面的代码核对汇总。在仓库根目录将它保存为临时核对脚本运行，或在Python交互环境中执行：

```python
import csv
from pathlib import Path

folder = Path("lesson-13/artifacts/baseline")
with (folder / "trials.csv").open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
coverage = sum(int(r["covered"]) for r in rows) / len(rows)
width = sum(float(r["width"]) for r in rows) / len(rows)
print("调查轮数：", len(rows))
print("经验覆盖率：", coverage)
print("平均宽度：", width)
```

## 三、另存配置，比较第二个条件

先复制 `lesson-13/config.json`，另存为 `lesson-13/my-plan.json`。方法比较示例只把 `method` 改为 `wald_fpc`，其他值保持不变：

```sh
python3 lesson-13/analysis.py --config lesson-13/my-plan.json --output lesson-13/artifacts/my-plan
```

每个条件保留自己的配置和输出。相同 $n$ 与种子产生相同的每轮抽样记录，便于方法间成对比较；自助重抽使用独立随机数序列，改变 $B$ 不会改变从总体抽出的样本。人数比较则可只把 $n$ 改为160，并保持方法等条件不变。

读完两个 `summary.json` 后，把条件、第一轮区间、覆盖率、平均宽度及模拟标准误并排整理。先写观察到的差异，再解释原因和业务意义。

## 四、让自己的比较可以重复运行

直接运行 `analysis.py` 要求输出目录不存在；但提交检查会在临时仓库中删除已登记的产物文件后重新运行，目录可能仍在。因此正式重建应使用下面这种方式：先在临时新目录计算，再把确定的四个产物复制到自己专用的结果目录。

将以下代码保存为 `lesson-13/my-analysis.py`。它读取默认配置与上一节另存的配置；请先确认两个配置确实对应你的比较问题。

```python
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "lesson-13"
CASES = {
    "condition-a": LESSON / "config.json",
    "condition-b": LESSON / "my-plan.json",
}
FILES = ("plan.json", "first_sample.csv", "trials.csv", "summary.json")

for name, config in CASES.items():
    destination = LESSON / "artifacts" / "rebuild" / name
    with tempfile.TemporaryDirectory(prefix="lesson13-") as temporary:
        fresh = Path(temporary) / "result"
        subprocess.run(
            [sys.executable, str(LESSON / "analysis.py"),
             "--config", str(config), "--output", str(fresh)],
            cwd=ROOT, check=True,
        )
        destination.mkdir(parents=True, exist_ok=True)
        for filename in FILES:
            shutil.copyfile(fresh / filename, destination / filename)
```

这里 `artifacts/rebuild/` 是你专门用于重建的目录，脚本会更新其中两个条件的四个输出文件；不改变原始数据、默认基线目录或报告。若需要保留旧实验，先将其另存到不同的实验目录。

连续运行两次，确认都能成功：

```sh
python3 lesson-13/my-analysis.py
python3 lesson-13/my-analysis.py
```

参数与输入不变时，四个产物应逐字节一致。两次运行成功只是初步检查，下一节的 `ci` 会正式核对。

## 五、登记提交并检查

完成报告后，编辑 `lesson-13/submission.json`。使用上面的目录与脚本时可采用以下结构；若自己改了路径，要同步修改登记。

```json
{
  "lesson": "lesson-13",
  "status": "complete",
  "run": ["python3", "lesson-13/my-analysis.py"],
  "artifacts": [
    "lesson-13/artifacts/rebuild/condition-a/plan.json",
    "lesson-13/artifacts/rebuild/condition-a/first_sample.csv",
    "lesson-13/artifacts/rebuild/condition-a/trials.csv",
    "lesson-13/artifacts/rebuild/condition-a/summary.json",
    "lesson-13/artifacts/rebuild/condition-b/plan.json",
    "lesson-13/artifacts/rebuild/condition-b/first_sample.csv",
    "lesson-13/artifacts/rebuild/condition-b/trials.csv",
    "lesson-13/artifacts/rebuild/condition-b/summary.json"
  ],
  "report": "lesson-13/report.md"
}
```

```sh
python3 scripts/course_l1314.py check 13
python3 scripts/course_l1314.py ci 13
```

`check` 检查提交结构与登记材料；`ci` 还会在临时副本中重建并核对产物。通过自动检查不等于统计解释正确，仍需逐项核对练习与报告要求。按既有流程提交，标签为 `v2-l13-final`。

## 六、常见问题

|现象|排查顺序|
|---|---|
|找不到 `lesson-13/analysis.py`|确认终端当前目录是仓库根目录，而不是某个课次目录|
|`Use a new output directory`|首次试验换一个尚不存在的输出目录；正式重建采用第四节脚本，不反复删除旧实验|
|`Unknown fields` 或 `Unknown method`|检查JSON字段和方法名，区分英文下划线与拼写|
|人数或重抽次数报错|`n` 必须为2到4000的整数；bootstrap的重抽次数至少100|
|JSON解析失败|检查双引号、逗号，不要在JSON中加入注释|
|CI提示产物不一致|核对配置、种子、数据和脚本是否同步；检查是否手工编辑过输出或写入运行时间|
|CI找不到脚本或配置|确认新增的脚本和配置已保存并随提交保留，路径从仓库根目录起算|
|结果与默认数值不同|先核对方法、人数、种子和轮数；改过条件后不应强求默认答案|

不要为通过检查手改覆盖率、删除原始CSV或把两种条件的结果复制成一样。保存报错原文和使用的命令，有助于定位问题。
