"""Small, transparent course workflow. Checks delivery, never authorship or reasoning."""
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
RELEASE_REMOTE = "course-release"
RELEASE_URL = "ssh://git@hblu.top:2222/statistics/course-student-release-2026.git"
ACTIVE_LESSONS = tuple(range(1, 11))
ACTIVE_DATASETS = {"service", "alerts", "inference-09-14"}
L10_SUPPORT = ("scripts/course_l10.py",)


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
        raise ValueError(f"{lesson}：本课只有大纲占位，当前可运行、检查和同步的课次为01—10")
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


def git(root: Path, *args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def sync_reading_guide(root: Path, source_ref: str) -> bool:
    """Add the new shared guide only when absent; never replace local material."""
    relative = "docs/READING_GUIDE.md"
    entry = git(root, "ls-tree", source_ref, "--", relative, capture=True).strip()
    if not entry:
        return False  # Older releases do not contain this guide.
    metadata, name = entry.split("\t", 1)
    mode, kind, _ = metadata.split()
    if name != relative or kind != "blob" or mode not in {"100644", "100755"}:
        raise ValueError("发布的阅读指南必须是普通文件")
    target = root / relative
    if target.exists() or target.is_symlink():
        return False
    target = inside(root, relative)  # Reject a docs symlink outside the repository.
    content = git(root, "show", f"{source_ref}:{relative}", capture=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="") as handle:
        handle.write(content)
    git(root, "add", "--", relative)
    print(f"已补齐并暂存 {relative}；已存在的说明文件不会覆盖。")
    return True


def sync_missing_tree(root: Path, source_ref: str, prefix: str, label: str) -> list[str]:
    """只补齐发布仓库中已有、学生仓库中缺少的普通文件。

    数据与检查工具同课次分开存放，可能随发布新增。这里不替换
    已存在文件，因此既能补齐发布文件，也不会覆盖学生改动。
    """
    listing = git(root, "ls-tree", "-r", source_ref, "--", prefix, capture=True)
    added: list[str] = []
    for entry in listing.splitlines():
        metadata, relative = entry.split("\t", 1)
        mode, kind, _ = metadata.split()
        if prefix == "data":
            parts = relative.split("/")
            # An old remote data/README may still link to retired future data.
            # Sync only the two authored shared datasets, never that overview.
            if len(parts) < 3 or parts[1] not in ACTIVE_DATASETS:
                continue
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"发布的{label}必须是普通文件：{relative}")
        if relative != prefix and not relative.startswith(prefix + "/"):
            raise ValueError(f"发布路径超出 {prefix}/：{relative}")
        target = root / relative
        if target.exists() or target.is_symlink():
            continue
        target = inside(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        git(root, "restore", "--source", source_ref, "--", relative)
        git(root, "add", "--", relative)
        added.append(relative)
    if added:
        print(f"已补齐并暂存{label}{len(added)}个；已存在的文件不会覆盖。")
    return added


def released_support(root: Path, source_ref: str, lessons: list[str]) -> dict[str, bytes]:
    """Resolve explicitly required versioned code when lesson 10 is published."""
    if "lesson-10" not in lessons:
        return {}
    contents = {}
    for relative in L10_SUPPORT:
        entry = git(root, "ls-tree", source_ref, "--", relative, capture=True).strip()
        if not entry:
            raise ValueError(f"第10课缺少发布依赖：{relative}")
        metadata, name = entry.split("\t", 1)
        mode, kind, _ = metadata.split()
        if name != relative or kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"发布依赖必须是普通文件：{relative}")
        contents[relative] = subprocess.run(
            ["git", "show", f"{source_ref}:{relative}"], cwd=root,
            check=True, capture_output=True,
        ).stdout
    return contents


def preflight_support(root: Path, contents: dict[str, bytes]) -> None:
    """Check code conflicts before copying/staging anything; never execute local code."""
    for relative, incoming in contents.items():
        if (root / relative).is_symlink():
            raise ValueError(f"共享代码路径不是普通文件：{relative}；保留已有文件")
        target = inside(root, relative)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f"共享代码路径不是普通文件：{relative}；保留已有文件")
        if target.exists() and target.read_bytes() != incoming:
            raise ValueError(
                f"共享代码与发布版本不兼容：{relative}；未覆盖任何文件。"
                "请保留个人修改，并为不同实现使用新的模块名"
            )


def add_missing_support(root: Path, contents: dict[str, bytes]) -> list[str]:
    added = []
    for relative, incoming in contents.items():
        target = inside(root, relative)
        if target.exists() or target.is_symlink():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(incoming)
        git(root, "add", "--", relative)
        added.append(relative)
    return added


def sync(root: Path) -> None:
    """Add missing lessons and released support files without replacing student work."""
    try:
        current_url = git(root, "remote", "get-url", RELEASE_REMOTE, capture=True).strip()
    except subprocess.CalledProcessError:
        git(root, "remote", "add", RELEASE_REMOTE, os.getenv("COURSE_RELEASE_URL", RELEASE_URL))
        current_url = os.getenv("COURSE_RELEASE_URL", RELEASE_URL)
    if not current_url:
        raise ValueError("课程发布仓库地址为空")
    git(root, "fetch", RELEASE_REMOTE, "main")
    source_ref = f"{RELEASE_REMOTE}/main"
    names = git(root, "ls-tree", "--name-only", "-d", source_ref, capture=True)
    published = sorted(
        name.strip()
        for name in names.splitlines()
        if LESSON_DIR.fullmatch(name.strip()) and int(name.strip()[-2:]) in ACTIVE_LESSONS
    )
    missing = [lesson for lesson in published if not ((root / lesson).exists() or (root / lesson).is_symlink())]
    already_present = [lesson for lesson in published if (root / lesson).exists() or (root / lesson).is_symlink()]
    required = released_support(root, source_ref, published)
    preflight_support(root, required)
    runner_added = add_missing_support(root, required)
    guide_added = sync_reading_guide(root, source_ref)
    data_added = sync_missing_tree(root, source_ref, "data", "课程数据")
    tests_added = sync_missing_tree(root, source_ref, "tests", "检查测试")
    workflows_added = sync_missing_tree(root, source_ref, ".gitea/workflows", "自动检查配置")
    support_added = bool(runner_added or guide_added or data_added or tests_added or workflows_added)
    if not published and not support_added:
        print("发布仓库中还没有可同步的课次。")
        return
    if already_present:
        print("已存在，跳过：" + ", ".join(already_present))
    if not missing and not support_added:
        print("没有新的课次需要同步。")
        return
    for lesson in missing:
        git(root, "restore", "--source", f"{RELEASE_REMOTE}/main", "--", lesson)
        git(root, "add", "--", lesson)
        print(f"已同步并暂存 {lesson}。")
    if "lesson-10" in missing:
        print("第10课兼容入口如下；已有scripts/course.py没有被覆盖：")
        for action in ("start", "run", "check"):
            print(f"python3 scripts/course_l10.py {action} 10")
    print("请检查 git diff --cached，然后提交并推送：git commit -m '同步课程发布' && git push")


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
