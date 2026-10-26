# 第13课｜运行帮助

沿用前课的Python环境，以下命令在学生仓库根目录执行。

## 运行前：区分三种次数

- `n`：一次调查抽取的人数，默认80。
- `repetitions`：从总体重复调查的次数 $R$ ，默认500。
- `bootstrap_draws`：每次调查内部自助重抽的次数 $B$ ，仅在bootstrap方法中使用，默认500。

`method`选择wilson、wald_fpc或bootstrap；`seed`确定各轮抽样；`decision_threshold`为事先选择的行动门槛，默认0.4。原始数据位于 `lesson-11/data/`。

## 第一次运行

```sh
python3 lesson-13/analysis.py
```

默认输出位于 `lesson-13/artifacts/baseline/`：

|文件|内容|
|---|---|
|plan.json|本次实验的完整设置|
|first_sample.csv|第一轮抽中的人，一行一人|
|trials.csv|重复调查的结果，一行一轮|
|summary.json|覆盖率、平均宽度等汇总|

先读first_sample.csv：80人中36人的observed_need为1，比例为0.45。再读trials.csv第一行：`lower` 约为0.3458、`upper` 约为0.5588、`width` 约为0.2130。covered=1表示区间覆盖课堂总体真值0.41；decision=uncertain表示区间包含门槛0.4。

最后查看summary.json。`coverage_mc_se`衡量有限次模拟所得覆盖率的不确定性；总体真值仅用于覆盖检查，不参与区间计算。

## 比较第二种条件

复制 `lesson-13/config.json` 为 `lesson-13/my-plan.json`。例如比较两种区间方法，可只将method改为wald_fpc，保留 $n$ 和seed，再运行：

```sh
python3 lesson-13/analysis.py --config lesson-13/my-plan.json --output lesson-13/artifacts/my-plan
```

相同 $n$ 和seed产生相同的每轮抽样记录，便于成对比较。自助重抽使用独立随机数序列，改变 $B$ 不会改变从总体抽出的样本。每个条件使用新的输出目录。

## 提交与复现

把报告路径、自己的重建命令和各条件的四个产物登记到 `submission.json`。`run`使用命令参数列表，例如 `["python3", "lesson-13/my-analysis.py"]`；多条件分析可由该脚本依次运行。

```sh
python3 scripts/course_l1314.py check 13
python3 scripts/course_l1314.py ci 13
```

`ci`在临时副本中重建登记产物并核对字节，检查可复现性。若提示输出目录已存在，换用新目录；其他错误按提示核对字段名、方法名和取值。原始CSV保持不变。
