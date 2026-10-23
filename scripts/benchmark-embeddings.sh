#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image_name="x-bookmarks-library-benchmark:onnx"

cd "$project_dir"
mkdir -p models benchmark
docker build \
  --label x-bookmarks-library.owner=x-bookmarks-library \
  -t "$image_name" benchmark

docker run --rm \
  --name x-bookmarks-model-benchmark \
  --label x-bookmarks-library.role=ephemeral-benchmark \
  --cpus=2 \
  --memory=768m \
  -e BENCHMARK_RUNS=25 \
  -e EMBEDDING_THREADS=2 \
  -v "$project_dir/models:/models" \
  "$image_name" | tee benchmark/result-pi4-onnx.json

if docker ps -a --filter name=x-bookmarks-model-benchmark --format '{{.ID}}' | grep -q .; then
  echo "Error: el contenedor efímero no fue eliminado" >&2
  exit 1
fi
