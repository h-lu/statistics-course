#!/usr/bin/env python3
"""Publish one additional lesson into a student's working repository.

The destination is a local clone of one student's private Gitea repository.
The script is deliberately conservative: it never removes an existing lesson,
never overwrites student work, and copies only a missing requested lesson,
reading guide and (for lesson 10) versioned runtime. Existing lesson directories
are skipped in full; missing support files can still be added.
The teacher reviews the diff and performs the normal git commit/push.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ACTIVE_LESSONS = tuple(range(1, 11))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="完整教师/模板工作树")
    parser.add_argument("--destination", type=Path, required=True, help="学生私有仓库工作树")
    parser.add_argument("--lesson", type=int, required=True, choices=ACTIVE_LESSONS,
                        help="当前可在本地补齐的课次：01—10；不推送或部署")
    parser.add_argument("--dry-run", action="store_true", help="只作本地预检，不复制文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source / f"lesson-{args.lesson:02d}"
    destination = args.destination / source.name
    if not source.is_dir():
        raise SystemExit(f"源课次不存在：{source}")
    if not (args.destination / ".git").exists():
        raise SystemExit(f"目标不是 Git 工作树：{args.destination}")
    lesson_present = destination.exists() or destination.is_symlink()
    if lesson_present and args.lesson != 10:
        print(f"目标课次已存在，整课跳过以保留学生修改：{destination}")
        return 0
    support = []
    if args.lesson == 10:
        relative = Path("scripts/course_l10.py")
        support_source = args.source / relative
        support_target = args.destination / relative
        if support_source.is_symlink() or not support_source.is_file():
            raise SystemExit(f"第10课缺少普通文件依赖：{support_source}")
        if not support_target.resolve().is_relative_to(args.destination.resolve()):
            raise SystemExit("共享代码目标路径超出学生仓库")
        if support_target.exists() or support_target.is_symlink():
            if support_target.is_symlink() or not support_target.is_file() or support_target.read_bytes() != support_source.read_bytes():
                raise SystemExit(f"共享代码与发布版本不兼容：{relative}；未覆盖任何文件，请使用新的模块名")
        else:
            support.append((support_source, support_target))
    guide_source = args.source / "docs/READING_GUIDE.md"
    guide_destination = args.destination / "docs/READING_GUIDE.md"
    copy_guide = guide_source.exists() and not (
        guide_destination.exists() or guide_destination.is_symlink()
    )
    if copy_guide:
        if guide_source.is_symlink() or not guide_source.is_file():
            raise SystemExit("源阅读指南必须是普通文件")
        if not guide_destination.resolve().is_relative_to(args.destination.resolve()):
            raise SystemExit("阅读指南目标路径超出学生仓库")
    if args.dry_run:
        print(f"本地预检通过：{source.name}；将只补缺课次和依赖，未复制任何文件。")
        return 0
    if not lesson_present:
        shutil.copytree(source, destination)
    for support_source, support_target in support:
        support_target.parent.mkdir(parents=True, exist_ok=True)
        with support_source.open("rb") as src, support_target.open("xb") as dst:
            shutil.copyfileobj(src, dst)
    if copy_guide:
        guide_destination.parent.mkdir(parents=True, exist_ok=True)
        with guide_source.open("rb") as src, guide_destination.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        print("已补齐 docs/READING_GUIDE.md；没有覆盖任何已有说明文件。")
    if lesson_present:
        print(f"{source.name}已存在，整课跳过；只补缺少的支持文件。")
    else:
        print(f"已发布 {source.name}。请检查 git diff 后再提交和推送。")
    if args.lesson == 10:
        print("旧scripts/course.py保持原样；第10课兼容入口如下：")
        for action in ("start", "run", "check"):
            print(f"python3 scripts/course_l10.py {action} 10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
