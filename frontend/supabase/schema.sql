-- frontend/supabase/schema.sql
--
-- Run in the Supabase SQL editor to provision the platform's data model.
-- All tables are owner-scoped via Row Level Security: a user can only read
-- and write their own rows. Supabase Auth provides auth.uid().

-- ── Generic per-user KV (sharing prefs, health data, learning progress) ──────
create table if not exists public.app_kv (
  user_id     uuid not null references auth.users(id) on delete cascade,
  ns          text not null,                 -- namespace: 'sharing' | 'health' | 'learning' | ...
  data        jsonb not null default '{}',
  updated_at  timestamptz not null default now(),
  primary key (user_id, ns)
);

alter table public.app_kv enable row level security;

create policy "kv_select_own" on public.app_kv for select using (auth.uid() = user_id);
create policy "kv_insert_own" on public.app_kv for insert with check (auth.uid() = user_id);
create policy "kv_update_own" on public.app_kv for update using (auth.uid() = user_id);

-- ── AI feedback queue (append-only; drives model adaptation) ─────────────────
create table if not exists public.ai_feedback (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  mode          text not null,               -- relaymed | clinicore | clinmed
  rating        text not null,               -- up | down
  reason        text,
  question      text,
  answer_snippet text,
  created_at    timestamptz not null default now()
);

alter table public.ai_feedback enable row level security;
create policy "fb_select_own" on public.ai_feedback for select using (auth.uid() = user_id);
create policy "fb_insert_own" on public.ai_feedback for insert with check (auth.uid() = user_id);

-- ── Learning progress (Clinmed modules & videos) ────────────────────────────
create table if not exists public.learning_progress (
  user_id     uuid not null references auth.users(id) on delete cascade,
  module_id   text not null,
  percent     int not null default 0 check (percent between 0 and 100),
  updated_at  timestamptz not null default now(),
  primary key (user_id, module_id)
);

alter table public.learning_progress enable row level security;
create policy "lp_all_own" on public.learning_progress
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ── Clinician consultation references (audit of agentic PubMed lookups) ──────
create table if not exists public.consult_references (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  consultation_id text,
  pmid          text,
  title         text,
  url           text,
  created_at    timestamptz not null default now()
);

alter table public.consult_references enable row level security;
create policy "cr_all_own" on public.consult_references
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
