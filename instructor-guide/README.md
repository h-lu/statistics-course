# 统计学项目课：教师授课与课程编写指南

现行版本V2。学生可以全程使用AI；32次课分别完成有实际用途的统计项目。知识材料建立共同语言，课末自查帮助学习，课程不设置AI鉴定或额外闭卷环节。

## 编写和审核

- [课程设计标准](COURSE_DESIGN_STANDARD.md)：主任务难度、开放选择、知识连接与六项设计检查。
- [16周32课总表](COURSE_MAP.md)：唯一现行学期映射。
- [术语与基础知识规范](TERMINOLOGY_AND_FOUNDATIONS.md)：规范术语、通俗解释与知识层次。
- [本次术语与文字修订](LANGUAGE_REVIEW.md)：全32课检查范围、统计含义核对与验证结果。
- [评分规则](GRADING.md)：平时50分、代表作修订和补交口径。
- [课堂操作清单](CLASSROOM.md)：课前、课中、课后的操作安排。
- [发布与历史迁移](MIGRATION_V2.md)：归档、学生已有仓库与自查记录的兼容要求。
- [内容编写约定](AUTHORING_INTERFACE.md)：课程作者使用的路径与题库约定。
- [V2发布与核验记录](RELEASE_V2.md)：本次重建内容、运行测试、交叉审查与尚待试教部分。

每课目录`lesson-01`至`lesson-32`含`RUNBOOK.md`和`REFERENCE.md`，提供课堂安排、可接受分析路线、参考计算与六项设计检查。参考路线不是唯一正确答案。

学生使用[学生项目仓库](https://hblu.top/gitea/statistics/course-student-template)，不克隆本仓库。每课最后约15分钟使用[知识自查教师页](https://hblu.top/stat-check/teacher)，选择当节课的新版本题库（ID为`v2-lNN-r1`），新建自查场次。

## 课末完成快照

按`roster/roster.example.csv`填写不入库的`roster/roster.csv`，在已设置教师只读令牌的终端运行：

```bash
python3 scripts/course_status.py lesson-03 --roster roster/roster.csv --csv
```

课末保存输出；下次课前另存一次补交快照。脚本检查V2最终标签、完成声明与CI，不判断统计质量，不记录实际服务器接收时刻，也不应拿它判断课中学生是否落后。`checked_at`是快照检查时间。

## 历史与基础设施

- [V1归档与恢复](archive/v1-2026-09-05/README.md)：旧总计划及三个仓库完整历史。
- [学生账号与权限方案](GITEA_STUDENT_ACCESS_PLAN.md)：保留的基础设施执行参考。实施状态需按服务器核对，不能因课程重写就认为已全部实施。
- [知识自查设计](knowledge-check/DESIGN.md)、[实现与维护](knowledge-check/IMPLEMENTATION.md)。

本仓库保持Private；学生团队不加入本仓库。课程重写不改学生账号、学生提交、原自查场次或数据库内容。新旧题库按不同ID并存。
