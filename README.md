# 统计学课程

这是面向 AI 时代的项目制统计学课程资料库。课程以 16 周、32 次课组织，学生可以使用 AI 完成编程、计算、分析与写作，但需要对统计口径、分析选择、结论依据和适用范围负责。

## 目录

- `instructor-guide/`：教师课程标准、32 课设计、运行手册、知识自查题库与参考材料。
- `student-template/`：完整 32 课学生模板归档；实际 Gitea 学生仓库按教学进度逐课发布。
- `stat-check/`：课末知识自查服务，支持 Gitea 登录、A 版基础题、AI 学习、B 版变式题和教师统计。

机器学习课程不纳入本仓库。历史版本保留在各自仓库的 Git 历史和归档标签中。

## 课程设计入口

- [课程设计标准](instructor-guide/COURSE_DESIGN_STANDARD.md)
- [32 课总表](instructor-guide/COURSE_MAP.md)
- [按课次发布学生仓库](instructor-guide/STUDENT_LESSON_RELEASE.md)
- [学生模板](student-template/README.md)
- [知识自查设计](instructor-guide/knowledge-check/DESIGN.md)

## 本地运行知识自查

```bash
cd stat-check
python3 -m pytest -q
```

生产部署配置和真实凭据不放入本仓库。
