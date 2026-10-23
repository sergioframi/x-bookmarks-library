from __future__ import annotations

import hashlib
import json
import re
import unicodedata

import numpy as np

from .db import upsert_search_document
from .semantic_worker import OnDemandEmbeddingWorker, SemanticUnavailable
from .taxonomy import CATEGORY_TERMS, TAG_TERMS


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def normalize_tag(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", "-", value)


def combined_fields(row) -> dict[str,str]:
    urls = " ".join((item.get("expanded_url") or item.get("url") or "") for item in json.loads(row["urls_json"] or "[]") if isinstance(item,dict))
    return {"main":row["display_text"] or "", "quote":row["quote_text"] or "",
            "card":" ".join(filter(None,[row["card_title"],row["card_description"]])), "url":urls}


def evidence_for(terms: list[str], fields: dict[str,str]) -> tuple[float,dict]:
    weights = {"main":1.0,"card":0.7,"url":0.5,"quote":0.35}
    evidence = []
    score = 0.0
    for source,text in fields.items():
        lowered = text.casefold()
        matches = sorted({term.strip() for term in terms if term.casefold() in lowered})
        if matches:
            evidence.append({"source":source,"terms":matches[:6]})
            score += weights[source] * min(1.5, 0.65 + 0.25 * len(matches))
    return score,{"method":"rules-v1","matches":evidence}


def classify(connection, *, only_unclassified: bool = False, semantic: bool = True) -> dict:
    where = "AND NOT EXISTS (SELECT 1 FROM category_assignments ca WHERE ca.tweet_id=t.tweet_id)" if only_unclassified else ""
    rows = connection.execute(f"""
      SELECT t.*,COALESCE(qt.display_text,'') quote_text FROM tweets t
      LEFT JOIN bookmark_quotes bq ON bq.bookmark_id=t.tweet_id
      LEFT JOIN tweets qt ON qt.tweet_id=bq.quoted_tweet_id
      WHERE t.is_bookmark=1 {where} ORDER BY t.tweet_id
    """).fetchall()
    category_rows=list(connection.execute("""SELECT c.id,c.slug,p.slug parent_slug FROM categories c
      LEFT JOIN categories p ON p.id=c.parent_id"""))
    category_ids = {row["slug"]:row["id"] for row in category_rows}
    category_parents = {row["id"]:category_ids[row["parent_slug"]]
                        for row in category_rows if row["parent_slug"]}
    profile=connection.execute("SELECT state,source FROM taxonomy_profiles WHERE id=1").fetchone()
    adaptive=bool(profile and profile["state"]=="active" and profile["source"]=="discovery")
    prototypes: dict[int,np.ndarray] = {}
    semantic_error = None
    if semantic and rows and not adaptive:
        leaf_rows = connection.execute("""
          SELECT c.id,c.slug,c.name,c.description,p.name parent_name FROM categories c
          LEFT JOIN categories p ON p.id=c.parent_id WHERE c.parent_id IS NOT NULL
        """).fetchall()
        try:
            model,vectors = OnDemandEmbeddingWorker(timeout_seconds=45).encode(
                [f"{r['parent_name']}. {r['name']}. {r['description']}" for r in leaf_rows]
            )
            if model == MODEL:
                prototypes = {r["id"]:vectors[i] for i,r in enumerate(leaf_rows)}
        except SemanticUnavailable as exc:
            semantic_error = str(exc)
    classified = auto_categories = auto_tags = 0
    for row in rows:
        tweet_id = row["tweet_id"]
        connection.execute("DELETE FROM category_assignments WHERE tweet_id=? AND origin='auto'",(tweet_id,))
        connection.execute("DELETE FROM tag_assignments WHERE tweet_id=? AND origin='auto'",(tweet_id,))
        connection.execute("DELETE FROM content_type_assignments WHERE tweet_id=? AND origin='auto'",(tweet_id,))
        fields = combined_fields(row)
        assignments: dict[int,tuple[float,dict]] = {}
        for slug,terms in CATEGORY_TERMS.items():
            if adaptive or slug not in category_ids:
                continue
            score,evidence = evidence_for(terms,fields)
            if score >= 0.55:
                assignments[category_ids[slug]] = (min(0.99,0.5 + score/3),evidence)
        embedding_row = connection.execute("SELECT vector,dimension FROM embeddings WHERE tweet_id=? AND model=?",(tweet_id,MODEL)).fetchone()
        if adaptive and embedding_row:
            from .taxonomy_discovery import adaptive_assignments
            vector = np.frombuffer(embedding_row["vector"],dtype=np.float32)
            for category_id,similarity,evidence in adaptive_assignments(connection,vector):
                assignments[category_id]=(similarity,evidence)
        elif prototypes and embedding_row:
            vector = np.frombuffer(embedding_row["vector"],dtype=np.float32)
            semantic_scores = sorted(((float(np.dot(vector,p)),category_id) for category_id,p in prototypes.items()),reverse=True)
            for similarity,category_id in semantic_scores[:2]:
                if similarity >= (0.48 if assignments else 0.42):
                    existing = assignments.get(category_id)
                    evidence = {"method":"multilingual-embedding+rules-v1","semantic_similarity":round(similarity,4)}
                    if existing:
                        evidence["rule_evidence"] = existing[1]
                    assignments[category_id] = (max(existing[0] if existing else 0, min(0.9,similarity)),evidence)
        if not assignments and not adaptive and "other-interests" in category_ids:
            assignments[category_ids["other-interests"]] = (0.15,{"method":"fallback","reason":"sin señal suficiente; revisar"})
        for child,(confidence,evidence) in list(assignments.items()):
            parent=category_parents.get(child)
            if parent and parent not in assignments:
                assignments[parent]=(confidence,{"method":"taxonomy-parent","child":child})
        for category_id,(confidence,evidence) in assignments.items():
            connection.execute("""
              INSERT INTO category_assignments(tweet_id,category_id,origin,confidence,evidence_json)
              VALUES(?,?,'auto',?,?) ON CONFLICT(tweet_id,category_id,origin) DO UPDATE SET
               confidence=excluded.confidence,evidence_json=excluded.evidence_json
            """,(tweet_id,category_id,confidence,json.dumps(evidence,ensure_ascii=False)))
            auto_categories += 1
        for name,terms in TAG_TERMS.items():
            score,evidence = evidence_for(terms,fields)
            if score < 0.55: continue
            normalized=normalize_tag(name)
            connection.execute("INSERT INTO tags(name,normalized) VALUES(?,?) ON CONFLICT(normalized) DO NOTHING",(name,normalized))
            tag_id=connection.execute("SELECT id FROM tags WHERE normalized=?",(normalized,)).fetchone()[0]
            connection.execute("""INSERT INTO tag_assignments(tweet_id,tag_id,origin,confidence,evidence_json)
              VALUES(?,?,'auto',?,?) ON CONFLICT(tweet_id,tag_id,origin) DO UPDATE SET
              confidence=excluded.confidence,evidence_json=excluded.evidence_json""",
              (tweet_id,tag_id,min(.99,.5+score/3),json.dumps(evidence,ensure_ascii=False)))
            auto_tags += 1
        text=(fields["main"]+" "+fields["card"]).casefold()
        types=[]
        if any(x in text for x in ("github.com"," tool","extension","released","cli ")): types.append("tool")
        if row["card_title"] or any("http" in (u.get("expanded_url") or "") for u in json.loads(row["urls_json"] or "[]") if isinstance(u,dict)): types.append("article")
        if "thread" in text or row["conversation_id"] and row["conversation_id"] != tweet_id: types.append("thread")
        if any(x in text for x in ("tutorial","how to","guide","paso a paso")): types.append("tutorial")
        media_items=json.loads(row["media_json"] or "[]")
        if any(isinstance(item,dict) and item.get("type") in ("video","animated_gif") for item in media_items): types.append("video")
        if any(isinstance(item,dict) and item.get("type")=="photo" for item in media_items): types.append("image")
        if not types: types=["reference"]
        for content_type in set(types):
            connection.execute("INSERT INTO content_type_assignments(tweet_id,content_type,origin,confidence,evidence_json) VALUES(?,?,'auto',.7,'{}')",(tweet_id,content_type))
        classified += 1
    connection.commit()
    rebuild_search_documents(connection)
    personalized_count=connection.execute(
        "SELECT count(*) FROM category_prototypes WHERE model=?",(MODEL,)
    ).fetchone()[0] if adaptive else 0
    return {"processed":len(rows),"classified":classified,"auto_category_assignments":auto_categories,
            "auto_tag_assignments":auto_tags,"semantic_prototypes":len(prototypes)+personalized_count,
            "semantic_error":semantic_error}


def rebuild_search_documents(connection, tweet_ids: list[str] | None = None) -> int:
    selection=""
    params=()
    if tweet_ids:
        selection=" AND t.tweet_id IN ("+",".join("?" for _ in tweet_ids)+")"
        params=tuple(tweet_ids)
    rows=connection.execute("""
      SELECT t.*,COALESCE(qt.display_text,'') quote_text,COALESCE(qt.author_handle,'') quote_handle
      FROM tweets t LEFT JOIN bookmark_quotes bq ON bq.bookmark_id=t.tweet_id
      LEFT JOIN tweets qt ON qt.tweet_id=bq.quoted_tweet_id WHERE t.is_bookmark=1
    """+selection,params).fetchall()
    for row in rows:
        urls=[]
        for item in json.loads(row["urls_json"] or "[]"):
            if isinstance(item,dict): urls.extend(filter(None,[item.get("url"),item.get("expanded_url")]))
        media=json.loads(row["media_json"] or "[]")
        alt=" ".join(str(x.get("alt_text") or "") for x in media if isinstance(x,dict))
        labels=[r[0] for r in connection.execute("""SELECT c.name FROM effective_category_assignments e JOIN categories c ON c.id=e.category_id WHERE e.tweet_id=? UNION SELECT t.name FROM effective_tag_assignments e JOIN tags t ON t.id=e.tag_id WHERE e.tweet_id=?""",(row["tweet_id"],row["tweet_id"]))]
        main=row["display_text"] or ""
        card=" ".join(filter(None,[row["card_title"],row["card_description"],alt]))
        summary=(row["card_title"] or main[:280]).strip()
        embedding_text="\n".join(x for x in [main,row["quote_text"],card," ".join(urls)] if x)
        digest=hashlib.sha256(embedding_text.encode()).hexdigest()
        upsert_search_document(connection,row["tweet_id"],main_text=main,quote_text=row["quote_text"],
          card_text=card,urls_text=" ".join(urls),handles_text=" ".join(filter(None,[row["author_handle"],row["author_name"],row["quote_handle"]])),
          summary_text=summary,labels_text=" ".join(labels),embedding_text=embedding_text,embedding_sha256=digest)
    connection.commit()
    return len(rows)
