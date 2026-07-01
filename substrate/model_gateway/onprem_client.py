"""
platform/model_gateway/onprem_client.py

On-premises LLM client (vLLM with OpenAI-compatible API).

Used for raw-PHI paths — anything with PHI risk score >= threshold.
The model runs locally; no data leaves the network boundary.

Recommended models (all open-weight, available via Hugging Face):
  - Meditron-70B          (EPFL, strong on clinical benchmarks)
  - BioMistral-7B-DARE    (lighter, good for resource-constrained deployments)
  - OpenBioLLM-70B        (Saama, strong reasoning)
  - MedGemma-27B          (Google, 2025, multimodal)

Run with: vllm serve <model-id> --port 8080 --dtype bfloat16 --tensor-parallel-size <n_gpus>

Quality caveat (stated explicitly):
  Every medical-LLM benchmark is self-reported and not clinical validation.
  Treat leaderboard numbers as indicative, not authoritative.
  The only number that matters is your own eval harness result on your own
  clinician-labelled gold set (see ai_services/eval_harness/).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from substrate.model_gateway.cloud_client import LLMResponse   # reuse the same dataclass

logger = logging.getLogger(__name__)


class OnPremLLMClient:
    """
    OpenAI-compatible client for a locally-hosted vLLM instance.
    vLLM exposes /v1/chat/completions — same API surface as OpenAI.
    """

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._timeout = httpx.Timeout(120.0)   # longer timeout for on-prem inference

    async def complete(
        self,
        system_prompt: str,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
    ) -> LLMResponse:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history or [])

        if image_base64 and image_mime_type:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"},
                    },
                    {"type": "text", "text": user_text},
                ],
            })
        else:
            messages.append({"role": "user", "content": user_text})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def health_check(self) -> bool:
        """Return True if the vLLM server is reachable and serving the expected model."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{self._base_url}/v1/models", headers=self._headers)
                resp.raise_for_status()
                models = [m["id"] for m in resp.json().get("data", [])]
                return self.model in models
        except Exception as exc:
            logger.warning("onprem_health_check failed error=%s", exc)
            return False
