from __future__ import annotations

import json
import os
import platform
import resource
import statistics
import threading
import time
from pathlib import Path

import psutil
from fastembed import TextEmbedding


MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
CACHE = os.getenv("FASTEMBED_CACHE_PATH", "/models/fastembed")
THREADS = int(os.getenv("EMBEDDING_THREADS", "2"))
RUNS = int(os.getenv("BENCHMARK_RUNS", "25"))
QUERY = "herramientas para descubrir endpoints ocultos en ficheros JavaScript"


def mib(value: int | float) -> float:
    return round(float(value) / 1024 / 1024, 2)


class Sampler:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.stop_event = threading.Event()
        self.rss: list[int] = []
        self.cpu: list[float] = []
        self.process.cpu_percent(None)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.wait(0.05):
            self.rss.append(self.process.memory_info().rss)
            self.cpu.append(self.process.cpu_percent(None))

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.rss.append(self.process.memory_info().rss)


def embed_once(model: TextEmbedding, text: str) -> int:
    vector = next(iter(model.embed([text], batch_size=1)))
    return int(vector.shape[0])


def main() -> None:
    Path(CACHE).mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    available_before = psutil.virtual_memory().available
    cpu_before = process.cpu_times()
    rss_before = process.memory_info().rss
    wall_start = time.perf_counter()
    sampler = Sampler()
    sampler.start()

    load_start = time.perf_counter()
    model = TextEmbedding(model_name=MODEL, cache_dir=CACHE, threads=THREADS)
    load_seconds = time.perf_counter() - load_start
    rss_after_load = process.memory_info().rss

    first_start = time.perf_counter()
    dimension = embed_once(model, QUERY)
    first_query_ms = (time.perf_counter() - first_start) * 1000

    latencies: list[float] = []
    variants = [
        QUERY,
        "bypass de autenticación OAuth e IDOR",
        "fotografía nocturna y objetivos luminosos",
        "cómo montar servicios propios en una Raspberry Pi",
        "SSRF mediante redirecciones y DNS rebinding",
    ]
    for index in range(RUNS):
        start = time.perf_counter()
        embed_once(model, variants[index % len(variants)])
        latencies.append((time.perf_counter() - start) * 1000)

    sampler.stop()
    wall_seconds = time.perf_counter() - wall_start
    cpu_after = process.cpu_times()
    cpu_seconds = (
        cpu_after.user
        + cpu_after.system
        - cpu_before.user
        - cpu_before.system
    )
    max_rss_ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    max_rss = max([max_rss_ru, rss_before, rss_after_load, *sampler.rss])
    available_after = psutil.virtual_memory().available
    sorted_latencies = sorted(latencies)
    p95_index = max(0, min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95) - 1))

    result = {
        "model": MODEL,
        "runtime": "FastEmbed / ONNX Runtime CPU",
        "machine": platform.machine(),
        "threads_limited_to": THREADS,
        "dimension": dimension,
        "runs": RUNS,
        "load_seconds": round(load_seconds, 3),
        "first_query_ms": round(first_query_ms, 2),
        "warm_query_mean_ms": round(statistics.mean(latencies), 2),
        "warm_query_median_ms": round(statistics.median(latencies), 2),
        "warm_query_p95_ms": round(sorted_latencies[p95_index], 2),
        "warm_query_min_ms": round(min(latencies), 2),
        "warm_query_max_ms": round(max(latencies), 2),
        "rss_before_mib": mib(rss_before),
        "rss_after_load_mib": mib(rss_after_load),
        "peak_rss_mib": mib(max_rss),
        "system_available_before_mib": mib(available_before),
        "system_available_after_mib": mib(available_after),
        "cpu_process_seconds": round(cpu_seconds, 3),
        "cpu_average_one_core_percent": round(cpu_seconds / wall_seconds * 100, 1),
        "cpu_sample_peak_percent": round(max(sampler.cpu, default=0.0), 1),
        "total_wall_seconds": round(wall_seconds, 3),
        "pid": os.getpid(),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
