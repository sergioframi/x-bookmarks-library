from __future__ import annotations

import json

from app.db import connect,initialize_schema
from app.importer import import_xarchive
from app.search import filter_candidates


def archive(bookmarks):
    return {"export_metadata":{"tool":"xarchive","schema_version":2,"kind":"snapshot","collection":{"bookmarks":"partial"}},"bookmarks":bookmarks,"folders":[]}


def test_import_is_incremental_and_preserves_annotations(tmp_path):
    source=tmp_path/"export.json"
    source.write_text(json.dumps(archive([
      {"tweet_id":"9999999999999999991","sort_index":"100","status":"available","full_text":"main","author":{"screen_name":"alice"},"entities":{"urls":[],"hashtags":[],"mentions":[]},"quoted_tweet":{"tweet_id":"8888888888888888888","status":"available","full_text":"quoteOnlyTool","author":{"screen_name":"bob"}}},
      {"tweet_id":"9999999999999999992","sort_index":"200","status":"unavailable","full_text":None,"author":None,"entities":{}}
    ])),encoding="utf-8")
    connection=connect(tmp_path/"db.sqlite3");initialize_schema(connection)
    first=import_xarchive(connection,source)
    assert first["new"]==2 and first["unavailable"]==1 and first["quotes"]==1
    assert connection.execute("SELECT count(*) FROM tweets WHERE is_bookmark=1").fetchone()[0]==2
    assert connection.execute("SELECT is_bookmark FROM tweets WHERE tweet_id='8888888888888888888'").fetchone()[0]==0
    assert filter_candidates(connection,{})[:2]==["9999999999999999992","9999999999999999991"]
    assert connection.execute("SELECT bookmark_sort_index FROM tweets WHERE tweet_id='9999999999999999991'").fetchone()[0]==100
    connection.execute("UPDATE annotations SET priority=3,notes='keep' WHERE tweet_id='9999999999999999991'");connection.commit()
    second=import_xarchive(connection,source)
    assert second["existing"]==2 and second["new"]==0
    annotation=connection.execute("SELECT * FROM annotations WHERE tweet_id='9999999999999999991'").fetchone()
    assert (annotation["priority"],annotation["notes"])==(3,"keep")
    source.write_text(json.dumps(archive([json.loads(connection.execute("SELECT raw_json FROM tweets WHERE tweet_id='9999999999999999991'").fetchone()[0])])),encoding="utf-8")
    import_xarchive(connection,source)
    assert connection.execute("SELECT count(*) FROM tweets WHERE is_bookmark=1").fetchone()[0]==2


def test_quote_snapshot_never_downgrades_bookmark(tmp_path):
    source=tmp_path/"overlap.json"
    source.write_text(json.dumps(archive([
      {"tweet_id":"1000000000000000001","status":"available","full_text":"canonical complete text","author":{"screen_name":"author"},"entities":{}},
      {"tweet_id":"1000000000000000002","status":"available","full_text":"quotes it","author":{"screen_name":"other"},"entities":{},"quoted_tweet":{"tweet_id":"1000000000000000001","status":"available","full_text":"short snapshot","author":{"screen_name":"author"}}}
    ])),encoding="utf-8")
    connection=connect(tmp_path/"overlap.sqlite3");initialize_schema(connection)
    import_xarchive(connection,source)
    row=connection.execute("SELECT is_bookmark,full_text FROM tweets WHERE tweet_id='1000000000000000001'").fetchone()
    assert row["is_bookmark"]==1 and row["full_text"]=="canonical complete text"
