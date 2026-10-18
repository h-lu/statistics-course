# 第11课更新与检查

第11课已发布；请按教师课堂安排更新。在已有学生 Git 仓库根目录执行；只使用 `main` 发布线。助手只补充缺少的 `lesson-11/`、第11课独立入口及本页，不合并远端分支，不覆盖旧课、个人报告、运行结果或工作流。已有 `lesson-11/` 整个跳过；同名新入口若与发布字节不同，会在新增文件前停止，请先保留个人版本并核对。

```sh
(
  set -eu
  lesson11_helper=$(mktemp)
  trap 'rm -f "$lesson11_helper"' EXIT
  git fetch ssh://git@hblu.top:2222/statistics/course-student-release-2026.git main
  git show FETCH_HEAD:scripts/course_l11.py > "$lesson11_helper"
  python3 "$lesson11_helper" sync --destination "$PWD"
)
```

查看 `git status` 和 `git diff` 后，开始本课并运行起点程序：

```sh
python3 scripts/course_l11.py start 11
python3 scripts/course_l11.py run 11
```

第11课的抽样工具和数据都在本课目录，不需要替换旧的共享数据。程序能运行不表示已完成正式分析。按 README 自主形成方案、取得证据并解释适用范围，再填写自己的报告与 `submission.json` 中的实际运行命令、结果文件；完成后将状态改为 `complete`，检查并复现：

```sh
python3 scripts/course_l11.py check 11
GITHUB_REF=refs/tags/v2-l11-final python3 scripts/course_l11.py ci
```

这个入口独立支持已准备的第01—11课；原 `course.py` 和 `course_l10.py` 保持原样。提交检查核对声明和产物，不判定统计论证质量，也不表示远端 CI 已运行通过。

## 已有仓库的 CI 入口

助手保留已有 `.gitea/workflows/check.yml`。原步骤只认识第01—10课，因此提交第11课最终或修订标签前，需明确做一次人工迁移：找到 `Reproduce submitted project evidence`，保留该步骤的 `env`、环境创建及其他设置，只将 `run` 改为：

```yaml
        run: |
          if [ -f scripts/course_l11.py ]; then
            .venv/bin/python scripts/course_l11.py ci
          elif [ -f scripts/course_l10.py ]; then
            .venv/bin/python scripts/course_l10.py ci
          else
            .venv/bin/python scripts/course.py ci
          fi
```

没有迁移时，旧入口对第11课标签不能完成检查；请核对实际工作流，而不要把本地成功写成远端验收。按既有流程提交自己的工作与成果，原标签继续保留。课包更新不会启用、替换或开放线上正式选择题场次。
