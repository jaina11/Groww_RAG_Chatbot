"""Groq chat completions client."""

from __future__ import annotations

import os
from typing import List, Sequence

import requests

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_TIMEOUT_SEC = 30


class GroqClient:
    """Thin wrapper around the Groq OpenAI-compatible chat API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        """
        Initialize the Groq client using environment-backed credentials.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model or os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.timeout_sec = timeout_sec

    def complete(self, messages: Sequence[dict], temperature: float = 0.1) -> str:
        """
        Send a chat completion request and return the assistant message text.

        Raises RuntimeError when the API key is missing or the request fails.
        """
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set")

        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": 300,
            },
            timeout=self.timeout_sec,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Groq API error status={response.status_code} body={response.text}"
            )

        payload = response.json()
        choices: List[dict] = payload.get("choices", [])
        if not choices:
            raise RuntimeError("Groq API returned no choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not str(content).strip():
            raise RuntimeError("Groq API returned empty content")
        return str(content).strip()
