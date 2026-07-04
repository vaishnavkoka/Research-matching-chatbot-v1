"""Research Matching Chatbot — terminal loop.

State persists across turns via a LangGraph MemorySaver keyed by a single
thread_id, so follow-ups ("tell me more about the first match") work. The
Human-in-the-Loop pause is a real LangGraph interrupt: when the graph stops at
the confirmation node we prompt in the terminal and resume with Command(resume=…).
"""
from __future__ import annotations

import sys

from langgraph.types import Command

from src.config import status_banner
from src.state import new_state
from src.vectorstore import build_index
from src.graph import get_graph

THREAD = {"configurable": {"thread_id": "cli-session"}}

BANNER = r"""
============================================================
  Research Matching Chatbot
  (LangGraph · ChromaDB RAG · Tavily · Semantic Scholar)
============================================================
"""

HELP = """
Try queries like:
  STUDENT   : "Who works on NLP?"          -> RAG match scores
              "Tell me about Dr. Raman"     -> scoped detail lookup
              "Tell me more about the first match"  (follow-up)
  PROFESSOR : "What's trending in computer vision?"  -> live web + papers
              "Could I collaborate with Dr. Batra on IoT?"  -> matching
              "What are we missing in cybersecurity?"  -> gap analysis
Commands: :help  :mode  :reset  :quit
"""


def _render(result: dict) -> None:
    resp = result.get("final_response") or "(no response)"
    print("\n" + "-" * 60)
    print("ASSISTANT:\n" + resp)
    print("-" * 60)


def run_turn(graph, user_input: str, prior: dict) -> dict:
    state = new_state(user_input, prior)
    result = graph.invoke(state, THREAD)

    # Handle a Human-in-the-Loop interrupt (may loop if user is indecisive).
    while "__interrupt__" in result:
        intr = result["__interrupt__"][0]
        prompt = intr.value.get("prompt", "Confirm? (yes/no): ")
        answer = input(prompt).strip()
        result = graph.invoke(Command(resume=answer), THREAD)

    _render(result)
    # Carry forward sticky memory for the next turn.
    prior["messages"] = (prior.get("messages", []) +
                         [{"role": "user", "content": user_input},
                          {"role": "assistant", "content": result.get("final_response", "")}])
    prior["current_mode"] = result.get("current_mode", prior.get("current_mode", "student"))
    prior["focus_faculty"] = result.get("focus_faculty", prior.get("focus_faculty"))
    if result.get("last_results"):
        prior["last_results"] = result["last_results"]
    return prior


def main() -> None:
    print(BANNER)
    print("Booting vector store...")
    n = build_index()
    print(f"ChromaDB ready: {n} faculty profiles indexed.")
    print("Capabilities: " + status_banner())
    from src.llm import health_check
    ok, msg = health_check()
    print(f"LLM health check: {'[ok] ' if ok else '[warn] '}{msg}")
    print(HELP)

    graph = get_graph()
    prior: dict = {}

    while True:
        try:
            user_input = input("\nYOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue

        low = user_input.lower()
        if low in (":quit", ":q", "quit", "exit"):
            print("Goodbye!")
            break
        if low in (":help", "help"):
            print(HELP)
            continue
        if low == ":reset":
            prior = {}
            print("(context reset)")
            continue
        if low == ":mode":
            print(f"(current mode: {prior.get('current_mode', 'student')})")
            continue

        try:
            prior = run_turn(graph, user_input, prior)
        except Exception as exc:
            print(f"\n[!] Error handling that turn: {exc}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
