#!/bin/sh
set -eu
. /root/.config/statistics-release/env
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
two=$(printf '%02d' "$lesson")
dataset=""
case "$lesson" in
  1) dataset="service" ;;
  5) dataset="alerts" ;;
  9) dataset="inference" ;;
  15) dataset="experiments" ;;
  21) dataset="prediction" ;;
  27) dataset="policy" ;;
esac

tmp=$(mktemp -d /tmp/statistics-release.XXXX)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL -u "$GITEA_USER:$GITEA_TOKEN" -o "$tmp/source.tar.gz" \
  https://hblu.top/gitea/api/v1/repos/statistics/course-student-template/archive/main.tar.gz
tar -xzf "$tmp/source.tar.gz" -C "$tmp"
source_lesson=$(find "$tmp" -type d -name "lesson-$two" -print -quit)
[ -n "$source_lesson" ] && [ -d "$source_lesson" ]
git clone -q "https://$GITEA_USER:$GITEA_TOKEN@hblu.top/gitea/statistics/course-student-release-2026.git" "$tmp/release"

if [ ! -e "$tmp/release/lesson-$two" ]; then
  cp -a "$source_lesson" "$tmp/release/"
  git -C "$tmp/release" add "lesson-$two"
fi
if [ -n "$dataset" ] && [ ! -e "$tmp/release/data/$dataset" ]; then
  source_data=$(find "$tmp" -type d -path "*/data/$dataset" -print -quit)
  [ -n "$source_data" ] && [ -d "$source_data" ]
  mkdir -p "$tmp/release/data"
  cp -a "$source_data" "$tmp/release/data/"
  git -C "$tmp/release" add "data/$dataset"
fi
if [ "$lesson" -eq 27 ] && [ ! -e "$tmp/release/data/README.md" ]; then
  source_data_readme=$(find "$tmp" -type f -path '*/data/README.md' -print -quit)
  [ -n "$source_data_readme" ] && [ -f "$source_data_readme" ]
  cp "$source_data_readme" "$tmp/release/data/README.md"
  git -C "$tmp/release" add "data/README.md"
fi

if git -C "$tmp/release" diff --cached --quiet; then
  exit 0
fi
git -C "$tmp/release" config user.name "统计学课程发布机器人"
git -C "$tmp/release" config user.email "noreply@hblu.top"
git -C "$tmp/release" commit -qm "发布第${lesson}课"
git -C "$tmp/release" push -q origin main
