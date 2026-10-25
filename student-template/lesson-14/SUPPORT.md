# 第14课操作支持：卡在哪里，就查哪里

## 第一次运行
沿用前课学生仓库与Python环境。在仓库根目录运行：

```sh
python3 lesson-14/analysis.py
```

成功时打印摘要，并生成四个文件：plan.json记录实际设置；first_sample.csv一行一个抽中的人；trials.csv一行一轮调查；summary.json汇总多轮表现。不要把人行数当重复次数。

## 保存第二种条件
复制`lesson-14/config.json`为`lesson-14/my-plan.json`，根据自己的问题改一项设置，再运行：

```sh
python3 lesson-14/analysis.py --config lesson-14/my-plan.json --output lesson-14/artifacts/my-plan
```

输出目录必须尚不存在。保留旧结果，不用覆盖获得“最好一次”。一个条件的运行不是项目完整答案；比较和建议仍由你决定。

## 配置与输出
n_A/n_B是两层人数，repetitions是重复调查次数，seed控制抽样，budget是最大邀请费用。成本约束是n_A+3n_B≤budget，不是n_A+n_B≤budget。每组至少2人且不超过该组总体。

默认128/32的包含概率均.04，设计权重均25，成本224。首轮B样本比例.6875，总体加权比例.375。检查first_sample.csv各组的有需求人数，重算这些比例，再看summary的total和B各自empirical_se。pooled是未加权合并比例，仅作诊断，不自动视为总体估计。

design_effect_same_n的参照是同总人数SRS，不是同成本。若想公平比较预算，另存同预算可行方案，不用一个设计效应替代全部取舍。

## 错误与复现
配置拼写错误、超预算、样本超过总体、输出已存在均会停止；先读错误，不修改原始CSV。课堂模拟不生成新总体。把正式报告所用命令和四个产物完整登记进submission.json；多条件时run可以用命令参数列表指向你自己的重建脚本。

```sh
python3 scripts/course_l1314.py check 14
python3 scripts/course_l1314.py ci 14
```

ci会在临时副本删除登记的产物并重跑，核对字节；不要把运行时间写入这些产物。它检查可复现性，不替你判断调查设计合理性。必要图可用自己的代码生成并一并登记。

`submission.json`沿用原格式：lesson为`lesson-13`或`lesson-14`，report为报告相对路径，run为参数列表，例如 `["python3", "lesson-13/my-analysis.py"]`，不是一个shell字符串。
