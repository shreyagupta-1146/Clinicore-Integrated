"""
platform/model_gateway/router.py

ModelGateway — the hybrid sovereignty AI router.

Every AI inference call in the platform goes through this gateway.
The gateway decides, based on PHI risk classification, whether to:
  (a) Send de-identified text to the cloud frontier model (Claude)
  (b) Send raw content to the on-prem model (vLLM + open medical model)

This is the concrete implementation of the "hybrid" sovereignty model.

Design principles:
  1. No raw PHI ever reaches the cloud path — the de-identification pipeline
     is mandatory, not optional, for the cloud route.
  2. The cloud route requires a signed Zero-Data-Retention (ZDR) contract.
     This is an operational requirement, not enforced in code. The comment
     below is the technical reminder to verify this before production.
  3. The gateway is transparent to app code — apps call gateway.complete()
     and get a response; they don't know or care which backend served it.
  4. Fallback: if the primary backend fails, fall back to the other.
  5. All routing decisions are logged for auditing and cost tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Dict, List, Optional

from substrate.model_gateway.cloud_client import CloudLLMClient
from substrate.model_gateway.onprem_client import OnPremLLMClient
from substrate.model_gateway.policies import GatewayPolicy
from substrate.phi_vault.deidentification import DeidentificationResult, DeidentificationService

logger = logging.getLogger(__name__)

# ── OPERATIONAL REQUIREMENT ────────────────────────────────────────────────────
# Before ANY clinical text is sent to the cloud LLM:
#   1. Verify a Zero-Data-Retention (ZDR) agreement is signed with Anthropic.
#   2. Verify no-training agreement covers your specific use case.
#   3. Confirm data residency requirements under DPDP Act 2023.
# Anthropic's default commercial API does NOT train on input by default,
# but you should sign an explicit agreement and verify with your legal team.
# ──────────────────────────────────────────────────────────────────────────────

class Route(str, Enum):
    CLOUD = "cloud"       # De-identified text → Claude
    ONPREM = "on_prem"    # Raw PHI → local vLLM


@dataclass
class GatewayResponse:
    content: str
    route_used: Route
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    phi_risk_score: float
    routing_reason: str


class ModelGateway:
    """
    Singleton. Initialise once at app startup via ModelGateway.create().
    """

    def __init__(
        self,
        cloud_client: CloudLLMClient,
        onprem_client: OnPremLLMClient,
        deidentifier: DeidentificationService,
        policy: GatewayPolicy,
    ):
        self._cloud = cloud_client
        self._onprem = onprem_client
        self._deidentifier = deidentifier
        self._policy = policy

    @classmethod
    def create(
        cls,
        anthropic_api_key: str,
        cloud_model: str,
        onprem_url: str,
        onprem_model: str,
        phi_risk_threshold: float = 0.7,
        gateway_mode: str = "hybrid",
    ) -> "ModelGateway":
        cloud = CloudLLMClient(api_key=anthropic_api_key, model=cloud_model)
        onprem = OnPremLLMClient(base_url=onprem_url, model=onprem_model)
        deidentifier = DeidentificationService(phi_risk_threshold=phi_risk_threshold)
        policy = GatewayPolicy(mode=gateway_mode, phi_risk_threshold=phi_risk_threshold)
        return cls(cloud, onprem, deidentifier, policy)

    async def complete(
        self,
        system_prompt: str,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        force_onprem: bool = False,
    ) -> GatewayResponse:
        """
        Route a completion request to the appropriate backend.

        Args:
            system_prompt: The system/persona prompt (not de-identified — must be static)
            user_text: The user message, potentially containing PHI
            conversation_history: Prior turns
            image_base64: Optional image (always routed on-prem)
            force_onprem: Override routing to always use on-prem (e.g., for genetic data)

        Returns:
            GatewayResponse with the completion and routing metadata
        """
        t0 = time.monotonic()

        # Images always go to on-prem (can contain identifiable information in DICOM/pixels)
        if image_base64:
            force_onprem = True

        # De-identify the user text
        deid: DeidentificationResult = await asyncio.get_event_loop().run_in_executor(
            None, self._deidentifier.deidentify, user_text
        )

        route = self._policy.decide(deid, force_onprem=force_onprem)
        text_to_send = deid.anonymised_text if route == Route.CLOUD else user_text

        logger.info(
            "gateway_route route=%s phi_risk=%.2f model=%s",
            route.value,
            deid.residual_risk_score,
            self._cloud.model if route == Route.CLOUD else self._onprem.model,
        )

        response, model_used = await self._dispatch(
            route=route,
            system_prompt=system_prompt,
            user_text=text_to_send,
            conversation_history=conversation_history,
            image_base64=image_base64 if route == Route.ONPREM else None,
            image_mime_type=image_mime_type if route == Route.ONPREM else None,
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        return GatewayResponse(
            content=response.content,
            route_used=route,
            model_used=model_used,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=elapsed_ms,
            phi_risk_score=deid.residual_risk_score,
            routing_reason=(
                "forced_onprem" if force_onprem
                else ("cloud_safe" if route == Route.CLOUD else f"phi_risk={deid.residual_risk_score:.2f}")
            ),
        )

    async def stream(
        self,
        system_prompt: str,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> AsyncIterator[str]:
        """
        Streaming variant. Always cloud route (streaming on-prem is TODO).
        Only call this when you've already verified safe-for-cloud classification.
        """
        deid = await asyncio.get_event_loop().run_in_executor(
            None, self._deidentifier.deidentify, user_text
        )
        route = self._policy.decide(deid)

        if route == Route.ONPREM:
            raise OnPremStreamingNotSupportedError(
                "Streaming is only available for cloud-routed completions. "
                "This request was classified as requiring on-prem routing "
                f"(phi_risk={deid.residual_risk_score:.2f})."
            )

        async for token in self._cloud.stream(
            system_prompt=system_prompt,
            user_text=deid.anonymised_text,
            conversation_history=conversation_history,
        ):
            yield token

    async def onprem_health_check(self) -> bool:
        """Expose on-prem backend reachability for readiness probes."""
        return await self._onprem.health_check()

    async def _dispatch(self, route: Route, **kwargs):
        if route == Route.CLOUD:
            try:
                resp = await self._cloud.complete(**{
                    k: v for k, v in kwargs.items()
                    if k in ("system_prompt", "user_text", "conversation_history")
                })
                return resp, self._cloud.model
            except Exception as exc:
                logger.warning("cloud_llm_failure error=%s → falling back to on-prem", exc)
                resp = await self._onprem.complete(**kwargs)
                return resp, self._onprem.model
        else:
            try:
                resp = await self._onprem.complete(**kwargs)
                return resp, self._onprem.model
            except Exception as exc:
                logger.warning("onprem_llm_failure error=%s → falling back to cloud", exc)
                # Only fall back to cloud if PHI risk is safe enough
                raise OnPremFailedError(
                    f"On-prem LLM failed and cloud fallback not permitted for "
                    f"this data class: {exc}"
                ) from exc


class OnPremStreamingNotSupportedError(Exception):
    pass

class OnPremFailedError(Exception):
    pass
