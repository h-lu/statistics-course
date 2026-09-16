# 统计学项目课学生仓库

本仓库是一套完整的课程模板，包含32个课堂项目、教学数据、示例程序和提交检查工具。每课的具体任务写在对应目录的 `README.md` 和 `LEARN.md` 中。

课程的目标不是写出最多代码，而是用数据回答一个清楚的问题：你观察到了什么，证据是什么，结论适用于哪里，下一步还需要核实什么。你可以使用 AI 辅助编程、计算、查资料和修改文字，但提交前必须自己检查变量、分母、计算结果和结论范围。

## 先选择正确的仓库

正式上课时，优先使用按日期逐课开放的学生发布仓库创建自己的私有仓库：

[统计学逐课发布仓库](https://hblu.top/gitea/statistics/course-student-release-2026)

这个完整模板保留全部课次，适合查看课程结构、恢复文件和教师维护；如果直接从这里创建私有仓库，可能会提前看到尚未开放的课程。你的作业应保存在自己的私有仓库，不要直接在公共模板上修改。

## 第一次使用

在 Gitea 发布仓库页面点击“使用此模板”，创建自己的私有仓库，然后克隆到电脑：

```bash
git clone 你的私有仓库地址
cd 你的仓库目录
git config user.name "你的姓名"
git config user.email "你的学校邮箱"
python --version
```

Python 需要 3.10 或以上。如果电脑使用 `python3`，把下面的 `python` 换成 `python3`。使用 SSH 克隆和推送前，请先在 Gitea 配置自己的 SSH 密钥；不要把密码、令牌或私钥提交到仓库，也不要发给 AI。

## 每次发布新课时同步

课程按上海时间周一、周三逐课发布。第一次同步前，在自己的仓库根目录添加发布仓库：

```bash
git remote add course-release \
  ssh://git@hblu.top:2222/statistics/course-student-release-2026.git
```

如果提示 `course-release already exists`，说明已经设置过，不要重复添加。

如果你的私有仓库是在同步工具发布前创建的，先升级一次工具：

```bash
git fetch course-release main
git restore --source=course-release/main -- scripts/course.py
git add scripts/course.py
git commit -m "更新课程同步工具"
git push
```

以后教师发布新课后，先保存当前作业，再运行：

```bash
python scripts/course.py sync
```

工具只会新增本地没有的 `lesson-XX` 目录；已经存在的课次会跳过，不会覆盖你的代码、报告或结果。同步后检查暂存内容，再提交：

```bash
git diff --cached
git commit -m "同步课程发布"
git push
```

## 每课的工作流程

以第1课为例，在仓库根目录执行：

```bash
python scripts/course.py start 01
python scripts/course.py run 01
```

然后按这个顺序完成：

1. 阅读 `lesson-01/README.md`，明确问题、分析对象和交付要求；
2. 阅读 `lesson-01/LEARN.md`，理解本课会用到的统计概念；
3. 运行并检查示例程序，再根据自己的问题修改 `analysis.py`；
4. 在 `report.md` 写清楚数据范围、变量、分母、统计方法、结果和局限性；
5. 将支持结论的表、图或数据保存到 `artifacts/`；
6. 在 `submission.json` 中填写报告路径、结果文件和运行命令，并把 `status` 改为 `complete`；
7. 运行检查并提交：

   ```bash
   python scripts/course.py run 01
   python scripts/course.py check 01
   git add lesson-01 requirements.txt
   git commit -m "完成第01课项目"
   git push
   git tag v2-l01-final
   git push origin v2-l01-final
   ```

下一课只需把命令中的 `01` 换成 `02`。每课的 README 会说明该课的具体任务；不要把上一课的结论或代码未经检查地复制成下一课的报告。

## 每课需要提交什么

一份合格的项目通常包括：

- 一个明确、可回答的分析问题；
- 可运行的分析程序；
- 能支持结论的表、图或数据文件；
- 一份说明方法、结果、适用范围和局限性的报告；
- `submission.json` 中正确的路径和运行命令。

自动检查会在临时副本中重新运行程序，检查文件是否存在、路径是否正确、结果能否重现。检查通过不代表统计结论一定合理；你仍需核对分析单位、缺失值、分母、单位和解释。

## 数据、AI 和提交规则

- 课程数据是教学合成数据，不能把结果当作真实学校、企业或个人的事实；
- 原始数据保持不变，清洗后的数据另存；
- 报告中区分“观察到的事实”“可能的解释”和“需要进一步验证的行动”；
- AI 可以协助你，但不能替你决定分析对象、隐瞒失败结果或伪造运行结果；
- 不要提交密码、访问令牌、SSH 私钥或其他个人信息。

## 需要查阅的说明

- [操作与提交步骤](docs/WORKFLOW.md)
- [成果与评分](docs/ASSESSMENT.md)
- [AI 使用建议](docs/AI_USAGE.md)
- [知识自查说明](docs/KNOWLEDGE_CHECK.md)
- [数据总说明](data/README.md)
- [课程逐课发布日程](https://hblu.top/gitea/statistics/course-student-release-2026/src/branch/main/RELEASE_SCHEDULE.md)

每课最后约15分钟进入[知识自查](https://hblu.top/stat-check/)，确认教师已经开放对应场次后再作答。
