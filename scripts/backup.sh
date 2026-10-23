#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd);cd "$project_dir"
stamp=$(date +%Y%m%d-%H%M%S);mkdir -p backups
temporary="/app/data/.backup-$stamp.sqlite3"
destination="backups/backup-$stamp.sqlite3"
trap 'docker compose exec -T app rm -f "$temporary" >/dev/null 2>&1 || true' EXIT
docker compose exec -T app python manage.py backup "$temporary"
docker compose cp "app:$temporary" "$destination"
chmod 600 "$destination"
echo "$project_dir/$destination"
