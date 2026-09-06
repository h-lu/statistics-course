# 学生仓库的按课次发布

教师仓库保留完整 32 课；学生私有仓库不一次性获得全部课次。每次上课前，教师向对应学生仓库只发布下一课目录。

## 发布流程

1. 从 Gitea 克隆学生的私有仓库。
2. 运行：

   ```bash
   python instructor-guide/scripts/publish_student_lesson.py \
     --source lesson-01-first-green \
     --destination /path/to/student-repository \
     --lesson 1
   ```

3. 检查 `git diff`，确认没有覆盖学生已有文件。
4. 提交并推送：

   ```bash
   git add lesson-01
   git commit -m "发布第 1 课"
   git push origin main
   ```

脚本只允许新增不存在的课次目录；如果目标目录已经存在，会停止而不覆盖。学生仓库中的历史提交、已有答案和项目成果不删除。

## 权限与仓库整理

- `course-instructor`：教师私有仓库，保存完整课程、参考材料和题库。
- `course-student-template`：学生仓库起始模板，只作为复制起点。
- 学生团队：不直接授予完整教师仓库或完整模板仓库的读取权；授予各自学生私有仓库权限。
- `course-template`：历史归档仓库，保留用于追溯，不作为当前学生入口。
- 组织内没有明确多余的课程仓库时不执行删除；删除前必须核对仓库名、所有者、是否有学生提交和是否已有归档。
