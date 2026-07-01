# Clinicore Platform — Lovable Frontend Prompt (3 Modes)

> Paste the block below into Lovable. It builds ONE app with a pre-login **mode
> selector** leading to three visually distinct experiences: **Clinicore**
> (professional/clinical, admin auth), **RelayMed** (personal/wellness, user auth),
> and **Clinmed** (educational/training simulator, user auth). Grounded in the real
> backends in this repo and the original RelayMed frontend design system.

---

## THE PROMPT

Build **Clinicore** — a unified health-tech platform for India with **three distinct modes** the user chooses before logging in. Each mode is a fully separate experience with its own visual identity, navigation, and audience, but they share one codebase, one auth system, and one design-token architecture. Quality bar for all three: polished, detailed, beautifully animated, production-grade — no placeholder screens.

Tech: **React + TypeScript + Vite + Tailwind + shadcn/ui + lucide-react + recharts + TanStack Router + TanStack Query**. Fully responsive (sidebar on desktop, bottom-tab/drawer on mobile), accessible (labels, focus rings, contrast, `prefers-reduced-motion` respected), with elegant skeleton loaders and empty states in each mode's theme. Wire all data through a typed TanStack Query API client with rich realistic mock fallbacks so every screen looks alive in preview.

---

### 0) PRE-LOGIN — MODE SELECTOR (the first thing the user sees)

A serene full-screen landing with the platform wordmark "Clinicore" and the tagline "One platform. Three ways to care." Present **three large mode cards** side-by-side (stacked on mobile), each with its own preview thumbnail, icon, distinct accent color, a one-line description, and a "Continue" button. Hovering a card subtly shifts the page's ambient background toward that mode's palette (a lovely touch). The three cards:

1. **Clinicore — Professional** (clinical blue). "Clinical decision support for licensed clinicians & facilities." → leads to **institutional/admin login**.
2. **RelayMed — Personal** (sage green). "Track your health, medications & share with caregivers." → leads to **normal user login/signup**.
3. **Clinmed — Learn** (warm beige/amber). "Sharpen diagnostic skill with realistic case simulations." → leads to **normal user login/signup**.

Selecting a mode stores the choice (route + context) and routes to that mode's auth screen. A small "Switch mode" control is always available in each mode's profile menu to return here.

---

### 1) AUTH (two different flavors)

**RelayMed & Clinmed → consumer auth:** friendly email + password, plus social sign-in (Google, Apple, phone-OTP). Calm multi-step signup. Clinmed signup additionally asks: role (Medical student / Resident / Practicing doctor / Educator), specialty interest, and training level.

**Clinicore → institutional/admin auth:** a distinctly more serious, secure login. Steps: (1) select Facility/Hospital (searchable), (2) clinician credentials (email + password), (3) **step-up MFA / passkey (FIDO2/WebAuthn)** screen with a "phishing-resistant sign-in" note. Show a role chip after login: **Clinician**, **Facility Admin**, or **Platform Admin** — the admin roles unlock extra nav (user management, audit, facility settings). Prominent security/compliance strip: "DPDP Act 2023 · ABDM-ready · encrypted · audited."

---

### 2) MODE A — RelayMed (PERSONAL / WELLNESS)  ← reuse the existing RelayMed design exactly

Recreate the existing RelayMed app faithfully. **Design system:**

- **Palette (CSS vars, keep exact):** primary sage `oklch(0.62 0.12 160)`; mint `oklch(0.94 0.04 165)`; ocean `oklch(0.66 0.11 230)`; coral `oklch(0.72 0.16 30)`; sand `oklch(0.92 0.04 80)`; success `oklch(0.66 0.15 155)`; warning `oklch(0.78 0.14 70)`; destructive `oklch(0.68 0.18 25)`. Radius 1.25rem.
- **Background:** fixed radial mint bloom (top-left) + ocean bloom (top-right) over a near-white mint gradient.
- **Fonts:** `Fraunces` (serif) for headings, `Plus Jakarta Sans` for body; tight heading letter-spacing.
- **Utilities:** `.soft-card` (1.5rem radius, faint sage border, soft shadow), `.glass-card` (88% white + 10px backdrop blur), `.neu-btn` (neumorphic), `.gradient-sage`. Animations: `fade-in` (fade-up on load), `float` (gentle bob on hero emoji/elements), `pulse-ring` (live indicators), and flowing dashed SVG pathway lines.
- **Shell:** 260px sticky left **Sidebar** with sage logo tile "Relay-med / Your AI Health Companion", nav list, an "Upgrade to Pro" mint card, and a profile row with online dot + logout. Top **header** with a time-based greeting ("Good morning, {name} 🌿"), "Sync Devices" button (opens a device-sync modal), a notifications bell with unread badge (opens a severity-colored dropdown: high=coral, medium=amber, low=mint), and an avatar menu. A slim **SecurityFooter** on every page ("Your data is encrypted and never sold. DPDP Act 2023 compliant.").

**RelayMed pages (build all):**

1. **Dashboard** — greeting; row of **vital stat cards** (Heart Rate, Blood Pressure, SpO₂, Blood Glucose) each with latest value, unit, sparkline, tone dot; **Today's Medications** checklist with tap-to-mark (taken/skipped/snooze) + weekly adherence ring; the signature **"Your Health Journey"** hero (see Causal Pathways); a **caregiver presence** strip ("Shared with: Priya (daughter)").
2. **My Health** — full vitals hub: metric selector chips (HR, BP, SpO₂, Glucose, Weight, Temperature), large area trend chart (sage gradient fill) over 7d/30d/90d, "Log a reading" sheet (value, unit, source: Manual/Fitbit/Health Connect/Omron), and calm **anomaly banners** with plain-language guidance; critical values show "This may need urgent attention — call 112 / contact your doctor" (never drug dosing).
3. **Health Insights** — grid of AI-derived pattern cards (trend up / watch / tip), each icon-chip + title + friendly explanation, tone-colored.
4. **Causal Pathways** — the **Health Journey** visualization: three columns *Your Habits & Inputs → Key Health Factors → Future Outcomes*, node icon-chips with trust-score %, connected by animated dashed bezier curves (sage = positive influence, coral dashed = negative), a legend, plus Root Cause / Counterfactual / Filter summary cards. Make it gorgeous.
5. **What-If Simulator** — counterfactual sliders (walk min/day, extra sleep h, reduce stress %, weight loss kg) driving a live "predicted cardiovascular improvement (6 months) +X%" with a smooth line chart.
6. **Health Alerts** — notification center list with severity styling and read/dismiss.
7. **Relay Guide** — a calm AI health-companion **chat** (conversation summary widget + message thread + composer); reassuring, jargon-free; safety rules enforced (emergencies → 112, no specific drug dosing).
8. **Wellness Reports** — generated weekly/monthly report cards with download.
9. **Health Library** — searchable, friendly educational articles (cards by topic).
10. **Caregiver Hub** — **as patient:** "People who help me" (approved caregivers + exactly which categories they see: vitals/medications/lifestyle/conditions), **pending requests** to Approve/Decline, revoke toggle with confirm — framed as empowering, "You're in control." **As caregiver:** "People I care for" (linked-patient cards: last vitals, weekly adherence, anomaly flags) + "Request to monitor" flow (patient ID/ABHA + choose categories + message; patient must approve first).
11. **Caregiver Patient Detail** — reassuring overview honoring consent: only granted categories render (rest greyed "Not shared"); vitals tiles, adherence ring, plain-language **longitudinal trend** summary + overall "improving / stable / deteriorating" chip.
12. **Trust Center** — AES-256 encryption, immutable audit trail, zero data selling, role-based access cards.
13. **Settings** — profile, connected devices/wearables, notification prefs, consent management, ABHA linking (14-digit), language.

**RelayMed data endpoints** (base `/api/v1`, RelayMed backend :8001): `POST/GET /vitals`, `GET /vitals/{metric}`, `GET /medications`, `POST /medications/log`, `GET /medications/adherence`, `POST /wellness/log`, `GET /wellness/summary`, `POST /caregiver/request`, `POST /caregiver/{link_id}/approve|decline`, `GET /caregiver/my-links`, `GET /caregiver/pending-requests`, `GET /caregiver/{patient_id}/dashboard`.

---

### 3) MODE B — Clinicore (PROFESSIONAL / CLINICAL)  ← white + blue, same detail & polish as RelayMed

A crisp, trustworthy clinical workspace for doctors. Keep RelayMed's *level of craft and animation*, but a completely different, professional identity.

- **Palette:** clean **white** and cool-gray surfaces; primary **clinical blue** `oklch(0.55 0.14 245)`; deep navy `oklch(0.32 0.06 250)` for headers/rails; cyan/teal `oklch(0.68 0.11 220)` for data viz; amber `oklch(0.78 0.14 70)` for cautions; red `oklch(0.6 0.2 27)` for critical/red-flags; success green for normals. Tighter radius (~0.75rem), crisp low-spread shadows, thin precise borders. Denser, data-forward layout.
- **Fonts:** `Inter` (or `IBM Plex Sans`) throughout — precise, medical, highly legible; use weight and a subtle blue for hierarchy instead of serif flourish.
- **Shell:** slim dark-navy **icon+label sidebar**; top command bar with global patient search, facility name, role chip, MFA/session status, and a **de-identification / routing indicator** (a small badge showing whether the current AI request is running **On-Prem (raw PHI)** or **Cloud (de-identified)** — this is a signature trust feature). Every page footer: compliance + "All access is audit-logged."

**Clinicore pages (build all):**

1. **Clinician Dashboard** — today's patient panel, pending consults, red-flag alerts queue, recent activity, small KPIs (consults today, avg response, open escalations). Calm but information-dense cards.
2. **Patient Roster** — searchable/filterable table of patients (name masked until opened, ABHA id, age/sex, chronic problems, last seen, consent status pill). Row → consultation workspace.
3. **Consultation Workspace** (the core) — split view: left = **patient FHIR timeline** (vitals, medications, conditions, care plans, prior notes, and ABDM cross-facility records with a "fetched via ABDM — query not copy" badge); right = **AI Clinical Decision Support chat**. The AI panel shows: the de-identification indicator, streaming answers, and structured outputs — **Differential Diagnoses** (each with likelihood + **evidence level**: RCT / meta-analysis / cohort / guideline), **Diagnostic Gaps** (missing info + impact), and **cited research** (PubMed references, expandable). A persistent disclaimer: "Decision support only — final judgment rests with the clinician." Deterministic **red-flag banners** surface emergency features. Message/continuation limits respected.
4. **Diagnostic Insights** — differential explorer and evidence viewer with citation cards and confidence bars.
5. **Consent Management** — grant/verify/revoke patient consent (purpose-bound, category-bound, time-boxed per DPDP); sensitive-category (mental health/genetic) explicit-flag UI; delegated/caregiver consent visibility.
6. **Audit Trail** — immutable, hash-chained access log viewer: filter by actor/patient/time; each entry shows event type, actor, resource, and a "cryptographically verified ✓" indicator. Read-only, tamper-evident framing.
7. **ABDM / Health Records Exchange** — initiate federated record requests via ABHA + consent artefact; show pending/received bundles ("PHI stays at source facility").
8. **Admin (Facility Admin / Platform Admin only)** — clinician onboarding & roles, facility settings, SecOps overview (security incidents queue with severity + HITL "acknowledge" — no auto-enforcement), model-gateway mode (hybrid/cloud/on-prem) and thresholds, system health (Prometheus-style KPIs).
9. **Profile & Security** — sessions, passkeys/MFA devices, sign-out everywhere, switch mode.

**Clinicore data endpoints** (Clinicore backend :8000): `/api/v1/consultations…`, `/api/v1/consent…`, `/api/v1/health`, `/api/v1/abdm/callback`, plus admin/audit/secops views (mock where backend is internal). Model-routing and grounding metadata come back on AI responses (route: cloud|onprem, grounding_score, phi_risk_score) — surface them.

---

### 4) MODE C — Clinmed (EDUCATIONAL / DIAGNOSTIC TRAINING SIMULATOR)  ← white + beige academic, same detail & polish as RelayMed

A gamified medical-education app that trains **diagnostic reasoning under realistic clinical pressure**. This is the most novel mode — invest in the case-simulation experience.

- **Palette:** warm **white + beige/cream** surfaces (`oklch(0.97 0.02 85)` background, `oklch(0.99 0.005 85)` cards); ink/charcoal text `oklch(0.28 0.02 60)`; scholarly primary **deep teal** `oklch(0.5 0.09 200)`; warm **amber/ochre** accent `oklch(0.75 0.13 70)`; terracotta `oklch(0.62 0.14 40)` for "incorrect/urgent"; muted olive/green for "correct". Radius ~1rem. Paper-like subtle texture, refined shadows — a premium textbook-meets-app feel.
- **Fonts:** a refined serif — `Lora` or `Spectral` — for headings (academic tone), `Inter` for body. Numeric/score displays feel like a scoreboard.
- **Shell:** left sidebar with Clinmed logo; nav to Learn Home, Case Library, Simulator, Progress, Leaderboard, Review Deck, (Educator) Authoring. Top bar shows **XP / level**, current **streak 🔥**, and a "Daily Case" call-to-action.

**Clinmed pages (build all):**

1. **Learn Home** — greeting, "Daily Case" hero, streak & XP progress, recommended cases by weakness, recent scores, quick "Start a timed case" button.
2. **Case Library** — browse/filter clinical cases by **specialty, system, difficulty (Intern→Attending), and mode (Practice / Timed / Exam)**. Case cards show tags, difficulty, avg diagnostic accuracy, and completion state. Includes **OSCE-style stations** and full **case studies/vignettes**.
3. **Diagnosis Simulator** (the core, signature experience) — a step-through clinical case:
   - **Stages:** Presenting complaint → History taking (pick questions, spend virtual time) → Examination (select maneuvers, reveal findings) → Investigations (order tests, cost/time tradeoffs) → **Differential** (rank hypotheses) → **Final Diagnosis** (MCQ + free-text) → Management plan.
   - **Pressure mechanics:** a visible **countdown timer** and a **"cognitive load" meter**. Time and load affect the final score.
   - **★ Realistic distraction & interruption engine (must-have):** while answering, simulate a real ward. Toggleable **ambient noise** (ward/ED background audio). Randomized **interruptions** pop up mid-task and must be triaged/dismissed: e.g. a **pager/bleep** overlay ("Bleep: Bed 7 hypotensive — respond / defer"), a **nurse interruption** ("Nurse: sign this chart"), a **phone call** modal, an **overlapping second patient** nudge. Each interruption steals time, raises cognitive load, and (if mishandled) costs points — training focus under real conditions. Let users set intensity (Calm / Realistic / Chaotic) and mute audio for accessibility (respect `prefers-reduced-motion`; provide visual-only equivalents).
   - **Feedback:** on submit, a rich **debrief** — correct diagnosis, your path vs. optimal path, time-to-diagnosis, accuracy, distraction-handling score, and **teaching points with evidence/citations**. Offer "add missed case to Review Deck."
4. **Progress** — dashboards: accuracy over time, by specialty/system (radar), time-to-diagnosis trend, cognitive-load resilience, XP/level curve, badges.
5. **Leaderboard** — global/cohort/friends rankings (accuracy, speed, streaks); gamified but tasteful.
6. **Review Deck** — spaced-repetition of missed/flagged cases; "due today" queue.
7. **Educator / Authoring** (educator role) — create/edit cases: build the vignette, stage data, correct differential + diagnosis, teaching points & citations, set difficulty, and configure interruption scripts. Assign cases to a cohort and view cohort analytics.
8. **Profile** — role, specialty, level, achievements, switch mode.

**Clinmed data:** mock a `/api/v1/edu/*` API (cases, attempts, scores, leaderboard, review-deck) with generated content so it's fully interactive in preview. Keep clinical content clearly labeled "For education only — not for real patient care."

---

### 5) GLOBAL / SHARED

- One design-token file with three theme scopes (`.theme-relaymed`, `.theme-clinicore`, `.theme-clinmed`) toggled by the active mode; shadcn components adapt via CSS vars so each mode feels native.
- Smooth mode transitions; the chosen mode persists across reloads; "Switch mode" returns to the selector.
- Consistent, delightful loading/empty/error states per theme. Reusable `PageShell` (icon-chip + title + subtitle + content + footer) adapted per mode.
- Copy tone: RelayMed = warm & reassuring; Clinicore = precise & professional; Clinmed = encouraging & academic.
- Safety everywhere: RelayMed/Clinmed public content shows emergencies → **112 (India)** and never gives specific drug-dosing; Clinicore keeps the "decision support only" disclaimer.

Deliver a polished, multi-theme, fully navigable app where all three modes feel like distinct, finished products sharing one elegant foundation.

---

*End of prompt.*

## Notes for you (not for Lovable)

- **RelayMed** design tokens, utilities (`soft-card`/`glass-card`/`neu-btn`/`gradient-sage`), the Sidebar/AppLayout shell, and the full page list (Dashboard, My Health, Insights, Causal Pathways, Simulator, Alerts, Relay Guide, Reports, Library, Trust Center, Settings) are taken directly from the existing `RelayMed/Relay-med/relay-med-frontend` so the rebuild matches what you already had, plus the new Caregiver Hub wired to the integrated backend.
- **Clinicore** screens map to the real `apps/clinicore/backend` + `substrate` features you built: consultations with hybrid cloud/on-prem routing + de-identification indicator, differential diagnoses with evidence levels and diagnostic gaps (from `clinicore-backend/app/schemas/ai.py`), PubMed-cited research, DPDP consent, hash-chained audit trail, and ABDM federated exchange.
- **Clinmed** is the educational mode you described (quiz-style diagnosis, case studies, realistic noise/interruptions during answering). It's new — mock its API; keep it labeled education-only.
- After generation: point RelayMed API base at `:8001`, Clinicore at `:8000`; Clinmed runs on mock data until you build an `edu` service.
