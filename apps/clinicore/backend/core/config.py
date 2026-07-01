"""
apps/clinicore/backend/core/config.py

Clinicore (B2B) backend settings. Loaded from environment / .env via
pydantic-settings. See .env.example at the repo root for the full variable
reference shared across both apps.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClinicoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field("development", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")

    vault_url: str = Field(..., alias="VAULT_URL")
    vault_token: str = Field(..., alias="VAULT_TOKEN")
    vault_mount_path: str = Field("clinicore", alias="VAULT_MOUNT_PATH")

    keycloak_url: str = Field(..., alias="KEYCLOAK_URL")
    keycloak_realm: str = Field("clinicore", alias="KEYCLOAK_REALM")
    keycloak_clinicore_client_id: str = Field("clinicore-backend", alias="KEYCLOAK_CLINICORE_CLIENT_ID")

    immudb_host: str = Field("immudb", alias="IMMUDB_HOST")
    immudb_port: int = Field(3322, alias="IMMUDB_PORT")

    qdrant_url: str = Field("http://qdrant:6333", alias="QDRANT_URL")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-opus-4-8", alias="CLAUDE_MODEL")
    claude_fallback_model: str = Field("claude-sonnet-4-6", alias="CLAUDE_FALLBACK_MODEL")

    onprem_llm_url: str = Field("http://onprem-llm:8080", alias="ONPREM_LLM_URL")
    onprem_llm_model: str = Field("BioMistral-7B-DARE", alias="ONPREM_LLM_MODEL")

    model_gateway_mode: str = Field("hybrid", alias="MODEL_GATEWAY_MODE")
    phi_risk_threshold: float = Field(0.7, alias="PHI_RISK_THRESHOLD")

    pubmed_email: str = Field(..., alias="PUBMED_EMAIL")
    pubmed_api_key: str | None = Field(None, alias="PUBMED_API_KEY")

    max_messages_per_chat: int = Field(20, alias="MAX_MESSAGES_PER_CHAT")
    max_continuation_depth: int = Field(5, alias="MAX_CONTINUATION_DEPTH")
    audit_log_retention_days: int = Field(2555, alias="AUDIT_LOG_RETENTION_DAYS")  # ~7 years

    fhir_base_url: str = Field("http://fhir-server:8103/fhir", alias="FHIR_BASE_URL")
    fhir_auth_token: str = Field("", alias="FHIR_AUTH_TOKEN")

    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> ClinicoreSettings:
    return ClinicoreSettings()
