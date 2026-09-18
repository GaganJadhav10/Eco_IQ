"""LLMService: the only place the system talks to a language model.

Swappable behind two methods. With no GEMINI_API_KEY, `enabled` is False and every
caller falls back to deterministic code - the scientific content never changes.
"""
from __future__ import annotations

import json
import os

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(RuntimeError):
    pass


class LLMService:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 30.0):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _call(self, system: str, user: str, generation_config: dict) -> str:
        if not self.enabled:
            raise LLMError("LLM disabled (no GEMINI_API_KEY)")
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": generation_config,
        }
        try:
            r = httpx.post(GEMINI_URL.format(model=self.model), json=body, timeout=self.timeout,
                           headers={"x-goog-api-key": self.api_key})
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError) as e:
            raise LLMError(f"Gemini call failed: {e}") from e

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        text = self._call(system, user, {"temperature": 0, "responseMimeType": "application/json",
                                         "responseSchema": schema})
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"Non-JSON response: {e}") from e

    def generate_text(self, system: str, user: str, temperature: float = 0.2) -> str:
        return self._call(system, user, {"temperature": temperature})


_llm: LLMService | None = None


def get_llm() -> LLMService:
    global _llm
    if _llm is None:
        _llm = LLMService()
    return _llm
