from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import TypeVar

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

from ragchatbot.config import AppConfig, load_config

T = TypeVar("T", bound=BaseModel)

_PROVIDER_ENV = {
    "groq": ("GROQ_API_KEY", "GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    "cerebras": ("CEREBRAS_API_KEY", "CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
}


class LLMClient:
    def __init__(self, config: AppConfig | None = None) -> None:
        load_dotenv()
        self.config = config or load_config()
        self._last_call_at = 0.0
        self.config.llm.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _mock_enabled(self) -> bool:
        if os.getenv("RAGCHATBOT_MOCK_LLM", "").lower() in {"1", "true", "yes"}:
            return True
        for provider in [self.config.llm.primary_provider] + self.config.llm.fallback_providers:
            key_name = _PROVIDER_ENV.get(provider, ("", "", ""))[0]
            if key_name and os.getenv(key_name):
                return False
        return True

    def _cache_key(self, messages: list[dict[str, str]], model: str) -> str:
        payload = json.dumps({"model": model, "messages": messages}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _read_cache(self, key: str) -> str | None:
        path = self.config.llm.cache_path
        if not path.exists():
            return None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("key") == key:
                return row.get("content")
        return None

    def _write_cache(self, key: str, content: str) -> None:
        path = self.config.llm.cache_path
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "content": content}) + "\n")

    def _throttle(self) -> None:
        rpm = max(self.config.llm.requests_per_minute, 1)
        min_interval = 60.0 / rpm
        elapsed = time.time() - self._last_call_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_call_at = time.time()

    def _providers(self) -> list[str]:
        ordered = [self.config.llm.primary_provider] + list(self.config.llm.fallback_providers)
        seen: set[str] = set()
        result: list[str] = []
        for p in ordered:
            if p not in seen:
                seen.add(p)
                result.append(p)
        return result

    def complete_text(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        model = model or self.config.llm.default_model
        cache_key = self._cache_key(messages, model)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        if self._mock_enabled():
            content = self._mock_response(messages)
            self._write_cache(cache_key, content)
            return content

        last_error: Exception | None = None
        for provider in self._providers():
            key_name, base_env, default_base = _PROVIDER_ENV.get(provider, ("", "", ""))
            api_key = os.getenv(key_name, "")
            if not api_key:
                continue
            base_url = os.getenv(base_env, default_base)
            try:
                self._throttle()
                content = self._chat_completion(base_url, api_key, model, messages)
                self._write_cache(cache_key, content)
                return content
            except Exception as exc:  # noqa: BLE001 — try fallbacks
                last_error = exc
                continue
        raise RuntimeError(f"All LLM providers failed: {last_error}")

    def complete_json(self, messages: list[dict[str, str]], schema: type[T], model_name: str | None = None) -> T:
        text = self.complete_text(messages, model=model_name)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(text[start : end + 1])
            else:
                raise
        return schema.model_validate(data)

    def _chat_completion(self, base_url: str, api_key: str, model: str, messages: list[dict[str, str]]) -> str:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {
            "model": model,
            "messages": messages,
            "temperature": self.config.llm.temperature,
            "max_tokens": self.config.llm.max_tokens,
        }
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, headers=headers, json=body)
                    resp.raise_for_status()
                    payload = resp.json()
                    return payload["choices"][0]["message"]["content"]
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("unreachable")

    def _mock_response(self, messages: list[dict[str, str]]) -> str:
        joined = "\n".join(m["content"] for m in messages).lower()
        if "structured" in joined or '"summary"' in joined:
            return json.dumps(
                {
                    "summary": "POS register offline; telemetry shows recent heartbeat loss. Follow active POS offline runbook.",
                    "recommended_runbook_id": "rb-pos-offline",
                    "escalate": False,
                    "regional_incident": False,
                }
            )
        return (
            "Recommended: verify telemetry, restart POS service remotely, run test authorization, "
            "escalate to Network Operations if still offline."
        )
