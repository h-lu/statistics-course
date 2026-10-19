# 第11课首次使用

使用前面课程已建立的学生仓库，确认 Python 3.10 或以上可用。尚未建立仓库时，按[学生仓库首页](../README.md#第一次使用)完成准备。

在自己的学生仓库 `main` 工作树根目录操作。若缺少 `lesson-11/`，先取得本课材料：

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

开始本课并运行起点程序：

```sh
python3 scripts/course_l11.py start 11
python3 scripts/course_l11.py run 11
```

起点程序运行100人小例并检查公开名册，生成 `lesson-11/artifacts/example.json`。接着按[本课任务](../lesson-11/README.md)制定自己的正式调查方案。

## 提交检查

完成作品后，按[提交流程](WORKFLOW.md)登记报告、运行命令和产物，再运行：

```sh
python3 scripts/course_l11.py check 11
```

在 `.gitea/workflows/check.yml` 的 `Reproduce submitted project evidence` 步骤中，保留 `env` 等其他设置，将 `run` 设为：

```yaml
run: .venv/bin/python scripts/course_l11.py ci
```

提交后查看实际自动检查结果。
