"""Gradio front-end for the Research Matching Chatbot.

This is a thin UI over the exact same LangGraph agent that powers the terminal
app (src/graph.py). It adds three things a terminal can't show as cleanly:
  - a live execution trace (which node ran, which tool fired) beside the chat,
  - explicit Confirm / Cancel buttons for the human-in-the-loop step,
  - per-browser session isolation via a unique LangGraph thread_id.

Run:  python app_gradio.py   (then open the printed local URL)
Build the terminal version first; this only wraps it.
"""
from __future__ import annotations

import contextlib
import io
from uuid import uuid4

import gradio as gr
from langgraph.types import Command

from src.config import status_banner
from src.state import new_state
from src.vectorstore import build_index
from src.graph import get_graph

# Boot the vector store + graph once for the whole server.
print("Booting vector store for the UI...")
build_index()
GRAPH = get_graph()

HEADER_HTML = """
<div id="app-header">
  <h1>Research Matching Chatbot</h1>
  <p>Find the right faculty guide, explore live research trends, and spot
     collaboration gaps — grounded in real faculty profiles and live research data.</p>
</div>
"""

STATUS_HTML = f"<div class='status-pill'>{status_banner()}</div>"

STUDENT_EXAMPLES = [
    "Who works on NLP?",
    "Tell me about Dr. Raman",
    "Tell me more about the first match",
]
PROFESSOR_EXAMPLES = [
    "What's trending in computer vision?",
    "Could I collaborate with Dr. Batra on IoT?",
    "What are we missing in cybersecurity?",
]

CSS = """
.gradio-container {max-width: 1120px !important; margin: auto !important;}
#app-header {text-align:center; padding: 22px 18px; border-radius: 16px; color:#fff;
  background: linear-gradient(135deg,#4f46e5 0%,#7c3aed 55%,#9333ea 100%);
  box-shadow: 0 8px 24px rgba(79,70,229,.25); margin-bottom: 6px;}
#app-header h1 {margin:0; font-size:2rem; font-weight:700; letter-spacing:.2px;}
#app-header p {margin:8px auto 0; max-width:720px; opacity:.94; font-size:.97rem; line-height:1.4;}
.status-pill {text-align:center; font-size:.82rem; color:#475569; margin:2px 0 10px;
  font-family: ui-monospace,Menlo,Consolas,monospace;}
#trace-box textarea {font-family: ui-monospace,Menlo,Consolas,monospace !important;
  font-size:12px !important; line-height:1.45; background:#0f172a !important;
  color:#93c5fd !important; border-radius:10px;}
.panel-title {font-weight:600; color:#334155; margin:2px 0 -4px;}
.app-footer {text-align:center; color:#94a3b8; font-size:.82rem; padding-top:10px;}
"""


def _new_session() -> dict:
    return {"thread_id": "ui-" + uuid4().hex[:8], "awaiting": False, "prior": {}}


def _carry_forward(session: dict, result: dict) -> None:
    """Persist the sticky memory (mode, focused faculty, last matches) so
    follow-up turns resolve, mirroring the terminal loop."""
    p = session["prior"]
    p["current_mode"] = result.get("current_mode", p.get("current_mode", "student"))
    p["focus_faculty"] = result.get("focus_faculty", p.get("focus_faculty"))
    if result.get("last_results"):
        p["last_results"] = result["last_results"]


def step(user_msg: str, history: list, session: dict):
    """One chat turn. Handles both a fresh query and a resume of the HITL pause."""
    session = session or _new_session()
    history = history or []
    user_msg = (user_msg or "").strip()
    if not user_msg:
        return history, "", session, gr.update(), gr.update(), ""

    config = {"configurable": {"thread_id": session["thread_id"]}}
    history = history + [{"role": "user", "content": user_msg}]

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            if session["awaiting"]:
                # The user's message is the answer to the confirmation prompt.
                result = GRAPH.invoke(Command(resume=user_msg), config)
            else:
                result = GRAPH.invoke(new_state(user_msg, session["prior"]), config)
    except Exception as exc:  # never let the UI hard-crash mid-demo
        result = {"final_response": f"Something went wrong: {exc}"}

    trace = buf.getvalue().strip() or "(no trace)"

    if "__interrupt__" in result:
        session["awaiting"] = True
        assistant = result["__interrupt__"][0].value.get("prompt", "Confirm? (yes/no)")
    else:
        session["awaiting"] = False
        assistant = result.get("final_response", "(no response)")
        _carry_forward(session, result)

    history = history + [{"role": "assistant", "content": assistant}]
    show_btns = session["awaiting"]
    return (history, trace, session,
            gr.update(visible=show_btns), gr.update(visible=show_btns), "")


def reset():
    return [], "", _new_session(), gr.update(visible=False), gr.update(visible=False), ""


def build_graph_view(topic: str):
    """Render a live citation graph for a topic (moon-shot visualization)."""
    from src.tools.citation_graph import build_citation_graph
    try:
        path, summary = build_citation_graph(topic)
        return path, summary
    except Exception as exc:
        return None, f"Could not build the citation graph: {exc}"


THEME = gr.themes.Soft(primary_hue="indigo", secondary_hue="violet",
                       neutral_hue="slate", font=gr.themes.GoogleFont("Inter"))

with gr.Blocks(title="Research Matching Chatbot") as demo:
    gr.HTML(HEADER_HTML)
    gr.HTML(STATUS_HTML)
    session = gr.State(_new_session())

    with gr.Tabs():
        with gr.Tab("Assistant"):
            with gr.Row(equal_height=False):
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(height=430, label="Conversation")
                    with gr.Row():
                        txt = gr.Textbox(placeholder="Ask about faculty, research trends, or collaboration…",
                                         scale=8, show_label=False, autofocus=True, container=False)
                        send = gr.Button("Send", variant="primary", scale=1, min_width=90)
                    with gr.Row():
                        yes_btn = gr.Button("Confirm", variant="primary", visible=False)
                        no_btn = gr.Button("Cancel", variant="stop", visible=False)
                        clear = gr.Button("Reset conversation", variant="secondary")

                    gr.Markdown("<span class='panel-title'>Try a student query</span>")
                    gr.Examples(STUDENT_EXAMPLES, inputs=txt, label="")
                    gr.Markdown("<span class='panel-title'>Try a professor query</span>")
                    gr.Examples(PROFESSOR_EXAMPLES, inputs=txt, label="")

                with gr.Column(scale=2):
                    gr.Markdown("<span class='panel-title'>Live execution trace</span>")
                    trace = gr.Textbox(elem_id="trace-box", show_label=False, lines=26,
                                       interactive=False,
                                       placeholder="Each turn shows which node ran and which tool was called…")

        with gr.Tab("Citation Graph"):
            gr.Markdown("Visualize how research on a topic connects — the most-cited paper, "
                        "what it builds on, and what built on it (live Semantic Scholar data).")
            with gr.Row():
                graph_topic = gr.Textbox(placeholder="e.g. federated learning, computer vision, NLP",
                                         show_label=False, scale=8, container=False)
                graph_btn = gr.Button("Build graph", variant="primary", scale=1, min_width=110)
            gr.Examples(["federated learning", "computer vision", "graph neural networks",
                         "network security"], inputs=graph_topic, label="")
            with gr.Row():
                graph_img = gr.Image(label="Citation network", height=430)
                graph_summary = gr.Markdown()

    gr.HTML("<div class='app-footer'>LangGraph · ChromaDB RAG · Tavily · Semantic Scholar"
            " &nbsp;|&nbsp; Built by Vaishnav Koka and Pk Bhargavi</div>")

    outputs = [chatbot, trace, session, yes_btn, no_btn, txt]
    send.click(step, [txt, chatbot, session], outputs)
    txt.submit(step, [txt, chatbot, session], outputs)
    yes_btn.click(lambda h, s: step("yes", h, s), [chatbot, session], outputs)
    no_btn.click(lambda h, s: step("no", h, s), [chatbot, session], outputs)
    clear.click(reset, None, outputs)
    graph_btn.click(build_graph_view, [graph_topic], [graph_img, graph_summary])
    graph_topic.submit(build_graph_view, [graph_topic], [graph_img, graph_summary])


if __name__ == "__main__":
    import os
    share = os.getenv("GRADIO_SHARE", "").lower() in ("1", "true", "yes")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=share,
                theme=THEME, css=CSS)
