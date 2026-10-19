# 第11课更新与检查

在已有学生 Git 仓库根目录执行以下更新，只使用 `main`。本次同时修复第11课的临时复现目录问题：原版检查工具先备份，再单独升级；个人修改过的工具会停止，留待人工核对。课目录、报告、产物和工作流仍保留。

已有第11课者请先打开[发布库中的本页](https://hblu.top/gitea/statistics/course-student-release-2026/src/branch/main/docs/LESSON11_UPDATE.md)新版，本地旧说明不会自动替换。

```sh
(
  set -eu
  lesson11_release=ssh://git@hblu.top:2222/statistics/course-student-release-2026.git
  configured_release=$(git config --get remote.course-release.url || true)
  if [ -n "$configured_release" ] && [ "$configured_release" != "$lesson11_release" ]; then
    echo "course-release指向其他地址，请先核对本课发布仓库。" >&2
    exit 1
  fi
  lesson11_helper=$(mktemp)
  trap 'rm -f "$lesson11_helper"' EXIT
  git fetch "$lesson11_release" main
  git show FETCH_HEAD:scripts/course_l11.py > "$lesson11_helper"
  python3 - "$lesson11_helper" <<'PY'
from pathlib import Path
import hashlib, os, sys, tempfile

old_sha = "d4fadd4fa62b30ea9a384757ce6569e1c9d3d222a292aec384a4833d57f8c764"
new_sha = "fe6ee212ae000c2aff9eed5bd85ff19f95c9c00e9962528bc20b18f39a415725"
sha = lambda data: hashlib.sha256(data).hexdigest()
candidate = Path(sys.argv[1]).read_bytes()
if sha(candidate) != new_sha:
    raise SystemExit("发布工具版本不符，未替换本地工具。")
target = Path("scripts/course_l11.py")
if target.is_symlink() or target.parent.is_symlink():
    raise SystemExit("工具路径是符号链接，请人工核对。")
if target.exists():
    original = target.read_bytes()
    if original != candidate:
        if sha(original) != old_sha:
            raise SystemExit("本地工具有个人修改，已保留；请人工核对后升级。")
        with tempfile.NamedTemporaryFile(prefix="course-l11-backup-", suffix=".py", delete=False) as backup:
            backup.write(original)
        assert sha(Path(backup.name).read_bytes()) == old_sha
        print("原检查工具备份：", backup.name)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".course-l11-", delete=False) as output:
            output.write(candidate)
        pending = Path(output.name)
        try:
            if target.read_bytes() != original:
                raise SystemExit("升级期间本地工具发生变化，已停止。")
            os.replace(pending, target)
        finally:
            pending.unlink(missing_ok=True)
        assert sha(target.read_bytes()) == new_sha
PY
  python3 "$lesson11_helper" sync --destination "$PWD"
)
```

已有 `lesson-11/` 会整目录跳过。可直接在线阅读发布库最新的 README、LEARN、SUPPORT 和练习；如需本地更新，只取这些教学说明及 `data/README.md`，先保存自己的批注，保留 `report.md`、`submission.json`、配置、代码和 `artifacts`。

查看 `git status` 和 `git diff` 后，开始本课并运行起点程序：

```sh
python3 scripts/course_l11.py start 11
python3 scripts/course_l11.py run 11
```

完成分析后，在 `submission.json` 登记实际运行命令和结果，将状态改为 `complete`。`check` 核对提交文件，标签 `ci` 在临时副本重跑复现：

```sh
python3 scripts/course_l11.py check 11
GITHUB_REF=refs/tags/v2-l11-final python3 scripts/course_l11.py ci
```

本地检查通过后，按原流程提交。已有最终标签保留，工具修复按既有修订流程使用新标签；原 `course.py` 和 `course_l10.py` 保留。

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

工作流迁移后，查看实际远端CI结果。线上选择题场次仍由教师另行开放。
