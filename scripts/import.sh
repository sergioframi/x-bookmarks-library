#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
file=${1:?"Uso: scripts/import.sh nombre.json (debe estar en imports/)"}
case "$file" in */*|*..*) echo "Indica solo un nombre dentro de imports/" >&2;exit 1;; esac
docker compose run --rm app python manage.py import "/app/imports/$file"
docker compose run --rm app python manage.py classify --only-unclassified --no-semantic
docker compose run --rm app python manage.py embed
docker compose run --rm app python manage.py finalize-taxonomy
