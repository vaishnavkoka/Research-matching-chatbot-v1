<div align="center">

# Research Matching Chatbot

**Connect students with the right faculty guides, and help professors explore research trends, find collaborators, and spot research gaps — grounded in real faculty profiles and live research data.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Built%20with-LangGraph-1C3C3C?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Gradio](https://img.shields.io/badge/UI-Gradio-F97316?style=flat-square)](https://www.gradio.app/)
[![Live Demo](https://img.shields.io/badge/Live-Demo-2ea44f?style=flat-square)](https://research-matching-chatbot.example.com)

</div>

## Table of Contents

- [Overview](#overview)
- [Live Demo](#live-demo)
- [Key Features](#key-features)
- [Architecture and Workflow](#architecture-and-workflow)
  - [CLI Architecture](#cli-architecture)
  - [Web UI Architecture](#web-ui-architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [How to Use](#how-to-use)
- [Screenshots](#screenshots)
  - [CLI Output](#cli-output)
  - [Web UI Output](#web-ui-output)
- [Repository Structure](#repository-structure)
- [Contributors](#contributors)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## Overview

The Research Matching Chatbot is a conversational assistant with two modes:

- **Student mode** — "Who works on NLP?", "Tell me about Dr. Raman", "What project could I do in computer vision?"
- **Professor mode** — "What's trending in NLP?", "Could I collaborate with Dr. Batra?", "What are we missing in cybersecurity?"

It answers by searching a knowledge base of real faculty profiles, pulling live research papers and web trends, and reasoning over both. Before it logs a decision or sends an email, it always pauses and asks the user to confirm. It runs both as a terminal application and as a web app that share the same underlying engine.

---

## Live Demo

The web application is hosted here: **(https://ace09328f1a41e51c7.gradio.live/)**

---

## Key Features

| Capability | What it does |
| --- | --- |
| **Faculty matching (search)** | Finds the most relevant faculty for a topic and shows a similarity match score for each. |
| **Scoped profile lookup** | Pulls the exact profile when a specific professor is named. |
| **Project suggestions** | Proposes concrete, feasible student projects grounded in faculty expertise and current papers. |
| **Live research trends** | Fetches real papers with real citation counts, plus current web results. |
| **Collaboration matching** | Suggests which faculty could team up on a topic, with a workload note. |
| **Gap analysis** | Compares what is trending against what faculty actually cover to flag gaps. |
| **Human-in-the-loop** | Pauses and asks for confirmation before logging a match or sending an email. |
| **Email summary** | Sends a match/collaboration summary to your inbox with a ready-to-forward draft. |
| **Citation graph** | Visualizes how research on a topic connects — the most-cited paper, what it builds on, and what built on it. |
| **Two front-ends** | A terminal app and a web app, both powered by the same engine. |

---

## Architecture and Workflow

### CLI Architecture

![CLI architecture and workflow](architecture-diagram/cli-architecture.png)

<div align="center">

[![View the simple, non-technical CLI diagram](https://img.shields.io/badge/View-Simple_(Layman)_CLI_Diagram-8A2BE2?style=for-the-badge)](architecture-diagram/cli-architecture-layman.png)

</div>

### Web UI Architecture

![Web UI architecture and workflow](architecture-diagram/gui-architecture.png)

<div align="center">

[![View the simple, non-technical Web UI diagram](https://img.shields.io/badge/View-Simple_(Layman)_Web_UI_Diagram-8A2BE2?style=for-the-badge)](architecture-diagram/gui-architecture-layman.png)

</div>

---

## Tech Stack

- **Orchestration:** LangGraph (a small graph of single-purpose steps, with a confirmation pause and memory across turns)
- **Knowledge base / search:** ChromaDB vector store over faculty profiles (with similarity scores)
- **Live data:** Semantic Scholar (papers and citations) and Tavily (web trends)
- **Language model:** Google Gemini (free tier), with Groq as an optional alternative; the app falls back to clean templated answers if no key is set
- **Email:** SMTP (sends the match summary to your own inbox)
- **Visualization:** networkx and matplotlib for the citation graph
- **Web interface:** Gradio

---

## Getting Started

### 1. Clone and set up

```bash
git clone https://github.com/vaishnavkoka/Research-matching-chatbot-v1.git
cd Research-matching-chatbot-v1

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your keys

```bash
cp .env.example .env
```

Then edit `.env`:

- `GEMINI_API_KEY` — free from https://aistudio.google.com/apikey (or use `GROQ_API_KEY`)
- `TAVILY_API_KEY` — free from https://tavily.com (optional; enables live web trends)
- `SEMANTIC_SCHOLAR_API_KEY` — optional (works without a key)
- `SMTP_*` — optional, only needed for the email feature (for Gmail, use an App Password)

The app still runs without any keys, using rule-based routing and templated answers.

---

## How to Use

### Run the terminal app

```bash
python main.py
```

Type your question at the `YOU:` prompt. When the assistant pauses to confirm an action, type `yes` or `no`. Commands: `:help`, `:reset`, `:quit`.

### Run the web app

```bash
python app_gradio.py
```

Open **http://127.0.0.1:7860** in your browser. Use the **Assistant** tab to chat and the **Citation Graph** tab to visualize a topic.

### Example queries

```
Who works on NLP?
Tell me more about the first match
What project could I do in computer vision?
What's trending in computer vision?
Could I collaborate with Dr. Batra on IoT?
What are we missing in cybersecurity?
Draft a collaboration email to Dr. Batra about IoT
```

For actions like collaboration matches, gap findings, or emails, the assistant shows **Confirm / Cancel** (web) or asks for **yes / no** (terminal) before it proceeds.

---

## Screenshots

### CLI Output

**Faculty search with match scores, and a live step-by-step trace.**

![CLI - faculty search](CLI-output/1.png)

**Follow-up detail lookup, and project suggestions grounded in faculty and papers.**

![CLI - detail and project ideas](CLI-output/2.png)

**Trend analysis using live papers and web search, then a collaboration request.**

![CLI - trends and collaboration](CLI-output/3.png)

**Confirming a collaboration (which gets logged), and a departmental gap analysis.**

![CLI - confirm and gap analysis](CLI-output/4.png)

### Web UI Output

**Assistant tab — faculty matches with scores and a live execution trace panel.**

![Web UI - assistant](Gradio-UI-output/1.png)

**Follow-up: drilling into a specific match.**

![Web UI - follow up detail](Gradio-UI-output/2.png)

**Scoped lookup for a named professor.**

![Web UI - named lookup](Gradio-UI-output/3.png)

**Human-in-the-loop: Confirm / Cancel buttons appear before logging a match.**

![Web UI - confirmation buttons](Gradio-UI-output/4.png)

**Citation Graph tab — a live network of how papers on a topic connect.**

![Web UI - citation graph](Gradio-UI-output/5.png)

**Email feature — the assistant confirms it sent the summary...**

![Web UI - email sent](Gradio-UI-output/email-sent-6.png)

**...the email arrives in the inbox...**

![Email received](Gradio-UI-output/email-received-7.png)

**...with the full match summary and a ready-to-forward outreach draft.**

![Email content](Gradio-UI-output/email-content-8.png)

---

## Repository Structure

```
Research-matching-chatbot/
├── main.py                       # Terminal (CLI) application
├── app_gradio.py                 # Web application (Gradio)
├── requirements.txt
├── .env.example                  # Template for your keys
├── LICENSE
├── README.md
│
├── data/
│   └── faculty_profiles.py       # 15 faculty profiles (name, areas, workload)
│
├── src/
│   ├── config.py                 # Keys, provider selection, settings
│   ├── state.py                  # Shared conversation state
│   ├── router.py                 # Understands what the user is asking
│   ├── vectorstore.py            # Faculty knowledge base + search (ChromaDB)
│   ├── llm.py                    # Language-model access (Gemini / Groq)
│   ├── nodes.py                  # The individual steps of the workflow
│   ├── graph.py                  # Wires the steps together + confirmation pause
│   └── tools/
│       ├── semantic_scholar.py   # Live papers and citation counts
│       ├── tavily_search.py      # Live web trends
│       ├── email_draft.py        # Compose and send the summary email
│       └── citation_graph.py     # Build the citation network image
│
├── architecture-diagram/         # Workflow diagrams (technical + simple)
├── CLI-output/                   # Terminal screenshots
└── Gradio-UI-output/             # Web app screenshots
```

---

## Contributors

<div align="center">

| Contributor | Email |
| :---: | :---: |
| **Vaishnav Koka** | [vaishnav.koka@iitgn.ac.in](mailto:vaishnav.koka@iitgn.ac.in) |
| **PK Bhargavi** | [skbhargavi14@gmail.com](mailto:skbhargavi14@gmail.com) |

</div>

---

## Disclaimer

This project was developed by the contributors as part of a hackathon/bootcamp learning experience. It is an independent student project and does not represent the official views, policies, or endorsements of the Indian Institute of Technology Gandhinagar (IITGN) or any affiliated faculty, department, or organization.

All design decisions, implementation, and content are the sole responsibility of the project contributors.

---

## License

Released under the [MIT License](LICENSE).
