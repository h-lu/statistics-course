# 第14课｜运行帮助

沿用前课Python环境，以下命令在学生仓库根目录执行。

## 运行前核对

`n_A`、`n_B`是各层单次抽样人数，`repetitions`是重复调查次数 $R$ ，`seed`控制抽样，`budget`为邀请费用上限。每组至少2人且不超过该组总体，费用满足 $n_A+3n_B\le\mathrm{budget}$ 。

## 默认方案

```sh
python3 lesson-14/analysis.py
```

结果位于 `lesson-14/artifacts/baseline/`：plan.json记录设置，first_sample.csv一行一人，trials.csv一行一轮，summary.json汇总精度。

按以下顺序核对：

1. 默认128/32方案中，两组包含概率均为0.04，设计权重均为25，成本224。
2. first_sample.csv首轮A组128人中38人有需求，B组32人中22人有需求。重算 $\widehat p_A=38/128$ 、 $\widehat p_B=22/32=0.6875$ ，总体估计 $0.8\widehat p_A+0.2\widehat p_B=0.375$ 。
3. trials.csv第一行应给出相同结果。summary.json的total、B各含empirical_se，即重复估计的标准差。pooled为未加权合并比例，供比较样本构成的影响。

`design_effect_same_n`参照同总人数的简单随机抽样，不是同成本方案。

## 比较与预算变化

复制 `lesson-14/config.json` 为 `lesson-14/my-plan.json`，修改两层人数及预算后运行：

```sh
python3 lesson-14/analysis.py --config lesson-14/my-plan.json --output lesson-14/artifacts/my-plan
```

比较方案时保持总体、重复次数和评价指标相同，记录实际费用。预算改为180时，需要同时检查两层人数对应的费用；只改budget不会自动重新分配人数。每次使用新的输出目录。

## 提交检查

把各方案的重建命令写进自己的脚本，在 `submission.json` 中用参数列表登记 `run`，例如 `["python3", "lesson-14/my-analysis.py"]`；`artifacts`列各方案的四个产物，`report`填报告路径，完成后设 `status=complete`。

```sh
python3 scripts/course_l1314.py check 14
python3 scripts/course_l1314.py ci 14
```

`ci`会在临时副本中重建登记文件并核对字节。若报错，核对字段、人数、费用与输出目录。原始CSV保持不变。
