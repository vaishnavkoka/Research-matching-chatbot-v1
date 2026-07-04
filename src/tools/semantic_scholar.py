"""Semantic Scholar Graph API — live papers, abstracts, real citation counts.
Keyless (optional key raises rate limits). This is a real tool the LLM cannot do:
it fetches live citation data.
"""
from __future__ import annotations

import requests

from src.config import SEMANTIC_SCHOLAR_API_KEY

_BASE = "https://api.semanticscholar.org/graph/v1"
_TIMEOUT = 15


def _headers() -> dict:
    return {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}


def search_papers(topic: str, limit: int = 5) -> list[dict]:
    """Return recent, highly-cited papers for a topic with real citation counts."""
    try:
        resp = requests.get(
            f"{_BASE}/paper/search",
            params={
                "query": topic,
                "limit": limit,
                "fields": "title,abstract,year,citationCount,authors,url",
                "sort": "citationCount:desc",
            },
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", []) or []
    except Exception as exc:
        return [{"error": f"Semantic Scholar unavailable: {exc}"}]

    papers = []
    for p in data:
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:4])
        papers.append({
            "title": p.get("title", "Untitled"),
            "year": p.get("year"),
            "citations": p.get("citationCount", 0),
            "authors": authors,
            "abstract": (p.get("abstract") or "")[:400],
            "url": p.get("url", ""),
        })
    return papers


if __name__ == "__main__":
    for p in search_papers("federated learning", 3):
        print(f"[{p.get('citations')} cites] {p.get('title')} ({p.get('year')})")
