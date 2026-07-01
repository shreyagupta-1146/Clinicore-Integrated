# Clinicore Platform — API Keys & Credentials Master List

Every external API / credential the platform uses, **what it's for**, the **env var**,
the **exact file that reads it**, and **where to get it**. Fill the two `.env` files:

- **Frontend:** `frontend/.env`  (copy from `frontend/.env.example`) — only `VITE_*` (public) vars
- **Backend:** `.env`  (copy from `.env.example`) — all secrets live here / in Vault

> Rule of thumb: anything that must stay secret goes in the **backend** `.env` (or Vault).
> The frontend only holds **public** client IDs and the anon/publishable keys.

---

## 1. Core data & auth

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **Supabase URL** | System of record (DB + auth) | `VITE_SUPABASE_URL` | `frontend/src/lib/supabase.ts` | supabase.com → Project Settings → API |
| **Supabase anon key** | Public client key (RLS-protected) | `VITE_SUPABASE_ANON_KEY` | `frontend/src/lib/supabase.ts` | same page (anon/public) |
| **Supabase service key** | Server-side privileged access | `SUPABASE_SERVICE_ROLE_KEY` *(add to backend `.env`)* | backend service layer (add when wiring) | same page (service_role — **secret**) |
| **Postgres** | Primary relational DB | `DATABASE_URL`, `POSTGRES_USER/PASSWORD/DB` | `substrate/db/base.py`, `docker-compose.yml`, `infrastructure/postgres/init.sql` | self-hosted / managed PG |
| **Redis** | Cache, Celery broker, SecOps queue | `REDIS_URL`, `REDIS_PASSWORD`, `RELAYMED_REDIS_URL` | `docker-compose.yml`, `secops/response/handler.py` | self-hosted |

---

## 2. AI / LLM (Grok is the active provider — replaces Google)

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **Grok (xAI)** | Cloud clinical reasoning + chat | `GROK_API_KEY`, `GROK_API_BASE`, `GROK_MODEL`, `GROK_FALLBACK_MODEL` | `substrate/model_gateway/grok_client.py`; selected by `CLOUD_LLM_PROVIDER` | console.x.ai |
| **AI proxy (frontend→backend)** | Keeps the Grok key server-side | `VITE_AI_PROXY_URL` | `frontend/src/lib/pubmed.ts` (TL;DR), chat components | your own backend route `/api/v1/ai/chat` |
| **Anthropic (Claude)** | Optional alternate cloud LLM | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CLAUDE_FALLBACK_MODEL` | `substrate/model_gateway/cloud_client.py` | console.anthropic.com |
| **On-prem vLLM** | Raw-PHI path (never leaves boundary) | `ONPREM_LLM_URL`, `ONPREM_LLM_MODEL`, `ONPREM_LLM_API_KEY` | `substrate/model_gateway/onprem_client.py` | self-hosted vLLM |

> **Note:** the original PRISM self-healing middleware used **Groq (`llama3-70b`)** — if you
> mean Groq (not xAI Grok), point `GROK_API_BASE=https://api.groq.com/openai/v1` and set the model accordingly.

---

## 3. Agentic evidence & learning content (outsourced)

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **PubMed E-utilities** | Referenced cases behind each diagnosis | `VITE_PUBMED_API_KEY` (optional), `PUBMED_EMAIL` | `frontend/src/lib/pubmed.ts`; backend `app/services/rag_service.py` (source) | ncbi.nlm.nih.gov/account (API key optional) |
| **YouTube Data API v3** | Clinmed learning videos & durations | `VITE_YOUTUBE_API_KEY` | `frontend/src/modes/clinmed/pages/Modules.tsx` | console.cloud.google.com → YouTube Data API |
| **Qdrant** | Vector store for RAG semantic search | `QDRANT_URL`, `QDRANT_API_KEY` | `docker-compose.yml`; RAG service | self-hosted / Qdrant Cloud |

---

## 4. OAuth / Sign-in  ⟵ *the space you asked for*

### 4a. Consumer OAuth — RelayMed & Clinmed (via Supabase Auth)
Configure each provider in **Supabase → Authentication → Providers** (Supabase stores the
client *secret*; the frontend only needs the public client ID + redirect URL).

| Provider | Purpose | Env var (frontend) | Read in file | Where to get it |
|---|---|---|---|---|
| **Google** | "Continue with Google" | `VITE_OAUTH_GOOGLE_CLIENT_ID` | `frontend/src/components/ConsumerLogin.tsx` | console.cloud.google.com → OAuth consent + credentials |
| **Apple** | "Continue with Apple" | `VITE_OAUTH_APPLE_CLIENT_ID` | `frontend/src/components/ConsumerLogin.tsx` | developer.apple.com → Sign in with Apple |
| **Phone OTP** | SMS one-time-passcode login | `VITE_OAUTH_ENABLE_PHONE_OTP` | `frontend/src/components/ConsumerLogin.tsx` | Supabase → Auth → Phone (needs an SMS provider e.g. Twilio) |
| **Redirect URL** | OAuth callback target | `VITE_OAUTH_REDIRECT_URL` | `frontend/src/context/AuthContext.tsx` (wire on integration) | your app URL + `/auth/callback` |

> Provider **secrets** (Google client secret, Apple key, Twilio token) are entered in the
> Supabase dashboard, **not** in any file in this repo.

### 4b. Professional OIDC — Clinicore clinicians (via Keycloak)
| Item | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **Keycloak URL / realm** | Clinician identity provider | `VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM` | `frontend/src/modes/clinicore/Login.tsx` (wire on integration) | your Keycloak server |
| **Web client (PKCE)** | Public SPA login client | `VITE_KEYCLOAK_CLIENT_ID` | same | Keycloak realm → Clients → `clinicore-web` |
| **Backend client secret** | Service-to-service token | `KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_CLIENT_ID` | `apps/*/backend/core/config.py`, `infrastructure/keycloak/realm-export.json` | Keycloak realm → Clients → Credentials |
| **Keycloak admin** | Realm bootstrap / session revoke | `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` | `docker-compose.yml`, `secops/response/handler.py` | set at deploy |
| **FIDO2 / passkeys** | Phishing-resistant step-up MFA | `KEYCLOAK_HOSTNAME` (RP ID) | `infrastructure/keycloak/realm-export.json` | configured in realm (no external key) |

---

## 5. India health stack (ABDM / ABHA)

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **ABDM HIE-CM** | Cross-facility federated records | `ABDM_CLIENT_ID`, `ABDM_CLIENT_SECRET`, `ABDM_BASE_URL`, `ABHA_GATEWAY_URL` | `substrate/fhir/abdm_client.py`; `apps/clinicore/backend/api/v1/routes/abdm_callback.py` | sandbox.abdm.gov.in (free), then NHA prod onboarding |

---

## 6. Wearables & health data (RelayMed)

**Two ingestion planes** (see `apps/relaymed/backend/wearables/`):

**Plane A — on-device hubs (NO server key; lives in the mobile app).**
Android **Health Connect** and iOS **Apple HealthKit** are read *inside the mobile
app* via the platform SDK with the user's per-category permission, then POSTed to
`POST /api/v1/vitals/bulk`. There is **no cloud API key** — compliance is the mobile
app's Google Play (Health Connect) / App Store (HealthKit) data-use review.
*(The old `GOOGLE_HEALTH_CONNECT_CLIENT_ID` was conceptually wrong and has been removed.)*

**Plane B — cloud APIs pulled server-side.**

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **Fitbit Web API** | Server-side OAuth pull | `FITBIT_CLIENT_ID`, `FITBIT_CLIENT_SECRET`, `FITBIT_REDIRECT_URI` | `apps/relaymed/backend/wearables/fitbit_client.py`; `.../routes/wearables.py` | dev.fitbit.com (intraday-at-scale needs Fitbit approval) |
| **Aggregator** | One contract → Fitbit/Garmin/Oura/Whoop/… | `WEARABLE_AGGREGATOR_PROVIDER`, `WEARABLE_AGGREGATOR_API_KEY`, `WEARABLE_AGGREGATOR_DEV_ID`, `WEARABLE_AGGREGATOR_WEBHOOK_SECRET` | `apps/relaymed/backend/wearables/aggregator.py`; `.../routes/wearables.py` | Terra / Spike / Rook / Validic |
| **Google Health Connect (Android)** | On-device — no key | — (mobile SDK + Play Console declaration) | mobile app → `POST /vitals/bulk` | developer.android.com/health-and-fitness/guides/health-connect |
| **Apple HealthKit (iOS)** | On-device — no key | — (HealthKit entitlement) | mobile app → `POST /vitals/bulk` | developer.apple.com → HealthKit |

> **Note:** Fitbit does **not** write to Apple HealthKit. iPhone + Fitbit users must use
> the Fitbit Web API path (Plane B); Android + Fitbit users can use Health Connect (Plane A).

---

## 7. Secrets, crypto & audit

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **HashiCorp Vault** | KMS + secrets (AES-256, PQC keys, audit signing key) | `VAULT_URL`, `VAULT_TOKEN`, `VAULT_DEV_TOKEN`, `VAULT_MOUNT_PATH` | `substrate/encryption/vault_client.py`, `infrastructure/vault/policies/clinicore.hcl` | self-hosted Vault |
| **immudb** | Tamper-evident WORM audit ledger | `IMMUDB_HOST/PORT/USER/PASSWORD/DATABASE` | `substrate/audit/chain.py` | self-hosted |
| **App secret keys** | JWT/session signing | `CLINICORE_SECRET_KEY`, `RELAYMED_SECRET_KEY` | `apps/*/backend/core/config.py` | generate (`openssl rand -hex 32`) |
| **MinIO** | Object storage (images, reports) | `MINIO_URL`, `MINIO_ROOT_USER/PASSWORD`, `MINIO_BUCKET_*` | `docker-compose.yml`; storage service | self-hosted / S3-compatible |

---

## 8. Observability & alerting (SecOps / SRE)

| Service | Purpose | Env var | Read in file | Where to get it |
|---|---|---|---|---|
| **OpenSearch** | SIEM telemetry | `OPENSEARCH_URL/USER/PASSWORD` | `docker-compose.yml`; `secops/ueba/analyzer.py` | self-hosted |
| **Prometheus / Grafana** | Metrics + dashboards | `PROMETHEUS_URL`, `GRAFANA_PASSWORD` | `sre/monitoring/prometheus.yml` | self-hosted |
| **PagerDuty** | On-call paging (HITL escalation) | `PAGERDUTY_INTEGRATION_KEY` | `secops/response/handler.py` | pagerduty.com → Integrations |
| **Slack** | SecOps notifications | `SLACK_WEBHOOK_URL` | `secops/response/handler.py` | api.slack.com → Incoming Webhooks |

---

## Minimum set to run a demo
1. `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` (data + auth)
2. `GROK_API_KEY` (+ `VITE_AI_PROXY_URL` route) (AI)
3. One OAuth provider in Supabase (e.g. Google) — or use email/password
4. Everything else has a working local/demo fallback (PubMed runs keyless; Vault/immudb/Keycloak via `docker-compose up`).

## What already works with **no** key
- PubMed agentic references (public E-utilities)
- The whole UI (local-mirror fallback when Supabase isn't set)
- YouTube module **links** (embeds work; the Data API key only adds live metadata)
