"""Read-only structural checks and optional execution of V2 student starting points."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import yaml

TEACHER = Path(__file__).resolve().parents[1]


def local_links(path: Path, root: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    errors = []
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        link = link.strip().strip("<>")
        if urlsplit(link).scheme or link.startswith(("#", "/")):
            continue
        target = unquote(link.split("#")[0].split("?")[0])
        if not target:
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.is_relative_to(root.resolve()):
            errors.append(f"{path.relative_to(root)}: link leaves repository: {link}")
        elif not resolved.exists():
            errors.append(f"{path.relative_to(root)}: missing link: {link}")
    return errors


def validate(student: Path, execute: bool = False) -> dict:
    errors = []
    stats = {"lessons": 0, "questions": 0, "starting_points_run": 0, "data_files": 0}
    banks = TEACHER / "knowledge-check/question-bank"
    for n in range(1, 33):
        lesson = f"lesson-{n:02d}"
        for root, files in [(student, ["README.md", "LEARN.md", "analysis.py", "report.md", "submission.json"]), (TEACHER, ["RUNBOOK.md", "REFERENCE.md", "reference.py"])]:
            for file in files:
                path = root / lesson / file
                if not path.is_file() or path.stat().st_size == 0:
                    errors.append(f"missing {root.name}/{lesson}/{file}")
        meta_path = student / lesson / "submission.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                assert meta["lesson"] == lesson and meta["status"] == "not_started"
                assert isinstance(meta["run"], list) and meta["run"]
                assert meta["artifacts"] == []
            except (ValueError, KeyError, AssertionError):
                errors.append(f"{lesson}: invalid initial manifest")
        bank_path = banks / f"lesson-v2r1-{n:02d}.yml"
        if not bank_path.exists():
            errors.append(f"missing {bank_path.name}")
        else:
            try:
                bank = yaml.safe_load(bank_path.read_text(encoding="utf-8"))
                assert bank["lesson_id"] == f"v2-l{n:02d}-r1" and len(bank["items"]) == 5
                student_heading = (student / lesson / "README.md").read_text(encoding="utf-8").splitlines()[0]
                assert bank["title"].split(" · ", 1)[1] == student_heading.split(" · ", 1)[1], "lesson title mismatch"
                ids = [item["concept_id"] for item in bank["items"]]
                assert len(set(ids)) == 5
                answers = []
                for item in bank["items"]:
                    assert item["title"].strip() and item["tutor_context"].strip()
                    assert set(item["pair"]) == {"a", "b"}
                    assert item["pair"]["a"]["prompt"] != item["pair"]["b"]["prompt"]
                    for phase in ("a", "b"):
                        q = item["pair"][phase]
                        assert {str(o["id"]) for o in q["options"]} == set("ABCD")
                        assert len(q["options"]) == 4 and q["answer"] in set("ABCD")
                        assert q["prompt"].strip() and q["explanation"].strip()
                        answers.append(q["answer"])
                        stats["questions"] += 1
                assert set(answers) == set("ABCD") and max(answers.count(a) for a in set("ABCD")) <= 4
            except (ValueError, KeyError, TypeError, AssertionError) as error:
                errors.append(f"{bank_path.name}: invalid bank ({error})")
        script = student / lesson / "analysis.py"
        if execute and script.exists():
            process = subprocess.run([sys.executable, str(script)], cwd=student, capture_output=True, text=True, timeout=60)
            if process.returncode:
                errors.append(f"{lesson} run failed: {process.stderr[-1000:]}")
            else:
                stats["starting_points_run"] += 1
        stats["lessons"] += 1

    for root in [student, TEACHER]:
        for path in root.rglob("*.md"):
            if any(p in {"archive", ".git", ".venv", "legacy"} for p in path.relative_to(root).parts):
                continue
            errors.extend(local_links(path, root))
        for path in root.rglob("*.py"):
            if any(p in {"archive", ".git", ".venv", "__pycache__"} for p in path.relative_to(root).parts):
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as error:
                errors.append(str(error))
    for path in (student / "data").glob("*/*.csv"):
        if path.stat().st_size == 0:
            errors.append(f"empty data: {path}")
        stats["data_files"] += 1
    stats["errors"] = errors
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--student", type=Path, default=TEACHER.parent / "lesson-01-first-green")
    parser.add_argument("--run", action="store_true", help="Execute starting points; writes only their generated artifacts")
    args = parser.parse_args()
    result = validate(args.student.resolve(), args.run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(result["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
