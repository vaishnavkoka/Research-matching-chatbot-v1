"""Central configuration: env loading, model IDs, and feature flags.

The whole app degrades gracefully. If a key is missing the corresponding
capability turns off but the graph still runs end-to-end, which keeps the demo
robust.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv, dotenv_values

# Load .env from the project root (one level up from src/). The project .env is
# authoritative: a key present in the file (even if set empty) wins over any
# ambient shell env var of the same name (e.g. a global GROQ_API_KEY). This is
# why we read dotenv_values directly instead of trusting os.getenv, which
# python-dotenv will NOT override when the file value is blank.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH, override=True)
_FILE = dotenv_values(_ENV_PATH)


def _env(key: str, default: str = "") -> str:
    """.env file value wins if the key appears in the file (even blank); else
    fall back to the process environment."""
    if key in _FILE:
        return (_FILE[key] or "").strip()
    return (os.getenv(key, default) or "").strip()


# --- API keys ---------------------------------------------------------------
GROQ_API_KEY = _env("GROQ_API_KEY")
GEMINI_API_KEY = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
TAVILY_API_KEY = _env("TAVILY_API_KEY")
SEMANTIC_SCHOLAR_API_KEY = _env("SEMANTIC_SCHOLAR_API_KEY")

# --- SMTP (optional email send) ---------------------------------------------
SMTP_HOST = _env("SMTP_HOST")
SMTP_PORT = int(_env("SMTP_PORT", "587") or "587")
SMTP_USER = _env("SMTP_USER")
SMTP_PASSWORD = _env("SMTP_PASSWORD")
SMTP_FROM = _env("SMTP_FROM")

# --- LLM provider selection -------------------------------------------------
# Auto-pick the first provider that has a key (both are free tiers).
# Override with LLM_PROVIDER in .env.
def _pick_provider() -> str:
    forced = _env("LLM_PROVIDER").lower()
    if forced:
        return forced
    if GROQ_API_KEY:
        return "groq"
    if GEMINI_API_KEY:
        return "gemini"
    return "none"


LLM_PROVIDER = _pick_provider()

# Per-provider model IDs: (router/fast model, synthesis/strong model).
_MODELS = {
    "groq": ("llama-3.1-8b-instant", "llama-3.3-70b-versatile"),
    # flash-lite has a separate, more generous free-tier daily quota than
    # gemini-2.5-flash, which matters when the app makes a call per turn.
    "gemini": ("gemini-2.5-flash-lite", "gemini-2.5-flash-lite"),
    "none": ("", ""),
}
# Allow explicit overrides from .env.
MODEL_ROUTER = _env("MODEL_ROUTER") or _MODELS[LLM_PROVIDER][0]
MODEL_SYNTH = _env("MODEL_SYNTH") or _MODELS[LLM_PROVIDER][1]

# --- Feature flags ----------------------------------------------------------
LLM_ENABLED = LLM_PROVIDER != "none"
TAVILY_ENABLED = bool(TAVILY_API_KEY)

# --- Vector store -----------------------------------------------------------
CHROMA_DIR = str(PROJECT_ROOT / "chroma_db")
COLLECTION_NAME = "iitgn_cse_faculty"

# Where confirmed decisions get logged (HITL finalize step).
DECISIONS_LOG = str(PROJECT_ROOT / "logged_decisions.jsonl")
EMAIL_DRAFTS_DIR = str(PROJECT_ROOT / "email_drafts")


def status_banner() -> str:
    """Human-readable summary of which capabilities are live."""
    def mark(on: bool) -> str:
        return "ON " if on else "off"
    llm = f"{LLM_PROVIDER}:{MODEL_SYNTH}" if LLM_ENABLED else "off"
    return (
        f"LLM: {llm} | "
        f"Tavily web: {mark(TAVILY_ENABLED)} | "
        f"Semantic Scholar: ON  (keyless)"
    )
