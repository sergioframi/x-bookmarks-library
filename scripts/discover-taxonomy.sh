#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec docker compose run --rm app python manage.py discover-taxonomy
