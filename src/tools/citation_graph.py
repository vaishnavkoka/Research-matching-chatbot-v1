"""Citation graph visualization (moon-shot).

Given a research topic, find the most-cited paper on Semantic Scholar, pull the
papers it references and the papers that cite it, and render a directed citation
network:  references -> anchor paper -> citing papers.

Returns (image_path, markdown_summary). Real live data, no mock.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import requests

from src.config import SEMANTIC_SCHOLAR_API_KEY, PROJECT_ROOT

_BASE = "https://api.semanticscholar.org/graph/v1"
_TIMEOUT = 20
_OUT = Path(PROJECT_ROOT) / "chroma_db" / ".citation_graphs"  # scratch dir (gitignored parent)


def _headers() -> dict:
    return {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}


def _get(path: str, params: dict) -> dict:
    r = requests.get(f"{_BASE}/{path}", params=params, headers=_headers(), timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _short(title: str, n: int = 34) -> str:
    title = (title or "untitled").strip()
    return title if len(title) <= n else title[: n - 1] + "…"


def build_citation_graph(topic: str, max_refs: int = 6, max_cites: int = 6):
    """Build and render a citation graph for the most-cited paper on `topic`."""
    if not topic or not topic.strip():
        return None, "Enter a topic to build its citation graph."

    # 1. Anchor = the most-cited paper for the topic.
    search = _get("paper/search", {
        "query": topic, "limit": 1,
        "fields": "title,year,citationCount,authors", "sort": "citationCount:desc",
    })
    data = search.get("data") or []
    if not data:
        return None, f"No papers found on Semantic Scholar for '{topic}'."
    anchor = data[0]
    pid = anchor["paperId"]

    # 2. What it cites (references) and what cites it (citations).
    refs = _get(f"paper/{pid}/references",
                {"fields": "title,year", "limit": max_refs}).get("data", []) or []
    cites = _get(f"paper/{pid}/citations",
                 {"fields": "title,year", "limit": max_cites}).get("data", []) or []

    # 3. Assemble a directed graph.
    import networkx as nx
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    G = nx.DiGraph()
    center = _short(anchor.get("title"), 40)
    G.add_node(center, kind="anchor")

    ref_titles, cite_titles = [], []
    for r in refs:
        p = r.get("citedPaper") or r
        t = _short(p.get("title"))
        if t and t != center:
            G.add_node(t, kind="ref")
            G.add_edge(center, t)      # anchor cites reference
            ref_titles.append(p.get("title") or t)
    for c in cites:
        p = c.get("citingPaper") or c
        t = _short(p.get("title"))
        if t and t != center:
            G.add_node(t, kind="cite")
            G.add_edge(t, center)      # citing paper -> anchor
            cite_titles.append(p.get("title") or t)

    colors = {"anchor": "#dc2626", "ref": "#2563eb", "cite": "#16a34a"}
    node_colors = [colors[G.nodes[n]["kind"]] for n in G.nodes]
    node_sizes = [1600 if G.nodes[n]["kind"] == "anchor" else 850 for n in G.nodes]

    plt.figure(figsize=(11, 7.5))
    pos = nx.spring_layout(G, k=1.1, seed=42)
    nx.draw_networkx_edges(G, pos, edge_color="#94a3b8", arrows=True,
                           arrowsize=13, width=1.2, alpha=0.7)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes,
                           edgecolors="white", linewidths=1.5)
    labels = {n: "\n".join(textwrap.wrap(n, 18)) for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, font_color="#0f172a")
    plt.title(f"Citation graph — most-cited paper on “{topic}”\n"
              "red = anchor · blue = it cites · green = cites it", fontsize=11)
    plt.axis("off")
    plt.tight_layout()

    _OUT.mkdir(parents=True, exist_ok=True)
    out_path = _OUT / f"graph_{abs(hash(topic)) % 10**8}.png"
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close()

    authors = ", ".join(a.get("name", "") for a in (anchor.get("authors") or [])[:4])
    summary = (
        f"**Anchor paper:** {anchor.get('title')} "
        f"({anchor.get('year')}, {anchor.get('citationCount')} citations)\n\n"
        f"*{authors}*\n\n"
        f"- **{len(ref_titles)}** references pulled (papers it builds on)\n"
        f"- **{len(cite_titles)}** citing papers pulled (work that built on it)\n\n"
        "Data: live Semantic Scholar graph API."
    )
    return str(out_path), summary


if __name__ == "__main__":
    path, summ = build_citation_graph("federated learning")
    print(path)
    print(summ)
