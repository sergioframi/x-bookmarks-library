from __future__ import annotations

import json
import os
import time

import psutil

from app.semantic_worker import OnDemandEmbeddingWorker


process = psutil.Process()
rss_before = process.memory_info().rss
started = time.perf_counter()
model, vector = OnDemandEmbeddingWorker(timeout_seconds=30).encode_query(
    "herramientas para descubrir endpoints ocultos en ficheros JavaScript"
)
elapsed = time.perf_counter() - started
time.sleep(0.2)
children = [child.pid for child in process.children(recursive=True) if child.is_running()]
rss_after = process.memory_info().rss
print(
    json.dumps(
        {
            "parent_pid": os.getpid(),
            "model": model,
            "dimension": int(vector.size),
            "vector_norm": round(float((vector @ vector) ** 0.5), 6),
            "elapsed_seconds": round(elapsed, 3),
            "parent_rss_before_mib": round(rss_before / 1024 / 1024, 2),
            "parent_rss_after_mib": round(rss_after / 1024 / 1024, 2),
            "live_child_pids_after_response": children,
        },
        sort_keys=True,
    )
)
if children:
    raise SystemExit("el worker dejó procesos hijos activos")
