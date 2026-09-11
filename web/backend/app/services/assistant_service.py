"""AI assistant backend.

Generates a reply to a user message. If ``LLM_API_KEY`` is configured it can be
wired to a real provider (LiteLLM/OpenAI-compatible); until then it returns a
grounded, helpful canned response so the chat UI is fully functional. It can
also optionally consult the Pentest RAG service for security questions.
"""

import httpx

from app.core.config import settings

_NO_PROXY = {"http://": None, "https://": None}


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


def generate_reply(message: str, history: list[dict]) -> str:
    """Return an assistant reply. Replace the body with a real LLM call when ready."""
    rag_ctx = _try_rag(message)

    if settings.LLM_API_KEY:
        # TODO: wire LiteLLM here, e.g.:
        #   import litellm
        #   messages = history + [{"role": "user", "content": message}]
        #   resp = litellm.completion(model=settings.ASSISTANT_LLM, messages=messages,
        #                             api_key=settings.LLM_API_KEY)
        #   return resp.choices[0].message.content
        pass

    intro = (
        "I'm the Strix assistant. I can help you plan assessments, interpret findings, "
        "and draft remediation guidance.\n\n"
    )
    if rag_ctx:
        return (
            intro
            + "Here's relevant context from the knowledge base:\n\n"
            + rag_ctx[:1200]
            + "\n\n(Configure LLM_API_KEY to get fully generated answers.)"
        )
    return (
        intro
        + f'You asked: "{message}"\n\n'
        + "Connect an LLM by setting LLM_API_KEY (and ASSISTANT_LLM) in the backend .env "
        + "to enable full AI responses. RAG grounding activates automatically when the "
        + "Pentest RAG service is reachable."
    )
