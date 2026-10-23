from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .classifier import classify
from .config import settings
from .db import connect
from .importer import canonical_json, import_xarchive
from .progress import add_event,release_enrichment_lock,update_job
from .semantic_worker import exclusive_embedding_file_lock


PAIRING_TTL_MINUTES = 10
MAX_ARCHIVE_BYTES = 30 * 1024 * 1024


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat()


def secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_pairing_code(connection) -> dict[str, str]:
    stored = connection.execute(
        "SELECT value FROM schema_meta WHERE key='x_account_id'"
    ).fetchone()
    account_user_id = (stored["value"] if stored else settings.x_account_id).strip()
    raw = secrets.token_hex(4).upper()
    code = f"{raw[:4]}-{raw[4:]}"
    now = utcnow()
    expires = now + timedelta(minutes=PAIRING_TTL_MINUTES)
    connection.execute("DELETE FROM pairing_codes WHERE expires_at<? OR used_at IS NOT NULL", (iso(now),))
    connection.execute(
        "INSERT INTO pairing_codes(code_hash,account_user_id,created_at,expires_at) VALUES(?,?,?,?)",
        (secret_hash(code), account_user_id, iso(now), iso(expires)),
    )
    connection.commit()
    return {"code": code, "expires_at": iso(expires), "account_user_id": account_user_id}


def pair_device(connection, code: str, name: str, extension_version: str | None) -> dict[str, str]:
    normalized = code.strip().upper()
    row = connection.execute(
        "SELECT * FROM pairing_codes WHERE code_hash=?", (secret_hash(normalized),)
    ).fetchone()
    if not row or row["used_at"] or row["expires_at"] < iso():
        raise ValueError("código de emparejamiento inválido o caducado")
    device_id = str(uuid.uuid4())
    token = "xbd_" + secrets.token_urlsafe(36)
    connection.execute("UPDATE pairing_codes SET used_at=? WHERE code_hash=?", (iso(), row["code_hash"]))
    connection.execute(
        """INSERT INTO sync_devices(id,name,token_hash,account_user_id,created_at,extension_version)
           VALUES(?,?,?,?,?,?)""",
        (device_id, name.strip()[:100] or "Chrome", secret_hash(token), row["account_user_id"], iso(), extension_version),
    )
    connection.commit()
    instance = connection.execute("SELECT value FROM schema_meta WHERE key='instance_id'").fetchone()
    return {"device_id": device_id, "device_token": token, "account_user_id": row["account_user_id"],
            "server_id": instance["value"] if instance else ""}


def authenticate_device(connection, authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    row = connection.execute(
        "SELECT * FROM sync_devices WHERE token_hash=? AND revoked_at IS NULL", (secret_hash(token),)
    ).fetchone()
    if row:
        connection.execute("UPDATE sync_devices SET last_seen_at=? WHERE id=?", (iso(), row["id"]))
        connection.commit()
    return row


def validate_archive(value: Any, expected_account: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("bookmarks"), list):
        raise ValueError("archivo xarchive inválido")
    meta = value.get("export_metadata") or {}
    if meta.get("tool") != "xarchive" or meta.get("schema_version") != 2:
        raise ValueError("solo se admite xarchive schema 2")
    archive_account = str(meta.get("user_id") or "").strip()
    if not archive_account:
        raise ValueError("el archivo no identifica la cuenta de X")
    if expected_account and archive_account != expected_account:
        raise ValueError("el archivo pertenece a otra cuenta de X")
    for bookmark in value["bookmarks"]:
        if not isinstance(bookmark, dict) or not isinstance(bookmark.get("tweet_id"), str):
            raise ValueError("todos los tweet_id deben ser strings")
    return value


def _write_archive(archive: dict[str, Any]) -> tuple[str, Path]:
    raw = canonical_json(archive).encode()
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("el archivo acumulado supera el límite de 30 MiB")
    digest = hashlib.sha256(raw).hexdigest()
    root = settings.sync_archive_dir
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / f"{digest}.json"
    if not path.exists():
        temporary = root / f".{digest}.{secrets.token_hex(4)}.tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
    return digest, path


def _reconcile_lifecycle(connection, scan_id: str, snapshot: dict[str, Any] | None) -> dict[str, int]:
    if not snapshot:
        return {"activated": 0, "suspected_removed": 0, "removed": 0}
    collection = (snapshot.get("export_metadata") or {}).get("collection") or {}
    observed = {
        bookmark["tweet_id"] for bookmark in snapshot.get("bookmarks", [])
        if isinstance(bookmark, dict) and isinstance(bookmark.get("tweet_id"), str)
    }
    activated = 0
    if observed:
        marks = ",".join("?" for _ in observed)
        activated = connection.execute(
            f"SELECT count(*) FROM tweets WHERE tweet_id IN ({marks}) AND is_bookmark=1 AND bookmark_state<>'active'",
            tuple(observed),
        ).fetchone()[0]
        connection.execute(
            f"""UPDATE tweets SET bookmark_state='active',missing_complete_scans=0,
                 last_observed_scan_id=?,removed_at=NULL
                 WHERE tweet_id IN ({marks}) AND is_bookmark=1""",
            (scan_id, *observed),
        )
    suspected = removed = 0
    is_complete_full = collection.get("mode") == "full" and collection.get("bookmarks") == "complete"
    if is_complete_full:
        clauses = ["is_bookmark=1", "bookmark_state<>'locally_archived'"]
        params: list[Any] = []
        if observed:
            marks = ",".join("?" for _ in observed)
            clauses.append(f"tweet_id NOT IN ({marks})")
            params.extend(observed)
        missing = connection.execute(
            f"SELECT tweet_id,bookmark_state,missing_complete_scans FROM tweets WHERE {' AND '.join(clauses)}",
            params,
        ).fetchall()
        for row in missing:
            count = int(row["missing_complete_scans"]) + 1
            state = "removed" if count >= 2 else "suspected_removed"
            if state == "removed" and row["bookmark_state"] != "removed":
                removed += 1
            elif state == "suspected_removed" and row["bookmark_state"] != "suspected_removed":
                suspected += 1
            connection.execute(
                """UPDATE tweets SET bookmark_state=?,missing_complete_scans=?,
                   removed_at=CASE WHEN ?='removed' THEN COALESCE(removed_at,?) ELSE NULL END
                   WHERE tweet_id=?""",
                (state, count, state, iso(), row["tweet_id"]),
            )
    return {"activated": activated, "suspected_removed": suspected, "removed": removed}


def process_sync(connection, device, payload: dict[str, Any]) -> dict[str, Any]:
    scan_id = str(payload.get("scan_id") or "").strip()
    if not scan_id or len(scan_id) > 200 or not re.fullmatch(r"[A-Za-z0-9_.:+-]+", scan_id):
        raise ValueError("scan_id inválido")
    previous = connection.execute("SELECT receipt_json FROM sync_runs WHERE scan_id=?", (scan_id,)).fetchone()
    if previous:
        receipt = json.loads(previous["receipt_json"])
        receipt["idempotent_replay"] = True
        return receipt
    expected_account = str(device["account_user_id"] or "").strip()
    archive = validate_archive(payload.get("archive"), expected_account)
    archive_account = str((archive.get("export_metadata") or {}).get("user_id"))
    if not expected_account:
        stored = connection.execute(
            "SELECT value FROM schema_meta WHERE key='x_account_id'"
        ).fetchone()
        configured_account = (stored["value"] if stored else settings.x_account_id).strip()
        if configured_account and configured_account != archive_account:
            raise ValueError("el archivo pertenece a otra cuenta de X")
        expected_account = archive_account
        connection.execute(
            "UPDATE sync_devices SET account_user_id=? WHERE id=? AND account_user_id=''",
            (expected_account, device["id"]),
        )
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('x_account_id',?)",
            (expected_account,),
        )
    snapshot_value = payload.get("snapshot")
    snapshot = validate_archive(snapshot_value, expected_account) if snapshot_value else None
    digest, path = _write_archive(archive)
    report = import_xarchive(connection, path)
    lifecycle = _reconcile_lifecycle(connection, scan_id, snapshot)
    classification = classify(connection, only_unclassified=True, semantic=False)
    collection = ((snapshot or archive).get("export_metadata") or {}).get("collection") or {}
    run_id = str(uuid.uuid4())
    receipt = {
        "sync_id": run_id,
        "scan_id": scan_id,
        "archive_sha256": digest,
        "import": report,
        "lifecycle": lifecycle,
        "classification": classification,
        "enrichment": "pending_embeddings",
        "idempotent_replay": False,
    }
    connection.execute(
        """INSERT INTO sync_runs(id,scan_id,device_id,archive_sha256,archive_path,
          collection_mode,collection_status,collection_reason,started_at,finished_at,status,import_id,
          activated_count,suspected_removed_count,removed_count,receipt_json)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, scan_id, device["id"], digest, str(path), collection.get("mode"),
         collection.get("bookmarks"), collection.get("reason"), iso(), iso(), "pending_embeddings",
         report["import_id"], lifecycle["activated"], lifecycle["suspected_removed"],
         lifecycle["removed"], canonical_json(receipt)),
    )
    connection.commit()
    return receipt


def run_incremental_embeddings(sync_id: str, lock_owner: str | None = None) -> None:
    status = "ready"
    failure = None
    try:
        with connect(settings.database_path) as connection:
            update_job(connection,sync_id,status="running",phase="embeddings",
              message="Iniciando el modelo local de embeddings")
            add_event(connection,sync_id,"server","info","embeddings",
              "Modelo local de embeddings iniciado")
            connection.commit()
        environment=os.environ.copy();environment["ENRICHMENT_JOB_ID"]=sync_id
        environment.setdefault("RUST_BACKTRACE", "1")
        with exclusive_embedding_file_lock(blocking=True):
            completed=subprocess.run(
                [sys.executable, "/app/manage.py", "embed"],
                check=True,
                timeout=3600,
                capture_output=True,
                text=True,
                env=environment,
            )
    except Exception as exc:
        status = "embedding_failed_fts_available"
        failure = str(exc)
        if isinstance(exc,subprocess.CalledProcessError):
            diagnostic=(exc.stderr or exc.stdout or str(exc)).strip()
            failure=diagnostic[-4000:] if diagnostic else str(exc)
    try:
        with connect(settings.database_path) as connection:
            if status == "ready":
                profile = connection.execute(
                    "SELECT state FROM taxonomy_profiles WHERE id=1"
                ).fetchone()
                try:
                    update_job(connection,sync_id,status="running",phase="taxonomy",
                      message="Descubriendo categorías localmente")
                    add_event(connection,sync_id,"taxonomy","info","taxonomy",
                      "Descubrimiento local de temas iniciado")
                    connection.commit()
                    def taxonomy_progress(phase,message,completed_count,total_count):
                        update_job(connection,sync_id,status="running",phase=phase,
                          total=total_count,completed=completed_count,message=message)
                        add_event(connection,sync_id,"taxonomy","info",phase,message,
                          {"completed":completed_count,"total":total_count})
                        connection.commit()
                    if profile and profile["state"] == "empty":
                        from .taxonomy_discovery import discover_taxonomy
                        discover_taxonomy(connection,progress_callback=taxonomy_progress)
                        status = "taxonomy_draft_ready"
                    elif profile and profile["state"] == "active":
                        update_job(connection,sync_id,status="running",phase="classification",
                          message="Clasificando nuevos bookmarks")
                        classify(connection, only_unclassified=True, semantic=True)
                except Exception as exc:
                    failure=str(exc)[:500]
                    status = "taxonomy_discovery_failed_search_available"
            if status in {"ready","taxonomy_draft_ready"}:
                update_job(connection,sync_id,status="complete",phase="complete",
                  message="Enriquecimiento local completado",finished=True)
                add_event(connection,sync_id,"server","success","complete",
                  "Enriquecimiento local completado")
            else:
                update_job(connection,sync_id,status="failed",phase="failed",
                  message="El enriquecimiento no pudo completarse",error=failure or status,finished=True)
                add_event(connection,sync_id,"server","error","failed",
                  f"Error de enriquecimiento: {failure or status}")
            row = connection.execute("SELECT receipt_json FROM sync_runs WHERE id=?", (sync_id,)).fetchone()
            if row:
                receipt = json.loads(row["receipt_json"])
                receipt["enrichment"] = status
                connection.execute(
                    "UPDATE sync_runs SET status=?,receipt_json=? WHERE id=?",
                    (status, canonical_json(receipt), sync_id),
                )
                connection.commit()
    except Exception as exc:
        failure=str(exc)[:500]
        try:
            with connect(settings.database_path) as connection:
                update_job(connection,sync_id,status="failed",phase="failed",
                  message="El enriquecimiento no pudo completarse",error=failure,finished=True)
                add_event(connection,sync_id,"server","error","failed",
                  f"Error de enriquecimiento: {failure}")
                connection.execute("UPDATE sync_runs SET status='failed' WHERE id=?",(sync_id,))
                connection.commit()
        except Exception:
            pass
    finally:
        try:
            with connect(settings.database_path) as connection:
                release_enrichment_lock(connection,lock_owner)
        except Exception:
            # A restart also clears stale locks and marks unfinished jobs as interrupted.
            pass


def bootstrap_archive(connection) -> Path | None:
    latest = connection.execute(
        "SELECT archive_path FROM sync_runs WHERE status<>'failed' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if latest and Path(latest["archive_path"]).is_file():
        return Path(latest["archive_path"])
    imported = connection.execute(
        "SELECT filename FROM source_imports WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if imported:
        candidate = (settings.imports_dir / Path(imported["filename"]).name).resolve()
        try:
            candidate.relative_to(settings.imports_dir.resolve())
        except ValueError:
            return None
        if candidate.is_file():
            return candidate
    return None
