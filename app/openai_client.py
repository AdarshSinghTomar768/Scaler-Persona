from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)


class OpenAIClient:
    def __init__(self) -> None:
        provider = (LLM_PROVIDER or "openai").strip().lower()
        if provider == "groq":
            self.provider = "groq"
            self.api_key = GROQ_API_KEY
            self.base_url = GROQ_BASE_URL
            self.model = GROQ_MODEL
        elif provider == "openrouter":
            self.provider = "openrouter"
            self.api_key = OPENROUTER_API_KEY
            self.base_url = OPENROUTER_BASE_URL
            self.model = OPENROUTER_MODEL
        else:
            self.provider = "openai"
            self.api_key = OPENAI_API_KEY
            self.base_url = OPENAI_BASE_URL
            self.model = OPENAI_MODEL
        self.enabled = bool(self.api_key)

    def answer(self, system_prompt: str, messages: list[dict]) -> str:
        if not self.enabled:
            raise RuntimeError(f"{self.provider.upper()} API key is not configured.")

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": self._build_messages(system_prompt, messages),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://scaler-persona.vercel.app"
            headers["X-Title"] = "scaler-persona"

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"{self.provider.capitalize()} API request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{self.provider.capitalize()} API request failed: {exc.reason}") from exc

        return data["choices"][0]["message"]["content"].strip()

    def _build_messages(self, system_prompt: str, messages: list[dict]) -> list[dict]:
        if self.provider != "openrouter":
            return [{"role": "system", "content": system_prompt}, *messages]

        flattened = list(messages)
        instruction = f"Follow these instructions exactly:\n{system_prompt}"
        if flattened and flattened[0].get("role") == "user":
            flattened[0] = {
                "role": "user",
                "content": f"{instruction}\n\nUser request:\n{flattened[0].get('content', '')}",
            }
            return flattened

        return [{"role": "user", "content": instruction}, *flattened]
