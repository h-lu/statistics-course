# 统计学 2026–2027：学习材料改进

保留原32课主线、模块用途与评分；课程按每次90分钟组织，学生可以全程使用AI，需对统计问题、分析单位、分母、方法依据和结论范围负责。现行学期设计见[32课课程地图](instructor-guide/COURSE_MAP.md)。当前实际制作范围为第1–8课；第9–32课只保留大纲占位，新课包尚未制作。

- [学生学习材料](student-template/README.md)：第1–8课任务、学习页、分层练习、合成数据和运行工具。
- [教师材料](instructor-guide/README.md)：课程规范、10/65/15课堂安排、过程答案和评价依据。
- [知识自查](stat-check/README.md)：当前可新建场次为第1–8课；全部旧题库ID继续可供历史场次读取。
- [重设计前完整归档与恢复](archive/redesign-2026-10-09/README.md)：原1–8课、原9–32课、旧大纲和全部tracked教学文件的逐路径SHA-256与恢复工具。

学生从本课README了解情境、目标、资源、约束和证据标准，可直接自主分析，遇阻时任选SUPPORT提示或LEARN解释与小例。至少两项会影响结论的重要决定由学生作出，允许多个合理方法与有证据的保留意见。基础练习帮助开始；标准任务要求完成统计判断；提高与拓展比较合理规则、敏感性或决策后果。教学合成数据须明确标注，不能当作真实机构事实。

课程规范以[课程设计标准](instructor-guide/COURSE_DESIGN_STANDARD.md)、[术语与基础知识规范](instructor-guide/TERMINOLOGY_AND_FOUNDATIONS.md)、[学生材料规范](instructor-guide/STUDENT_MATERIALS_STANDARD.md)和[评分规则](instructor-guide/GRADING.md)为准。本次不改评分，不修改真实学生仓库、已发布课次、账号、成绩或历史场次。教学内容发布到GitHub main；课程服务器部署和新题库场次启用须另行操作，不随本次发布执行。

本地结构与运行核验：

```bash
python3 instructor-guide/scripts/validate_course.py --student student-template --run
python3 -m unittest discover -s student-template/tests -v
cd stat-check
python3 -m pytest -q
```

[独立质量审核](instructor-guide/REDESIGN_QA.md)记录实跑、概念与数值检查。最新模拟课堂操作见[第1–4课](instructor-guide/FINAL_STUDENT_SIMULATION_01_04.md)、[第5–7课](instructor-guide/FINAL_STUDENT_SIMULATION_05_07.md)和[第8课](instructor-guide/FINAL_STUDENT_SIMULATION_08.md)。[学习改进框架](instructor-guide/REDESIGN_FRAMEWORK_2026-10-09.md)说明原设计继承与当前边界。

运行成功和文件检查不等于统计论证已经合格，也不等于真实学生90分钟试教通过。当前课次边界在检查、运行、同步、发布和新场次目录中均明确设为第1–8课；后续占位不会执行旧内容。
