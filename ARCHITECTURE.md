# Research Matching Chatbot — Architecture Blueprint (Phase 1)

An agentic, terminal-based LangGraph application that connects **students** to the
right faculty guides and helps **professors** explore research trends, find
collaboration partners, and spot departmental gaps. Grounded in **real IIT
Gandhinagar CSE faculty data** (ChromaDB RAG) + **live APIs** (Tavily, Semantic
Scholar).

---

## 1. State Definition (`ResearchState` TypedDict)

Every field, its type, and why it exists. The state is the single source of truth
that flows through the graph and **persists across turns** via a LangGraph
`MemorySaver` checkpointer keyed by `thread_id`.

| Field | Type | Purpose |
|-------|------|---------|
| `user_query` | `str` | Raw text the user typed this turn. Router input. |
| `messages` | `List[dict]` | Rolling conversation history (`{role, content}`) for multi-turn follow-ups ("tell me more about the first one"). |
| `current_mode` | `Literal["student","professor"]` | Which persona flow we are in. Sticky across turns unless the user switches. |
| `intent` | `str` | Fine-grained label from the router: `who_works_on`, `faculty_detail`, `next_match`, `trend_analysis`, `collaboration`, `gap_analysis`, `email_draft`, `smalltalk`. |
| `routing_target` | `str` | Name of the next node the router selected. Drives the conditional edge. |
| `topic` | `Optional[str]` | Research topic extracted from the query (e.g. "NLP", "federated learning"). Feeds RAG + APIs. |
| `focus_faculty` | `Optional[str]` | A specific faculty name the user is asking about / following up on. Enables scoped lookup. |
| `retrieved_docs` | `List[dict]` | RAG hits: `{name, area, text, score}` with **cosine similarity match scores**. |
| `last_results` | `List[dict]` | Cache of the previous turn's ranked matches so "the first match" resolves without re-querying. |
| `api_results` | `dict` | `{"tavily": [...], "semantic_scholar": [...]}` live tool outputs. |
| `analysis` | `str` | LLM-synthesized reasoning (matching rationale, gap analysis, trend summary). |
| `proposed_action` | `Optional[dict]` | A decision awaiting human sign-off: `{type, summary, payload}` (e.g. log a match, draft an email). |
| `awaiting_confirmation` | `bool` | HITL flag — set when the graph is paused at the confirmation node. |
| `human_confirmation` | `Optional[str]` | The user's yes/no (+ edits) captured on resume. |
| `final_response` | `str` | Rendered answer shown in the terminal this turn. |
| `log` | `List[str]` | Ordered execution trace (nodes entered, tools called) printed for demo transparency. |

---

## 2. Nodes — strict "one job per node"

| Node | Single Responsibility |
|------|----------------------|
| **IntentRouter** | Classify the query into mode + fine-grained intent and pick `routing_target`. **Rule-first (zero LLM calls)**; a single cheap Haiku call is used *only* when keyword confidence is low. Never does retrieval or synthesis. |
| **FacultyRAGRetrieval** | Vector-search ChromaDB for a topic ("who works on X") and return ranked faculty with similarity scores. Nothing else. |
| **ScopedDetailLookup** | Fetch the *exact* profile for one named faculty (metadata filter, not fuzzy vector search) for "tell me about Dr. X". |
| **ProjectSuggestion** | For "What project could I do on X?" — combine the top matching faculty profiles with live papers on the topic into 2–3 concrete, feasible project ideas and who to approach. |
| **WebTrendAnalysis** | Call Tavily (live web) + Semantic Scholar (papers, citations) for the topic. Pure data gathering. |
| **CollaborativeMatching** | Cross-reference trends/papers against faculty profiles → propose internal pairings or a student project match. Produces a `proposed_action`. |
| **GapAnalysis** | Compare what is *trending* vs what faculty *actually cover* → flag departmental research gaps + workload notes. |
| **SynthesizeAnswer** | Turn the gathered docs/analysis into the final user-facing message (tone-adapted: simpler for students, citation-depth for professors). |
| **HumanConfirmationNode** | HITL gate. Calls LangGraph `interrupt()` to pause before any decision is *logged* or an email is *drafted*; resumes with the user's answer. |
| **FinalizeAction** | Execute the approved action (log the match to disk / hand off the email draft) — only reached after a "yes". |

---

## 3. Conditionals & Edges (execution flow)

```
                          ┌──────────────┐
              START ─────▶│ IntentRouter │
                          └──────┬───────┘
                 route_from_intent (conditional)
      ┌───────────────┬─────────┼────────────┬──────────────┐
      ▼               ▼         ▼            ▼              ▼
FacultyRAG      ScopedDetail  WebTrend   (prof flows)   Synthesize
Retrieval        Lookup      Analysis        │         (smalltalk)
      │               │         │            │              │
      │               │    route_after_trend │              │
      │               │      ┌────┴─────┐    │              │
      │               │      ▼          ▼    ▼              │
      │               │  Collaborative  GapAnalysis         │
      │               │   Matching       │                  │
      │               │      │           │                  │
      └───────┬───────┴──────┴─────┬─────┘                  │
              ▼                     ▼                        │
        SynthesizeAnswer ◀──────────┘                        │
              │                                              │
      needs_confirmation? (conditional)                      │
        ┌─────┴───────────┐                                  │
        ▼                 ▼                                  │
 HumanConfirmation      END ◀──────────────────────────────┘
   (interrupt)
        │  resume with human_confirmation
   approved? (conditional)
    ┌────┴─────┐
    ▼          ▼
FinalizeAction END (declined)
    │
    ▼
   END
```

**Branch points (conditional edges):**

1. `route_from_intent` (after IntentRouter): the core dispatcher.
   - `who_works_on` → FacultyRAGRetrieval
   - `faculty_detail` / `next_match` → ScopedDetailLookup
   - `trend_analysis` / `collaboration` / `gap_analysis` → WebTrendAnalysis
   - `smalltalk` → SynthesizeAnswer (no tools, no wasted calls)

2. `route_after_trend` (after WebTrendAnalysis): professor sub-router.
   - `collaboration` → CollaborativeMatching
   - `gap_analysis` → GapAnalysis
   - `trend_analysis` → SynthesizeAnswer directly

3. `needs_confirmation` (after SynthesizeAnswer): the **HITL gate**.
   - If `proposed_action` exists (a match to log / an email to draft) → HumanConfirmationNode
   - else → END (plain informational answers never nag the user).

4. `approved` (after HumanConfirmationNode resumes):
   - `human_confirmation ∈ {yes, y, confirm, approve}` → FinalizeAction → END
   - otherwise → END (politely declined, nothing logged).

**Loop / persistence:** the terminal loop re-invokes the compiled graph with the
same `thread_id` every turn, so `messages`, `current_mode`, `focus_faculty`, and
`last_results` survive — enabling follow-ups. The HITL pause is a genuine
LangGraph `interrupt`, not a fake `input()` inside a node, so the checkpointer
holds the paused state until the user answers.
