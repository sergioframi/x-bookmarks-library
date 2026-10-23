from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import initialize_schema


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def source_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def as_json(value: Any, default: Any) -> str:
    return canonical_json(default if value is None else value)


def twitter_date(value: Any) -> str | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc).isoformat()
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            return None


def tweet_values(tweet: dict[str, Any], is_bookmark: bool) -> tuple[Any, ...]:
    tweet_id = tweet.get("tweet_id")
    if tweet_id is None:
        raise ValueError("tweet_id ausente")
    tweet_id = str(tweet_id)
    if not tweet_id or not tweet_id.isdigit():
        raise ValueError(f"tweet_id inválido: {tweet_id!r}")
    author = tweet.get("author") or {}
    entities = tweet.get("entities") or {}
    card = tweet.get("card") or {}
    text = tweet.get("full_text") or ""
    raw = canonical_json(tweet)
    sort_index = tweet.get("sort_index") if is_bookmark else None
    if sort_index is not None:
        try:
            sort_index = int(str(sort_index))
        except ValueError as exc:
            raise ValueError(f"sort_index inválido: {sort_index!r}") from exc
        if sort_index < 0 or sort_index > 9_223_372_036_854_775_807:
            raise ValueError(f"sort_index fuera de rango: {sort_index!r}")
    return (
        tweet_id, int(is_bookmark), sort_index, tweet.get("status") or "available", text,
        html.unescape(text), str(author.get("user_id")) if author.get("user_id") else None,
        author.get("screen_name"), author.get("name"), author.get("profile_image_url"),
        tweet.get("created_at"), twitter_date(tweet.get("created_at")), tweet.get("lang"),
        tweet.get("source"), str(tweet.get("conversation_id")) if tweet.get("conversation_id") else None,
        str(tweet.get("in_reply_to_tweet_id")) if tweet.get("in_reply_to_tweet_id") else None,
        str(tweet.get("in_reply_to_user_id")) if tweet.get("in_reply_to_user_id") else None,
        card.get("type"), card.get("url"), card.get("title"), card.get("description"),
        as_json(entities.get("urls"), []), as_json(entities.get("hashtags"), []),
        as_json(entities.get("mentions"), []), as_json(tweet.get("media"), []),
        as_json(tweet.get("folder_ids") or tweet.get("folders"), []),
        as_json(tweet.get("metrics"), {}), raw, hashlib.sha256(raw.encode()).hexdigest(),
    )


UPSERT_TWEET = """
INSERT INTO tweets(
 tweet_id,is_bookmark,bookmark_sort_index,source_status,full_text,display_text,author_id,author_handle,author_name,
 author_avatar,created_at_raw,created_at_iso,lang,source,conversation_id,in_reply_to_tweet_id,
 in_reply_to_user_id,card_type,card_url,card_title,card_description,urls_json,hashtags_json,
 mentions_json,media_json,folder_ids_json,metrics_json,raw_json,source_hash
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(tweet_id) DO UPDATE SET
 is_bookmark=MAX(tweets.is_bookmark,excluded.is_bookmark), source_status=excluded.source_status,
 bookmark_sort_index=COALESCE(excluded.bookmark_sort_index,tweets.bookmark_sort_index),
 full_text=excluded.full_text,display_text=excluded.display_text,author_id=excluded.author_id,
 author_handle=excluded.author_handle,author_name=excluded.author_name,author_avatar=excluded.author_avatar,
 created_at_raw=excluded.created_at_raw,created_at_iso=excluded.created_at_iso,lang=excluded.lang,
 source=excluded.source,conversation_id=excluded.conversation_id,
 in_reply_to_tweet_id=excluded.in_reply_to_tweet_id,in_reply_to_user_id=excluded.in_reply_to_user_id,
 card_type=excluded.card_type,card_url=excluded.card_url,card_title=excluded.card_title,
 card_description=excluded.card_description,urls_json=excluded.urls_json,
 hashtags_json=excluded.hashtags_json,mentions_json=excluded.mentions_json,
 media_json=excluded.media_json,folder_ids_json=excluded.folder_ids_json,
 metrics_json=excluded.metrics_json,raw_json=excluded.raw_json,source_hash=excluded.source_hash,
 last_seen_at=CURRENT_TIMESTAMP
"""


def import_xarchive(connection, path: str | Path) -> dict[str, Any]:
    initialize_schema(connection)
    source_path = Path(path).resolve()
    if not source_path.is_file() or source_path.suffix.lower() != ".json":
        raise ValueError("la importación debe ser un fichero JSON existente")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    with source_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    meta = payload.get("export_metadata") or {}
    if meta.get("tool") != "xarchive" or meta.get("schema_version") != 2:
        raise ValueError("se esperaba una exportación xarchive schema_version=2")
    bookmarks = payload.get("bookmarks")
    if not isinstance(bookmarks, list):
        raise ValueError("bookmarks debe ser una lista")
    started = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute("""
      INSERT INTO source_imports(filename,sha256,tool,schema_version,kind,collection_status,started_at,total)
      VALUES(?,?,?,?,?,?,?,?)
    """, (source_path.name,digest,meta.get("tool"),2,meta.get("kind"),
           (meta.get("collection") or {}).get("bookmarks"),started,len(bookmarks)))
    report: dict[str, Any] = {"import_id": cursor.lastrowid,"total":len(bookmarks),"new":0,
        "updated":0,"existing":0,"unavailable":0,"quotes":0,"quotes_with_text":0,"errors":[]}
    for index, bookmark in enumerate(bookmarks):
        savepoint = f"record_{index}"
        connection.execute(f"SAVEPOINT {savepoint}")
        try:
            if not isinstance(bookmark, dict):
                raise ValueError("registro no es objeto")
            values = tweet_values(bookmark, True)
            tweet_id, incoming_hash = values[0], values[-1]
            previous = connection.execute(
                "SELECT source_hash,is_bookmark FROM tweets WHERE tweet_id=?", (tweet_id,)
            ).fetchone()
            connection.execute(UPSERT_TWEET, values)
            connection.execute(
                "INSERT OR IGNORE INTO annotations(tweet_id) VALUES(?)", (tweet_id,)
            )
            if previous is None:
                report["new"] += 1
            elif previous["source_hash"] == incoming_hash and previous["is_bookmark"]:
                report["existing"] += 1
            else:
                report["updated"] += 1
            if bookmark.get("status") == "unavailable":
                report["unavailable"] += 1
            quote = bookmark.get("quoted_tweet")
            if quote is not None:
                if not isinstance(quote, dict):
                    raise ValueError("quoted_tweet no es objeto")
                report["quotes"] += 1
                if quote.get("full_text"):
                    report["quotes_with_text"] += 1
                quoted_id = quote.get("tweet_id")
                if quoted_id is not None:
                    quoted_id = str(quoted_id)
                    existing_quote=connection.execute("SELECT is_bookmark FROM tweets WHERE tweet_id=?",(quoted_id,)).fetchone()
                    # A reduced quote snapshot must never overwrite the richer
                    # source record of an independently bookmarked tweet.
                    if existing_quote is None or not existing_quote["is_bookmark"]:
                        connection.execute(UPSERT_TWEET, tweet_values(quote, False))
                connection.execute("""
                  INSERT INTO bookmark_quotes(bookmark_id,quoted_tweet_id,quote_status,raw_json)
                  VALUES(?,?,?,?) ON CONFLICT(bookmark_id) DO UPDATE SET
                   quoted_tweet_id=excluded.quoted_tweet_id,quote_status=excluded.quote_status,
                   raw_json=excluded.raw_json
                """, (tweet_id,quoted_id,quote.get("status") or "available",canonical_json(quote)))
            connection.execute(f"RELEASE {savepoint}")
        except Exception as exc:
            connection.execute(f"ROLLBACK TO {savepoint}")
            connection.execute(f"RELEASE {savepoint}")
            report["errors"].append({"index":index,"error":str(exc)[:300]})
    finished = datetime.now(timezone.utc).isoformat()
    connection.execute("""
      UPDATE source_imports SET finished_at=?,new_count=?,updated_count=?,existing_count=?,
       unavailable_count=?,quote_count=?,quote_text_count=?,error_count=?,errors_json=? WHERE id=?
    """, (finished,report["new"],report["updated"],report["existing"],report["unavailable"],
           report["quotes"],report["quotes_with_text"],len(report["errors"]),
           canonical_json(report["errors"]),report["import_id"]))
    connection.commit()
    report["sha256"] = digest
    report["partial"] = (meta.get("collection") or {}).get("bookmarks") == "partial"
    return report
