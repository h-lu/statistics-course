#!/usr/bin/env python3
"""Publish one additional lesson into a student's working repository.

The destination is a local clone of one student's private Gitea repository.
The script is deliberately conservative: it never removes an existing lesson,
never overwrites student work, and only copies the requested lesson directory.
The teacher reviews the diff and performs the normal git commit/push.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="完整教师/模板工作树")
    parser.add_argument("--destination", type=Path, required=True, help="学生私有仓库工作树")
    parser.add_argument("--lesson", type=int, required=True, choices=range(1, 33))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source / f"lesson-{args.lesson:02d}"
    destination = args.destination / source.name
    if not source.is_dir():
        raise SystemExit(f"源课次不存在：{source}")
    if not (args.destination / ".git").exists():
        raise SystemExit(f"目标不是 Git 工作树：{args.destination}")
    if destination.exists():
        raise SystemExit(f"目标课次已存在，为避免覆盖学生修改而停止：{destination}")
    shutil.copytree(source, destination)
    print(f"已发布 {source.name}。请检查 git diff 后再提交和推送。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
