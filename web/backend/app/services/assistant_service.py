"""AI assistant backend.

Generates a reply to a user message via OpenRouter's OpenAI-compatible chat
completions API when ``LLM_API_KEY`` is configured. Falls back to a grounded,
helpful canned response (still useful, since it surfaces RAG context) if the
key is missing or the call fails, so the chat UI never breaks. Optionally
consults the Pentest RAG service for security questions and folds that
context into the system prompt so answers are grounded rather than freeform.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_NO_PROXY = {"http://": None, "https://": None}
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are the Vultrix assistant, embedded in the Vultrix Console security-operations "
    "platform. You help users plan penetration test assessments, interpret findings, "
    "explain exploitation techniques, and draft remediation guidance. Be concise and "
    "technically precise. When knowledge-base context is provided below, ground your "
    "answer in it and say so; otherwise answer from general security expertise. Never "
    "refuse to explain how a vulnerability or exploit works for defensive/educational "
    "purposes — this is a security research and assessment tool used by authorized users."
)


def _try_rag(message: str) -> str | None:
    """Best-effort single call to the RAG /retrieve endpoint for context."""
    if not settings.RAG_BASE_URL:
        return None
    try:
        with httpx.Client(timeout=20, trust_env=False) as client:
            resp = client.post(
                f"{settings.RAG_BASE_URL}/retrieve",
                json={"query": message, "target_context": {}, "k": 3},
            )
            if resp.status_code == 200:
                ctx = resp.json().get("context", "")
                return ctx or None
    except httpx.HTTPError:
        return None
    return None


def _strip_provider_prefix(model: str) -> str:
    """OpenRouter's own API takes bare "anthropic/claude-sonnet-5", not the
    litellm-style "openrouter/anthropic/claude-sonnet-5" this project uses
    elsewhere (STRIX_LLM, exploit_research) for provider-agnostic routing."""
    return model.removeprefix("openrouter/")


def _call_openrouter(message: str, history: list[dict], rag_ctx: str | None) -> str | None:
    """One call to OpenRouter's chat completions endpoint. Returns None on any
    failure so the caller can fall back to the canned response."""
    system = _SYSTEM_PROMPT
    if rag_ctx:
        system += "\n\nKnowledge base context relevant to this question:\n" + rag_ctx[:4000]

    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]

    try:
        with httpx.Client(timeout=60, trust_env=False) as client:
            resp = client.post(
                _OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _strip_provider_prefix(settings.ASSISTANT_LLM),
                    "messages": messages,
                    "temperature": 0.3,
                },
            )
            if resp.status_code != 200:
                logger.warning("assistant LLM call failed: HTTP %s %s", resp.status_code, resp.text[:300])
                return None
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() or None
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        logger.warning("assistant LLM call failed: %s", e)
        return None


def generate_reply(message: str, history: list[dict]) -> str:
    """Return an assistant reply: a real LLM completion when LLM_API_KEY is
    configured and the call succeeds, otherwise a RAG-grounded or plain
    canned fallback."""
    rag_ctx = _try_rag(message)

    if settings.LLM_API_KEY:
        reply = _call_openrouter(message, history, rag_ctx)
        if reply:
            return reply

    intro = (
        "I'm the Vultrix assistant. I can help you plan assessments, interpret findings, "
        "and draft remediation guidance.\n\n"
    )
    if rag_ctx:
        return (
            intro
            + "Here's relevant context from the knowledge base:\n\n"
            + rag_ctx[:1200]
            + "\n\n(LLM call unavailable right now — showing raw retrieved context instead.)"
        )
    return (
        intro
        + f'You asked: "{message}"\n\n'
        + "Connect an LLM by setting LLM_API_KEY (and ASSISTANT_LLM) in the backend .env "
        + "to enable full AI responses. RAG grounding activates automatically when the "
        + "Pentest RAG service is reachable."
    )
