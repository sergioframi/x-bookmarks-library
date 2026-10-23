from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from typing import Any,Callable

import numpy as np

from .classifier import MODEL, rebuild_search_documents
from .taxonomy import CATEGORY_TERMS, TAXONOMY


METHOD = "local-spherical-kmeans-v1"
STOPWORDS = {
    "about", "after", "also", "and", "are", "been", "before", "being", "but",
    "can", "como", "con", "cuando", "del", "desde", "does", "este", "esto",
    "for", "from", "has", "have", "here", "how", "https", "into", "its", "las",
    "los", "más", "para", "pero", "por", "que", "qué", "sin", "sobre", "that",
    "the", "their", "them", "then", "there", "these", "they", "this", "thread",
    "todo", "una", "uno", "use", "using", "was", "were", "what", "when", "which",
    "with", "you", "your", "www", "com", "twitter", "tweet", "today", "new", "aquí",
    "año", "años", "esta", "estas", "estos", "muy", "son", "hay", "cada", "hacer",
    "ahora", "así", "solo", "than", "just", "get", "got", "will", "would", "could",
}
GENERIC = {
    "bugbounty", "bug bounty", "bugbountytips", "cybersecurity", "hacking", "infosec",
    "security", "tool", "tools", "tips", "read", "check", "learn", "free", "good",
}
DISCOVERY_ALIASES = {
    "finance-economy": ["acciones", "bolsa", "inversión", "invertir", "cartera", "economía",
                        "finanzas", "mercados", "dividendos", "stocks", "portfolio"],
    "travel": ["viajar", "viajes", "hotel", "hoteles", "vuelos", "turismo", "destino"],
    "photography": ["fotografía", "fotógrafo", "cámara", "cámaras", "objetivo", "retrato"],
    "football-celta": ["fútbol", "futbol", "laliga", "real madrid", "barcelona", "equipo"],
    "entertainment": ["película", "películas", "serie", "series", "cine", "música"],
    "shopping": ["comprar", "compra", "oferta", "descuento", "precio"],
}
ENGLISH_CATEGORY_NAMES = {
    "offensive-security": "Offensive security", "bug-bounty": "Bug bounty",
    "recon-osint": "Recon/OSINT", "web-api": "Web/API", "xss-csp": "XSS/CSP",
    "ssrf": "SSRF", "sqli": "SQL injection", "auth-idor-oauth": "Auth/IDOR/OAuth",
    "rce-uploads": "RCE/Uploads", "graphql": "GraphQL", "cloud-security": "Cloud security",
    "mobile-security": "Mobile Android/iOS", "vulnerability-research": "Vulnerability research",
    "ai-security": "AI security", "ai-agents": "AI and agents", "llms": "LLMs",
    "coding-agents": "Coding agents", "harnesses": "Harnesses", "mcp": "MCP",
    "prompts": "Prompts", "automation": "Automation", "models": "Models",
    "development-systems": "Development and systems", "programming": "Programming",
    "linux-macos": "Linux/macOS", "devtools": "DevTools", "vps": "VPS",
    "self-hosting": "Self-hosting/HomeLab", "networks": "Networks",
    "finance-economy": "Finance and economics", "travel": "Travel",
    "photography": "Photography", "videogames": "Video games", "pokemon-vgc": "Pokémon/VGC",
    "nintendo": "Nintendo", "retro-games": "Retro and other games",
    "learning-culture": "Learning and culture", "other-interests": "Other interests",
    "football-celta": "Football/Celta", "entertainment": "Entertainment",
    "shopping": "Shopping", "home": "Home",
}


def _unit(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return values / norms


def _kmeans(vectors: np.ndarray, k: int, seed: int = 731, iterations: int = 35):
    rng = np.random.default_rng(seed + k)
    centers = [vectors[int(rng.integers(len(vectors)))]]
    for _ in range(1, k):
        best = np.max(vectors @ np.vstack(centers).T, axis=1)
        weights = np.square(np.clip(1 - best, 0, None))
        if float(weights.sum()) == 0:
            index = int(rng.integers(len(vectors)))
        else:
            index = int(rng.choice(len(vectors), p=weights / weights.sum()))
        centers.append(vectors[index])
    centers_array = _unit(np.vstack(centers).astype(np.float32))
    labels = np.zeros(len(vectors), dtype=np.int32)
    for _ in range(iterations):
        similarities = vectors @ centers_array.T
        next_labels = np.argmax(similarities, axis=1).astype(np.int32)
        if np.array_equal(labels, next_labels) and _:
            break
        labels = next_labels
        for index in range(k):
            members = vectors[labels == index]
            if len(members):
                center = members.mean(axis=0, keepdims=True)
                centers_array[index] = _unit(center)[0]
            else:
                nearest = np.max(similarities, axis=1)
                centers_array[index] = vectors[int(np.argmin(nearest))]
    similarities = vectors @ centers_array.T
    labels = np.argmax(similarities, axis=1).astype(np.int32)
    return labels, centers_array, similarities


def _select_clusters(vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    count = len(vectors)
    target = max(2, min(12, round(math.sqrt(count / 30))))
    maximum = max(2, min(14, count // max(6, min(15, count // 20 or 1))))
    choices = sorted({max(2, min(maximum, target + offset)) for offset in (-2, 0, 2)})
    best = None
    trials = []
    for k in choices:
        labels, centers, similarities = _kmeans(vectors, k)
        ordered = np.sort(similarities, axis=1)
        margin = float(np.mean(ordered[:, -1] - ordered[:, -2])) if k > 1 else 0.0
        cohesion = float(np.mean(ordered[:, -1]))
        sizes = np.bincount(labels, minlength=k)
        tiny = float(np.sum(sizes < max(3, count // 100))) / k
        imbalance = float(np.std(sizes) / max(1.0, np.mean(sizes)))
        score = margin + 0.08 * cohesion - 0.10 * tiny - 0.015 * imbalance
        trials.append({"k": k, "score": round(score, 6), "sizes": sizes.tolist()})
        if best is None or score > best[0]:
            best = (score, labels, centers)
    assert best is not None
    return best[1], best[2], {"target": target, "trials": trials}


def _tokens(value: str) -> list[str]:
    value = re.sub(r"(?:https?://|www\.)\S+", " ", value)
    words = re.findall(r"[^\W_][\w+#.-]{2,}", unicodedata.normalize("NFKC", value).casefold(), re.UNICODE)
    words = [word.strip(".-") for word in words]
    words = [word for word in words if word and word not in STOPWORDS and not word.isdigit()
             and not word.startswith("http") and word not in {"co", "t.co"}
             and not ("." in word and any(character.isdigit() for character in word))]
    phrases = [f"{left} {right}" for left, right in zip(words, words[1:])
               if left not in GENERIC and right not in GENERIC]
    return words + phrases


def _display_term(term: str, locale: str = "es") -> str:
    known = {"api": "API", "ai": "AI" if locale == "en" else "IA", "llm": "LLM", "xss": "XSS", "ssrf": "SSRF",
             "oauth": "OAuth", "idor": "IDOR", "osint": "OSINT", "rce": "RCE",
             "cve": "CVE", "mcp": "MCP", "javascript": "JavaScript", "ios": "iOS"}
    return " ".join(known.get(part, part.capitalize()) for part in term.split())


def _cluster_label(indexes: np.ndarray, documents: list[str], document_frequency: Counter,
                   catalogue_frequency: dict[str, int], all_count: int,
                   locale: str = "es") -> tuple[str, str, list[str], bool]:
    counter: Counter[str] = Counter()
    texts = []
    for index in indexes.tolist():
        text = documents[index].casefold()
        texts.append(text)
        counter.update(_tokens(text))
    ranked = []
    for term, frequency in counter.items():
        if frequency < 2 or term in GENERIC or len(term) > 52:
            continue
        inverse = math.log((all_count + 1) / (document_frequency[term] + 1)) + 0.25
        ranked.append((frequency * inverse / max(1, len(indexes)), term))
    ranked.sort(reverse=True)
    keywords = []
    for _, term in ranked:
        if any(term in chosen or chosen in term for chosen in keywords):
            continue
        keywords.append(term)
        if len(keywords) == 8:
            break

    taxonomy_names = (ENGLISH_CATEGORY_NAMES if locale == "en"
                      else {slug: name for name, slug, _, _ in TAXONOMY})
    matches = []
    for slug, configured_terms in CATEGORY_TERMS.items():
        terms = [*configured_terms, *DISCOVERY_ALIASES.get(slug, [])]
        hits = sum(any(term.casefold().strip() in text for term in terms) for text in texts)
        if hits >= max(2, math.ceil(len(texts) * 0.025)):
            prevalence = hits / len(texts)
            global_prevalence = catalogue_frequency.get(slug, 0) / all_count
            matches.append((prevalence - 0.65 * global_prevalence, prevalence, hits, slug))
    matches.sort(reverse=True)
    recognized = bool(matches and matches[0][0] >= 0.035 and matches[0][1] >= 0.08)
    if recognized:
        name = taxonomy_names.get(matches[0][3], _display_term(matches[0][3].replace("-", " "), locale))
    elif keywords and counter[keywords[0]] / len(indexes) >= 0.08:
        name = " · ".join(_display_term(term, locale) for term in keywords[:2])
    else:
        name = "Other topics" if locale == "en" else "Otros temas"
    visible = [_display_term(term, locale) for term in keywords[:6]]
    if locale == "en":
        description = "Topics found locally: " + ", ".join(visible) if visible else "Topic group found locally"
    else:
        description = "Temas detectados localmente: " + ", ".join(visible) if visible else "Grupo temático detectado localmente"
    return name[:100], description[:500], visible, recognized


def taxonomy_status(connection) -> dict[str, Any]:
    profile = connection.execute("SELECT * FROM taxonomy_profiles WHERE id=1").fetchone()
    if not profile:
        return {"state": "empty", "source": "adaptive", "candidates": []}
    run = connection.execute(
        "SELECT * FROM taxonomy_discovery_runs WHERE status='draft' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    candidates = []
    if run:
        for row in connection.execute(
            "SELECT * FROM taxonomy_candidates WHERE run_id=? ORDER BY sort_order,id", (run["id"],)
        ):
            examples = [dict(item) for item in connection.execute(
                """SELECT t.tweet_id,t.display_text text,t.author_handle
                   FROM taxonomy_candidate_members m JOIN tweets t ON t.tweet_id=m.tweet_id
                   WHERE m.candidate_id=? ORDER BY m.similarity DESC LIMIT 5""", (row["id"],)
            )]
            candidates.append({"id": row["id"], "name": row["name"],
                "description": row["description"], "keywords": json.loads(row["keywords_json"]),
                "bookmark_count": row["bookmark_count"], "cohesion": row["cohesion"],
                "examples": examples})
    return {"state": profile["state"], "source": profile["source"],
        "run_id": run["id"] if run else None, "candidates": candidates}


def discover_taxonomy(connection, progress_callback:Callable[[str,str,int,int],None]|None=None) -> dict[str, Any]:
    profile = connection.execute("SELECT * FROM taxonomy_profiles WHERE id=1").fetchone()
    if profile and profile["state"] == "active":
        raise ValueError("la biblioteca ya tiene una taxonomía activa")
    preference = connection.execute("SELECT locale FROM onboarding_state WHERE id=1").fetchone()
    locale = preference["locale"] if preference and preference["locale"] in {"es", "en"} else "es"
    rows = connection.execute(
        """SELECT e.tweet_id,e.vector,e.dimension,d.main_text,d.card_text
           FROM embeddings e JOIN search_documents d ON d.tweet_id=e.tweet_id
           JOIN tweets t ON t.tweet_id=e.tweet_id
           WHERE e.model=? AND t.is_bookmark=1
             AND t.bookmark_state NOT IN ('removed','locally_archived')
             AND (d.main_text<>'' OR d.card_text<>'') ORDER BY e.tweet_id""", (MODEL,)
    ).fetchall()
    if len(rows) < 20:
        raise ValueError("se necesitan al menos 20 bookmarks con embeddings para descubrir categorías")
    if progress_callback:progress_callback("taxonomy_loading","Cargando vectores para descubrir temas",0,len(rows))
    vectors = _unit(np.vstack([np.frombuffer(row["vector"], dtype=np.float32) for row in rows]))
    if progress_callback:progress_callback("taxonomy_clustering","Seleccionando agrupaciones temáticas",0,len(rows))
    labels, centers, selection = _select_clusters(vectors)
    documents = [" ".join(filter(None, (row["main_text"], row["card_text"]))) for row in rows]
    frequency: Counter[str] = Counter()
    for document in documents:
        frequency.update(set(_tokens(document)))
    lowered_documents = [document.casefold() for document in documents]
    catalogue_frequency = {}
    for slug, configured_terms in CATEGORY_TERMS.items():
        terms = [*configured_terms, *DISCOVERY_ALIASES.get(slug, [])]
        catalogue_frequency[slug] = sum(
            any(term.casefold().strip() in document for term in terms)
            for document in lowered_documents
        )
    connection.execute("DELETE FROM taxonomy_discovery_runs WHERE status='draft'")
    cursor = connection.execute(
        """INSERT INTO taxonomy_discovery_runs(status,model,bookmark_count,cluster_count,parameters_json)
           VALUES('draft',?,?,?,?)""",
        (MODEL, len(rows), len(centers), json.dumps({"method": METHOD, "locale": locale, **selection}, ensure_ascii=False)),
    )
    run_id = cursor.lastrowid
    used_names: Counter[str] = Counter()
    for order in range(len(centers)):
        if progress_callback:progress_callback("taxonomy_labels",f"Nombrando categoría {order+1} de {len(centers)}",order,len(centers))
        indexes = np.flatnonzero(labels == order)
        name, description, keywords, recognized = _cluster_label(
            indexes, documents, frequency, catalogue_frequency, len(rows), locale
        )
        similarities = vectors[indexes] @ centers[order]
        threshold = float(np.clip(np.percentile(similarities, 10) - 0.025, 0.35, 0.72))
        if not recognized and threshold <= 0.36:
            name = "Other topics" if locale == "en" else "Otros temas"
        used_names[name.casefold()] += 1
        if used_names[name.casefold()] > 1:
            suffix = keywords[0] if keywords else str(used_names[name.casefold()])
            name = f"{name} · {suffix}"[:100]
        candidate = connection.execute(
            """INSERT INTO taxonomy_candidates(run_id,name,description,keywords_json,bookmark_count,
               cohesion,threshold,dimension,centroid,sort_order) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (run_id, name, description, json.dumps(keywords, ensure_ascii=False), len(indexes),
             float(np.mean(similarities)), threshold, centers.shape[1],
             centers[order].astype(np.float32).tobytes(), order),
        ).lastrowid
        connection.executemany(
            "INSERT INTO taxonomy_candidate_members(candidate_id,tweet_id,similarity) VALUES(?,?,?)",
            [(candidate, rows[index]["tweet_id"], float(similarity))
             for index, similarity in zip(indexes.tolist(), similarities.tolist())],
        )
    connection.execute(
        "UPDATE taxonomy_profiles SET state='draft',source='adaptive',updated_at=CURRENT_TIMESTAMP WHERE id=1"
    )
    connection.commit()
    if progress_callback:progress_callback("taxonomy_ready",f"Borrador preparado con {len(centers)} categorías",len(centers),len(centers))
    return taxonomy_status(connection)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:70] or "category"


def apply_discovery(connection, choices: list[dict[str, Any]]) -> dict[str, Any]:
    profile = connection.execute("SELECT * FROM taxonomy_profiles WHERE id=1").fetchone()
    if not profile or profile["state"] != "draft":
        raise ValueError("no hay un descubrimiento pendiente de confirmar")
    if connection.execute("SELECT 1 FROM categories LIMIT 1").fetchone():
        raise ValueError("la biblioteca ya contiene categorías; no se reemplazarán automáticamente")
    run = connection.execute(
        "SELECT * FROM taxonomy_discovery_runs WHERE status='draft' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not run:
        raise ValueError("no hay un descubrimiento pendiente")
    available = {row["id"]: row for row in connection.execute(
        "SELECT * FROM taxonomy_candidates WHERE run_id=?", (run["id"],)
    )}
    selected = []
    names = set()
    for item in choices:
        if not item.get("enabled", True):
            continue
        candidate = available.get(int(item.get("id", 0)))
        if not candidate:
            raise ValueError("la propuesta contiene una categoría desconocida")
        name = str(item.get("name") or candidate["name"]).strip()[:100]
        description = str(item.get("description") or candidate["description"]).strip()[:500]
        if not name or name.casefold() in names:
            raise ValueError("los nombres de categoría deben ser únicos y no estar vacíos")
        names.add(name.casefold())
        selected.append((candidate, name, description))
    if not selected:
        raise ValueError("selecciona al menos una categoría")
    category_rows = []
    for order, (candidate, name, description) in enumerate(selected):
        base = _slug(name)
        slug, suffix = base, 2
        while connection.execute("SELECT 1 FROM categories WHERE slug=?", (slug,)).fetchone():
            slug, suffix = f"{base}-{suffix}", suffix + 1
        category_id = connection.execute(
            "INSERT INTO categories(name,slug,description,sort_order) VALUES(?,?,?,?)",
            (name, slug, description, order),
        ).lastrowid
        connection.execute(
            """INSERT INTO category_prototypes(category_id,model,dimension,vector,threshold,sample_size)
               VALUES(?,?,?,?,?,?)""",
            (category_id, MODEL, candidate["dimension"], candidate["centroid"],
             candidate["threshold"], candidate["bookmark_count"]),
        )
        category_rows.append((category_id, candidate))
    embeddings = connection.execute(
        """SELECT e.tweet_id,e.vector FROM embeddings e JOIN tweets t ON t.tweet_id=e.tweet_id
           WHERE e.model=? AND t.is_bookmark=1 AND t.bookmark_state NOT IN ('removed','locally_archived')""",
        (MODEL,),
    ).fetchall()
    centers = np.vstack([np.frombuffer(candidate["centroid"], dtype=np.float32)
                         for _, candidate in category_rows])
    thresholds = np.asarray([candidate["threshold"] for _, candidate in category_rows])
    for row in embeddings:
        vector = np.frombuffer(row["vector"], dtype=np.float32)
        scores = vector @ centers.T
        order = np.argsort(scores)[::-1]
        accepted = []
        for position in order[:2]:
            relaxed = thresholds[position] - (0.06 if not accepted else 0.0)
            if scores[position] >= relaxed and (not accepted or scores[position] >= scores[order[0]] - 0.035):
                accepted.append(int(position))
        for position in accepted:
            connection.execute(
                """INSERT INTO category_assignments(tweet_id,category_id,origin,confidence,evidence_json)
                   VALUES(?,?,'auto',?,?)""",
                (row["tweet_id"], category_rows[position][0], min(0.99, max(0.0, float(scores[position]))),
                 json.dumps({"method": METHOD, "run_id": run["id"],
                             "similarity": round(float(scores[position]), 4)}, ensure_ascii=False)),
            )
    connection.execute(
        "UPDATE taxonomy_discovery_runs SET status='applied',applied_at=CURRENT_TIMESTAMP WHERE id=?",
        (run["id"],),
    )
    connection.execute(
        """UPDATE taxonomy_profiles SET state='active',source='discovery',active_run_id=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=1""", (run["id"],)
    )
    connection.commit()
    rebuild_search_documents(connection)
    return {"state": "active", "source": "discovery", "run_id": run["id"],
        "categories": len(category_rows),
        "assignments": connection.execute(
            "SELECT count(*) FROM category_assignments WHERE origin='auto'"
        ).fetchone()[0]}


def adaptive_assignments(connection, vector: np.ndarray) -> list[tuple[int, float, dict[str, Any]]]:
    rows = connection.execute(
        "SELECT category_id,vector,threshold FROM category_prototypes WHERE model=?", (MODEL,)
    ).fetchall()
    if not rows:
        return []
    centers = np.vstack([np.frombuffer(row["vector"], dtype=np.float32) for row in rows])
    scores = vector @ centers.T
    ranking = np.argsort(scores)[::-1]
    result = []
    for position in ranking[:2]:
        score = float(scores[position])
        threshold = float(rows[position]["threshold"])
        if score >= threshold and (not result or score >= float(scores[ranking[0]]) - 0.035):
            result.append((rows[position]["category_id"], score,
                {"method": "personalized-centroid-v1", "similarity": round(score, 4)}))
    return result


def refresh_prototypes_from_feedback(connection, category_ids: set[int]) -> None:
    for category_id in category_ids:
        prototype = connection.execute(
            "SELECT * FROM category_prototypes WHERE category_id=?", (category_id,)
        ).fetchone()
        if not prototype:
            continue
        positives = connection.execute(
            """SELECT e.vector FROM category_assignments a JOIN embeddings e ON e.tweet_id=a.tweet_id
               WHERE a.category_id=? AND a.origin='manual' AND e.model=?""",
            (category_id, MODEL),
        ).fetchall()
        base = np.frombuffer(prototype["vector"], dtype=np.float32)
        if positives:
            values = np.vstack([np.frombuffer(row["vector"], dtype=np.float32) for row in positives])
            updated = base * max(5, int(prototype["sample_size"])) + values.sum(axis=0) * 4
            updated = updated / max(float(np.linalg.norm(updated)), 1e-9)
        else:
            updated = base
        negatives = connection.execute(
            """SELECT e.vector FROM category_suppressions s JOIN embeddings e ON e.tweet_id=s.tweet_id
               WHERE s.category_id=? AND e.model=?""", (category_id, MODEL)
        ).fetchall()
        threshold = float(prototype["threshold"])
        if negatives:
            negative_scores = [float(np.dot(updated, np.frombuffer(row["vector"], dtype=np.float32)))
                               for row in negatives]
            threshold = min(0.78, max(threshold, float(np.percentile(negative_scores, 75)) + 0.015))
        connection.execute(
            """UPDATE category_prototypes SET vector=?,threshold=?,updated_at=CURRENT_TIMESTAMP
               WHERE category_id=?""", (updated.astype(np.float32).tobytes(), threshold, category_id)
        )
