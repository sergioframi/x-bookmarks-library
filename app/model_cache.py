from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EXPECTED_DIMENSION = 384
MARKER_NAME = ".x-bookmarks-model-ready.json"


def cache_root() -> Path:
    return Path(os.getenv("FASTEMBED_CACHE_PATH", "/app/models/fastembed"))


def marker_path(root: Path | None = None) -> Path:
    return (root or cache_root()) / MARKER_NAME


def model_cache_status(root: Path | None = None) -> dict[str, Any]:
    marker = marker_path(root)
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return {"ready": False, "model": MODEL}
    return {
        "ready": payload.get("model") == MODEL
        and payload.get("dimension") == EXPECTED_DIMENSION,
        "model": payload.get("model", MODEL),
        "dimension": payload.get("dimension"),
        "prepared_at": payload.get("prepared_at"),
    }


def prepare_embedding_model(
    root: Path | None = None,
    embedding_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Download, load and execute the embedding model before the web app starts."""
    target = root or cache_root()
    target.mkdir(parents=True, exist_ok=True)
    if embedding_factory is None:
        from fastembed import TextEmbedding

        embedding_factory = TextEmbedding
    threads = max(1, min(int(os.getenv("EMBEDDING_THREADS", "4")), 4))
    model = embedding_factory(model_name=MODEL, cache_dir=str(target), threads=threads)
    vector = next(iter(model.embed(["x bookmarks model readiness check"], batch_size=1)))
    dimension = int(getattr(vector, "size", len(vector)))
    if dimension != EXPECTED_DIMENSION:
        raise RuntimeError(
            f"dimensión inesperada del modelo: {dimension}; se esperaban {EXPECTED_DIMENSION}"
        )
    payload = {
        "model": MODEL,
        "dimension": dimension,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    descriptor, temporary_name = tempfile.mkstemp(prefix=".model-ready-", dir=target)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, marker_path(target))
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return {"ready": True, **payload, "cache_dir": str(target)}
