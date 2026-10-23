"""One-shot ONNX process.

This module is intentionally the only application module that imports FastEmbed.
It reads one JSON request from stdin, writes one JSON response, and exits.
"""

from __future__ import annotations

import json
import os
import resource
import sys


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main() -> int:
    address_limit_mib = int(os.getenv("EMBEDDING_RLIMIT_AS_MIB", "1536"))
    if address_limit_mib > 0:
        address_limit = address_limit_mib * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (address_limit, address_limit))
    request = json.load(sys.stdin)
    texts = request.get("texts")
    if not isinstance(texts, list) or not texts or not all(isinstance(x, str) for x in texts):
        raise ValueError("texts debe ser una lista no vacía de cadenas")
    if len(texts) > int(os.getenv("EMBEDDING_MAX_BATCH", "64")):
        raise ValueError("lote de embeddings demasiado grande")

    # Importing here is deliberate: the long-running web process never loads ONNX
    # or model weights. The operating system reclaims all of this process' memory
    # immediately after the response has been emitted.
    import numpy as np
    from fastembed import TextEmbedding

    model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
    cache_dir = os.getenv("FASTEMBED_CACHE_PATH", "/app/models/fastembed")
    threads = max(1, min(int(os.getenv("EMBEDDING_THREADS", "2")), 2))
    model = TextEmbedding(model_name=model_name, cache_dir=cache_dir, threads=threads)
    vectors = []
    for vector in model.embed(texts, batch_size=min(8, len(texts))):
        value = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(value))
        if norm:
            value /= norm
        vectors.append(value.tolist())
    print(json.dumps({"model": model_name, "vectors": vectors}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"embedding worker: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
