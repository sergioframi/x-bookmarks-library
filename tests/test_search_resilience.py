from __future__ import annotations

import sqlite3

from app.db import initialize_search_schema, upsert_search_document
from app.search import SearchEngine, fts_literal_query
from app.semantic_worker import SemanticUnavailable


class FailingWorker:
    def encode_query(self, query: str):
        raise SemanticUnavailable("fallo deliberado del fixture")


def database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_search_schema(connection)
    for tweet_id in ("main-hit","quote-hit"):
        connection.execute("INSERT INTO tweets(tweet_id,is_bookmark,raw_json,source_hash) VALUES(?,1,'{}','x')",(tweet_id,))
        connection.execute("INSERT INTO annotations(tweet_id) VALUES(?)",(tweet_id,))
    upsert_search_document(
        connection,
        "main-hit",
        main_text="SSRF through redirects and DNS rebinding",
        quote_text="unrelated quote",
    )
    upsert_search_document(
        connection,
        "quote-hit",
        main_text="Interesting security thread",
        quote_text="Use quoteOnlyTool to discover hidden endpoints",
    )
    connection.commit()
    return connection


def test_fts_survives_semantic_failure() -> None:
    result = SearchEngine(database(), worker=FailingWorker()).search("SSRF", mode="hybrid")
    assert result["effective_mode"] == "text"
    assert result["semantic"]["status"] == "degraded_to_fts"
    assert [item["tweet_id"] for item in result["results"]] == ["main-hit"]


def test_semantic_only_request_still_falls_back_to_fts() -> None:
    result = SearchEngine(database(), worker=FailingWorker()).search("SSRF", mode="semantic")
    assert result["total"] == 1
    assert result["results"][0]["sources"] == ["fts"]


def test_quote_only_match_is_explicit() -> None:
    result = SearchEngine(database()).search("quoteOnlyTool", mode="text")
    assert result["results"][0]["tweet_id"] == "quote-hit"
    assert result["results"][0]["match_only_in_quote"] is True


def test_code_and_cve_tokens_are_escaped_as_literals() -> None:
    assert fts_literal_query('CVE-2023-4596 "postMessage tracker"') == (
        '"CVE-2023-4596" AND "postMessage tracker"'
    )


def test_fts_result_count_is_not_capped_to_the_original_library_size() -> None:
    connection=sqlite3.connect(":memory:")
    connection.row_factory=sqlite3.Row
    initialize_search_schema(connection)
    for index in range(3035):
        tweet_id=f"public-{index}"
        connection.execute("INSERT INTO tweets(tweet_id,is_bookmark,raw_json,source_hash) VALUES(?,1,'{}','x')",(tweet_id,))
        connection.execute("INSERT INTO annotations(tweet_id) VALUES(?)",(tweet_id,))
        upsert_search_document(connection,tweet_id,main_text="shared searchable phrase")
    connection.commit()
    result=SearchEngine(connection).text("shared",{},page=1,page_size=1)
    assert result["total"]==3035
