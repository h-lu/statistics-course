# 统计学项目课：用数据形成有依据的判断

本课程按课次逐步发布项目。当前仓库已开放第 1 课；后续课次将在教师发布后出现在仓库中。你可以全程使用AI完成编程、计算、分析和写作；提交前需要说明分析结论、判断依据和适用范围。

每节课先阅读对应目录的`README.md`，了解项目背景，明确分析问题和任务要求，再学习`LEARN.md`中的基础知识，开展数据分析。最后约15分钟完成[知识自查](https://hblu.top/stat-check/)。项目允许有依据的不同方法和结论，不以代码量、模型数量或页面复杂程度评分。

## 第一次使用

按[操作与提交步骤](docs/WORKFLOW.md)创建个人私有仓库，检查Python与Git。课程已提供数据和可直接运行的示例代码。请在此基础上编写或修改分析程序，完成当课的分析任务。

```bash
python scripts/course.py start 01
python scripts/course.py run 01
```

若你的电脑使用`python3`，把命令里的`python`换成`python3`。基础工具只需要Python 3.10或以上；分析依赖按需安装，见[环境与排障](docs/TROUBLESHOOTING.md)。

## 当前已发布项目

| 课次 | 分析任务 |
|---|---|
| 01 | [服务数据的探索性分析](lesson-01/README.md) |

## 需要提交什么

每课提交分析报告、支持结论的图表或数据，以及能重新生成结果的代码。默认在当课`report.md`写报告，在`artifacts/`保存分析结果；也可以采用适合问题的其他形式，并在`submission.json`填写文件路径和运行命令。只运行示例代码、生成文件，还没有完成分析任务。

阅读[成果与评分](docs/ASSESSMENT.md)、[AI使用建议](docs/AI_USAGE.md)和[知识自查说明](docs/KNOWLEDGE_CHECK.md)，需要补充解释时可用[查阅资料](docs/RESOURCES.md)。随课数据均为教学合成数据，使用前请阅读[数据说明](data/README.md)，不能把分析结论作为现实学校或机构的事实。
