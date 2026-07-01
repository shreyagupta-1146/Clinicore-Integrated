"""
apps/relaymed/backend/core/config.py

RelayMed settings — pydantic-settings reads from environment / .env file.
Shares Vault, immudb, DB, and Redis with Clinicore (same infra layer),
but has its own FHIR URL and notification credentials.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RelayMedSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Core ──────────────────────────────────────────────────────────────────
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(...)

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://:changeme@redis:6379/0")

    # ── Vault ─────────────────────────────────────────────────────────────────
    vault_url: str = Field(default="http://vault:8200")
    vault_token: str = Field(...)
    vault_mount_path: str = Field(default="clinicore")

    # ── immudb (shared audit chain) ───────────────────────────────────────────
    immudb_host: str = Field(default="immudb")
    immudb_port: int = Field(default=3322)

    # ── Keycloak ──────────────────────────────────────────────────────────────
    keycloak_url: str = Field(default="http://keycloak:8080")
    keycloak_realm: str = Field(default="clinicore")
    keycloak_client_id: str = Field(default="relaymed-backend")
    keycloak_client_secret: str = Field(...)

    # ── FHIR ──────────────────────────────────────────────────────────────────
    fhir_base_url: str = Field(default="http://hapi-fhir:8080/fhir")

    # ── Notifications (Expo push for mobile, no Telegram) ────────────────────
    expo_access_token: str = Field(default="")

    # ── Wearable data ingestion ───────────────────────────────────────────────
    # Two ingestion planes (see apps/relaymed/backend/wearables/):
    #
    #   Plane A — ON-DEVICE hubs (Android Health Connect, iOS Apple HealthKit).
    #     Read INSIDE the mobile app via the platform SDK with the user's
    #     per-category permission, then POSTed to /api/v1/vitals/bulk.
    #     >>> There is NO server API key for these. <<< Compliance is the mobile
    #     app's Play Console (Health Connect) / App Store (HealthKit) review.
    #
    #   Plane B — CLOUD APIs pulled server-side (Fitbit Web API, or a
    #     multi-device aggregator like Terra / Spike / Rook / Validic).
    #
    # Fitbit Web API (server-to-server OAuth 2.0)
    fitbit_client_id: str = Field(default="")
    fitbit_client_secret: str = Field(default="")
    fitbit_redirect_uri: str = Field(default="https://api.relaymed.in/api/v1/wearables/fitbit/callback")

    # Multi-device aggregator (one contract → Fitbit, Garmin, Oura, Whoop, …)
    wearable_aggregator_provider: str = Field(default="none")  # none | terra | spike | rook | validic
    wearable_aggregator_api_key: str = Field(default="")
    wearable_aggregator_dev_id: str = Field(default="")
    wearable_aggregator_webhook_secret: str = Field(default="")  # verifies inbound webhook signatures

    # ── Model gateway (de-identified nudges only) ─────────────────────────────
    anthropic_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-opus-4-8")
    claude_fallback_model: str = Field(default="claude-sonnet-4-6")
    onprem_llm_url: str = Field(default="http://vllm:8080")
    onprem_llm_model: str = Field(default="BioMistral-7B-DARE")
    phi_risk_threshold: float = Field(default=0.7)
    model_gateway_mode: str = Field(default="hybrid")

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_allowed_origins: List[str] = Field(default=["http://localhost:3000"])


@lru_cache()
def get_settings() -> RelayMedSettings:
    return RelayMedSettings()
