"""Versioned lesson11 start/run/check/ci and missing-only updater.

This standalone helper never imports or replaces an older scripts/course.py.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"not_started", "in_progress", "complete"}
TAG = re.compile(r"^v2-l(\d{2})-(?:final|revision-[1-9]\d*)$")
LESSON_DIR = re.compile(r"^lesson-(\d{2})$")
RELEASE_URL = "ssh://git@hblu.top:2222/statistics/course-student-release-2026.git"
ACTIVE_LESSONS = tuple(range(1, 12))
LESSON11_SHARED = ("scripts/course_l11.py", "docs/LESSON11_UPDATE.md")
EXACT_SHARED = ("scripts/course_l11.py",)
LESSON11_REQUIRED = (
    "lesson-11/analysis.py", "lesson-11/sampling_tools.py", "lesson-11/submission.json",
    "lesson-11/README.md", "lesson-11/LEARN.md", "lesson-11/data/frame.csv",
    "lesson-11/data/strata.csv", "lesson-11/data/provenance.json",
)

def lesson_name(value: str | int) -> str:
    raw = str(value).removeprefix("lesson-")
    if not raw.isdigit() or not 1 <= int(raw) <= 32:
        raise ValueError("课次必须为01—32")
    return f"lesson-{int(raw):02d}"


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
        raise ValueError("提交文件的路径必须是非空的仓库相对路径")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"路径超出仓库：{relative}")
    return path


def manifest(root: Path, lesson: str) -> dict:
    if int(lesson_name(lesson)[-2:]) not in ACTIVE_LESSONS:
        raise ValueError(f"{lesson}：本课只有大纲占位，当前可运行、检查和同步的课次为01—11")
    path = root / lesson / "submission.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("lesson") != lesson:
        raise ValueError(f"{lesson}：submission.json课次不符")
    if obj.get("status") not in STATUSES:
        raise ValueError(f"{lesson}：status应为not_started、in_progress或complete")
    inside(root, obj.get("report", ""))
    paths = obj.get("artifacts")
    if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
        raise ValueError(f"{lesson}：artifacts必须为文件路径列表")
    if len(set(paths)) != len(paths):
        raise ValueError(f"{lesson}：artifacts有重复路径")
    for item in paths:
        inside(root, item)
    command = obj.get("run")
    if not isinstance(command, list) or not command or any(not isinstance(p, str) or not p for p in command):
        raise ValueError(f"{lesson}：run必须为非空命令参数列表")
    return obj


def start(root: Path, lesson: str) -> None:
    obj = manifest(root, lesson)
    if obj["status"] == "complete":
        print(f"{lesson}已有完成声明；继续修订时保留原标签。")
        return
    obj["status"] = "in_progress"
    (root / lesson / "submission.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已开始{lesson}。先读README明确问题与证据要求，自主组织分析；SUPPORT和LEARN按需查看，最后核对标准任务。")


def run(root: Path, lesson: str) -> None:
    command = list(manifest(root, lesson)["run"])
    if command[0] in {"python", "python3"}:
        command[0] = sys.executable
    print(f"运行{lesson}：{' '.join(command)}", flush=True)
    subprocess.run(command, cwd=root, check=True, timeout=600)


def check(root: Path, lesson: str) -> dict:
    obj = manifest(root, lesson)
    if obj["status"] != "complete":
        raise ValueError(f"{lesson}：尚未标记complete；请先完成项目，再检查提交文件")
    report = inside(root, obj["report"])
    if not report.is_file() or report.stat().st_size == 0:
        raise ValueError(f"{lesson}：报告不存在或为空")
    if not obj["artifacts"]:
        raise ValueError(f"{lesson}：请列出支持报告结论的结果文件；仅运行示例代码不等于完成项目")
    for value in obj["artifacts"]:
        evidence = inside(root, value)
        if not evidence.is_file() or evidence.stat().st_size == 0:
            raise ValueError(f"{lesson}：结果文件不存在或为空：{value}")
        if value == obj["report"] or evidence.name == "submission.json":
            raise ValueError(f"{lesson}：结果文件应包含分析结果，不能填写完成声明或报告本身")
    print(f"{lesson}提交文件检查通过；仍需核对分析问题、计算结果和结论。")
    return obj


def digest(root: Path, paths: list[str]) -> dict[str, str]:
    return {p: hashlib.sha256(inside(root, p).read_bytes()).hexdigest() for p in paths}


def reproduce(root: Path, lesson: str) -> None:
    obj = check(root, lesson)
    before = digest(root, obj["artifacts"])
    # Work on a disposable copy: a no-op must not pass by reusing old outputs,
    # and a failed reproduction must not destroy the student's submitted files.
    with tempfile.TemporaryDirectory(prefix="statistics-reproduce-") as temp:
        scratch = Path(temp) / "project"
        shutil.copytree(root, scratch, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        for path in obj["artifacts"]:
            inside(scratch, path).unlink()
        run(scratch, lesson)
        check(scratch, lesson)
        if before != digest(scratch, obj["artifacts"]):
            raise ValueError(f"{lesson}：重新运行得到的结果与已提交文件不同；请检查随机种子，或重新生成结果后提交")


def ci(root: Path, ref: str = "") -> None:
    # A final/revision tag concerns one lesson, even in a partial release.
    if ref.startswith("refs/tags/v2-"):
        match = TAG.fullmatch(ref.removeprefix("refs/tags/"))
        if not match:
            raise ValueError("V2标签应为v2-lNN-final或v2-lNN-revision-N")
        selected = lesson_name(match.group(1))
        check(root, selected)
        reproduce(root, selected)
    else:
        lessons = sorted(
            path.name for path in root.iterdir()
            if path.is_dir() and LESSON_DIR.fullmatch(path.name)
            and int(path.name[-2:]) in ACTIVE_LESSONS
        )
        # A published directory with a missing/bad manifest must still fail.
        objects = {lesson: manifest(root, lesson) for lesson in lessons}
        for lesson, obj in objects.items():
            if obj["status"] == "complete":
                reproduce(root, lesson)
            elif obj["status"] == "in_progress":
                run(root, lesson)
    print("检查结束。尚未开始的项目未计为完成；统计质量由成果评价。")




def _plain_target(root: Path, relative: str) -> Path:
    """Reject symlinks anywhere along a destination before considering a write."""
    target = root / relative
    for part in (target, *target.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"同步路径包含符号链接：{relative}；已有内容保持不变")
    checked = inside(root, relative)
    if checked.exists() and not checked.is_file():
        raise ValueError(f"共享文件路径不是普通文件：{relative}")
    parent = checked.parent
    while parent != root:
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"新增文件的上级路径不是目录：{relative}")
        parent = parent.parent
    return checked


def sync(root: Path) -> None:
    """Only add lesson11 and explicitly required missing files; never replace work."""
    root = root.resolve()

    def _git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root)

    top = Path(_git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != root:
        raise ValueError("同步目标须为已有学生Git仓库的根目录")
    pass  # Statistics uses a versioned standalone entrypoint; no manifest mutation.
    remote = "course-release"
    if remote not in _git("remote").decode().splitlines():
        _git("remote", "add", remote, RELEASE_URL)
    _git("fetch", remote, "main")
    source_ref = _git("rev-parse", f"{remote}/main").decode().strip()
    selected = "lesson-11"
    tree = _git("ls-tree", source_ref, "--", selected).decode()
    if not tree.startswith("040000 tree "):
        raise ValueError("发布仓库尚未提供第11课；未新增课包")
    lesson = root / selected
    if lesson.is_symlink() or (lesson.exists() and not lesson.is_dir()):
        raise ValueError("已有lesson-11不是普通目录；未新增、未覆盖")
    include_lesson = not lesson.exists()
    prefixes = [selected, *LESSON11_SHARED]
    source_files: dict[str, bytes] = {}
    for entry in _git("ls-tree", "-r", source_ref, "--", *prefixes).decode().splitlines():
        metadata, relative = entry.split("\t", 1)
        mode, kind, _ = metadata.split()
        if relative not in LESSON11_SHARED and not relative.startswith(selected + "/"):
            raise ValueError(f"发布路径超出第11课范围：{relative}")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"发布文件须为普通文件：{relative}")
        # An existing lesson is skipped as a whole, even if it is incomplete.
        if include_lesson or not relative.startswith(selected + "/"):
            _plain_target(root, relative)
        source_files[relative] = _git("show", f"{source_ref}:{relative}")
    required = (*LESSON11_SHARED, *LESSON11_REQUIRED)
    missing = [name for name in required if name not in source_files]
    if missing:
        raise ValueError("发布仓库第11课依赖不完整：" + ", ".join(missing))
    for relative in EXACT_SHARED:
        target = _plain_target(root, relative)
        if target.exists() and target.read_bytes() != source_files[relative]:
            raise ValueError(f"已有共享代码或固定数据与发布字节不同：{relative}；未新增、未覆盖，请保留个人版本并先核对兼容性")
    pass  # All lesson11 data is inside the new immutable lesson tree.
    pending: list[tuple[Path, bytes]] = []
    for relative, content in source_files.items():
        if relative.startswith(selected + "/") and not include_lesson:
            continue
        target = _plain_target(root, relative)
        if not target.exists():
            pending.append((target, content))
    for target, content in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(content)
    print("第11课运行/检查请使用：python3 scripts/course_l11.py run 11 / check 11；CI入口参见docs/LESSON11_UPDATE.md。")
    print(f"已补齐{len(pending)}个第11课缺失文件；已有课目录、旧脚本、工作流和结果未覆盖。")
    if not include_lesson:
        print("已存在，跳过整个lesson-11；未用发布文件填补或替换个人课目录。")
    print("查看git status与git diff后，按原提交流程自行提交；本助手不会提交、推送或开放测验场次。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "run", "check", "sync", "ci"])
    parser.add_argument("lesson", nargs="?")
    parser.add_argument("--destination", type=Path,
                        help="仅sync可指定已有学生Git目录；其余动作使用脚本所在目录")
    args = parser.parse_args()
    if args.destination is not None and args.action != "sync":
        parser.error("--destination仅用于sync；start/run/check使用学生目录中的入口")
    try:
        if args.action == "ci":
            ci(ROOT, os.getenv("GITHUB_REF", ""))
        elif args.action == "sync":
            destination = args.destination.resolve() if args.destination is not None else ROOT
            if args.destination is not None and not (destination / ".git").exists():
                raise ValueError("同步目标必须是已有学生Git工作树")
            sync(destination)
        else:
            if args.lesson is None:
                parser.error("请填写课次，如：python scripts/course.py run 03")
            name = lesson_name(args.lesson)
            {"start": start, "run": run, "check": check}[args.action](ROOT, name)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"检查未通过：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
