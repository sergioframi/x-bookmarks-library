from __future__ import annotations

import json

from pydantic import ValidationError

from app.config import settings
from app.db import connect, initialize_schema
from app.main import (UpdateBookmark, apply_update, delete_revoked_device,
                      revoke_device)
from app.security import create_session, hash_password, read_session, verify_password
from app.taxonomy import seed_taxonomy
from app.xarchive_sync import (authenticate_device, create_pairing_code, pair_device,
                               process_sync)


def archive(ids, *, complete=False):
    return {
        "export_metadata": {
            "tool": "xarchive", "schema_version": 2, "kind": "snapshot",
            "user_id": "42", "screen_name": "tester",
            "collection": {
                "mode": "full" if complete else "quick",
                "bookmarks": "complete" if complete else "partial",
                "folders": "partial", "reason": "complete" if complete else "quick_boundary",
            },
        },
        "folders": [],
        "bookmarks": [
            {"tweet_id": value, "status": "available", "full_text": f"tweet {value}",
             "author": {"screen_name": "author"}, "entities": {}}
            for value in ids
        ],
    }


def configured(tmp_path):
    object.__setattr__(settings, "x_account_id", "42")
    object.__setattr__(settings, "sync_archive_dir", tmp_path / "archives")
    object.__setattr__(settings, "imports_dir", tmp_path / "imports")
    connection = connect(tmp_path / "library.sqlite3")
    initialize_schema(connection)
    seed_taxonomy(connection)
    connection.execute(
        "UPDATE taxonomy_profiles SET state='active',source='legacy' WHERE id=1"
    )
    connection.commit()
    code = create_pairing_code(connection)["code"]
    paired = pair_device(connection, code, "Test Chrome", "1.2.0")
    device = authenticate_device(connection, f"Bearer {paired['device_token']}")
    return connection, device, paired


def test_first_sync_binds_an_unconfigured_installation_to_the_archive_account(tmp_path):
    object.__setattr__(settings, "x_account_id", "")
    object.__setattr__(settings, "sync_archive_dir", tmp_path / "archives")
    object.__setattr__(settings, "imports_dir", tmp_path / "imports")
    connection = connect(tmp_path / "unbound.sqlite3")
    initialize_schema(connection)
    paired = pair_device(connection, create_pairing_code(connection)["code"], "New Chrome", "1.5.0")
    assert paired["account_user_id"] == ""
    device = authenticate_device(connection, f"Bearer {paired['device_token']}")
    process_sync(connection, device, {"scan_id": "first-bind", "archive": archive(["1000000000000000001"])})
    assert connection.execute("SELECT account_user_id FROM sync_devices").fetchone()[0] == "42"
    assert connection.execute("SELECT value FROM schema_meta WHERE key='x_account_id'").fetchone()[0] == "42"
    next_pairing = create_pairing_code(connection)
    assert next_pairing["account_user_id"] == "42"
    connection.close()


def test_pairing_is_one_time_and_device_token_authenticates(tmp_path):
    connection, device, paired = configured(tmp_path)
    assert device["id"] == paired["device_id"]
    assert len(paired["server_id"]) == 32
    assert authenticate_device(connection, "Bearer invalid") is None
    used = connection.execute("SELECT used_at FROM pairing_codes").fetchone()[0]
    assert used


def test_only_revoked_devices_can_be_permanently_deleted(tmp_path):
    connection, _, paired = configured(tmp_path)
    device_id = paired["device_id"]
    try:
        delete_revoked_device(device_id, connection, {})
    except Exception as error:
        assert getattr(error, "status_code", None) == 409
    else:
        raise AssertionError("se eliminó un dispositivo activo")
    assert revoke_device(device_id, connection, {}) == {"revoked": True}
    assert delete_revoked_device(device_id, connection, {}) == {"deleted": True}
    assert connection.execute(
        "SELECT 1 FROM sync_devices WHERE id=?", (device_id,)
    ).fetchone() is None


def test_sync_is_idempotent_and_conservatively_reconciles_removals(tmp_path):
    connection, device, _ = configured(tmp_path)
    cumulative = archive(["1000000000000000001", "1000000000000000002"])
    first = process_sync(connection, device, {
        "scan_id": "scan-1", "archive": cumulative,
        "snapshot": archive(["1000000000000000001", "1000000000000000002"], complete=True),
    })
    assert first["import"]["new"] == 2
    connection.execute("UPDATE annotations SET notes='keep me' WHERE tweet_id='1000000000000000002'")
    connection.commit()

    second_payload = {
        "scan_id": "scan-2", "archive": cumulative,
        "snapshot": archive(["1000000000000000001"], complete=True),
    }
    second = process_sync(connection, device, second_payload)
    row = connection.execute("SELECT bookmark_state,missing_complete_scans FROM tweets WHERE tweet_id='1000000000000000002'").fetchone()
    assert tuple(row) == ("suspected_removed", 1)
    replay = process_sync(connection, device, second_payload)
    assert replay["idempotent_replay"] is True
    assert connection.execute("SELECT missing_complete_scans FROM tweets WHERE tweet_id='1000000000000000002'").fetchone()[0] == 1

    third = process_sync(connection, device, {
        "scan_id": "scan-3", "archive": cumulative,
        "snapshot": archive(["1000000000000000001"], complete=True),
    })
    assert third["lifecycle"]["removed"] == 1
    row = connection.execute("SELECT bookmark_state,missing_complete_scans FROM tweets WHERE tweet_id='1000000000000000002'").fetchone()
    assert tuple(row) == ("removed", 2)

    process_sync(connection, device, {
        "scan_id": "scan-4", "archive": cumulative,
        "snapshot": archive(["1000000000000000001", "1000000000000000002"]),
    })
    row = connection.execute("""SELECT t.bookmark_state,t.missing_complete_scans,a.notes
      FROM tweets t JOIN annotations a USING(tweet_id) WHERE t.tweet_id='1000000000000000002'""").fetchone()
    assert tuple(row) == ("active", 0, "keep me")


def test_partial_scan_never_marks_missing_bookmarks(tmp_path):
    connection, device, _ = configured(tmp_path)
    cumulative = archive(["1000000000000000001", "1000000000000000002"])
    process_sync(connection, device, {"scan_id": "partial-1", "archive": cumulative,
                                      "snapshot": archive(["1000000000000000001"])})
    row = connection.execute("SELECT bookmark_state,missing_complete_scans FROM tweets WHERE tweet_id='1000000000000000002'").fetchone()
    assert tuple(row) == ("active", 0)


def test_manual_category_edit_survives_sync_and_outranks_auto(tmp_path):
    connection, device, _ = configured(tmp_path)
    tweet_id = "1000000000000000001"
    cumulative = archive([tweet_id])
    process_sync(connection, device, {
        "scan_id": "category-1", "archive": cumulative, "snapshot": cumulative,
    })
    automatic = {
        row[0] for row in connection.execute(
            "SELECT category_id FROM effective_category_assignments WHERE tweet_id=?",
            (tweet_id,),
        )
    }
    manual_id = connection.execute(
        "SELECT id FROM categories WHERE id NOT IN ("
        "SELECT category_id FROM effective_category_assignments WHERE tweet_id=?"
        ") ORDER BY id LIMIT 1",
        (tweet_id,),
    ).fetchone()[0]

    apply_update(
        connection,
        tweet_id,
        UpdateBookmark(category_ids=[manual_id]),
        rebuild=False,
    )
    process_sync(connection, device, {
        "scan_id": "category-2", "archive": cumulative, "snapshot": cumulative,
    })

    effective = connection.execute(
        "SELECT category_id,origin FROM effective_category_assignments WHERE tweet_id=?",
        (tweet_id,),
    ).fetchall()
    assert [tuple(row) for row in effective] == [(manual_id, "manual")]
    assert automatic <= {
        row[0] for row in connection.execute(
            "SELECT category_id FROM category_suppressions WHERE tweet_id=?",
            (tweet_id,),
        )
    }


def test_retained_automatic_category_is_promoted_to_manual(tmp_path):
    connection, device, _ = configured(tmp_path)
    tweet_id = "1000000000000000001"
    cumulative = archive([tweet_id])
    process_sync(connection, device, {
        "scan_id": "promote-1", "archive": cumulative, "snapshot": cumulative,
    })
    category_id = connection.execute(
        "SELECT category_id FROM effective_category_assignments WHERE tweet_id=? LIMIT 1",
        (tweet_id,),
    ).fetchone()[0]

    apply_update(
        connection,
        tweet_id,
        UpdateBookmark(category_ids=[category_id]),
        rebuild=False,
    )

    effective = connection.execute(
        "SELECT category_id,origin FROM effective_category_assignments WHERE tweet_id=?",
        (tweet_id,),
    ).fetchall()
    assert [tuple(row) for row in effective] == [(category_id, "manual")]


def test_every_leaf_category_belongs_to_a_collapsible_parent(tmp_path):
    connection = connect(tmp_path / "taxonomy.sqlite3")
    initialize_schema(connection)
    seed_taxonomy(connection)
    standalone = connection.execute("""
      SELECT slug FROM categories category
      WHERE parent_id IS NULL
        AND NOT EXISTS (SELECT 1 FROM categories child WHERE child.parent_id=category.id)
    """).fetchall()
    assert standalone == []
    other = connection.execute(
        "SELECT id FROM categories WHERE slug='other-interests'"
    ).fetchone()[0]
    grouped = {
        row["slug"]:row["parent_id"] for row in connection.execute(
            "SELECT slug,parent_id FROM categories WHERE slug IN "
            "('finance-economy','travel','photography','learning-culture')"
        )
    }
    assert grouped == {
        "finance-economy":other,
        "travel":other,
        "photography":other,
        "learning-culture":other,
    }


def test_removed_personal_fields_are_rejected():
    for payload in ({"favorite":True}, {"reading_status":"reading"}):
        try:
            UpdateBookmark(**payload)
        except ValidationError:
            continue
        raise AssertionError(f"campo personal obsoleto aceptado: {payload}")


def test_password_hash_and_session_version_are_verifiable():
    encoded = hash_password("una contraseña suficientemente larga")
    assert verify_password("una contraseña suficientemente larga", encoded)
    assert not verify_password("otra contraseña", encoded)
    token, csrf = create_session("admin", "test-secret", 1, session_version=7)
    session = read_session(token, "test-secret")
    assert session and session["csrf"] == csrf and session["sv"] == 7


def test_schema_persists_mutable_application_credentials(tmp_path):
    connection = connect(tmp_path / "credentials.sqlite3")
    initialize_schema(connection)
    connection.execute("INSERT INTO app_users(username,password_hash) VALUES('admin','hash')")
    connection.commit()
    row = connection.execute("SELECT password_hash,session_version FROM app_users WHERE username='admin'").fetchone()
    assert tuple(row) == ("hash", 1)
