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

from src.config import (GROQ_API_KEY, GEMINI_API_KEY, PROVIDER_MODELS,
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
    # Fail fast on a 429 (daily quota won't recover, so don't stall — the provider
    # chain falls back to Groq instantly). Only a transient 5xx gets one quick retry.
    resp = None
    for attempt in range(2):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=_TIMEOUT)
        except requests.RequestException:
            if attempt == 0:
                time.sleep(0.5)
                continue
            raise
        if resp.status_code in (500, 502, 503, 504) and attempt == 0:
            time.sleep(0.5)
            continue
        break
    resp.raise_for_status()
    cands = resp.json().get("candidates", [])
    parts = cands[0]["content"]["parts"] if cands else []
    return "".join(p.get("text", "") for p in parts).strip()


_DISPATCH = {"groq": _groq, "gemini": _gemini}


def _provider_chain() -> list[str]:
    """Primary provider first, then any other configured provider as a fallback —
    so a per-day quota (e.g. Gemini 429) automatically rolls over to Groq."""
    order = []
    if LLM_PROVIDER in _DISPATCH:
        order.append(LLM_PROVIDER)
    for prov, key in (("gemini", GEMINI_API_KEY), ("groq", GROQ_API_KEY)):
        if key and prov in _DISPATCH and prov not in order:
            order.append(prov)
    return order


# A provider that just failed (esp. with a 429) is skipped for a while, so we
# don't pay the round-trip to a quota-dead provider on every single turn.
_cooldown: dict[str, float] = {}


def _live_chain() -> list[str]:
    now = time.time()
    chain = _provider_chain()
    live = [p for p in chain if _cooldown.get(p, 0.0) <= now]
    return live or chain  # if everything is cooling down, still try the primary


# --------------------------------------------------------------------------- #
# Public interface
# --------------------------------------------------------------------------- #
def complete(prompt: str, system: str = "", role: str = "synth",
             max_tokens: int = 900, temperature: float = 0.3) -> str | None:
    """Single-shot completion. Tries the primary provider, then falls back to any
    other configured provider. A failing provider is put on cooldown so later turns
    skip it. Returns None only if every provider fails."""
    if not LLM_ENABLED:
        return None
    system = system or "You are a concise, helpful research-matching assistant."
    last_exc = None
    for prov in _live_chain():
        model = PROVIDER_MODELS[prov][0 if role == "router" else 1]
        try:
            return _DISPATCH[prov](prompt, system, model, max_tokens, temperature)
        except Exception as exc:  # try the next provider (quota / network / key)
            last_exc = exc
            # 429 = quota, likely won't recover soon → long cooldown; else brief.
            _cooldown[prov] = time.time() + (900 if "429" in str(exc) else 20)
            continue
    if last_exc is not None:
        _warn_once(last_exc)
    return None


def classify(prompt: str, system: str) -> str | None:
    """Cheap router disambiguation using the fast model of whichever provider answers."""
    return complete(prompt, system=system, role="router",
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
