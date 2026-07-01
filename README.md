# Clinicore-Integrated

> **One secure, sovereign, consent-and-audit health-data platform.**
> Two apps (Clinicore B2B + RelayMed B2C). One shared substrate. Two internal security layers.

---

## What this is

This is an enterprise-grade healthcare data platform built for the Indian market,
integrating four prior projects into a single coherent system:

| Layer | Source | Role |
|---|---|---|
| **Clinicore** (B2B app) | clinicore-backend | Clinical decision support for doctors, medical students, emergency centres |
| **RelayMed** (B2C app) | Relay-med | Longitudinal wellness monitoring, chronic-condition management, caregiver loop |
| **SentiHealth** (SecOps) | SentiHealth project | Internal SIEM/UEBA — threat detection on platform telemetry |
| **weave-heal** (SRE) | weave-heal-main | GitOps self-healing control plane + SOC console |

The four are **not four products**. They are one platform with two user-facing apps and two
internal operational layers.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  APPS / UX                                                           │
│   Clinicore (B2B)  ·  RelayMed (B2C)  ·  SOC/ops console (internal) │
├────────────────────────────────────────────────────────────────────┤
│  AI SERVICES                                                         │
│   Clinical reasoning  ·  RAG (Qdrant+PubMed)  ·  Longitudinal       │
│   Model Gateway (de-id → cloud frontier ↔ raw PHI → on-prem)        │
│   Eval + guardrail harness  ·  Bias auditor                          │
├────────────────────────────────────────────────────────────────────┤
│  PLATFORM SUBSTRATE  (built once, used by both apps)                │
│   Identity/RBAC/step-up (Keycloak + FIDO2)                          │
│   Consent ledger (DPDP Act 2023 aligned)                            │
│   PHI vault + de-identification (Presidio)                          │
│   Encryption + KMS (HashiCorp Vault, hybrid PQC for long-lived data)│
│   Immutable audit (SHA-256 hash-chain + immudb WORM)                │
│   FHIR R4 timeline  ·  ABHA/ABDM linkage                           │
├────────────────────────────────────────────────────────────────────┤
│  SECOPS / SRE  (internal — NOT sold separately)                     │
│   SentiHealth → real SIEM/UEBA on platform telemetry (Wazuh+Falco) │
│   weave-heal  → GitOps (Argo CD/Rollouts) + SOC console             │
└────────────────────────────────────────────────────────────────────┘
```

### Hybrid Sovereignty Model

PHI **never** crosses the network boundary to a cloud provider.
Only Presidio-de-identified text is routed to the cloud frontier model (Claude).
Raw PHI stays on-prem and is served by a locally-hosted open medical LLM (vLLM).

```
Raw PHI  ──► PHI Vault ──► Presidio de-id ──► Policy engine
                                                    │
                          de-identified ────────────┤──► Cloud LLM (Claude, ZDR contract)
                          raw PHI / high-risk ──────┘──► On-prem LLM (vLLM)
```

---

## Regulatory context (India-first)

| Regulation | How we comply |
|---|---|
| DPDP Act 2023 | Purpose-bound, revocable, time-boxed consent ledger; data-principal rights; breach notification hooks |
| ABDM/ABHA | FHIR R4 timeline; ABHA health-ID linkage; federated consent via HIE-CM |
| CDSCO SaMD | **Get a regulatory opinion on Clinicore before shipping to patients** — device classification gates the roadmap |
| Telemedicine Practice Guidelines 2020 | Clinician-in-loop; AI augments, never replaces; patient must be identifiable professional |

---

## Quick start

```bash
# 1. Copy and fill environment file
cp .env.example .env

# 2. Start infrastructure
docker compose up -d postgres redis qdrant minio keycloak vault immudb opensearch

# 3. Start application backends
docker compose up -d clinicore-backend relaymed-backend celery-worker

# 4. View dashboards
#    Clinicore API:  http://localhost:8000/docs
#    RelayMed API:   http://localhost:8001/docs
#    Keycloak:       http://localhost:8080
#    Vault:          http://localhost:8200
#    Grafana:        http://localhost:3000
```

---

## Directory structure

```
Clinicore-Integrated/
├── substrate/               # Shared substrate (consumed by both apps)
│   ├── consent/            # DPDP-aligned consent ledger
│   ├── audit/              # Immutable hash-chain audit log
│   ├── encryption/         # Vault KMS + AES-256-GCM + hybrid PQC
│   ├── phi_vault/          # PHI storage + Presidio de-identification
│   ├── fhir/               # FHIR R4 models + ABHA linkage
│   └── model_gateway/      # Cloud/on-prem AI routing by data class
├── ai_services/            # AI layer (shared)
│   ├── guardrails/         # Deterministic safety + escalation layer
│   ├── eval_harness/       # Clinical evaluation + red-team framework
│   ├── clinical_reasoning/ # Clinicore AI pipeline (migrated + improved)
│   └── longitudinal/       # RelayMed baseline anomaly + TDEE what-if
├── apps/
│   ├── clinicore/backend/  # B2B FastAPI (migrated from clinicore-backend)
│   └── relaymed/backend/   # B2C FastAPI (migrated from Relay-med)
│       └── modules/caregiver/  # NEW: caregiver delegation + adherence
├── secops/                 # Internal SecOps layer (from SentiHealth)
│   ├── ueba/               # Real UEBA on platform telemetry
│   ├── detection/          # Wazuh/Falco integration configs
│   └── response/           # Human-in-loop tiered response (HITL pattern)
├── sre/                    # Internal SRE layer (from weave-heal)
│   ├── k8s/                # Kubernetes manifests (Kustomize)
│   ├── gitops/             # Argo CD application configs
│   ├── monitoring/         # Prometheus + Grafana
│   └── console/            # SOC/ops console (React, from weave-heal UI)
└── infrastructure/
    ├── keycloak/           # Realm export + FIDO2 config
    ├── postgres/           # Init SQL (schemas, pgcrypto)
    ├── vault/              # Vault policies + PKI setup
    └── ci/                 # GitHub Actions workflows
```
