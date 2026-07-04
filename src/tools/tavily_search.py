"""Tavily live web search — current research trends, news, and buzz that a static
model cannot know. Degrades to an empty result set when no key is configured.
"""
from __future__ import annotations

from src.config import TAVILY_API_KEY, TAVILY_ENABLED

_client = None


def _get_client():
    global _client
    if not TAVILY_ENABLED:
        return None
    if _client is None:
        from tavily import TavilyClient
        _client = TavilyClient(api_key=TAVILY_API_KEY)
    return _client


def web_trends(topic: str, max_results: int = 5) -> list[dict]:
    """Search the live web for current trends on a research topic."""
    client = _get_client()
    if client is None:
        return [{"note": "Tavily disabled (no TAVILY_API_KEY); skipping web trends."}]
    try:
        resp = client.search(
            query=f"latest research trends and breakthroughs in {topic} 2025 2026",
            search_depth="advanced",
            max_results=max_results,
        )
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:400],
                "score": round(r.get("score", 0.0), 3),
            }
            for r in resp.get("results", [])
        ]
    except Exception as exc:
        return [{"error": f"Tavily search failed: {exc}"}]


if __name__ == "__main__":
    for r in web_trends("large language models"):
        print(r.get("title") or r.get("note") or r.get("error"))
