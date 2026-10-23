from __future__ import annotations

import json

import numpy as np

from app.model_cache import EXPECTED_DIMENSION, model_cache_status, prepare_embedding_model


class FakeEmbedding:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def embed(self, texts, batch_size):
        assert texts == ["x bookmarks model readiness check"]
        assert batch_size == 1
        yield np.ones(EXPECTED_DIMENSION, dtype=np.float32)


def test_model_preparation_validates_inference_and_writes_atomic_marker(tmp_path):
    result = prepare_embedding_model(tmp_path, FakeEmbedding)
    assert result["ready"] is True
    assert model_cache_status(tmp_path)["ready"] is True
    marker = json.loads((tmp_path / ".x-bookmarks-model-ready.json").read_text())
    assert marker["dimension"] == EXPECTED_DIMENSION
    assert not list(tmp_path.glob(".model-ready-*"))


def test_invalid_or_missing_marker_is_not_ready(tmp_path):
    assert model_cache_status(tmp_path)["ready"] is False
    (tmp_path / ".x-bookmarks-model-ready.json").write_text("{}")
    assert model_cache_status(tmp_path)["ready"] is False
