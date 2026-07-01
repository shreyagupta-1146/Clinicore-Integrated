/**
 * lib/db.ts
 *
 * Namespaced key-value store. Supabase table `app_kv` is the durable system of
 * record; localStorage is a synchronous cache/mirror so the reactive UI stays
 * instant and works offline. Every write goes to both; on load we hydrate the
 * cache from Supabase.
 *
 *   kvReadCache(ns)      -> sync read of the local mirror (for React snapshots)
 *   kvWrite(ns, data)    -> write cache + upsert to Supabase (best-effort)
 *   kvHydrate(ns)        -> pull latest from Supabase into the cache
 */

import { supabase, currentUserId } from "./supabase";

const cacheKey = (ns: string) => `clinicore.kv.${ns}`;

export function kvReadCache<T>(ns: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(cacheKey(ns));
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export async function kvWrite<T>(ns: string, data: T): Promise<void> {
  // 1. local mirror (sync, instant)
  localStorage.setItem(cacheKey(ns), JSON.stringify(data));
  window.dispatchEvent(new StorageEvent("storage", { key: cacheKey(ns) }));

  // 2. durable store (Supabase, best-effort)
  if (!supabase) return;
  try {
    const uid = await currentUserId();
    await supabase.from("app_kv").upsert(
      { user_id: uid, ns, data, updated_at: new Date().toISOString() },
      { onConflict: "user_id,ns" }
    );
  } catch {
    /* offline / not configured — cache still holds the value */
  }
}

export async function kvHydrate<T>(ns: string, fallback: T): Promise<T> {
  if (!supabase) return kvReadCache(ns, fallback);
  try {
    const uid = await currentUserId();
    const { data, error } = await supabase.from("app_kv").select("data").eq("user_id", uid).eq("ns", ns).maybeSingle();
    if (!error && data?.data !== undefined) {
      localStorage.setItem(cacheKey(ns), JSON.stringify(data.data));
      window.dispatchEvent(new StorageEvent("storage", { key: cacheKey(ns) }));
      return data.data as T;
    }
  } catch {
    /* fall through to cache */
  }
  return kvReadCache(ns, fallback);
}

/** Insert an append-only row (used for the AI feedback queue). */
export async function insertRow(table: string, row: Record<string, unknown>): Promise<void> {
  if (!supabase) return;
  try {
    const uid = await currentUserId();
    await supabase.from(table).insert({ user_id: uid, ...row });
  } catch {
    /* best-effort */
  }
}
