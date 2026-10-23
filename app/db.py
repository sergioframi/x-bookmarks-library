from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_users (
 username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
 session_version INTEGER NOT NULL DEFAULT 1 CHECK(session_version > 0),
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS onboarding_state (
 id INTEGER PRIMARY KEY CHECK(id=1),
 locale TEXT NOT NULL DEFAULT 'es' CHECK(locale IN ('es','en')),
 theme TEXT NOT NULL DEFAULT 'light' CHECK(theme IN ('light','dark')),
 palette TEXT NOT NULL DEFAULT 'ice' CHECK(palette IN ('mono','ice','lavender','rose','coral')),
 step TEXT NOT NULL DEFAULT 'account' CHECK(step IN
 ('account','welcome','extension','import','categories','category_confirmation','complete')),
 completed_at TEXT,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS source_imports (
 id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, sha256 TEXT NOT NULL,
 tool TEXT, schema_version INTEGER, kind TEXT, collection_status TEXT,
 started_at TEXT NOT NULL, finished_at TEXT, total INTEGER NOT NULL DEFAULT 0,
 new_count INTEGER NOT NULL DEFAULT 0, updated_count INTEGER NOT NULL DEFAULT 0,
 existing_count INTEGER NOT NULL DEFAULT 0, unavailable_count INTEGER NOT NULL DEFAULT 0,
 quote_count INTEGER NOT NULL DEFAULT 0, quote_text_count INTEGER NOT NULL DEFAULT 0,
 error_count INTEGER NOT NULL DEFAULT 0, errors_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS sync_devices (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
 account_user_id TEXT NOT NULL, created_at TEXT NOT NULL, last_seen_at TEXT,
 revoked_at TEXT, extension_version TEXT
);
CREATE TABLE IF NOT EXISTS pairing_codes (
 code_hash TEXT PRIMARY KEY, account_user_id TEXT NOT NULL,
 created_at TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_runs (
 id TEXT PRIMARY KEY, scan_id TEXT NOT NULL UNIQUE,
 device_id TEXT REFERENCES sync_devices(id) ON DELETE SET NULL,
 archive_sha256 TEXT NOT NULL, archive_path TEXT NOT NULL,
 collection_mode TEXT, collection_status TEXT, collection_reason TEXT,
 started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL DEFAULT 'processing', import_id INTEGER REFERENCES source_imports(id),
 activated_count INTEGER NOT NULL DEFAULT 0,
 suspected_removed_count INTEGER NOT NULL DEFAULT 0,
 removed_count INTEGER NOT NULL DEFAULT 0,
 receipt_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS runtime_locks (
 name TEXT PRIMARY KEY, owner TEXT NOT NULL, acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS enrichment_jobs (
 id TEXT PRIMARY KEY, sync_id TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL, phase TEXT NOT NULL DEFAULT 'queued',
 total INTEGER NOT NULL DEFAULT 0, completed INTEGER NOT NULL DEFAULT 0,
 message TEXT NOT NULL DEFAULT '', error TEXT,
 started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 heartbeat_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, sync_id TEXT NOT NULL,
 source TEXT NOT NULL, level TEXT NOT NULL, phase TEXT NOT NULL DEFAULT '',
 message TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sync_events_run ON sync_events(sync_id,id);
CREATE TABLE IF NOT EXISTS tweets (
 tweet_id TEXT PRIMARY KEY, is_bookmark INTEGER NOT NULL DEFAULT 0 CHECK(is_bookmark IN (0,1)),
 bookmark_sort_index INTEGER,
 bookmark_state TEXT NOT NULL DEFAULT 'active' CHECK(bookmark_state IN
 ('active','suspected_removed','removed','locally_archived')),
 missing_complete_scans INTEGER NOT NULL DEFAULT 0,
 last_observed_scan_id TEXT, removed_at TEXT,
 source_status TEXT NOT NULL DEFAULT 'available', full_text TEXT NOT NULL DEFAULT '',
 display_text TEXT NOT NULL DEFAULT '', author_id TEXT, author_handle TEXT, author_name TEXT,
 author_avatar TEXT, created_at_raw TEXT, created_at_iso TEXT, lang TEXT, source TEXT,
 conversation_id TEXT, in_reply_to_tweet_id TEXT, in_reply_to_user_id TEXT,
 card_type TEXT, card_url TEXT, card_title TEXT, card_description TEXT,
 urls_json TEXT NOT NULL DEFAULT '[]', hashtags_json TEXT NOT NULL DEFAULT '[]',
 mentions_json TEXT NOT NULL DEFAULT '[]', media_json TEXT NOT NULL DEFAULT '[]',
 folder_ids_json TEXT NOT NULL DEFAULT '[]', metrics_json TEXT NOT NULL DEFAULT '{}',
 raw_json TEXT NOT NULL, source_hash TEXT NOT NULL,
 first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tweets_bookmark ON tweets(is_bookmark);
CREATE INDEX IF NOT EXISTS idx_tweets_bookmark_state ON tweets(is_bookmark,bookmark_state);
CREATE INDEX IF NOT EXISTS idx_tweets_author ON tweets(author_handle);
CREATE INDEX IF NOT EXISTS idx_tweets_created ON tweets(created_at_iso);
CREATE INDEX IF NOT EXISTS idx_tweets_status ON tweets(source_status);
CREATE TABLE IF NOT EXISTS bookmark_quotes (
 bookmark_id TEXT PRIMARY KEY REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 quoted_tweet_id TEXT REFERENCES tweets(tweet_id) ON DELETE SET NULL,
 quote_status TEXT NOT NULL DEFAULT 'available', raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quotes_quoted ON bookmark_quotes(quoted_tweet_id);
CREATE TABLE IF NOT EXISTS annotations (
 tweet_id TEXT PRIMARY KEY REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 reading_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK(reading_status IN
 ('unreviewed','read_later','try_later','reading','completed','reference','archived')),
 priority INTEGER NOT NULL DEFAULT 0 CHECK(priority BETWEEN 0 AND 5),
 favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)), notes TEXT NOT NULL DEFAULT '',
 review_date TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categories (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
 parent_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
 description TEXT NOT NULL DEFAULT '', sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS category_assignments (
 tweet_id TEXT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
 origin TEXT NOT NULL CHECK(origin IN ('auto','manual')), confidence REAL,
 evidence_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(tweet_id, category_id, origin)
);
CREATE TABLE IF NOT EXISTS category_suppressions (
 tweet_id TEXT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(tweet_id, category_id)
);
CREATE TABLE IF NOT EXISTS tags (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, normalized TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS tag_assignments (
 tweet_id TEXT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
 origin TEXT NOT NULL CHECK(origin IN ('auto','manual')), confidence REAL,
 evidence_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(tweet_id, tag_id, origin)
);
CREATE TABLE IF NOT EXISTS tag_suppressions (
 tweet_id TEXT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(tweet_id, tag_id)
);
CREATE TABLE IF NOT EXISTS content_type_assignments (
 tweet_id TEXT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 content_type TEXT NOT NULL CHECK(content_type IN
 ('tool','article','thread','tutorial','reference','video','image','other')),
 origin TEXT NOT NULL CHECK(origin IN ('auto','manual')), confidence REAL,
 evidence_json TEXT NOT NULL DEFAULT '{}', PRIMARY KEY(tweet_id, content_type, origin)
);
CREATE TABLE IF NOT EXISTS custom_views (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
 is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
 sort_order INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS custom_view_columns (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 view_id INTEGER NOT NULL REFERENCES custom_views(id) ON DELETE CASCADE,
 category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
 title TEXT NOT NULL DEFAULT '', position INTEGER NOT NULL DEFAULT 0,
 width INTEGER NOT NULL DEFAULT 360 CHECK(width BETWEEN 300 AND 2400),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(view_id,category_id)
);
CREATE INDEX IF NOT EXISTS idx_custom_view_columns_order
 ON custom_view_columns(view_id,position,id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_custom_view_columns_all_unique
 ON custom_view_columns(view_id) WHERE category_id IS NULL;
CREATE TABLE IF NOT EXISTS search_documents (
 tweet_id TEXT PRIMARY KEY REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 main_text TEXT NOT NULL DEFAULT '', quote_text TEXT NOT NULL DEFAULT '',
 card_text TEXT NOT NULL DEFAULT '', urls_text TEXT NOT NULL DEFAULT '',
 handles_text TEXT NOT NULL DEFAULT '', summary_text TEXT NOT NULL DEFAULT '',
 labels_text TEXT NOT NULL DEFAULT '', embedding_text TEXT NOT NULL DEFAULT '',
 embedding_sha256 TEXT NOT NULL DEFAULT ''
);
CREATE VIRTUAL TABLE IF NOT EXISTS tweet_fts USING fts5(
 tweet_id UNINDEXED, main_text, quote_text, card_text, urls_text, handles_text,
 summary_text, labels_text, tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS embeddings (
 tweet_id TEXT NOT NULL REFERENCES search_documents(tweet_id) ON DELETE CASCADE,
 model TEXT NOT NULL, dimension INTEGER NOT NULL CHECK(dimension > 0), vector BLOB NOT NULL,
 text_sha256 TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(tweet_id, model)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
CREATE TABLE IF NOT EXISTS semantic_query_cache (
 query_hash TEXT NOT NULL, model TEXT NOT NULL, query_text TEXT NOT NULL,
 dimension INTEGER NOT NULL, vector BLOB NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, use_count INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(query_hash, model)
);
CREATE TABLE IF NOT EXISTS taxonomy_profiles (
 id INTEGER PRIMARY KEY CHECK(id=1),
 state TEXT NOT NULL CHECK(state IN ('empty','draft','active')),
 source TEXT NOT NULL CHECK(source IN ('adaptive','discovery','legacy','template')),
 active_run_id INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS taxonomy_discovery_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 status TEXT NOT NULL CHECK(status IN ('draft','applied','failed')),
 model TEXT NOT NULL, bookmark_count INTEGER NOT NULL,
 cluster_count INTEGER NOT NULL DEFAULT 0,
 parameters_json TEXT NOT NULL DEFAULT '{}', error TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 applied_at TEXT
);
CREATE TABLE IF NOT EXISTS taxonomy_candidates (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id INTEGER NOT NULL REFERENCES taxonomy_discovery_runs(id) ON DELETE CASCADE,
 name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
 keywords_json TEXT NOT NULL DEFAULT '[]', bookmark_count INTEGER NOT NULL,
 cohesion REAL NOT NULL, threshold REAL NOT NULL,
 dimension INTEGER NOT NULL, centroid BLOB NOT NULL,
 sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS taxonomy_candidate_members (
 candidate_id INTEGER NOT NULL REFERENCES taxonomy_candidates(id) ON DELETE CASCADE,
 tweet_id TEXT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
 similarity REAL NOT NULL,
 PRIMARY KEY(candidate_id,tweet_id)
);
CREATE INDEX IF NOT EXISTS idx_taxonomy_candidate_run
 ON taxonomy_candidates(run_id,sort_order);
CREATE TABLE IF NOT EXISTS category_prototypes (
 category_id INTEGER PRIMARY KEY REFERENCES categories(id) ON DELETE CASCADE,
 model TEXT NOT NULL, dimension INTEGER NOT NULL,
 vector BLOB NOT NULL, threshold REAL NOT NULL,
 sample_size INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE VIEW IF NOT EXISTS effective_category_assignments AS
 SELECT ca.tweet_id,ca.category_id,ca.origin,ca.confidence,ca.evidence_json
 FROM category_assignments ca WHERE ca.origin='manual' OR (ca.origin='auto' AND NOT EXISTS
 (SELECT 1 FROM category_suppressions cs WHERE cs.tweet_id=ca.tweet_id AND cs.category_id=ca.category_id)
 AND NOT EXISTS (SELECT 1 FROM category_assignments manual
  WHERE manual.tweet_id=ca.tweet_id AND manual.category_id=ca.category_id AND manual.origin='manual'));
CREATE VIEW IF NOT EXISTS effective_tag_assignments AS
 SELECT ta.tweet_id,ta.tag_id,ta.origin,ta.confidence,ta.evidence_json
 FROM tag_assignments ta WHERE ta.origin='manual' OR NOT EXISTS
 (SELECT 1 FROM tag_suppressions ts WHERE ts.tweet_id=ta.tweet_id AND ts.tag_id=ta.tag_id);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    # FastAPI may resume a synchronous dependency in a different worker thread
    # when several column requests arrive together. Each request still owns its
    # connection, but SQLite must allow that sequential thread hand-off.
    connection = sqlite3.connect(path, timeout=10, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    # Version 2 keeps X's bookmark timeline position.  ALTER is deliberately
    # additive so existing annotations and indexes remain untouched.
    tweet_columns = {row[1] for row in connection.execute("PRAGMA table_info(tweets)")}
    if "bookmark_sort_index" not in tweet_columns:
        connection.execute("ALTER TABLE tweets ADD COLUMN bookmark_sort_index INTEGER")
    additions = {
        "bookmark_state": "TEXT NOT NULL DEFAULT 'active'",
        "missing_complete_scans": "INTEGER NOT NULL DEFAULT 0",
        "last_observed_scan_id": "TEXT",
        "removed_at": "TEXT",
    }
    for name, definition in additions.items():
        if name not in tweet_columns:
            connection.execute(f"ALTER TABLE tweets ADD COLUMN {name} {definition}")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_tweets_bookmark_sort ON tweets(bookmark_sort_index DESC)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_tweets_bookmark_state ON tweets(is_bookmark,bookmark_state)"
    )
    version_row = connection.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()
    try:
        schema_version = int(version_row[0]) if version_row else 0
    except (TypeError, ValueError):
        schema_version = 0
    if schema_version < 6:
        # A manual category is the authoritative row for that tweet/category
        # pair. Recreate the view once on existing databases so an automatic
        # row can never duplicate or outrank the user's selection.
        connection.execute("DROP VIEW IF EXISTS effective_category_assignments")
        connection.execute("""
          CREATE VIEW effective_category_assignments AS
          SELECT ca.tweet_id,ca.category_id,ca.origin,ca.confidence,ca.evidence_json
          FROM category_assignments ca
          WHERE ca.origin='manual' OR (ca.origin='auto'
            AND NOT EXISTS (SELECT 1 FROM category_suppressions cs
              WHERE cs.tweet_id=ca.tweet_id AND cs.category_id=ca.category_id)
            AND NOT EXISTS (SELECT 1 FROM category_assignments manual
              WHERE manual.tweet_id=ca.tweet_id AND manual.category_id=ca.category_id
                AND manual.origin='manual'))
        """)
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','6')"
        )
    if schema_version < 7:
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','7')"
        )
    if schema_version < 8:
        column_info = {
            row[1]: row for row in connection.execute(
                "PRAGMA table_info(custom_view_columns)"
            )
        }
        category_is_required = bool(column_info.get("category_id", (None,) * 4)[3])
        if "width" not in column_info or category_is_required:
            connection.execute("DROP INDEX IF EXISTS idx_custom_view_columns_order")
            connection.execute("DROP INDEX IF EXISTS idx_custom_view_columns_all_unique")
            connection.execute("""
              CREATE TABLE custom_view_columns_v8 (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               view_id INTEGER NOT NULL REFERENCES custom_views(id) ON DELETE CASCADE,
               category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
               title TEXT NOT NULL DEFAULT '', position INTEGER NOT NULL DEFAULT 0,
               width INTEGER NOT NULL DEFAULT 360 CHECK(width BETWEEN 300 AND 2400),
               created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
               updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
               UNIQUE(view_id,category_id)
              )
            """)
            width_expression = "width" if "width" in column_info else "360"
            connection.execute(f"""
              INSERT INTO custom_view_columns_v8(
               id,view_id,category_id,title,position,width,created_at,updated_at
              )
              SELECT id,view_id,category_id,title,position,{width_expression},created_at,updated_at
              FROM custom_view_columns
            """)
            connection.execute("DROP TABLE custom_view_columns")
            connection.execute(
                "ALTER TABLE custom_view_columns_v8 RENAME TO custom_view_columns"
            )
            connection.execute("""
              CREATE INDEX idx_custom_view_columns_order
              ON custom_view_columns(view_id,position,id)
            """)
            connection.execute("""
              CREATE UNIQUE INDEX idx_custom_view_columns_all_unique
              ON custom_view_columns(view_id) WHERE category_id IS NULL
            """)
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','8')"
        )
    if schema_version < 9:
        category_count = connection.execute("SELECT count(*) FROM categories").fetchone()[0]
        state, source = ("active", "legacy") if category_count else ("empty", "adaptive")
        connection.execute(
            """INSERT OR IGNORE INTO taxonomy_profiles(id,state,source)
               VALUES(1,?,?)""",
            (state, source),
        )
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','9')"
        )
    if schema_version < 10:
        user_count = connection.execute("SELECT count(*) FROM app_users").fetchone()[0]
        step = "complete" if user_count else "account"
        connection.execute(
            """INSERT OR IGNORE INTO onboarding_state(id,step,completed_at)
               VALUES(1,?,CASE WHEN ?='complete' THEN CURRENT_TIMESTAMP END)""",
            (step, step),
        )
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','10')"
        )
    if schema_version < 11:
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','11')"
        )
    connection.execute("INSERT OR IGNORE INTO schema_meta(key,value) VALUES('instance_id',?)", (str(secrets.token_hex(16)),))
    connection.commit()


initialize_search_schema = initialize_schema


def upsert_search_document(connection: sqlite3.Connection, tweet_id: str, **fields: str) -> None:
    names = ("main_text","quote_text","card_text","urls_text","handles_text",
             "summary_text","labels_text","embedding_text","embedding_sha256")
    values = (str(tweet_id), *(fields.get(name, "") for name in names))
    connection.execute("""
      INSERT INTO search_documents(tweet_id,main_text,quote_text,card_text,urls_text,
       handles_text,summary_text,labels_text,embedding_text,embedding_sha256)
      VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(tweet_id) DO UPDATE SET
       main_text=excluded.main_text,quote_text=excluded.quote_text,card_text=excluded.card_text,
       urls_text=excluded.urls_text,handles_text=excluded.handles_text,
       summary_text=excluded.summary_text,labels_text=excluded.labels_text,
       embedding_text=excluded.embedding_text,embedding_sha256=excluded.embedding_sha256
    """, values)
    connection.execute("DELETE FROM tweet_fts WHERE tweet_id=?", (str(tweet_id),))
    connection.execute("""
      INSERT INTO tweet_fts(tweet_id,main_text,quote_text,card_text,urls_text,
       handles_text,summary_text,labels_text) VALUES(?,?,?,?,?,?,?,?)
    """, values[:8])
