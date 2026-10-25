# 第13课操作支持：卡在哪里，就查哪里

## 第一次运行
沿用前课学生仓库与Python环境。在仓库根目录运行：

```sh
python3 lesson-13/analysis.py
```

成功时打印摘要，并生成四个文件：plan.json记录实际设置；first_sample.csv一行一个抽中的人；trials.csv一行一轮调查；summary.json汇总多轮表现。不要把人行数当重复次数。

## 保存第二种条件
复制`lesson-13/config.json`为`lesson-13/my-plan.json`，根据自己的问题改一项设置，再运行：

```sh
python3 lesson-13/analysis.py --config lesson-13/my-plan.json --output lesson-13/artifacts/my-plan
```

输出目录必须尚不存在。保留旧结果，不用覆盖获得“最好一次”。一个条件的运行不是项目完整答案；比较和建议仍由你决定。

## 配置与输出
n是一次抽样人数，repetitions是调查重复次数，seed控制每轮抽样，method选wilson/wald_fpc/bootstrap，decision_threshold是事先确定的行动门槛；bootstrap_draws仅控制区间内部重抽次数。

默认第一轮80人36个1，比例.45。上下限约.3458和.5588，width约.2130，covered=1表示它覆盖课堂已知真值.41；decision=uncertain因为区间跨过门槛.4。coverage_mc_se是有限覆盖实验的不确定性，不是一次比例的标准误。

相同seed和n对应相同抽样记录，便于成对比较方法；自助随机数另用独立种子，避免B改变下一轮抽样。每轮真值只用于审核覆盖，不参与区间计算。

## 错误与复现
配置拼写错误、超预算、样本超过总体、输出已存在均会停止；先读错误，不修改原始CSV。课堂模拟不生成新总体。把正式报告所用命令和四个产物完整登记进submission.json；多条件时run可以用命令参数列表指向你自己的重建脚本。

```sh
python3 scripts/course_l1314.py check 13
python3 scripts/course_l1314.py ci 13
```

ci会在临时副本删除登记的产物并重跑，核对字节；不要把运行时间写入这些产物。它检查可复现性，不替你判断调查设计合理性。必要图可用自己的代码生成并一并登记。

`submission.json`沿用原格式：lesson为`lesson-13`或`lesson-14`，report为报告相对路径，run为参数列表，例如 `["python3", "lesson-13/my-analysis.py"]`，不是一个shell字符串。
