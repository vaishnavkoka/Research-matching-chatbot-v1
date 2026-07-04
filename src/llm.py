"""Provider-agnostic LLM layer.

Auto-selects a backend from whichever key is present (config.LLM_PROVIDER):
  - "groq"    -> free, fast Llama models (REST)
  - "gemini"  -> Google Gemini free tier (REST)
  - "none"    -> disabled; callers fall back to templated output.

Every path degrades to None on any error so the graph still runs end-to-end.
Public interface is unchanged: complete(), classify(), health_check().
"""
from __future__ import annotations

import sys
import time

import requests

from src.config import (GROQ_API_KEY, GEMINI_API_KEY,
                        LLM_ENABLED, LLM_PROVIDER, MODEL_SYNTH, MODEL_ROUTER)

_TIMEOUT = 30
_warned = False


def _warn_once(exc: Exception) -> None:
    """Surface the first LLM failure so a silent fallback isn't mistaken for success."""
    global _warned
    if not _warned:
        _warned = True
        print(f"\n[LLM disabled -> using templated fallback] {type(exc).__name__}: "
              f"{str(exc)[:200]}\n", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Provider implementations
# --------------------------------------------------------------------------- #
def _groq(prompt: str, system: str, model: str, max_tokens: int, temperature: float) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",  # Groq chat-completions endpoint
        headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _gemini(prompt: str, system: str, model: str, max_tokens: int, temperature: float) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        # thinkingBudget=0 disables 2.5 "thinking" so short calls (e.g. the
        # 30-token router) spend their whole budget on the actual answer.
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature,
                             "thinkingConfig": {"thinkingBudget": 0}},
    }
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    # One short retry smooths transient per-minute rate limits. A per-day quota
    # won't recover here, so we cap the wait and give up quickly to the fallback.
    for attempt in range(2):
        resp = requests.post(url, headers=headers, json=payload, timeout=_TIMEOUT)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(3)
            continue
        break
    resp.raise_for_status()
    cands = resp.json().get("candidates", [])
    parts = cands[0]["content"]["parts"] if cands else []
    return "".join(p.get("text", "") for p in parts).strip()


_DISPATCH = {"groq": _groq, "gemini": _gemini}


# --------------------------------------------------------------------------- #
# Public interface
# --------------------------------------------------------------------------- #
def complete(prompt: str, system: str = "", model: str | None = None,
             max_tokens: int = 900, temperature: float = 0.3) -> str | None:
    """Single-shot completion. Returns None if the LLM is unavailable or errors."""
    if not LLM_ENABLED:
        return None
    system = system or "You are a concise, helpful research-matching assistant."
    fn = _DISPATCH.get(LLM_PROVIDER)
    if fn is None:
        return None
    try:
        return fn(prompt, system, model or MODEL_SYNTH, max_tokens, temperature)
    except Exception as exc:  # network/key/credit/rate-limit — stay graceful
        _warn_once(exc)
        return None


def classify(prompt: str, system: str) -> str | None:
    """Cheap router disambiguation using the fast model."""
    return complete(prompt, system=system, model=MODEL_ROUTER,
                    max_tokens=30, temperature=0.0)


def health_check() -> tuple[bool, str]:
    """Ping the API once at boot. Returns (ok, message) for an honest banner."""
    if not LLM_ENABLED:
        return False, "no LLM key set (templated fallback)"
    fn = _DISPATCH.get(LLM_PROVIDER)
    if fn is None:
        return False, f"unknown provider {LLM_PROVIDER!r}"
    try:
        out = fn("ping", "Reply with the single word OK.", MODEL_ROUTER, 5, 0.0)
        return True, f"{LLM_PROVIDER} reachable ({MODEL_ROUTER})"
    except Exception as exc:
        return False, f"{LLM_PROVIDER} {type(exc).__name__}: {str(exc)[:140]}"
