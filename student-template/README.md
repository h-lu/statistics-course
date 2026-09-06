# 统计学项目课：用数据形成有依据的判断

本学期你将完成32次课堂项目：提出分析问题、比较不同方案、设计调查和实验、建立统计模型，并根据分析结果提出建议。你可以全程使用AI完成编程、计算、分析和写作；提交前需要说明分析结论、判断依据和适用范围。

每节课先阅读对应目录的`README.md`，了解项目背景，明确分析问题和任务要求，再学习`LEARN.md`中的基础知识，开展数据分析。最后约15分钟完成[知识自查](https://hblu.top/stat-check/)。项目允许有依据的不同方法和结论，不以代码量、模型数量或页面复杂程度评分。

## 第一次使用

按[操作与提交步骤](docs/WORKFLOW.md)创建个人私有仓库，检查Python与Git。课程已提供数据和可直接运行的示例代码。请在此基础上编写或修改分析程序，完成当课的分析任务。

```bash
python scripts/course.py start 01
python scripts/course.py run 01
```

若你的电脑使用`python3`，把命令里的`python`换成`python3`。基础工具只需要Python 3.10或以上；分析依赖按需安装，见[环境与排障](docs/TROUBLESHOOTING.md)。

## 本学期项目

| 周 | 课次与分析任务 |
|---|---|
| 1 | [01 服务数据的探索性分析](lesson-01/README.md) · [02 分析结论对统计口径有多敏感](lesson-02/README.md) |
| 2 | [03 业务数据质量与适用性评估](lesson-03/README.md) · [04 设计服务质量评价办法](lesson-04/README.md) |
| 3 | [05 有限复核名额下的告警策略](lesson-05/README.md) · [06 业务构成不同的机构应如何比较](lesson-06/README.md) |
| 4 | [07 满意度调查的覆盖与无回答问题](lesson-07/README.md) · [08 多表数据整合与统计指标核查](lesson-08/README.md) |
| 5 | [09 筛查阳性之后怎样安排复核](lesson-09/README.md) · [10 为随机需求设计容量方案](lesson-10/README.md) |
| 6 | [11 自愿调查能够代表哪些人](lesson-11/README.md) · [12 比较估计方法的适用条件](lesson-12/README.md) |
| 7 | [13 置信区间能否支持决策](lesson-13/README.md) · [14 在有限预算下设计一项调查](lesson-14/README.md) |
| 8 | [15 设计能回答实际问题的随机实验](lesson-15/README.md) · [16 根据实验结果决定推广、试用或停止](lesson-16/README.md) |
| 9 | [17 配对、独立样本与重复测量的比较](lesson-17/README.md) · [18 预算允许的实验是否值得开展](lesson-18/README.md) |
| 10 | [19 大量发现中哪些可以对外发布](lesson-19/README.md) · [20 序贯分析与实验停止规则](lesson-20/README.md) |
| 11 | [21 如何解释相关与回归结果](lesson-21/README.md) · [22 多元回归的模型比较与解释](lesson-22/README.md) |
| 12 | [23 风险预测与复核决策](lesson-23/README.md) · [24 模型比较与泛化能力评价](lesson-24/README.md) |
| 13 | [25 预测性能与模型维护成本](lesson-25/README.md) · [26 风险模型的校准与试运行评价](lesson-26/README.md) |
| 14 | [27 从观察关联到因果研究设计](lesson-27/README.md) · [28 观察数据中的效应估计与共同支持](lesson-28/README.md) |
| 15 | [29 政策效果的双重差分评估](lesson-29/README.md) · [30 时间序列预测与容量规划](lesson-30/README.md) |
| 16 | [31 追加调查是否值得：信息价值分析](lesson-31/README.md) · [32 面向新问题的统计分析综合报告](lesson-32/README.md) |

## 需要提交什么

每课提交分析报告、支持结论的图表或数据，以及能重新生成结果的代码。默认在当课`report.md`写报告，在`artifacts/`保存分析结果；也可以采用适合问题的其他形式，并在`submission.json`填写文件路径和运行命令。只运行示例代码、生成文件，还没有完成分析任务。

阅读[成果与评分](docs/ASSESSMENT.md)、[AI使用建议](docs/AI_USAGE.md)和[知识自查说明](docs/KNOWLEDGE_CHECK.md)，需要补充解释时可用[查阅资料](docs/RESOURCES.md)。随课数据均为教学合成数据，使用前请阅读[数据说明](data/README.md)，不能把分析结论作为现实学校或机构的事实。
