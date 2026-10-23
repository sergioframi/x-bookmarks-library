from __future__ import annotations

import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from app.db import connect,initialize_schema,upsert_search_document
from app.embedder import MODEL
from app.search import SearchEngine


class SlowWorker:
    calls=0
    def encode_query(self,query):
        self.calls+=1;time.sleep(.7)
        vector=np.zeros(384,dtype=np.float32);vector[0]=1
        return MODEL,vector


def prepare(path):
    connection=connect(path);initialize_schema(connection)
    connection.execute("INSERT INTO tweets(tweet_id,is_bookmark,raw_json,source_hash) VALUES('1',1,'{}','x')")
    connection.execute("INSERT INTO annotations(tweet_id) VALUES('1')")
    upsert_search_document(connection,"1",main_text="SSRF exact result",embedding_text="SSRF exact result",embedding_sha256="x")
    vector=np.zeros(384,dtype=np.float32);vector[0]=1
    connection.execute("INSERT INTO embeddings(tweet_id,model,dimension,vector,text_sha256) VALUES(?,?,?,?,?)",("1",MODEL,384,vector.tobytes(),"x"));connection.commit();connection.close()


def test_fts_remains_responsive_and_query_vector_is_cached(tmp_path):
    path=tmp_path/"search.sqlite3";prepare(path);worker=SlowWorker()
    def hybrid():
        c=connect(path)
        try:return SearchEngine(c,worker).hybrid("SSRF",{},1,30)
        finally:c.close()
    with ThreadPoolExecutor() as pool:
        pending=pool.submit(hybrid);time.sleep(.1)
        c=connect(path);started=time.perf_counter();exact=SearchEngine(c,worker).text("SSRF",{},1,30);elapsed=time.perf_counter()-started;c.close()
        result=pending.result()
    assert elapsed<.3 and exact["results"][0]["tweet_id"]=="1"
    assert result["effective_mode"]=="hybrid" and worker.calls==1
    c=connect(path);cached=SearchEngine(c,worker).hybrid("SSRF",{},1,30);c.close()
    assert cached["semantic"]["query_cache_hit"] is True and worker.calls==1
