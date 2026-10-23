#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd);cd "$project_dir"
docker compose run --rm app python manage.py embed "$@"
