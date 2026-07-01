# Clinicore Platform — Frontend

A single React app with a **pre-login mode selector** leading to three visually
distinct, fully-built experiences. Each mode reuses RelayMed's original design
DNA (soft cards, gradient backgrounds, animated pathways) but with its own theme,
navigation, and audience.

## Run it

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # production build (tsc + vite) — passes clean
```

## The three modes

| Route | Mode | Vibe | Auth |
|-------|------|------|------|
| `/` | **Mode selector** | neutral premium; ambient bg shifts on hover | — |
| `/relaymed` | **RelayMed** — personal/wellness | sage green, Fraunces serif (ported from original RelayMed) | consumer (email / Google / OTP) |
| `/clinicore` | **Clinicore** — professional/clinical | white + clinical blue, navy sidebar, Inter | institutional 3-step + FIDO2 passkey, role chips |
| `/clinmed` | **Clinmed** — educational | white + beige academic, Lora serif | student / educator |

Any mode's "Switch mode" (sidebar/settings) returns to the selector. Auth is
mock — any credentials work; state persists in localStorage.

## What's built (real, interactive pages — not stubs)

**RelayMed** (13 pages): Dashboard (vitals, med checklist, adherence ring, caregiver strip),
My Health (metric chart + anomaly banner + log sheet), Health Insights, Causal Pathways
(the signature animated Health Journey), What-If Simulator (live counterfactual),
Health Alerts, Relay Guide (AI chat), **Caregiver Hub** (patient/caregiver dual view with
DPDP consent approve/decline/revoke), Health Library, Trust Center, Settings.

**Clinicore** (8 screens): institutional login (facility → credentials → passkey),
Dashboard (KPIs, consult queue, red-flag alerts), Patient Roster (table), **Consultation
Workspace** (FHIR timeline + AI CDS with differential diagnoses, evidence levels,
diagnostic gaps, citations, de-id/routing badge, red-flag banner), Consent Management,
Audit Trail (hash-chain verified), ABDM Exchange, Admin & SecOps (HITL incident queue,
model-gateway toggle, system health).

**Clinmed** (7 screens): Learn Home (daily case, weak-spot recs), Case Library (filterable),
**Diagnosis Simulator** — the signature immersive experience: intensity picker
(Calm / Realistic / Chaotic), live countdown + cognitive-load meter, 5-stage reasoning
(history→exam→investigations→differential→diagnosis), and the **distraction/interruption
engine** (randomised pager bleeps with WebAudio, nurse, phone-call, second-patient overlays
that cost time and raise load; mutable for accessibility) → rich debrief (accuracy,
time-to-diagnosis, focus score, reasoning path, teaching points). Plus Progress (radar +
trends), Leaderboard, Review Deck (spaced repetition), Authoring (educator).

## Design system

`src/index.css` defines three `data-theme` token scopes. `ThemeScope` sets the theme on
`<html>` so the fixed gradient background switches per mode. Shared primitives live in
`src/components/` (ui.tsx, PageShell, Sparkline, ConsumerLogin). Each mode is self-contained
under `src/modes/<mode>/`.

## Wiring to the backend

Mock data is inline for preview. To connect: point RelayMed calls at `:8001`, Clinicore at
`:8000` (see `apps/*/backend`). The Clinmed `edu` API is mock-only until that service exists.

> Not affiliated with Lovable — this is a hand-built, self-contained Vite app.
