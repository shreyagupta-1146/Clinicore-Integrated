"""
substrate/model_gateway/grok_client.py

Cloud LLM client for Grok (xAI). This is the platform's ACTIVE cloud provider,
replacing the Google/Gemini path which proved unreliable.

xAI exposes an OpenAI-compatible API (/v1/chat/completions), so this client
mirrors the on-prem vLLM client's shape and returns the same LLMResponse.

IMPORTANT: as with any cloud LLM, only de-identified text may reach this client.
The ModelGateway enforces that — do not instantiate GrokClient directly from
application code.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import httpx

from substrate.model_gateway.cloud_client import LLMResponse  # reuse dataclass

logger = logging.getLogger(__name__)


class GrokClient:
    def __init__(
        self,
        api_key: str,
        model: str = "grok-4",
        api_base: str = "https://api.x.ai/v1",
        fallback_model: str = "grok-3-mini",
    ):
        self.model = model
        self._fallback_model = fallback_model
        self._base = api_base.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._timeout = httpx.Timeout(90.0)

    async def complete(
        self,
        system_prompt: str,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history or [])
        messages.append({"role": "user", "content": user_text})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base}/chat/completions", json=payload, headers=self._headers)
            if resp.status_code >= 500:
                # transient upstream error — retry once on the smaller/faster model
                logger.warning("grok_5xx status=%s falling back to %s", resp.status_code, self._fallback_model)
                payload["model"] = self._fallback_model
                resp = await client.post(f"{self._base}/chat/completions", json=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{self._base}/models", headers=self._headers)
                return resp.status_code == 200
        except Exception as exc:
            logger.warning("grok_health_check failed error=%s", exc)
            return False
