/**
 * lib/supabase.ts
 *
 * Single Supabase client for the whole platform. Supabase is the system of
 * record for ALL user data (auth, learning progress, AI feedback, sharing
 * prefs, health data). A thin localStorage cache mirrors it only for instant
 * UI and offline resilience — the durable copy always lives in Supabase.
 *
 * Configure with (frontend/.env):
 *   VITE_SUPABASE_URL=https://<project>.supabase.co
 *   VITE_SUPABASE_ANON_KEY=<anon key>
 *
 * When these are absent (e.g. local preview before a project is provisioned)
 * the client is null and the data layer falls back to the local cache so the
 * app still runs. See supabase/schema.sql for the tables + RLS policies.
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isSupabaseConfigured = Boolean(url && anonKey);

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(url!, anonKey!, {
      auth: { persistSession: true, autoRefreshToken: true },
    })
  : null;

/** Resolve the current user id (Supabase auth uid, or a stable anon device id). */
export async function currentUserId(): Promise<string> {
  if (supabase) {
    const { data } = await supabase.auth.getUser();
    if (data.user) return data.user.id;
  }
  // anonymous fallback id (device-scoped)
  let id = localStorage.getItem("clinicore.anonId");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("clinicore.anonId", id);
  }
  return id;
}
