"""LangGraph nodes. Strict one-job-per-node. Each node appends to state['log']
so the terminal can show exactly which node ran and which tools fired.
"""
from __future__ import annotations

import json
from datetime import datetime

from langgraph.types import interrupt

from src.state import ResearchState
from src.router import classify_intent
from src.vectorstore import retrieve
from src.llm import complete
from src.tools.semantic_scholar import search_papers
from src.tools.tavily_search import web_trends
from src.tools.email_draft import draft_email, send_email
from data.faculty_profiles import get_by_name, all_profiles
from src.config import DECISIONS_LOG, MODEL_SYNTH, SMTP_FROM, SMTP_USER


def _log(state: ResearchState, msg: str) -> None:
    state.setdefault("log", []).append(msg)
    print(f"   - {msg}")


# --------------------------------------------------------------------------- #
# 1. IntentRouter — classify only. No retrieval, no synthesis.
# --------------------------------------------------------------------------- #
def intent_router(state: ResearchState) -> ResearchState:
    print("\n[NODE] IntentRouter")
    r = classify_intent(state["user_query"], state.get("current_mode", "student"),
                        state.get("last_results", []))
    state["current_mode"] = r["mode"]
    state["intent"] = r["intent"]
    state["topic"] = r["topic"] or state.get("topic")
    if r["focus_faculty"]:
        state["focus_faculty"] = r["focus_faculty"]
    elif r["intent"] in ("who_works_on", "trend_analysis"):
        # Fresh topic-centric query: don't inherit a previous faculty anchor.
        state["focus_faculty"] = None

    target = {
        "who_works_on": "faculty_rag",
        "faculty_detail": "scoped_lookup",
        "next_match": "scoped_lookup",
        "project_ideas": "project_suggestion",
        "trend_analysis": "web_trends",
        "collaboration": "web_trends",
        "gap_analysis": "web_trends",
        "email_draft": "collaborative_matching",
        "smalltalk": "synthesize",
    }.get(r["intent"], "synthesize")
    state["routing_target"] = target
    how = "keyword-rules" if r["confident"] else "llm-fallback"
    _log(state, f"mode={r['mode']} intent={r['intent']} topic={r['topic']!r} "
                f"faculty={state.get('focus_faculty')!r} route->{target} ({how})")
    return state


# --------------------------------------------------------------------------- #
# 2. FacultyRAGRetrieval — vector search only.
# --------------------------------------------------------------------------- #
def faculty_rag(state: ResearchState) -> ResearchState:
    print("[NODE] FacultyRAGRetrieval")
    query = state.get("topic") or state["user_query"]
    _log(state, f"ChromaDB vector search: {query!r}")
    hits = retrieve(query, k=4)
    state["retrieved_docs"] = hits
    state["last_results"] = hits
    _log(state, "top matches: " + ", ".join(f"{h['name']} ({h['score']}%)" for h in hits))
    return state


# --------------------------------------------------------------------------- #
# 3. ScopedDetailLookup — exact profile fetch (metadata, not fuzzy search).
# --------------------------------------------------------------------------- #
def scoped_lookup(state: ResearchState) -> ResearchState:
    print("[NODE] ScopedDetailLookup")
    name = state.get("focus_faculty")
    prof = get_by_name(name) if name else None
    if prof:
        _log(state, f"scoped profile fetch: {prof['name']}")
        state["retrieved_docs"] = [{
            "name": prof["name"], "faculty_id": prof["id"], "subfield": prof["subfield"],
            "areas": ", ".join(prof["areas"]), "email": prof["email"],
            "active_projects": prof["active_projects"], "text": prof["profile"],
            "score": 100.0,
        }]
    else:
        _log(state, f"no exact match for {name!r}; falling back to vector search")
        state["retrieved_docs"] = retrieve(name or state["user_query"], k=1)
    return state


# --------------------------------------------------------------------------- #
# 3b. ProjectSuggestion — propose concrete student projects grounded in the
#     matching faculty profiles + current papers on the topic.
# --------------------------------------------------------------------------- #
def project_suggestion(state: ResearchState) -> ResearchState:
    print("[NODE] ProjectSuggestion")
    topic = state.get("topic") or state["user_query"]
    faculty = retrieve(topic, k=3)
    state["retrieved_docs"] = faculty
    _log(state, "grounding on faculty: " + ", ".join(f["name"] for f in faculty))
    _log(state, f"TOOL Semantic Scholar: papers on {topic!r}")
    papers = search_papers(topic, limit=3)
    state["api_results"] = {"semantic_scholar": papers}
    state["analysis"] = _llm_or_template_projects(state, topic, faculty, papers)
    _log(state, "generated project ideas")
    return state


# --------------------------------------------------------------------------- #
# 4. WebTrendAnalysis — live tools only (Tavily + Semantic Scholar).
# --------------------------------------------------------------------------- #
def web_trend_analysis(state: ResearchState) -> ResearchState:
    print("[NODE] WebTrendAnalysis")
    topic = state.get("topic") or state["user_query"]
    _log(state, f"TOOL Semantic Scholar: papers on {topic!r}")
    papers = search_papers(topic, limit=5)
    _log(state, f"TOOL Tavily: web trends on {topic!r}")
    web = web_trends(topic, max_results=4)
    state["api_results"] = {"semantic_scholar": papers, "tavily": web}
    n_papers = len([p for p in papers if "title" in p])
    _log(state, f"fetched {n_papers} papers + {len(web)} web results")
    # Also pull the internal faculty landscape for cross-matching downstream.
    state["retrieved_docs"] = retrieve(topic, k=5)
    return state


# --------------------------------------------------------------------------- #
# 5. CollaborativeMatching — propose internal pairings / project matches.
# --------------------------------------------------------------------------- #
def collaborative_matching(state: ResearchState) -> ResearchState:
    print("[NODE] CollaborativeMatching")
    topic = state.get("topic") or state["user_query"]
    faculty = state.get("retrieved_docs") or retrieve(topic, k=5)
    state["retrieved_docs"] = faculty

    anchor = state.get("focus_faculty")
    partners = [f for f in faculty if f["name"] != anchor][:3]
    _log(state, "candidate collaborators: " + ", ".join(f["name"] for f in partners))

    rationale = _llm_or_template_matching(state, topic, anchor, partners)
    state["analysis"] = rationale

    # Stage an action that will require human confirmation before logging.
    if partners:
        top = partners[0]
        state["proposed_action"] = {
            "type": "log_collaboration" if state["intent"] != "email_draft" else "draft_email",
            "summary": (f"Pair {anchor or 'the requester'} with {top['name']} "
                        f"on '{topic}'"),
            "payload": {
                "topic": topic,
                "anchor": anchor,
                "partner": top["name"],
                "partner_email": top["email"],
                "partners": [p["name"] for p in partners],
            },
        }
        _log(state, f"proposed action staged: {state['proposed_action']['type']}")
    return state


# --------------------------------------------------------------------------- #
# 6. GapAnalysis — trending research vs what faculty actually cover.
# --------------------------------------------------------------------------- #
def gap_analysis(state: ResearchState) -> ResearchState:
    print("[NODE] GapAnalysis")
    topic = state.get("topic") or state["user_query"]
    papers = state.get("api_results", {}).get("semantic_scholar", [])
    faculty = state.get("retrieved_docs") or retrieve(topic, k=5)
    state["retrieved_docs"] = faculty

    # A gap is signalled when even the best internal match is weak.
    best = max((f["score"] for f in faculty), default=0.0)
    coverage = "well covered" if best >= 45 else ("thinly covered" if best >= 30 else "a likely gap")
    _log(state, f"internal best-match score={best}% -> {coverage}")

    analysis = _llm_or_template_gap(state, topic, faculty, papers, coverage)
    state["analysis"] = analysis
    state["proposed_action"] = {
        "type": "log_gap_finding",
        "summary": f"Record gap-analysis finding for '{topic}' ({coverage})",
        "payload": {"topic": topic, "coverage": coverage,
                     "best_match": faculty[0]["name"] if faculty else None},
    }
    _log(state, "proposed action staged: log_gap_finding")
    return state


# --------------------------------------------------------------------------- #
# 7. SynthesizeAnswer — render the final user-facing message.
# --------------------------------------------------------------------------- #
def synthesize(state: ResearchState) -> ResearchState:
    print("[NODE] SynthesizeAnswer")
    intent = state.get("intent")
    if intent == "smalltalk":
        state["final_response"] = _smalltalk(state)
        return state

    if state.get("analysis"):
        # Professor flows already produced analysis; format with any staged action.
        body = state["analysis"]
        if state.get("proposed_action"):
            body += f"\n\nProposed next step: {state['proposed_action']['summary']}"
        state["final_response"] = body
        _log(state, "rendered analysis answer")
        return state

    # Student flows: format the retrieved matches.
    docs = state.get("retrieved_docs", [])
    if intent == "faculty_detail":
        state["final_response"] = _render_detail(state, docs)
    elif intent == "trend_analysis":
        state["final_response"] = _render_trends(state, docs)
    else:
        state["final_response"] = _render_matches(state, docs)
    _log(state, "rendered retrieval answer")
    return state


# --------------------------------------------------------------------------- #
# 8. HumanConfirmationNode — the HITL gate (real LangGraph interrupt).
# --------------------------------------------------------------------------- #
def human_confirmation(state: ResearchState) -> ResearchState:
    print("[NODE] HumanConfirmationNode (HITL)")
    action = state.get("proposed_action") or {}
    _log(state, "pausing for human confirmation")
    decision = interrupt({
        "prompt": (f"\nConfirm before I log/act:\n   {action.get('summary')}\n"
                   "   Type 'yes' to proceed, or 'no' to cancel: "),
        "action": action,
    })
    state["human_confirmation"] = str(decision).strip().lower()
    _log(state, f"human said: {state['human_confirmation']!r}")
    return state


# --------------------------------------------------------------------------- #
# 9. FinalizeAction — execute the approved action.
# --------------------------------------------------------------------------- #
def finalize_action(state: ResearchState) -> ResearchState:
    print("[NODE] FinalizeAction")
    action = state.get("proposed_action") or {}
    kind = action.get("type")

    if kind == "draft_email":
        p = action["payload"]
        # Deliver the match summary to the user's own inbox (a "notify me" email),
        # with a ready-to-forward outreach draft for the faculty member inside.
        recipient = SMTP_FROM or SMTP_USER or p["partner_email"]
        subject = f"Collaboration match on {p['topic']}: consider {p['partner']}"
        outreach = (f"Dear {p['partner']},\n\n{state.get('analysis', '')}\n\n"
                    f"Would you be open to exploring a collaboration on {p['topic']}?\n\n"
                    "Best regards,")
        body = (
            "Hi,\n\nThe Research Matching Assistant prepared this collaboration match "
            "for you.\n\n"
            f"Topic: {p['topic']}\n"
            f"Suggested collaborator: {p['partner']}\n\n"
            f"Why this pairing:\n{state.get('analysis', '')}\n\n"
            "----- Ready-to-send outreach draft -----\n"
            f"{outreach}\n"
            "----------------------------------------\n"
        )
        draft = draft_email("You", recipient, subject, body)
        result = send_email(draft)
        _log(state, f"email finalized: {result}")
        state["final_response"] = (f"Done. {result}\nSent to: {recipient}\n"
                                   f"Subject: {subject}")
    else:
        record = {"time": datetime.now().isoformat(timespec="seconds"),
                  "type": kind, "summary": action.get("summary"),
                  "payload": action.get("payload")}
        with open(DECISIONS_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        _log(state, f"logged decision to {DECISIONS_LOG}")
        state["final_response"] = f"Confirmed and logged: {action.get('summary')}"
    state["proposed_action"] = None
    return state


# --------------------------------------------------------------------------- #
# Rendering / LLM helpers
# --------------------------------------------------------------------------- #
def _tone(state: ResearchState) -> str:
    return ("Use simple, encouraging language suitable for a student."
            if state.get("current_mode") == "student"
            else "Use precise, citation-aware language suitable for a professor.")


def _render_matches(state: ResearchState, docs: list) -> str:
    topic = state.get("topic") or "your topic"
    if not docs:
        return f"I couldn't find a faculty match for '{topic}'."
    lines = [f"Here are the top faculty matches for '{topic}':\n"]
    for i, d in enumerate(docs, 1):
        lines.append(f"{i}. {d['name']} — {d['subfield']}  (match {d['score']}%)")
        lines.append(f"   Areas: {d['areas']}")
        lines.append(f"   Load: {d['active_projects']} active projects | {d['email']}")
    # Optional LLM polish for rationale.
    polish = complete(
        system="You are a faculty-matching assistant. " + _tone(state),
        prompt=(f"Student topic: {topic}. Candidate faculty (with match %):\n"
                + "\n".join(f"- {d['name']} ({d['score']}%): {d['areas']}" for d in docs)
                + "\nIn 2 sentences, tell the student which match to approach first and why."),
        max_tokens=160,
    )
    if polish:
        lines.append(f"\nRecommendation: {polish}")
    lines.append("\n(Ask 'tell me more about the first match' to drill in.)")
    return "\n".join(lines)


def _render_detail(state: ResearchState, docs: list) -> str:
    if not docs:
        return "I don't have a profile for that faculty member."
    d = docs[0]
    base = (f"{d['name']} — {d['subfield']}\n"
            f"Areas: {d['areas']}\n"
            f"Active projects this semester: {d['active_projects']}\n"
            f"Contact: {d['email']}\n\n{d['text']}")
    polish = complete(
        system="You summarize a faculty profile for a prospective student. " + _tone(state),
        prompt=(f"Profile:\n{d['text']}\n\nWrite 2-3 sentences on what kinds of student "
                "projects would be a great fit with this professor."),
        max_tokens=180,
    )
    return base + (f"\n\nGood project fits: {polish}" if polish else "")


def _render_trends(state: ResearchState, docs: list) -> str:
    topic = state.get("topic") or "your topic"
    api = state.get("api_results", {})
    papers = [p for p in api.get("semantic_scholar", []) if "title" in p]
    web = [w for w in api.get("tavily", []) if "title" in w]

    lines = [f"Current research landscape for '{topic}':\n"]
    if papers:
        lines.append("Top papers (live, Semantic Scholar — real citation counts):")
        for p in papers[:5]:
            lines.append(f"   • [{p['citations']} cites] {p['title']} ({p.get('year','n/a')})")
            if p.get("authors"):
                lines.append(f"     {p['authors']}")
    if web:
        lines.append("\nWeb trends (live, Tavily):")
        for w in web[:4]:
            lines.append(f"   • {w['title']}\n     {w['url']}")
    if not papers and not web:
        lines.append("(No live results available — check TAVILY_API_KEY / network.)")

    # Ground the trend against internal faculty who cover it.
    if docs:
        lines.append("\nFaculty here closest to this topic:")
        for d in docs[:3]:
            lines.append(f"   • {d['name']} ({d['subfield']}, {d['score']}% match)")

    polish = complete(
        system="You are a research-trends analyst for a CS department. " + _tone(state),
        prompt=(f"Topic: {topic}\nPapers: "
                + "; ".join(f"{p['title']} ({p['citations']} cites)" for p in papers[:5])
                + f"\nInternal faculty: "
                + "; ".join(f"{d['name']} ({d['score']}%)" for d in docs[:3])
                + "\nIn 3 sentences summarize where this field is heading and which local "
                "faculty could ride the trend."),
        max_tokens=240,
    )
    if polish:
        lines.append(f"\nSummary: {polish}")
    return "\n".join(lines)


def _smalltalk(state: ResearchState) -> str:
    reply = complete(
        system="You are a friendly research-matching assistant for IIT Gandhinagar CSE. "
               "Briefly help and suggest what the user can ask.",
        prompt=state["user_query"], max_tokens=120,
    )
    return reply or (
        "I connect students with faculty guides and help professors find collaborators "
        "and research gaps. Try: 'Who works on NLP?', 'Tell me about Dr. Raman', "
        "'What's trending in computer vision?', or 'What are we missing in cybersecurity?'"
    )


def _llm_or_template_matching(state, topic, anchor, partners) -> str:
    fac_lines = "\n".join(
        f"- {p['name']} ({p['subfield']}, {p['score']}% topical match, "
        f"{p['active_projects']} active projects): {p['areas']}" for p in partners)
    papers = state.get("api_results", {}).get("semantic_scholar", [])
    paper_lines = "\n".join(f"- [{p.get('citations')} cites] {p.get('title')} ({p.get('year')})"
                            for p in papers if "title" in p)
    llm = complete(
        system="You are a research-collaboration strategist for a CS department. " + _tone(state),
        prompt=(f"Topic: {topic}\nAnchor faculty: {anchor or 'none specified'}\n"
                f"Candidate internal collaborators:\n{fac_lines}\n\n"
                f"Live trending papers:\n{paper_lines}\n\n"
                "Recommend the single best internal pairing and justify it in 3-4 sentences, "
                "referencing complementary expertise and the trend. Note workload if relevant."),
        max_tokens=320,
    )
    if llm:
        return llm
    if not partners:
        return f"No strong internal collaborators surfaced for '{topic}'."
    top = partners[0]
    return (f"For '{topic}', the strongest internal pairing is {anchor or 'you'} with "
            f"{top['name']} ({top['subfield']}, {top['score']}% topical overlap). "
            f"Their work on {top['areas']} complements the topic. "
            f"Note: {top['name']} has {top['active_projects']} active projects.")


def _llm_or_template_projects(state, topic, faculty, papers) -> str:
    fac = "\n".join(f"- {f['name']} ({f['subfield']}): {f['areas']}" for f in faculty)
    pap = "\n".join(f"- {p['title']} ({p.get('year')}, {p.get('citations')} cites)"
                    for p in papers if "title" in p)
    llm = complete(
        system="You suggest concrete, feasible student research projects. " + _tone(state),
        prompt=(f"Topic: {topic}\nFaculty who could guide (with expertise):\n{fac}\n\n"
                f"Recent papers on the topic:\n{pap}\n\n"
                "Propose exactly 3 concrete project ideas a student could realistically "
                "pursue on this topic. For each idea give: a short title, one or two "
                "sentences on what to build or investigate, and which faculty member to "
                "approach and why. Keep it practical and encouraging."),
        max_tokens=430,
    )
    if llm:
        return f"Project ideas for '{topic}':\n\n{llm}"
    ideas = []
    for i, f in enumerate(faculty, 1):
        area = f["areas"].split(",")[0].strip()
        ideas.append(f"{i}. Build something applying {area}. Approach {f['name']} "
                     f"({f['subfield']}), whose work covers {f['areas']}.")
    return f"Project ideas for '{topic}':\n\n" + "\n".join(ideas)


def _llm_or_template_gap(state, topic, faculty, papers, coverage) -> str:
    fac_lines = "\n".join(f"- {f['name']} ({f['subfield']}, {f['score']}%)" for f in faculty)
    paper_lines = "\n".join(f"- [{p.get('citations')} cites] {p.get('title')} ({p.get('year')})"
                            for p in papers if "title" in p)
    llm = complete(
        system="You are a department research-strategy analyst. " + _tone(state),
        prompt=(f"Trending topic: {topic}\nLive high-impact papers:\n{paper_lines}\n\n"
                f"Closest internal faculty (topical match %):\n{fac_lines}\n\n"
                f"Internal coverage looks: {coverage}. In 4-5 sentences, assess whether this "
                "is a genuine departmental research gap, who is closest to cover it, and one "
                "concrete step to close the gap."),
        max_tokens=340,
    )
    if llm:
        return llm
    closest = faculty[0]["name"] if faculty else "no one"
    return (f"On '{topic}', high-citation work is active externally, but internal coverage is "
            f"{coverage} (closest: {closest}). This suggests {'a gap worth seeding' if 'gap' in coverage else 'reasonable coverage'}. "
            f"A concrete step: encourage {closest} to co-advise a project or seminar on {topic}.")
