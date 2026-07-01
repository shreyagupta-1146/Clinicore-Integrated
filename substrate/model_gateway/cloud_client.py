"""
platform/model_gateway/cloud_client.py

Cloud LLM client (Anthropic Claude).

IMPORTANT: Only de-identified text must reach this client.
The ModelGateway enforces this; do NOT instantiate CloudLLMClient directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Optional

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int


class CloudLLMClient:
    def __init__(self, api_key: str, model: str = "claude-opus-4-8"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_text})

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            temperature=temperature,
        )

        return LLMResponse(
            content=response.content[0].text,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

    async def stream(
        self,
        system_prompt: str,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> AsyncIterator[str]:
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_text})

        async with self._client.messages.stream(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            temperature=0.3,
        ) as stream:
            async for text in stream.text_stream:
                yield text
