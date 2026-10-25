# 取得第13、14课，保留个人成果

继续原课程个人仓库，不另建一个。先确认course-release指向原发布仓库：

`ssh://git@hblu.top:2222/statistics/course-student-release-2026.git`

若尚无此remote，按前课方式添加；若已有但地址不同，先核对，不自动改地址。然后在个人仓库根目录执行：

```sh
git fetch course-release main
git show course-release/main:scripts/course_l1314.py > /tmp/course_l1314.py
python3 /tmp/course_l1314.py sync --destination "$PWD"
```

工具只增加缺失新文件；已有lesson-13/14整目录跳过。共享依赖不同则先停止，保留个人版本核对，不覆盖旧课、报告、结果、工作流。sync不会替你提交或推送。机器学习仅在成功补齐后给学生活跃清单追加13/14，教师题库不变。

之后可用`python3 scripts/course_l1314.py start 13`，按本课说明运行；完成报告后check、ci，再沿用v2-l13-final或v2-l14-final标签。run保持原命令参数列表格式。

## 已有个人仓库的标签路由

机器学习原`scripts/course.py ci`会读取追加后的active_lessons，原工作流可继续用。统计学旧工作流需要在第12课判断之前增加一个分支：当GITHUB_REF匹配`refs/tags/v2-l13-final`、`v2-l14-final`或相应revision-N时，调用`.venv/bin/python scripts/course_l1314.py ci`，其他课保留原分支。新模板已含此路由；sync不覆盖个人工作流，先查看发布版`.gitea/workflows/check.yml`，只合并这个分支后自行提交。若暂未合并，仍可本地check/ci，但不能称该新课标签已通过线上检查。

模型资源已在机器学习发布树，课前准备依赖，不要求学生课堂下载模型。教师最终留出仍另存；网页课包不包含标签、参考答案或新测验激活操作。
