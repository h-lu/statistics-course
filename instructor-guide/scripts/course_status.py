from __future__ import annotations

import argparse
import base64
import binascii
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


TAG_BY_LESSON = {f"lesson-{n:02d}": f"v2-l{n:02d}-final" for n in range(1, 33)}

STATUS_FILE_BY_TAG = {
    **{f"v2-l{n:02d}-final": f"lesson-{n:02d}/submission.json" for n in range(1, 33)},
    "p0-c1": "submission.json",
    "p0-final": "lesson-02/submission.json",
    "s01-final": "lesson-03/submission.json",
    "s02-final": "lesson-04/submission.json",
    "s03-final": "lesson-05/submission.json",
    "s04-final": "lesson-06/submission.json",
}


def api_get(base_url: str, token: str, path: str) -> tuple[int, object | None]:
    request = Request(
        f"{base_url.rstrip('/')}/api/v1{path}",
        headers={"Authorization": f"token {token}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return 404, None
        raise


def read_roster(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"student_id", "gitea_login", "repo_owner", "repo_name"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"名单必须包含：{', '.join(sorted(required))}")
    return rows


def repo_path(row: dict[str, str]) -> str:
    owner = quote(row["repo_owner"], safe="")
    repo = quote(row["repo_name"], safe="")
    return f"/repos/{owner}/{repo}"


def status_for(
    base_url: str, token: str, row: dict[str, str], tag: str
) -> dict[str, str]:
    path = repo_path(row)
    repo_code, _ = api_get(base_url, token, path)
    if repo_code == 404:
        return {
            "light": "RED",
            "tag": "missing repo",
            "signed": "-",
            "sha": "-",
            "ci": "-",
        }

    tag_code, refs = api_get(
        base_url,
        token,
        f"{path}/git/refs/{quote('tags/' + tag, safe='')}",
    )
    if tag_code == 404 or not refs:
        return {
            "light": "RED",
            "tag": "missing",
            "signed": "-",
            "sha": "-",
            "ci": "-",
        }

    status_file = STATUS_FILE_BY_TAG[tag]
    content_code, content_payload = api_get(
        base_url,
        token,
        f"{path}/contents/{quote(status_file, safe='/')}?ref={quote(tag, safe='')}",
    )
    signed = "missing"
    if content_code == 200 and isinstance(content_payload, dict):
        try:
            encoded = str(content_payload["content"]).replace("\n", "")
            submission = json.loads(base64.b64decode(encoded).decode("utf-8"))
            signed = str(submission.get("status", "missing"))
            if tag.startswith("v2-") and submission.get("lesson") != status_file.split("/")[0]:
                signed = "wrong_lesson"
        except (
            KeyError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            binascii.Error,
        ):
            signed = "invalid"

    status_code, combined = api_get(
        base_url, token, f"{path}/commits/{quote(tag, safe='')}/status"
    )
    if status_code == 404 or not isinstance(combined, dict):
        return {
            "light": "RED" if signed != "complete" else "YELLOW",
            "tag": "present",
            "signed": signed,
            "sha": "-",
            "ci": "none",
        }

    state = str(combined.get("state") or "unknown")
    sha = str(combined.get("sha") or "-")
    if signed != "complete":
        light = "RED"
    else:
        light = "GREEN" if state == "success" else "YELLOW"
    return {
        "light": light,
        "tag": "present",
        "signed": signed,
        "sha": sha,
        "ci": state,
    }


def print_table(rows: list[dict[str, str]]) -> None:
    fields = (
        "checked_at",
        "light",
        "student_id",
        "gitea_login",
        "repository",
        "tag",
        "signed",
        "sha",
        "ci",
    )
    widths = {
        field: max(len(field), *(len(str(row[field])) for row in rows))
        for field in fields
    }
    print("  ".join(field.ljust(widths[field]) for field in fields))
    print("  ".join("-" * widths[field] for field in fields))
    for row in rows:
        print("  ".join(str(row[field]).ljust(widths[field]) for field in fields))


def main() -> int:
    parser = argparse.ArgumentParser(description="保存V2课末完成快照；不是课中进度或自动迟交判定器")
    parser.add_argument("lesson", choices=sorted(TAG_BY_LESSON))
    parser.add_argument("--roster", type=Path, default=Path("roster/roster.csv"))
    parser.add_argument("--base-url", default=os.getenv("GITEA_BASE_URL", "https://hblu.top/gitea"))
    parser.add_argument("--csv", action="store_true", help="输出 CSV")
    args = parser.parse_args()

    token = os.getenv("GITEA_TOKEN", "").strip()
    if not token:
        parser.error("请通过环境变量 GITEA_TOKEN 提供只读或教师令牌")

    try:
        roster = read_roster(args.roster)
        output = []
        tag = TAG_BY_LESSON[args.lesson]
        checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
        for student in roster:
            result = status_for(args.base_url, token, student, tag)
            output.append(
                {
                    "checked_at": checked_at,
                    "light": result["light"],
                    "student_id": student["student_id"],
                    "gitea_login": student["gitea_login"],
                    "repository": f"{student['repo_owner']}/{student['repo_name']}",
                    "tag": result["tag"],
                    "signed": result["signed"],
                    "sha": result["sha"],
                    "ci": result["ci"],
                }
            )
    except (OSError, ValueError, HTTPError, URLError) as error:
        print(f"状态汇总失败：{error}", file=sys.stderr)
        return 1

    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    else:
        print(f"课次：{args.lesson}  final tag：{tag}")
        print_table(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
