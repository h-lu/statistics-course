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

所有命令都从仓库根目录运行，也就是能看到 `scripts`、`data` 和已开放课次目录的位置。

## 2. 同步新发布的课程

先保存当前作业，再运行：

```bash
python scripts/course.py sync
git diff --cached
git commit -m "同步课程发布"
git push
```

`sync` 只新增没有的 `lesson-XX` 目录，不覆盖已经存在的代码、报告或结果。若没有新课，也可能补齐发布仓库提供的共享说明文件。

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
