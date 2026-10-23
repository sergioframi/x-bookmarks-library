from __future__ import annotations

import json
import sqlite3
from typing import Any


LOCK_NAME = "sync-enrichment"


class EnrichmentBusy(RuntimeError):
    pass


def recover_interrupted(connection) -> None:
    connection.execute(
        """UPDATE enrichment_jobs SET status='interrupted',phase='interrupted',
           message='El proceso se interrumpió al detener la aplicación',
           error='interrupted',finished_at=CURRENT_TIMESTAMP,heartbeat_at=CURRENT_TIMESTAMP
           WHERE status IN ('queued','running')"""
    )
    connection.execute("DELETE FROM runtime_locks WHERE name=?", (LOCK_NAME,))
    connection.execute(
        "UPDATE sync_runs SET status='interrupted' WHERE status='pending_embeddings'"
    )
    connection.commit()


def acquire_enrichment_lock(connection, owner: str) -> None:
    try:
        connection.execute(
            "INSERT INTO runtime_locks(name,owner) VALUES(?,?)", (LOCK_NAME, owner)
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise EnrichmentBusy("Ya hay una sincronización o enriquecimiento en curso") from exc


def release_enrichment_lock(connection, owner: str | None = None) -> None:
    if owner:
        connection.execute(
            "DELETE FROM runtime_locks WHERE name=? AND owner=?", (LOCK_NAME, owner)
        )
    else:
        connection.execute("DELETE FROM runtime_locks WHERE name=?", (LOCK_NAME,))
    connection.commit()


def create_enrichment_job(connection, sync_id: str) -> None:
    total = connection.execute(
        "SELECT count(*) FROM search_documents WHERE embedding_text<>''"
    ).fetchone()[0]
    completed = connection.execute(
        """SELECT count(*) FROM search_documents d WHERE d.embedding_text<>'' AND EXISTS
           (SELECT 1 FROM embeddings e WHERE e.tweet_id=d.tweet_id
            AND e.text_sha256=d.embedding_sha256)"""
    ).fetchone()[0]
    connection.execute(
        """INSERT OR REPLACE INTO enrichment_jobs(
           id,sync_id,status,phase,total,completed,message,started_at,heartbeat_at,finished_at,error
           ) VALUES(?,?,'queued','queued',?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,NULL,NULL)""",
        (sync_id, sync_id, total, completed, "Sincronización recibida; preparando embeddings"),
    )
    add_event(connection, sync_id, "server", "success", "received",
              f"Importación recibida: {total} documentos preparados")
    connection.commit()


def update_job(connection, sync_id: str, *, status: str | None = None,
               phase: str | None = None, total: int | None = None,
               completed: int | None = None, message: str | None = None,
               error: str | None = None, finished: bool = False) -> None:
    parameters: list[Any] = []
    assignments = ["heartbeat_at=CURRENT_TIMESTAMP"]
    for name, value in (("status", status), ("phase", phase), ("total", total),
                        ("completed", completed), ("message", message), ("error", error)):
        if value is not None:
            assignments.append(f"{name}=?")
            parameters.append(value)
    if finished:
        assignments.append("finished_at=CURRENT_TIMESTAMP")
    parameters.append(sync_id)
    connection.execute(
        f"UPDATE enrichment_jobs SET {','.join(assignments)} WHERE sync_id=?", parameters
    )
    connection.commit()


def add_event(connection, sync_id: str, source: str, level: str, phase: str,
              message: str, details: dict[str, Any] | None = None) -> None:
    connection.execute(
        """INSERT INTO sync_events(sync_id,source,level,phase,message,details_json)
           VALUES(?,?,?,?,?,?)""",
        (sync_id, source, level, phase, message,
         json.dumps(details or {}, ensure_ascii=False, separators=(",", ":"))),
    )
    connection.execute(
        """DELETE FROM sync_events WHERE sync_id=? AND id NOT IN
           (SELECT id FROM sync_events WHERE sync_id=? ORDER BY id DESC LIMIT 300)""",
        (sync_id, sync_id),
    )


def enrichment_status(connection) -> dict[str, Any]:
    lock = connection.execute(
        "SELECT owner,acquired_at FROM runtime_locks WHERE name=?", (LOCK_NAME,)
    ).fetchone()
    job = connection.execute(
        "SELECT * FROM enrichment_jobs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    documents = connection.execute(
        "SELECT count(*) FROM search_documents WHERE embedding_text<>''"
    ).fetchone()[0]
    embeddings = connection.execute(
        """SELECT count(*) FROM search_documents d WHERE d.embedding_text<>'' AND EXISTS
           (SELECT 1 FROM embeddings e WHERE e.tweet_id=d.tweet_id
            AND e.text_sha256=d.embedding_sha256)"""
    ).fetchone()[0]
    profile = connection.execute(
        "SELECT state FROM taxonomy_profiles WHERE id=1"
    ).fetchone()
    events = []
    if job:
        events = [dict(row) for row in connection.execute(
            """SELECT id,source,level,phase,message,details_json,created_at FROM sync_events
               WHERE sync_id=? ORDER BY id DESC LIMIT 100""", (job["sync_id"],)
        )][::-1]
        for event in events:
            try:
                event["details"] = json.loads(event.pop("details_json"))
            except (TypeError, ValueError):
                event["details"] = {}
    return {
        "busy": bool(lock), "lock": dict(lock) if lock else None,
        "job": dict(job) if job else None, "documents": documents,
        "embeddings": embeddings, "taxonomy_state": profile["state"] if profile else "empty",
        "events": events,
    }
