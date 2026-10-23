from __future__ import annotations

import json

import numpy as np
import pytest

from app.classifier import MODEL, classify
from app.db import connect, initialize_schema, upsert_search_document
from app.taxonomy import seed_taxonomy
from app.taxonomy_discovery import apply_discovery, discover_taxonomy, taxonomy_status


def add_document(connection, tweet_id: str, text: str, vector: np.ndarray) -> None:
    connection.execute(
        """INSERT INTO tweets(tweet_id,is_bookmark,full_text,display_text,raw_json,source_hash)
           VALUES(?,1,?,?,?,?)""",
        (tweet_id, text, text, json.dumps({"tweet_id": tweet_id}), tweet_id),
    )
    connection.execute("INSERT INTO annotations(tweet_id) VALUES(?)", (tweet_id,))
    upsert_search_document(
        connection, tweet_id, main_text=text, quote_text="", card_text="", urls_text="",
        handles_text="", summary_text=text, labels_text="", embedding_text=text,
        embedding_sha256=tweet_id,
    )
    value = np.array(vector, dtype=np.float32, copy=True)
    value /= np.linalg.norm(value)
    connection.execute(
        "INSERT INTO embeddings(tweet_id,model,dimension,vector,text_sha256) VALUES(?,?,?,?,?)",
        (tweet_id, MODEL, value.size, value.tobytes(), tweet_id),
    )


def test_first_library_discovers_reviews_and_applies_local_categories(tmp_path):
    connection = connect(tmp_path / "discovery.sqlite3")
    initialize_schema(connection)
    rng = np.random.default_rng(91)
    for index in range(15):
        vector = np.r_[np.ones(4), np.zeros(4)] + rng.normal(0, 0.04, 8)
        add_document(connection, str(10_000 + index),
                     f"OAuth authentication JWT authorization account tutorial {index}", vector)
    for index in range(15):
        vector = np.r_[np.zeros(4), np.ones(4)] + rng.normal(0, 0.04, 8)
        add_document(connection, str(20_000 + index),
                     f"Photography camera lens portrait lightroom guide {index}", vector)
    connection.commit()

    assert taxonomy_status(connection)["state"] == "empty"
    proposal = discover_taxonomy(connection)
    assert proposal["state"] == "draft"
    assert 2 <= len(proposal["candidates"]) <= 4
    assert sum(item["bookmark_count"] for item in proposal["candidates"]) == 30
    assert all(item["examples"] for item in proposal["candidates"])

    choices = [{"id": item["id"], "name": f"Tema {position}",
                "description": item["description"], "enabled": True}
               for position, item in enumerate(proposal["candidates"], 1)]
    applied = apply_discovery(connection, choices)
    assert applied["state"] == "active"
    assert applied["categories"] == len(choices)
    assert connection.execute("SELECT count(*) FROM category_prototypes").fetchone()[0] == len(choices)
    assert connection.execute("SELECT count(DISTINCT tweet_id) FROM category_assignments").fetchone()[0] == 30
    with pytest.raises(ValueError, match="taxonomía activa"):
        discover_taxonomy(connection)

    first = connection.execute("SELECT vector FROM category_prototypes ORDER BY category_id LIMIT 1").fetchone()
    add_document(connection, "30000", "A new local item", np.frombuffer(first["vector"], dtype=np.float32))
    connection.commit()
    result = classify(connection, only_unclassified=True, semantic=True)
    assert result["processed"] == 1
    assert connection.execute(
        "SELECT count(*) FROM category_assignments WHERE tweet_id='30000'"
    ).fetchone()[0] >= 1
    connection.close()


def test_discovery_uses_the_onboarding_language_for_category_content(tmp_path):
    connection = connect(tmp_path / "english-discovery.sqlite3")
    initialize_schema(connection)
    connection.execute("UPDATE onboarding_state SET locale='en' WHERE id=1")
    rng = np.random.default_rng(18)
    for index in range(20):
        vector = np.r_[np.ones(4), np.zeros(4)] + rng.normal(0, 0.03, 8)
        add_document(connection, str(40_000 + index),
                     f"Photography camera lens portrait lightroom guide {index}", vector)
    for index in range(20):
        vector = np.r_[np.zeros(4), np.ones(4)] + rng.normal(0, 0.03, 8)
        add_document(connection, str(50_000 + index),
                     f"OAuth authentication JWT authorization account tutorial {index}", vector)
    connection.commit()
    proposal = discover_taxonomy(connection)
    assert any(item["name"] == "Photography" for item in proposal["candidates"])
    assert all(not item["description"].startswith("Temas detectados") for item in proposal["candidates"])
    parameters = connection.execute(
        "SELECT parameters_json FROM taxonomy_discovery_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    assert json.loads(parameters)["locale"] == "en"
    connection.close()


def test_v8_installation_with_categories_is_migrated_as_legacy_without_changes(tmp_path):
    connection = connect(tmp_path / "legacy.sqlite3")
    initialize_schema(connection)
    seed_taxonomy(connection)
    before = connection.execute("SELECT count(*) FROM categories").fetchone()[0]
    connection.execute("DELETE FROM taxonomy_profiles")
    connection.execute("UPDATE schema_meta SET value='8' WHERE key='schema_version'")
    connection.commit()
    initialize_schema(connection)
    profile = connection.execute("SELECT state,source FROM taxonomy_profiles WHERE id=1").fetchone()
    assert tuple(profile) == ("active", "legacy")
    assert connection.execute("SELECT count(*) FROM categories").fetchone()[0] == before
    connection.close()
