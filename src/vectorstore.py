"""ChromaDB setup, ingestion, and retrieval with real similarity match scores.

Uses Chroma's built-in DefaultEmbeddingFunction (all-MiniLM-L6-v2, ONNX) so no
embedding API key is required. Distances are cosine; we convert to a 0-100
"match score" for a friendly demo.
"""
from __future__ import annotations

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from src.config import CHROMA_DIR, COLLECTION_NAME
from data.faculty_profiles import all_profiles

_EMBED_FN = embedding_functions.DefaultEmbeddingFunction()


def _client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )


def build_index(reset: bool = False) -> int:
    """Chunk (one profile == one chunk here — profiles are short and self-contained),
    embed, and store all faculty profiles. Returns the number of documents indexed.
    """
    client = _client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_EMBED_FN,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() >= len(all_profiles()) and not reset:
        return collection.count()

    docs, metas, ids = [], [], []
    for f in all_profiles():
        # The embedded document blends areas + narrative so topical queries match well.
        doc = f"{f['name']} — {f['designation']}. Areas: {', '.join(f['areas'])}. {f['profile']}"
        docs.append(doc)
        metas.append({
            "name": f["name"],
            "faculty_id": f["id"],
            "subfield": f["subfield"],
            "areas": ", ".join(f["areas"]),
            "email": f["email"],
            "active_projects": f["active_projects"],
        })
        ids.append(f["id"])

    collection.upsert(documents=docs, metadatas=metas, ids=ids)
    return collection.count()


def get_collection():
    return _client().get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=_EMBED_FN,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Semantic search. Returns ranked matches with a 0-100 similarity score."""
    collection = get_collection()
    if collection.count() == 0:
        build_index()
        collection = get_collection()

    res = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    hits: list[dict] = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        # cosine distance in [0,2]; similarity = 1 - dist, clamped to [0,1].
        sim = max(0.0, 1.0 - float(dist))
        hits.append({
            "name": meta["name"],
            "faculty_id": meta["faculty_id"],
            "subfield": meta["subfield"],
            "areas": meta["areas"],
            "email": meta["email"],
            "active_projects": meta["active_projects"],
            "text": doc,
            "score": round(sim * 100, 1),
        })
    return hits


if __name__ == "__main__":
    n = build_index(reset=True)
    print(f"Indexed {n} faculty profiles into ChromaDB.")
    for h in retrieve("who works on natural language processing", k=3):
        print(f"  {h['score']:5.1f}  {h['name']} ({h['subfield']})")
