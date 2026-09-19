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
    print(f"已开始{lesson}。请阅读本课README和LEARN。")


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
            and 1 <= int(path.name[-2:]) <= 32
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


def sync(root: Path) -> None:
    """Add missing lessons and the reading guide without replacing student work."""
    try:
        current_url = git(root, "remote", "get-url", RELEASE_REMOTE, capture=True).strip()
    except subprocess.CalledProcessError:
        git(root, "remote", "add", RELEASE_REMOTE, os.getenv("COURSE_RELEASE_URL", RELEASE_URL))
        current_url = os.getenv("COURSE_RELEASE_URL", RELEASE_URL)
    if not current_url:
        raise ValueError("课程发布仓库地址为空")
    git(root, "fetch", RELEASE_REMOTE, "main")
    guide_added = sync_reading_guide(root, f"{RELEASE_REMOTE}/main")
    names = git(root, "ls-tree", "--name-only", "-d", f"{RELEASE_REMOTE}/main", capture=True)
    published = sorted(
        name.strip()
        for name in names.splitlines()
        if LESSON_DIR.fullmatch(name.strip()) and 1 <= int(name.strip()[-2:]) <= 32
    )
    if not published and not guide_added:
        print("发布仓库中还没有可同步的课次。")
        return
    missing = [lesson for lesson in published if not ((root / lesson).exists() or (root / lesson).is_symlink())]
    already_present = [lesson for lesson in published if (root / lesson).exists() or (root / lesson).is_symlink()]
    if already_present:
        print("已存在，跳过：" + ", ".join(already_present))
    if not missing and not guide_added:
        print("没有新的课次需要同步。")
        return
    for lesson in missing:
        git(root, "restore", "--source", f"{RELEASE_REMOTE}/main", "--", lesson)
        git(root, "add", "--", lesson)
        print(f"已同步并暂存 {lesson}。")
    print("请检查 git diff --cached，然后提交并推送：git commit -m '同步课程发布' && git push")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "run", "check", "sync", "ci"])
    parser.add_argument("lesson", nargs="?")
    args = parser.parse_args()
    try:
        if args.action == "ci":
            ci(ROOT, os.getenv("GITHUB_REF", ""))
        elif args.action == "sync":
            sync(ROOT)
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
