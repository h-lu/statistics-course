#!/bin/sh
set -eu
if [ "$#" -gt 0 ]; then
  case "$1" in
    --dry-run)
      shift
      script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
      exec python3 "$script_dir/publish_student_lesson.py" --dry-run "$@"
      ;;
    *) echo "本地预检：$0 --dry-run --source TEMPLATE --destination LOCAL_CLONE --lesson 10" >&2; exit 2 ;;
  esac
fi
today=$(TZ=Asia/Shanghai date +%F)
lesson=$(TODAY="$today" python3 - <<'PY'
import os
from datetime import date, timedelta
start = date(2026, 9, 14)
today = date.fromisoformat(os.environ["TODAY"])
if today < start or today.weekday() not in (0, 2):
    raise SystemExit(0)
number = 0
day = start
while day <= today:
    if day.weekday() in (0, 2):
        number += 1
    day += timedelta(days=1)
print(number if number <= 32 else 0)
PY
)
[ -n "$lesson" ] || exit 0
[ "$lesson" -gt 0 ] || exit 0
# 本地发布入口支持第1—10课；线上配置须另行部署，不随源文件修改启用。
# 扩大范围前应完成新课包、数据和核验，并同步所有 ACTIVE_LESSONS。
[ "$lesson" -le 10 ] || exit 0
. /root/.config/statistics-release/env
two=$(printf '%02d' "$lesson")
dataset=""
case "$lesson" in
  1) dataset="service" ;;
  5) dataset="alerts" ;;
esac

tmp=$(mktemp -d /tmp/statistics-release.XXXX)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -u "$GITEA_USER:$GITEA_TOKEN" -o "$tmp/source.tar.gz" \
  https://hblu.top/gitea/api/v1/repos/statistics/course-student-template/archive/main.tar.gz
tar -xzf "$tmp/source.tar.gz" -C "$tmp"
source_lesson=$(find "$tmp" -type d -name "lesson-$two" -print -quit)
[ -n "$source_lesson" ] && [ -d "$source_lesson" ]
git clone -q "https://$GITEA_USER:$GITEA_TOKEN@hblu.top/gitea/statistics/course-student-release-2026.git" "$tmp/release"

if [ "$lesson" -eq 10 ]; then
  source_runner=$(find "$tmp" -type f -path "*/scripts/course_l10.py" -print -quit)
  [ -n "$source_runner" ] && [ -f "$source_runner" ]
  target_runner="$tmp/release/scripts/course_l10.py"
  if [ -e "$target_runner" ] || [ -L "$target_runner" ]; then
    [ ! -L "$target_runner" ] && [ -f "$target_runner" ] && cmp -s "$source_runner" "$target_runner" || {
      echo "共享代码scripts/course_l10.py与发布版本不兼容；未复制课次" >&2
      exit 1
    }
  else
    mkdir -p "$tmp/release/scripts"
    cp -a "$source_runner" "$target_runner"
    git -C "$tmp/release" add "scripts/course_l10.py"
  fi
fi

if [ ! -e "$tmp/release/lesson-$two" ] && [ ! -L "$tmp/release/lesson-$two" ]; then
  cp -a "$source_lesson" "$tmp/release/"
  git -C "$tmp/release" add "lesson-$two"
fi
if [ -n "$dataset" ] && [ ! -e "$tmp/release/data/$dataset" ] && [ ! -L "$tmp/release/data/$dataset" ]; then
  source_data=$(find "$tmp" -type d -path "*/data/$dataset" -print -quit)
  [ -n "$source_data" ] && [ -d "$source_data" ]
  mkdir -p "$tmp/release/data"
  cp -a "$source_data" "$tmp/release/data/"
  git -C "$tmp/release" add "data/$dataset"
fi
if git -C "$tmp/release" diff --cached --quiet; then
  exit 0
fi
git -C "$tmp/release" config user.name "统计学课程发布机器人"
git -C "$tmp/release" config user.email "noreply@hblu.top"
git -C "$tmp/release" commit -qm "发布第${lesson}课"
git -C "$tmp/release" push -q origin main
