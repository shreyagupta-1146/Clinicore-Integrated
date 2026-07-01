"""
platform/model_gateway/policies.py

Routing policies for the model gateway.

Three modes:
  hybrid     — route by PHI risk (recommended)
  cloud_only — everything goes to cloud (requires ZDR contract + no raw PHI ever)
  onprem_only — everything stays local (maximum sovereignty; needs on-prem GPU)
"""

from __future__ import annotations

from substrate.phi_vault.deidentification import DeidentificationResult
from substrate.model_gateway.router import Route


class GatewayPolicy:
    def __init__(self, mode: str = "hybrid", phi_risk_threshold: float = 0.7):
        if mode not in ("hybrid", "cloud_only", "onprem_only"):
            raise ValueError(f"Unknown gateway mode: {mode!r}")
        self._mode = mode
        self._threshold = phi_risk_threshold

    def decide(self, deid: DeidentificationResult, force_onprem: bool = False) -> Route:
        if force_onprem:
            return Route.ONPREM
        if self._mode == "onprem_only":
            return Route.ONPREM
        if self._mode == "cloud_only":
            return Route.CLOUD
        # hybrid: route by risk score
        return Route.CLOUD if deid.residual_risk_score < self._threshold else Route.ONPREM
