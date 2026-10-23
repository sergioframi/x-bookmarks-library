from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np


class SemanticUnavailable(RuntimeError):
    """Semantic inference failed; callers must continue with FTS5."""


def available_memory_mib() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
    except (OSError, ValueError, IndexError):
        pass
    return float("inf")


class OnDemandEmbeddingWorker:
    """Launches one disposable subprocess per embedding request.

    Neither FastEmbed nor ONNX Runtime is imported by this parent process.
    A process-local semaphore and an OS file lock prevent concurrent model loads.
    """

    _semaphore = threading.BoundedSemaphore(value=1)

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        minimum_available_mib: int = 1536,
        lock_path: str | Path | None = None,
        command: Sequence[str] | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.minimum_available_mib = minimum_available_mib
        self.lock_path = Path(lock_path or os.getenv("EMBEDDING_LOCK_PATH", "/tmp/x-bookmarks-embedding.lock"))
        self.command = list(command or [sys.executable, "-m", "app._embedding_process"])

    @contextmanager
    def _exclusive_slot(self) -> Iterator[None]:
        if not self._semaphore.acquire(timeout=0.25):
            raise SemanticUnavailable("encoder ocupado; se usa FTS5")
        lock_file = None
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_file = self.lock_path.open("a+")
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise SemanticUnavailable("encoder ocupado por otro proceso; se usa FTS5") from exc
            yield
        finally:
            if lock_file is not None:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                finally:
                    lock_file.close()
            self._semaphore.release()

    def encode(self, texts: Sequence[str]) -> tuple[str, np.ndarray]:
        cleaned = [text.strip() for text in texts]
        if not cleaned or any(not text for text in cleaned):
            raise SemanticUnavailable("consulta semántica vacía")
        available = available_memory_mib()
        if available < self.minimum_available_mib:
            raise SemanticUnavailable(
                f"memoria disponible insuficiente ({available:.0f} MiB); se usa FTS5"
            )

        with self._exclusive_slot():
            environment = os.environ.copy()
            environment.update(
                {
                    "OMP_NUM_THREADS": "2",
                    "OMP_THREAD_LIMIT": "2",
                    "OPENBLAS_NUM_THREADS": "2",
                    "TOKENIZERS_PARALLELISM": "false",
                    "EMBEDDING_THREADS": "2",
                    "EMBEDDING_RLIMIT_AS_MIB": os.getenv("EMBEDDING_RLIMIT_AS_MIB", "1536"),
                }
            )
            try:
                completed = subprocess.run(
                    self.command,
                    input=json.dumps({"texts": cleaned}),
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    env=environment,
                )
            except subprocess.TimeoutExpired as exc:
                raise SemanticUnavailable(
                    f"el encoder superó {self.timeout_seconds:.0f}s; se usa FTS5"
                ) from exc
            except OSError as exc:
                raise SemanticUnavailable(f"no se pudo iniciar el encoder: {exc}") from exc

        if completed.returncode != 0:
            error = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "error desconocido"
            raise SemanticUnavailable(f"falló el encoder ({error}); se usa FTS5")
        try:
            line = next(line for line in reversed(completed.stdout.splitlines()) if line.strip())
            response = json.loads(line)
            vectors = np.asarray(response["vectors"], dtype=np.float32)
            if vectors.ndim != 2 or vectors.shape[0] != len(cleaned):
                raise ValueError("dimensiones inesperadas")
            return str(response["model"]), vectors
        except (KeyError, ValueError, StopIteration, json.JSONDecodeError) as exc:
            raise SemanticUnavailable("respuesta inválida del encoder; se usa FTS5") from exc

    def encode_query(self, query: str) -> tuple[str, np.ndarray]:
        model, vectors = self.encode([query])
        return model, vectors[0]
