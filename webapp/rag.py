# webapp/rag.py
"""
RAG utilities for the EarthRISE Book Assistant.

Modes (controlled by RAG_MODE in settings):
  shared  — Shared Embedding Service (default; http://127.0.0.1:8023)
  local   — local Chroma + sentence-transformers
  proxy   — LiteLLM-hosted RAG endpoints
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import requests

from django.conf import settings

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

DEFAULT_TOP_K      = 20
DISTANCE_THRESHOLD = 0.75


# ---------- Local Chroma store ----------
def _resolve_persist_dir() -> str:
    user_dir = getattr(settings, "CHROMA_PERSIST_DIR", None)
    base_dir = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[1]))
    p = Path(user_dir) if user_dir else (base_dir / "chroma_db")
    if not p.is_absolute():
        p = base_dir / p
    return str(p)


class ChromaVectorStore:
    def __init__(self):
        import chromadb
        from chromadb.utils import embedding_functions as ef
        persist_dir = _resolve_persist_dir()
        collection_name = getattr(settings, "CHROMA_COLLECTION", "earthrise-book")
        model_name = getattr(settings, "LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        os.makedirs(persist_dir, exist_ok=True)
        self.chroma = chromadb.PersistentClient(path=persist_dir)
        emb_fn = ef.SentenceTransformerEmbeddingFunction(model_name=model_name)
        self.collection = self.chroma.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=emb_fn,
        )
        LOG.info(f"[RAG] ChromaVectorStore: collection='{collection_name}' count={self.collection.count()}")

    def upsert(self, docs: List[Dict[str, Any]]):
        if not docs:
            return
        self.collection.upsert(
            ids=[d["id"] for d in docs],
            documents=[d["text"] for d in docs],
            metadatas=[d.get("metadata", {}) for d in docs],
        )
        LOG.info(f"[RAG] Upserted {len(docs)} chunks into local Chroma.")

    def search(self, query: str, top_k: int = DEFAULT_TOP_K, session_id: str = None):
        where = {"is_global": True} if not session_id else {
            "$or": [{"session_id": session_id}, {"is_global": True}]
        }
        res = self.collection.query(query_texts=[query], n_results=top_k, where=where)
        ids       = res.get("ids", [[]])[0]
        docs      = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0] if "distances" in res else [None] * len(ids)
        return [
            {"id": ids[i], "text": docs[i], "metadata": metadatas[i], "distance": distances[i]}
            for i in range(len(ids))
        ]

    def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        try:
            result = self.collection.get(ids=ids)
            return [
                {"id": result["ids"][i], "text": result["documents"][i], "metadata": result["metadatas"][i] or {}}
                for i in range(len(result["ids"]))
            ]
        except Exception as e:
            LOG.warning(f"[RAG] get_by_ids failed: {e}")
            return []

    def delete_chapter_docs(self, chapter_slug: str):
        """Delete all chunks for a chapter before re-embedding."""
        if not chapter_slug:
            return
        try:
            self.collection.delete(where={"chapter": chapter_slug})
            LOG.info(f"[RAG] Deleted existing chunks for chapter '{chapter_slug}'.")
        except Exception as e:
            LOG.error(f"[RAG] delete_chapter_docs (local) failed: {e}")


# ---------- Shared Embedding Service ----------
class SharedEmbeddingServiceStore:
    UPSERT_BATCH_SIZE = 20

    def __init__(self):
        self.base = getattr(settings, "SHARED_EMBEDDING_SERVICE_URL", "http://127.0.0.1:8023").rstrip("/")
        self.api_key = getattr(settings, "SHARED_EMBEDDING_SERVICE_API_KEY", "")
        self.collection = getattr(settings, "CHROMA_COLLECTION", "earthrise-book")
        self._headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        LOG.info(f"[RAG] SharedEmbeddingServiceStore: {self.base}  collection: {self.collection}")

    def upsert(self, docs: List[Dict[str, Any]]):
        if not docs:
            return
        url = f"{self.base}/collections/{self.collection}/documents"
        total = len(docs)
        for start in range(0, total, self.UPSERT_BATCH_SIZE):
            batch = docs[start: start + self.UPSERT_BATCH_SIZE]
            payload = {
                "documents": [d["text"]             for d in batch],
                "ids":       [d["id"]               for d in batch],
                "metadatas": [d.get("metadata", {}) for d in batch],
            }
            resp = requests.put(url, json=payload, headers=self._headers, timeout=300)
            resp.raise_for_status()
            LOG.info(f"[RAG] Upserted batch {start + len(batch)}/{total} via shared service.")

    def search(self, query: str, top_k: int = DEFAULT_TOP_K, session_id: str = None) -> List[Dict[str, Any]]:
        where = {"is_global": True} if not session_id else {
            "$or": [{"session_id": session_id}, {"is_global": True}]
        }
        payload = {"query_texts": [query], "n_results": top_k, "where": where}
        resp = requests.post(
            f"{self.base}/collections/{self.collection}/query",
            json=payload, headers=self._headers, timeout=30,
        )
        resp.raise_for_status()
        res = resp.json()
        ids       = res.get("ids",       [[]])[0]
        docs      = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0] if "distances" in res else [None] * len(ids)
        results = [
            {"id": ids[i], "text": docs[i], "metadata": metadatas[i], "distance": distances[i]}
            for i in range(len(ids))
        ]
        LOG.info(f"[RAG] Shared-service search returned {len(results)} result(s).")
        return results

    def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        try:
            resp = requests.post(
                f"{self.base}/collections/{self.collection}/get",
                json={"ids": ids}, headers=self._headers, timeout=30,
            )
            resp.raise_for_status()
            res = resp.json()
            ret_ids   = res.get("ids",       [])
            ret_docs  = res.get("documents", [])
            ret_metas = res.get("metadatas", [])
            return [
                {"id": ret_ids[i], "text": ret_docs[i], "metadata": ret_metas[i] or {}}
                for i in range(len(ret_ids))
            ]
        except Exception as e:
            LOG.warning(f"[RAG] get_by_ids (shared service) failed: {e}")
            return []

    def delete_session_docs(self, session_id: str):
        if not session_id:
            return
        try:
            resp = requests.get(
                f"{self.base}/collections/{self.collection}/documents",
                params={"limit": 1000}, headers=self._headers, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            to_delete = [
                doc_id for doc_id, meta in zip(data.get("ids", []), data.get("metadatas", []))
                if (meta or {}).get("session_id") == session_id
            ]
            if not to_delete:
                return
            requests.delete(
                f"{self.base}/collections/{self.collection}/documents",
                json={"ids": to_delete}, headers=self._headers, timeout=30,
            ).raise_for_status()
            LOG.info(f"[RAG] Deleted {len(to_delete)} session docs for {session_id}.")
        except Exception as e:
            LOG.error(f"[RAG] delete_session_docs failed: {e}")

    def delete_chapter_docs(self, chapter_slug: str):
        """Delete all chunks for a chapter before re-embedding."""
        if not chapter_slug:
            return
        try:
            resp = requests.get(
                f"{self.base}/collections/{self.collection}/documents",
                params={"limit": 10000}, headers=self._headers, timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            to_delete = [
                doc_id for doc_id, meta in zip(data.get("ids", []), data.get("metadatas", []))
                if (meta or {}).get("chapter") == chapter_slug
            ]
            if not to_delete:
                LOG.info(f"[RAG] No existing chunks found for chapter '{chapter_slug}'.")
                return
            requests.delete(
                f"{self.base}/collections/{self.collection}/documents",
                json={"ids": to_delete}, headers=self._headers, timeout=30,
            ).raise_for_status()
            LOG.info(f"[RAG] Deleted {len(to_delete)} existing chunks for chapter '{chapter_slug}'.")
        except Exception as e:
            LOG.error(f"[RAG] delete_chapter_docs (shared service) failed: {e}")


# ---------- Proxy (LiteLLM RAG) ----------
class LiteLLMRagClient:
    def __init__(self):
        base = (getattr(settings, "OPENAI_BASE_URL", "") or "").rstrip("/")
        self.base = base
        self.search_path = getattr(settings, "LITELLM_RAG_SEARCH", "/rag/search")
        self.upsert_path = getattr(settings, "LITELLM_RAG_UPSERT", "/rag/upsert")
        self.api_key = getattr(settings, "OPENAI_API_KEY", "")

    def upsert(self, docs: List[Dict[str, Any]]):
        resp = requests.post(
            f"{self.base}{self.upsert_path}",
            json={"docs": docs},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        resp.raise_for_status()

    def search(self, query: str, top_k: int = DEFAULT_TOP_K, session_id: str = None):
        resp = requests.post(
            f"{self.base}{self.search_path}",
            json={"query": query, "top_k": top_k, "session_id": session_id},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("results", [])


# ---------- Singleton factory ----------
_store_instance = None


def get_store():
    global _store_instance
    if _store_instance is None:
        mode = (getattr(settings, "RAG_MODE", "shared") or "shared").lower()
        if mode == "proxy":
            _store_instance = LiteLLMRagClient()
        elif mode == "shared":
            _store_instance = SharedEmbeddingServiceStore()
        else:
            _store_instance = ChromaVectorStore()
    return _store_instance


# ---------- Build context snippets for the LLM ----------
def build_context_snippets(query: str, top_k: int = DEFAULT_TOP_K, session_id: str = None) -> str:
    """
    Multi-query expansion → deduplicate → parent expansion → format.
    """
    store = get_store()

    # Book-specific sub-queries expand retrieval coverage
    sub_queries = [
        query,
        f"deep learning code implementation: {query}",
        f"Earth observation remote sensing: {query}",
    ]

    seen_ids: set = set()
    all_results: List[Dict] = []
    per_q = max(top_k // len(sub_queries), 5)

    for q in sub_queries:
        for r in store.search(q, top_k=per_q, session_id=session_id):
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                all_results.append(r)

    # Drop parent-type chunks (stored for expansion only)
    child_results = [
        r for r in all_results
        if r.get("metadata", {}).get("chunk_type", "child") != "parent"
    ]

    filtered = [r for r in child_results if (r.get("distance") or 0.0) < DISTANCE_THRESHOLD]
    if not filtered:
        filtered = child_results

    filtered.sort(key=lambda x: x.get("distance") or 1.0)
    filtered = filtered[:top_k]

    # Deduplicate by parent_id
    seen_parents: set = set()
    deduped: List[Dict] = []
    for r in filtered:
        pid = r.get("metadata", {}).get("parent_id")
        if pid:
            if pid not in seen_parents:
                seen_parents.add(pid)
                deduped.append(r)
        else:
            deduped.append(r)

    context_docs = _expand_to_parents(store, deduped)

    lines = []
    for r in context_docs:
        meta    = r.get("metadata", {})
        chapter = meta.get("chapter", "")
        section = meta.get("section", "")
        chunk_i = meta.get("chunk_idx", "?")
        dist    = r.get("distance")
        score   = round(1.0 - dist, 2) if dist is not None else "?"

        chapter_info = f" | Chapter: {chapter}" if chapter else ""
        section_info = f" | Section: {section}" if section else ""
        header = f"[Source{chapter_info}{section_info} | Chunk: {chunk_i} | Relevance: {score}]"
        lines.append(f"{header}\n{r.get('text', '')}")

    return "\n\n---\n\n".join(lines)


def _expand_to_parents(store, child_hits: List[Dict]) -> List[Dict]:
    if not hasattr(store, "get_by_ids"):
        return child_hits

    parent_id_map: Dict[str, Dict] = {}
    for r in child_hits:
        meta = r.get("metadata", {})
        pid  = meta.get("parent_id")
        chapter = meta.get("chapter", "")
        if pid and chapter:
            parent_doc_id = f"{chapter}-parent-{pid}"
            if parent_doc_id not in parent_id_map:
                parent_id_map[parent_doc_id] = r

    if not parent_id_map:
        return child_hits

    fetched = store.get_by_ids(list(parent_id_map.keys()))
    parent_texts: Dict[str, str] = {p["id"]: p["text"] for p in fetched}

    results = []
    for r in child_hits:
        meta    = r.get("metadata", {})
        pid     = meta.get("parent_id")
        chapter = meta.get("chapter", "")
        parent_doc_id = f"{chapter}-parent-{pid}" if pid and chapter else None
        if parent_doc_id and parent_doc_id in parent_texts:
            results.append({**r, "text": parent_texts[parent_doc_id]})
        else:
            results.append(r)

    LOG.info(f"[RAG] Parent expansion: {len(parent_texts)}/{len(parent_id_map)} parents fetched.")
    return results
