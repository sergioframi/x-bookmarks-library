from __future__ import annotations

import os
import resource
from typing import Callable,Iterable


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def chunks(values: list, size: int) -> Iterable[list]:
    for offset in range(0, len(values), size):
        yield values[offset:offset+size]


def generate_embeddings(connection, *, only_missing: bool = True, batch_size: int = 32,
                        progress_callback:Callable[[int,int],None]|None=None) -> dict:
    limit_mib=int(os.getenv("EMBEDDING_RLIMIT_AS_MIB","2048"))
    if limit_mib:
        limit=limit_mib*1024*1024
        resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    import numpy as np
    from fastembed import TextEmbedding

    condition="""AND NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.tweet_id=d.tweet_id
      AND e.model=? AND e.text_sha256=d.embedding_sha256)""" if only_missing else ""
    params=(MODEL,) if only_missing else ()
    rows=connection.execute(f"""SELECT tweet_id,embedding_text,embedding_sha256
      FROM search_documents d WHERE embedding_text<>'' {condition} ORDER BY tweet_id""",params).fetchall()
    total=connection.execute("SELECT count(*) FROM search_documents WHERE embedding_text<>''").fetchone()[0]
    base=max(0,total-len(rows))
    if progress_callback:progress_callback(base,total)
    threads=max(1,min(int(os.getenv("EMBEDDING_THREADS","4")),4))
    model=TextEmbedding(model_name=MODEL,
      cache_dir=os.getenv("FASTEMBED_CACHE_PATH","/app/models/fastembed"),threads=threads)
    done=0
    for group in chunks(list(rows),batch_size):
        vectors=model.embed([row["embedding_text"] for row in group],batch_size=batch_size)
        for row,vector in zip(group,vectors):
            value=np.asarray(vector,dtype=np.float32)
            norm=float(np.linalg.norm(value))
            if norm: value/=norm
            connection.execute("""INSERT INTO embeddings(tweet_id,model,dimension,vector,text_sha256)
              VALUES(?,?,?,?,?) ON CONFLICT(tweet_id,model) DO UPDATE SET
              dimension=excluded.dimension,vector=excluded.vector,text_sha256=excluded.text_sha256,
              created_at=CURRENT_TIMESTAMP""",(row["tweet_id"],MODEL,value.size,value.tobytes(),row["embedding_sha256"]))
            done+=1
        connection.commit()
        if progress_callback:progress_callback(base+done,total)
    return {"model":MODEL,"embedded":done,"dimension":384,"candidates":len(rows)}
