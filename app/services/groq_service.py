"""Thin wrapper around the Groq chat API. Only the backend ever calls this."""
import json

import httpx

from app.config import settings
from app.services.errors import ExternalServiceError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def chat_json(system: str, user: str, temperature: float = 0.4, max_tokens: int = 4000) -> dict:
    """Ask the model for a JSON object and return it as a dict."""
    if not settings.GROQ_API_KEY:
        raise ExternalServiceError("GROQ_API_KEY is not configured on the server.", 503)

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    try:
        resp = httpx.post(GROQ_URL, json=payload, headers=headers, timeout=60)
    except httpx.HTTPError:
        raise ExternalServiceError("Could not reach the AI service. Please try again.") from None

    if resp.status_code == 429:
        raise ExternalServiceError("The AI service is busy (rate limit). Try again in a minute.", 429)
    if resp.status_code != 200:
        raise ExternalServiceError(f"The AI service returned an error (status {resp.status_code}).")

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except (KeyError, IndexError, ValueError, TypeError):
        raise ExternalServiceError("The AI service returned an unreadable response.") from None

    if not isinstance(data, dict):
        raise ExternalServiceError("The AI service returned an unexpected format.")
    return data
