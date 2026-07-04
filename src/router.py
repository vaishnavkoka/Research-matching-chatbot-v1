"""Rule-first intent classification. Zero LLM calls on the common path; a single
cheap Haiku call is used only when keyword confidence is low. Also extracts the
`topic` and `focus_faculty` slots.
"""
from __future__ import annotations

import re

from data.faculty_profiles import all_profiles, get_by_name
from src.llm import classify

# Intents grouped by mode.
STUDENT_INTENTS = {"who_works_on", "faculty_detail", "next_match"}
PROFESSOR_INTENTS = {"trend_analysis", "collaboration", "gap_analysis", "email_draft"}

_PROF_MODE_HINTS = ("trending", "collaborate", "collaboration", "missing", "gap",
                    "we cover", "our department", "our dept", "partner with", "team up")
_STUDENT_MODE_HINTS = ("who works on", "tell me about", "supervisor", "guide", "advisor",
                        "project could i", "what project", "i want to work")

# Ordinal words for "the first/second match" follow-ups.
_ORDINALS = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2,
             "fourth": 3, "4th": 3, "last": -1}

# Topic vocabulary drawn from faculty keywords for lightweight topic extraction.
_TOPIC_VOCAB = sorted(
    {kw for f in all_profiles() for kw in f["keywords"]} |
    {"nlp", "computer vision", "iot", "cybersecurity", "security", "data mining",
     "machine learning", "deep learning", "networking", "systems", "hci",
     "algorithms", "vlsi", "software engineering", "federated learning",
     "large language models", "reinforcement learning", "graph neural networks"},
    key=len, reverse=True,
)


def _faculty_names() -> list[str]:
    return [f["name"] for f in all_profiles()]


def _detect_faculty(text: str) -> str | None:
    """Detect a specific faculty mention (surname sufficient)."""
    low = text.lower()
    for f in all_profiles():
        surname = f["name"].split()[-1].lower()
        first = f["name"].split()[1].lower() if len(f["name"].split()) > 1 else ""
        if re.search(rf"\b{re.escape(surname)}\b", low) or (
            first and len(first) > 3 and re.search(rf"\b{re.escape(first)}\b", low)
        ):
            return f["name"]
    return None


def _detect_topic(text: str) -> str | None:
    low = text.lower()
    for term in _TOPIC_VOCAB:
        if term in low:
            return term
    # Fallback: strip common lead-ins to keep a usable topic phrase.
    m = re.search(r"(?:works? on|trending in|about|for|missing in|gap in)\s+(.+)", low)
    if m:
        return m.group(1).strip(" ?.").strip()
    return None


def _detect_ordinal(text: str) -> int | None:
    low = text.lower()
    for word, idx in _ORDINALS.items():
        if re.search(rf"\b{word}\b", low):
            return idx
    return None


def classify_intent(user_query: str, prior_mode: str, last_results: list) -> dict:
    """Return {mode, intent, topic, focus_faculty, ordinal, confident}."""
    text = user_query.strip()
    low = text.lower()

    faculty = _detect_faculty(text)
    topic = _detect_topic(text)
    ordinal = _detect_ordinal(text)

    # --- follow-up: "tell me more about the first match" ---
    if ordinal is not None and last_results:
        idx = ordinal if ordinal >= 0 else len(last_results) - 1
        idx = max(0, min(idx, len(last_results) - 1))
        return {"mode": "student", "intent": "faculty_detail",
                "topic": topic, "focus_faculty": last_results[idx]["name"],
                "ordinal": ordinal, "confident": True}

    # --- student: project ideas ("what project could I do on X?") ---
    # Checked before who_works_on because that path also matches "project on".
    if any(p in low for p in ("what project", "which project", "project idea", "project ideas",
                              "suggest a project", "suggest project", "project could i",
                              "could i do a project", "what can i work on", "what should i work on",
                              "give me a project", "ideas for a project", "project suggestion",
                              "what to work on", "propose a project")):
        return {"mode": "student", "intent": "project_ideas", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    # --- professor-mode intents (checked first; more specific verbs) ---
    # Email is checked before collaboration: "draft a collaboration email" is an
    # explicit ask to email, so that action should win over plain matching.
    if "email" in low or "draft" in low or "reach out" in low or "write to" in low:
        return {"mode": "professor", "intent": "email_draft", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    if any(w in low for w in ("missing", "gap", "what are we missing", "gap analysis",
                              "under-covered", "not covered", "blind spot")):
        return {"mode": "professor", "intent": "gap_analysis", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    if any(w in low for w in ("collaborate", "collaboration", "team up", "partner",
                              "pair", "who else works", "work together")):
        return {"mode": "professor", "intent": "collaboration", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    if "trend" in low or "trending" in low or "state of the art" in low or "latest in" in low:
        return {"mode": "professor", "intent": "trend_analysis", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    # --- student-mode intents ---
    if faculty and any(w in low for w in ("tell me about", "who is", "about dr",
                                          "profile of", "more on", "details on", "detail")):
        return {"mode": "student", "intent": "faculty_detail", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    if any(w in low for w in ("who works on", "who does", "who studies", "which faculty",
                              "find me", "looking for", "guide for", "supervisor for",
                              "i want to work on", "project on")):
        return {"mode": "student", "intent": "who_works_on", "topic": topic,
                "focus_faculty": None, "ordinal": None, "confident": True}

    if faculty:  # a bare name -> treat as detail lookup
        return {"mode": "student", "intent": "faculty_detail", "topic": topic,
                "focus_faculty": faculty, "ordinal": None, "confident": True}

    # --- low confidence: one cheap LLM disambiguation, else smalltalk ---
    label = classify(
        prompt=(f"Query: {text!r}\nReply with EXACTLY one label from: "
                "who_works_on, faculty_detail, trend_analysis, collaboration, "
                "gap_analysis, smalltalk."),
        system="You label research-assistant queries. Output only the label.",
    )
    if label:
        label = label.strip().lower().split()[0]
    if label in STUDENT_INTENTS or label in PROFESSOR_INTENTS:
        mode = "professor" if label in PROFESSOR_INTENTS else "student"
        return {"mode": mode, "intent": label, "topic": topic or text,
                "focus_faculty": faculty, "ordinal": None, "confident": bool(label)}

    return {"mode": prior_mode, "intent": "smalltalk", "topic": topic,
            "focus_faculty": faculty, "ordinal": None, "confident": False}
