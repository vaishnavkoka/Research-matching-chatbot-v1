"""Assemble the LangGraph: nodes, conditional edges, HITL interrupt, and a
MemorySaver checkpointer so state persists across turns (per thread_id).
See ARCHITECTURE.md section 3 for the flow diagram.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import ResearchState
from src import nodes


# --- conditional edge functions ------------------------------------------- #
def route_from_intent(state: ResearchState) -> str:
    return state.get("routing_target", "synthesize")


def route_after_trend(state: ResearchState) -> str:
    return {
        "collaboration": "collaborative_matching",
        "email_draft": "collaborative_matching",
        "gap_analysis": "gap_analysis",
        "trend_analysis": "synthesize",
    }.get(state.get("intent"), "synthesize")


def needs_confirmation(state: ResearchState) -> str:
    return "human_confirmation" if state.get("proposed_action") else "end"


def approved(state: ResearchState) -> str:
    ans = (state.get("human_confirmation") or "").strip().lower()
    return "finalize" if ans in {"yes", "y", "confirm", "approve", "ok", "sure", "go"} else "end"


def build_graph():
    g = StateGraph(ResearchState)

    g.add_node("intent_router", nodes.intent_router)
    g.add_node("faculty_rag", nodes.faculty_rag)
    g.add_node("scoped_lookup", nodes.scoped_lookup)
    g.add_node("project_suggestion", nodes.project_suggestion)
    g.add_node("web_trends", nodes.web_trend_analysis)
    g.add_node("collaborative_matching", nodes.collaborative_matching)
    g.add_node("gap_analysis", nodes.gap_analysis)
    g.add_node("synthesize", nodes.synthesize)
    g.add_node("human_confirmation", nodes.human_confirmation)
    g.add_node("finalize", nodes.finalize_action)

    g.add_edge(START, "intent_router")

    # Core dispatcher.
    g.add_conditional_edges("intent_router", route_from_intent, {
        "faculty_rag": "faculty_rag",
        "scoped_lookup": "scoped_lookup",
        "project_suggestion": "project_suggestion",
        "web_trends": "web_trends",
        "collaborative_matching": "collaborative_matching",
        "synthesize": "synthesize",
    })

    # Student retrieval paths go straight to synthesis.
    g.add_edge("faculty_rag", "synthesize")
    g.add_edge("scoped_lookup", "synthesize")
    g.add_edge("project_suggestion", "synthesize")

    # Professor trend sub-router.
    g.add_conditional_edges("web_trends", route_after_trend, {
        "collaborative_matching": "collaborative_matching",
        "gap_analysis": "gap_analysis",
        "synthesize": "synthesize",
    })
    g.add_edge("collaborative_matching", "synthesize")
    g.add_edge("gap_analysis", "synthesize")

    # HITL gate after synthesis.
    g.add_conditional_edges("synthesize", needs_confirmation, {
        "human_confirmation": "human_confirmation",
        "end": END,
    })
    g.add_conditional_edges("human_confirmation", approved, {
        "finalize": "finalize",
        "end": END,
    })
    g.add_edge("finalize", END)

    return g.compile(checkpointer=MemorySaver())


COMPILED = None


def get_graph():
    global COMPILED
    if COMPILED is None:
        COMPILED = build_graph()
    return COMPILED
