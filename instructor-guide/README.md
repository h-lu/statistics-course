# 统计学项目课：教师授课与课程编写指南

学期为32次、每次90分钟。当前制作第1–8课的学习页、教师讲解页、分层练习和过程答案；第9–32课仅有[课程地图](COURSE_MAP.md)与占位说明。学生全程可以使用AI，评价统计判断、可复核结果和解释范围。评分保持[原规则](GRADING.md)。

## 编写和授课入口

- [32课课程地图](COURSE_MAP.md)：唯一现行学期设计，含递进、先修、例子、90分钟分段、独立任务与贯穿项目。
- [课程设计标准](COURSE_DESIGN_STANDARD.md)、[术语与基础知识规范](TERMINOLOGY_AND_FOUNDATIONS.md)、[学生材料编写规范](STUDENT_MATERIALS_STANDARD.md)。
- [内容编写约定](AUTHORING_INTERFACE.md)、[课堂操作清单](CLASSROOM.md)、[逐课发布边界](STUDENT_LESSON_RELEASE.md)。
- [知识自查设计](knowledge-check/DESIGN.md)、[题库格式与历史保护](knowledge-check/question-bank/SCHEMA.md)。
- [完整旧材料归档与恢复](../archive/redesign-2026-10-09/README.md)。

第1–8课的 `RUNBOOK.md` 放90分钟安排、讲解与六问设计审查，`REFERENCE.md` 和 `reference.py` 放教师过程答案与可复核计算。参考路线不是唯一答案。第9–32课目录只含 README 占位，不作为教学、运行、同步或发布入口。旧整学期复核与发布记录位于 `archive/redesign-2026-10-09/old-documents/`，用于历史追溯。

当前自查新场次只列第1–8课：第5课为 `v2-l05-r4`，其余为r3；生产实际版本以部署状态为准。本地归档不改线上服务。原第9–32课全部旧ID仍可读，原题、答案和历史得分不改写。

## 完成快照与基础设施

`roster/roster.example.csv` 仍是示例，真实名单与只读令牌不入库。原 `scripts/course_status.py` 保留32课历史标签查询能力，用于已有提交追溯；它不发布课包，不改变评分，也不从大纲占位推断完成状态。

[学生账号与权限方案](GITEA_STUDENT_ACCESS_PLAN.md)和[V1归档](archive/v1-2026-09-05/README.md)保留为基础设施及历史参考。课程重写不改学生仓库、账号、提交、成绩、原自查场次或数据库。
