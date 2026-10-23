from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .embedder import MODEL
from .semantic_worker import OnDemandEmbeddingWorker, SemanticUnavailable


TOKEN_RE=re.compile(r'"([^"\n]+)"|(\S+)')


@dataclass
class SearchHit:
    tweet_id: str
    score: float
    snippet: str
    quote_snippet: str
    match_only_in_quote: bool
    sources: list[str]


def fts_literal_query(value: str) -> str:
    terms=[]
    for match in TOKEN_RE.finditer(value.strip()):
        term=(match.group(1) or match.group(2)).replace('"','""')
        if term: terms.append(f'"{term}"')
    return " AND ".join(terms)


def filter_candidates(connection: sqlite3.Connection, filters: dict[str,Any]) -> list[str]:
    clauses=["t.is_bookmark=1", "t.bookmark_state NOT IN ('removed','locally_archived')"]
    params=[]
    def multi_exists(values,key,sql):
        if values:
            marks=",".join("?" for _ in values); clauses.append(sql.format(marks=marks)); params.extend(values)
    multi_exists(filters.get("categories"),"categories","EXISTS (SELECT 1 FROM effective_category_assignments ec WHERE ec.tweet_id=t.tweet_id AND ec.category_id IN ({marks}))")
    multi_exists(filters.get("tags"),"tags","EXISTS (SELECT 1 FROM effective_tag_assignments et WHERE et.tweet_id=t.tweet_id AND et.tag_id IN ({marks}))")
    multi_exists(filters.get("authors"),"authors","t.author_handle IN ({marks})")
    multi_exists(filters.get("content_types"),"content_types","EXISTS (SELECT 1 FROM content_type_assignments ct WHERE ct.tweet_id=t.tweet_id AND ct.content_type IN ({marks}))")
    if filters.get("has_media") is not None:
        clauses.append("t.media_json " + ("<> '[]'" if filters["has_media"] else "= '[]'"))
    if filters.get("has_links") is not None:
        clauses.append("t.urls_json " + ("<> '[]'" if filters["has_links"] else "= '[]'"))
    if filters.get("date_from"):
        clauses.append("t.created_at_iso>=?"); params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("t.created_at_iso<=?"); params.append(filters["date_to"]+"T23:59:59+00:00")
    rows=connection.execute(f"""SELECT t.tweet_id FROM tweets t
      WHERE {' AND '.join(clauses)}
      ORDER BY (t.bookmark_sort_index IS NULL),t.bookmark_sort_index DESC,
               COALESCE(t.created_at_iso,'') DESC,t.tweet_id DESC""",params).fetchall()
    return [row[0] for row in rows]


class SearchEngine:
    def __init__(self, connection: sqlite3.Connection, worker: OnDemandEmbeddingWorker|None=None):
        self.connection=connection; self.connection.row_factory=sqlite3.Row
        self.worker=worker or OnDemandEmbeddingWorker()

    def _fts(self, query: str, candidates: list[str]) -> list[SearchHit]:
        expression=fts_literal_query(query)
        if not expression: return self._browse(candidates)
        allowed=set(candidates)
        rows=self.connection.execute("""SELECT tweet_id,bm25(tweet_fts,0,8,5,2,2,1.5,1,2.5) rank,
          highlight(tweet_fts,1,char(1),char(2)) main_hit,
          highlight(tweet_fts,2,char(1),char(2)) quote_hit,main_text,quote_text
          FROM tweet_fts WHERE tweet_fts MATCH ? ORDER BY rank""",(expression,)).fetchall()
        hits=[]
        for index,row in enumerate(row for row in rows if row["tweet_id"] in allowed):
            main_mark="\x01" in row["main_hit"]; quote_mark="\x01" in row["quote_hit"]
            hits.append(SearchHit(row["tweet_id"],1/(60+index+1),(row["main_text"] or "")[:500],
              (row["quote_text"] or "")[:400],quote_mark and not main_mark,["fts"]))
        return hits

    def _browse(self,candidates:list[str])->list[SearchHit]:
        if not candidates:return []
        docs={r["tweet_id"]:r for r in self.connection.execute("SELECT tweet_id,main_text,quote_text FROM search_documents")}
        return [SearchHit(tid,0,(docs[tid]["main_text"] or "")[:500] if tid in docs else "",
          (docs[tid]["quote_text"] or "")[:400] if tid in docs else "",False,["browse"]) for tid in candidates]

    def text(self,query:str,filters:dict[str,Any],page:int=1,page_size:int=30)->dict:
        candidates=filter_candidates(self.connection,filters)
        hits=self._fts(query,candidates)
        start=(page-1)*page_size
        return self._response(query,"text","text",hits[start:start+page_size],len(hits),page,page_size,None,False)

    def _query_vector(self,query:str)->tuple[np.ndarray,bool]:
        normalized=" ".join(query.casefold().split())
        digest=hashlib.sha256(normalized.encode()).hexdigest()
        row=self.connection.execute("SELECT dimension,vector FROM semantic_query_cache WHERE query_hash=? AND model=?",(digest,MODEL)).fetchone()
        if row:
            self.connection.execute("UPDATE semantic_query_cache SET last_used_at=CURRENT_TIMESTAMP,use_count=use_count+1 WHERE query_hash=? AND model=?",(digest,MODEL)); self.connection.commit()
            return np.frombuffer(row["vector"],dtype=np.float32),True
        model,vector=self.worker.encode_query(query)
        if model!=MODEL: raise SemanticUnavailable("modelo inesperado; se usa FTS5")
        self.connection.execute("""INSERT OR REPLACE INTO semantic_query_cache(query_hash,model,query_text,dimension,vector)
          VALUES(?,?,?,?,?)""",(digest,MODEL,query,vector.size,vector.astype(np.float32).tobytes())); self.connection.commit()
        return vector,False

    def _semantic(self,query:str,candidates:list[str])->tuple[list[SearchHit],bool]:
        vector,cached=self._query_vector(query); allowed=set(candidates)
        rows=self.connection.execute("""SELECT e.tweet_id,e.dimension,e.vector,d.main_text,d.quote_text
          FROM embeddings e JOIN search_documents d ON d.tweet_id=e.tweet_id WHERE e.model=?""",(MODEL,)).fetchall()
        scored=[]
        for row in rows:
            if row["tweet_id"] not in allowed: continue
            candidate=np.frombuffer(row["vector"],dtype=np.float32)
            if candidate.size==vector.size==row["dimension"]: scored.append((float(np.dot(vector,candidate)),row))
        scored.sort(key=lambda pair:pair[0],reverse=True)
        return [SearchHit(r["tweet_id"],score,(r["main_text"] or "")[:500],(r["quote_text"] or "")[:400],False,["semantic"]) for score,r in scored],cached

    @staticmethod
    def _rrf(text:list[SearchHit],semantic:list[SearchHit])->list[SearchHit]:
        combined={}; scores={}
        for source,hits,weight in (("fts",text,1.7),("semantic",semantic,1.0)):
            for rank,hit in enumerate(hits,start=1):
                scores[hit.tweet_id]=scores.get(hit.tweet_id,0)+weight/(60+rank)
                if hit.tweet_id not in combined or source=="fts": combined[hit.tweet_id]=hit
                if source not in combined[hit.tweet_id].sources: combined[hit.tweet_id].sources.append(source)
        ordered=sorted(combined.values(),key=lambda hit:scores[hit.tweet_id],reverse=True)
        for hit in ordered: hit.score=scores[hit.tweet_id]
        return ordered

    def hybrid(self,query:str,filters:dict[str,Any],page:int=1,page_size:int=30)->dict:
        candidates=filter_candidates(self.connection,filters); text=self._fts(query,candidates)
        if not query.strip():
            start=(page-1)*page_size
            return self._response(query,"hybrid","text",text[start:start+page_size],len(text),page,page_size,None,False)
        try:
            semantic,cached=self._semantic(query,candidates); hits=self._rrf(text,semantic); error=None; effective="hybrid"
        except Exception as exc:
            hits=text; cached=False; effective="text"
            error=str(exc) if isinstance(exc,SemanticUnavailable) else f"error semántico ({type(exc).__name__}); se usa FTS5"
        start=(page-1)*page_size
        return self._response(query,"hybrid",effective,hits[start:start+page_size],len(hits),page,page_size,error,cached)

    @staticmethod
    def _response(query,requested,effective,hits,total,page,page_size,error,cached):
        return {"query":query,"requested_mode":requested,"effective_mode":effective,
          "semantic":{"status":"ok" if effective=="hybrid" else ("degraded_to_fts" if error else "not_requested"),"error":error,"query_cache_hit":cached},
          "total":total,"page":page,"page_size":page_size,"results":[asdict(h) for h in hits]}

    def search(self,query:str,mode:str="hybrid",limit:int=30)->dict:
        return self.text(query,{},1,limit) if mode=="text" else self.hybrid(query,{},1,limit)
