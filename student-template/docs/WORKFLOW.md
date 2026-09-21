# 项目操作与提交步骤

## 1. 创建自己的私有仓库

在发布仓库页面点击“使用此模板”，创建私有仓库，再复制页面显示的地址：

```bash
git clone 你的仓库地址
cd 你的仓库目录
git config user.name "你的姓名"
git config user.email "你的学校邮箱"
python --version
git status
```

所有命令都从仓库根目录运行，也就是能看到 `scripts`、`data` 和已开放课次目录的位置。Python 需要 3.10 或以上；如果电脑使用 `python3`，把本文命令中的 `python` 换成 `python3`。

## 2. 同步新发布的课程

第一次同步前，在自己的仓库根目录添加课程发布仓库；如果提示 `course-release already exists`，说明已经设置过，不要重复添加：

```bash
git remote add course-release \
  ssh://git@hblu.top:2222/statistics/course-student-release-2026.git
```

如果教师通知了工具更新，或旧仓库缺少 `tests/`、`.gitea/workflows/check.yml`，先更新 `scripts/course.py`。更新前保存并提交当前修改；若你曾自行修改这个脚本，先向教师说明，不要直接覆盖：

```bash
git fetch course-release main
git restore --source=course-release/main -- scripts/course.py
git add scripts/course.py
git commit -m "更新课程同步工具"
git push
```

然后运行同步；以后每次发布新课时，先保存当前作业，再运行同一条命令：

```bash
python scripts/course.py sync
```

`sync` 会补齐发布仓库已经提供、本地尚缺少的内容：已发布的 `lesson-XX` 课次目录、`data/` 数据文件、`tests/` 检查程序、`.gitea/workflows/check.yml` 自动检查配置和 `docs/READING_GUIDE.md` 阅读指南。即使没有新课，也能补齐这些缺少的共用文件。

已有课次目录会跳过，已有代码、报告、数据、结果和共用文件不会被覆盖。`sync` 不会更新 `scripts/course.py` 自身；旧工具需要先按上面的命令升级，才能补齐检查程序和自动检查配置。

新增文件会自动暂存。检查内容后提交并推送；如果没有新增文件，就跳过提交和推送：

```bash
git diff --cached
git commit -m "同步课程发布"
git push
```

## 3. 完成一课

以第3课为例：

```bash
python scripts/course.py start 03
python scripts/course.py run 03
```

阅读 `lesson-03/README.md`、`SUPPORT.md` 和 `LEARN.md`，再修改程序和报告。原始数据不手工改写，处理后的数据和图表另存到 `lesson-03/artifacts/`。

在 `lesson-03/submission.json` 中填写：

```json
{
  "lesson": "lesson-03",
  "status": "complete",
  "report": "lesson-03/report.md",
  "artifacts": ["lesson-03/artifacts/evidence.csv"],
  "run": ["python", "lesson-03/analysis.py"]
}
```

路径都相对于仓库根目录；`evidence.csv` 只是示例，换成你真正生成的文件。结果文件必须能由 `run` 命令重新生成。

检查和提交：

```bash
python scripts/course.py run 03
python scripts/course.py check 03
git status
git diff
git add lesson-03 requirements.txt
git commit -m "完成第03课项目"
git push
git tag v2-l03-final
git push origin v2-l03-final
```

`check` 只检查完成状态、路径和文件，不判断统计方法或结论是否合理。自动检查会在临时副本中重新运行程序；固定随机种子、排序和输出精度，避免结果每次不同。

## 4. 修订作品

不要覆盖已有最终标签。修订时保留原版本，在报告中写明修改和依据，使用新的标签，例如 `v2-l03-revision-1`。
