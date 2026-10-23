from __future__ import annotations

import pytest

from app.db import connect, initialize_schema
from app.progress import (
    EnrichmentBusy,
    acquire_enrichment_lock,
    add_event,
    create_enrichment_job,
    enrichment_status,
    recover_interrupted,
)


def database(tmp_path):
    connection = connect(tmp_path / "progress.sqlite3")
    initialize_schema(connection)
    return connection


def test_enrichment_lock_rejects_a_second_sync(tmp_path):
    connection = database(tmp_path)
    acquire_enrichment_lock(connection, "first")
    with pytest.raises(EnrichmentBusy):
        acquire_enrichment_lock(connection, "second")
    assert enrichment_status(connection)["lock"]["owner"] == "first"


def test_recovery_interrupts_job_and_releases_lock(tmp_path):
    connection = database(tmp_path)
    acquire_enrichment_lock(connection, "device:scan")
    connection.execute(
        "INSERT INTO sync_runs(id,scan_id,archive_sha256,archive_path,started_at,status) "
        "VALUES('run','scan','hash','archive.json',CURRENT_TIMESTAMP,'pending_embeddings')"
    )
    create_enrichment_job(connection, "run")
    connection.execute("UPDATE enrichment_jobs SET status='running' WHERE sync_id='run'")
    connection.commit()

    recover_interrupted(connection)

    status = enrichment_status(connection)
    assert status["busy"] is False
    assert status["job"]["status"] == "interrupted"
    assert connection.execute("SELECT status FROM sync_runs WHERE id='run'").fetchone()[0] == "interrupted"


def test_progress_events_return_structured_details(tmp_path):
    connection = database(tmp_path)
    connection.execute(
        "INSERT INTO sync_runs(id,scan_id,archive_sha256,archive_path,started_at,status) "
        "VALUES('run','scan','hash','archive.json',CURRENT_TIMESTAMP,'pending_embeddings')"
    )
    create_enrichment_job(connection, "run")
    add_event(
        connection,
        "run",
        "embedding",
        "info",
        "embeddings",
        "Embeddings: 8 de 10",
        {"completed": 8, "total": 10},
    )
    connection.commit()

    event = enrichment_status(connection)["events"][-1]
    assert event["details"] == {"completed": 8, "total": 10}
    assert "details_json" not in event
