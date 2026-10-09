#!/usr/bin/env python3
"""Verify teaching-source snapshots and restore to a new local directory."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
PACKAGES = ("source-tracked", "lessons-01-08", "lessons-09-32-and-specific-assets", "old-course-documents")

def verified_members(package: str) -> list[tuple[dict, bytes, int]]:
    manifest = json.loads((HERE / f"{package}.manifest.json").read_text(encoding="utf-8"))
    rows = manifest["files"]
    expected = json.loads((HERE / "verification.json").read_text(encoding="utf-8"))[package]
    archive = HERE / f"{package}.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected["archive_sha256"]:
        raise ValueError(f"Archive hash mismatch: {package}")
    content = []
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        if len(members) != len(rows) or {m.name for m in members} != {r["path"] for r in rows}:
            raise ValueError(f"Member inventory mismatch: {package}")
        by_name = {m.name: m for m in members}
        for row in rows:
            name = PurePosixPath(row["path"])
            member = by_name[row["path"]]
            if name.is_absolute() or ".." in name.parts or not member.isfile():
                raise ValueError(f"Unsafe member: {name}")
            data = handle.extractfile(member).read()
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError(f"Member byte/hash mismatch: {name}")
            content.append((row, data, member.mode))
    return content

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", choices=PACKAGES, default="source-tracked")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    content = verified_members(args.package)
    print(f"Verified {args.package}: {len(content)} files, {sum(row['bytes'] for row, _, _ in content)} bytes")
    if args.verify_only:
        return 0
    if args.destination is None:
        parser.error("Restore requires --destination pointing to a new, empty directory")
    destination = args.destination.resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Destination must be a new or empty directory; existing files are never overwritten")
    destination.mkdir(parents=True, exist_ok=True)
    for row, data, mode in content:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
        target.chmod(mode & 0o777)
    print(f"Restored to {destination}; verify and selectively copy required paths after review")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
