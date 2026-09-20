# 统计学项目课

这是面向 AI 时代的项目制统计学课程资料库。课程按 16 周、32 次课组织。学生可以使用 AI 编程、计算、分析和写作，但要对统计口径、分析选择、结论依据和适用范围负责。

## 先看哪一部分

本仓库包含三类材料：

- [`instructor-guide/`](instructor-guide/)：教师使用的课程标准、32课地图、授课运行手册、知识自查题库和参考材料；
- [`student-template/`](student-template/)：完整的32课学生模板，包含数据、示例程序、每课任务和提交工具；
- [`stat-check/`](stat-check/)：课末知识自查服务，支持Gitea登录、A版基础题、学习阶段、B版变式题和教师统计。

正式上课时，学生不要直接从完整模板开始。学生应从 hblu.top 的逐课发布仓库创建自己的私有仓库，按课程进度获得材料：

[统计学逐课学生发布仓库](https://hblu.top/gitea/statistics/course-student-release-2026)

完整模板适合教师维护、查看全部课程结构或查找后续课次；它会提前包含尚未开放的课程。

## 学生材料怎样组织

每课目录通常包含：

- `README.md`：本课问题、数据、分析任务和需要提交的内容；
- `SUPPORT.md`：从第一步开始的入门跟做、概念提示、反思问题和提高路径；
- `LEARN.md`：统计术语、原理、手算例子和适用条件；
- `analysis.py`：可以运行的示例程序，不是完整作业答案；
- `report.md`、`submission.json` 和 `artifacts/`：学生的报告、提交声明和结果文件。

学生材料先使用通俗语言，再给出统计学社区通行术语。报告应区分“观察到的事实”“可能的解释”和“需要进一步验证的行动”。课程数据是教学合成数据，不能写成现实学校、企业或个人的事实。

## 课程设计入口

- [课程设计标准](instructor-guide/COURSE_DESIGN_STANDARD.md)
- [32课课程地图](instructor-guide/COURSE_MAP.md)
- [学生材料编写规范](instructor-guide/STUDENT_MATERIALS_STANDARD.md)
- [逐课发布说明](instructor-guide/STUDENT_LESSON_RELEASE.md)
- [完整学生模板](student-template/README.md)
- [知识自查设计](instructor-guide/knowledge-check/DESIGN.md)
- [工作区编写规则](AGENTS.md)

## 本地检查

修改课程材料后，先检查相关文件和链接，再运行知识自查测试：

```bash
cd stat-check
python3 -m pytest -q
```

生产部署配置、真实账号凭据和数据库不放入 Git。课程内容发布到Gitea前，应确认发布仓库只包含当前开放课次，并检查链接、命令、示例数字和 `git diff --check`。
