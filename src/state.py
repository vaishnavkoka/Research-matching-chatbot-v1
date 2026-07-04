"""The shared graph state. See ARCHITECTURE.md section 1 for the rationale."""
from __future__ import annotations

from typing import List, Optional, TypedDict


class ResearchState(TypedDict, total=False):
    # --- turn input / conversation memory ---
    user_query: str
    messages: List[dict]          # [{role, content}, ...]
    current_mode: str             # "student" | "professor"

    # --- routing ---
    intent: str                   # who_works_on | faculty_detail | next_match |
                                  # trend_analysis | collaboration | gap_analysis |
                                  # email_draft | smalltalk
    routing_target: str

    # --- extracted slots ---
    topic: Optional[str]
    focus_faculty: Optional[str]

    # --- retrieval / tools ---
    retrieved_docs: List[dict]    # {name, area, text, score}
    last_results: List[dict]      # cache for "the first match" follow-ups
    api_results: dict             # {"tavily": [...], "semantic_scholar": [...]}

    # --- reasoning / output ---
    analysis: str
    proposed_action: Optional[dict]   # {type, summary, payload}
    awaiting_confirmation: bool
    human_confirmation: Optional[str]
    final_response: str

    # --- observability ---
    log: List[str]


def new_state(user_query: str, prior: Optional[ResearchState] = None) -> ResearchState:
    """Build the per-turn state, carrying forward sticky memory from `prior`."""
    prior = prior or {}
    return ResearchState(
        user_query=user_query,
        messages=prior.get("messages", []),
        current_mode=prior.get("current_mode", "student"),
        intent="",
        routing_target="",
        topic=None,
        focus_faculty=prior.get("focus_faculty"),
        retrieved_docs=[],
        last_results=prior.get("last_results", []),
        api_results={},
        analysis="",
        proposed_action=None,
        awaiting_confirmation=False,
        human_confirmation=None,
        final_response="",
        log=[],
    )
