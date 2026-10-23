from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from app.db import connect, initialize_schema
from app.main import (
    CreateCustomView,
    CreateCustomViewColumn,
    DuplicateCustomView,
    ReorderCustomViewColumns,
    UpdateCustomView,
    UpdateCustomViewColumn,
    create_custom_view,
    create_custom_view_column,
    delete_custom_view,
    duplicate_custom_view,
    reorder_custom_view_columns,
    update_custom_view,
    update_custom_view_column,
)
from app.taxonomy import seed_taxonomy


def test_database_connection_allows_fastapi_worker_thread_handoff(tmp_path):
    connection = connect(tmp_path / "thread-handoff.sqlite3")
    initialize_schema(connection)
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(
            lambda: connection.execute("SELECT 1").fetchone()[0]
        ).result()
    assert result == 1
    connection.close()


def test_version_7_columns_migrate_without_losing_layout(tmp_path):
    connection = connect(tmp_path / "views-v7.sqlite3")
    connection.executescript("""
      CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
      INSERT INTO schema_meta(key,value) VALUES('schema_version','7');
      CREATE TABLE categories (
       id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
       slug TEXT NOT NULL UNIQUE, parent_id INTEGER REFERENCES categories(id),
       description TEXT NOT NULL DEFAULT '', sort_order INTEGER NOT NULL DEFAULT 0
      );
      CREATE TABLE custom_views (
       id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
       is_default INTEGER NOT NULL DEFAULT 0, sort_order INTEGER NOT NULL DEFAULT 0,
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE custom_view_columns (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       view_id INTEGER NOT NULL REFERENCES custom_views(id) ON DELETE CASCADE,
       category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
       title TEXT NOT NULL DEFAULT '', position INTEGER NOT NULL DEFAULT 0,
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(view_id,category_id)
      );
      INSERT INTO categories(id,name,slug) VALUES(1,'Tecnología','tecnologia');
      INSERT INTO custom_views(id,name,is_default) VALUES(1,'Panel',1);
      INSERT INTO custom_view_columns(id,view_id,category_id,title,position)
       VALUES(1,1,1,'Mi tecnología',0);
    """)
    initialize_schema(connection)
    row = connection.execute(
        "SELECT category_id,title,position,width FROM custom_view_columns WHERE id=1"
    ).fetchone()
    assert tuple(row) == (1, "Mi tecnología", 0, 360)
    info = {item[1]: item for item in connection.execute(
        "PRAGMA table_info(custom_view_columns)"
    )}
    assert info["category_id"][3] == 0
    assert connection.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()[0] == "11"
    connection.close()


def test_custom_views_persist_columns_order_and_default(tmp_path):
    connection = connect(tmp_path / "views.sqlite3")
    initialize_schema(connection)
    seed_taxonomy(connection)
    categories = [row[0] for row in connection.execute(
        "SELECT id FROM categories ORDER BY sort_order,id LIMIT 3"
    )]

    view = create_custom_view(
        CreateCustomView(name="Mi panel", category_ids=categories[:2]),
        connection,
        {},
    )
    assert view["is_default"] is True
    assert [column["category_id"] for column in view["columns"]] == categories[:2]

    updated = create_custom_view_column(
        view["id"], CreateCustomViewColumn(category_id=categories[2]), connection, {}
    )
    third_id = updated["columns"][2]["id"]
    renamed = update_custom_view_column(
        view["id"],
        third_id,
        UpdateCustomViewColumn(title="Columna especial"),
        connection,
        {},
    )
    assert renamed["columns"][2]["title"] == "Columna especial"

    resized = update_custom_view_column(
        view["id"],
        third_id,
        UpdateCustomViewColumn(width=980),
        connection,
        {},
    )
    assert resized["columns"][2]["width"] == 980

    with_all = create_custom_view_column(
        view["id"], CreateCustomViewColumn(category_id=None), connection, {}
    )
    assert with_all["columns"][-1]["category_id"] is None
    assert with_all["columns"][-1]["title"] == "Todo"
    assert with_all["columns"][-1]["category_name"] == "Todos los guardados"

    reversed_ids = [column["id"] for column in reversed(with_all["columns"])]
    reordered = reorder_custom_view_columns(
        view["id"], ReorderCustomViewColumns(column_ids=reversed_ids), connection, {}
    )
    assert [column["id"] for column in reordered["columns"]] == reversed_ids

    try:
        create_custom_view_column(
            view["id"], CreateCustomViewColumn(category_id=categories[0]), connection, {}
        )
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("se permitió una categoría duplicada en la misma vista")

    try:
        create_custom_view_column(
            view["id"], CreateCustomViewColumn(category_id=None), connection, {}
        )
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("se permitió duplicar la timeline general en la misma vista")

    copy = duplicate_custom_view(
        view["id"], DuplicateCustomView(name="Mi panel copia"), connection, {}
    )
    assert copy["is_default"] is False
    assert [column["category_id"] for column in copy["columns"]] == [
        column["category_id"] for column in reordered["columns"]
    ]
    assert [column["width"] for column in copy["columns"]] == [
        column["width"] for column in reordered["columns"]
    ]

    initial_all = create_custom_view(
        CreateCustomView(
            name="Timeline y categoría",
            category_ids=categories[:1],
            include_all=True,
        ),
        connection,
        {},
    )
    assert [column["category_id"] for column in initial_all["columns"]] == [
        None,
        categories[0],
    ]
    assert initial_all["columns"][0]["title"] == "Todo"

    promoted = update_custom_view(
        copy["id"], UpdateCustomView(is_default=True), connection, {}
    )
    assert promoted["is_default"] is True
    assert connection.execute(
        "SELECT is_default FROM custom_views WHERE id=?", (view["id"],)
    ).fetchone()[0] == 0

    delete_custom_view(copy["id"], connection, {})
    assert connection.execute(
        "SELECT is_default FROM custom_views WHERE id=?", (view["id"],)
    ).fetchone()[0] == 1
    assert connection.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()[0] == "11"
    column_info = {
        row[1]: row for row in connection.execute(
            "PRAGMA table_info(custom_view_columns)"
        )
    }
    assert column_info["category_id"][3] == 0
    assert "width" in column_info
