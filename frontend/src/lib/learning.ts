/**
 * lib/learning.ts
 *
 * Learning-progress tracking for Clinmed modules & videos.
 * Durable in Supabase (app_kv ns='learning'); mirrored locally for instant UI.
 *
 * Privacy-first: tracking is OPT-IN. When off, no progress is stored or read,
 * and any existing progress is cleared from both Supabase and the cache.
 */

import { useSyncExternalStore } from "react";
import { kvReadCache, kvWrite, kvHydrate } from "./db";

const NS = "learning";
interface LearningState {
  tracking: boolean;
  progress: Record<string, number>; // moduleId -> percent
}
const DEFAULT: LearningState = { tracking: true, progress: {} };

function read(): LearningState {
  return kvReadCache<LearningState>(NS, DEFAULT);
}

export function isTrackingEnabled(): boolean {
  return read().tracking;
}

export function setTrackingEnabled(on: boolean) {
  const cur = read();
  kvWrite(NS, { tracking: on, progress: on ? cur.progress : {} });
}

export function getProgress(id: string): number {
  const s = read();
  return s.tracking ? (s.progress[id] ?? 0) : 0;
}

export function setProgress(id: string, pct: number) {
  const cur = read();
  if (!cur.tracking) return; // no-op when tracking off
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  kvWrite(NS, { ...cur, progress: { ...cur.progress, [id]: clamped } });
}

export function advanceProgress(id: string, by = 25) {
  setProgress(id, getProgress(id) + by);
}

/** Pull latest from Supabase into the cache (call on page mount). */
export function hydrateLearning() {
  kvHydrate<LearningState>(NS, DEFAULT);
}

// ── reactive hook ────────────────────────────────────────────────────────────
const cacheKey = `clinicore.kv.${NS}`;
function subscribe(cb: () => void) {
  const h = (e: StorageEvent) => { if (!e.key || e.key === cacheKey) cb(); };
  window.addEventListener("storage", h);
  return () => window.removeEventListener("storage", h);
}
function snapshot() { return localStorage.getItem(cacheKey) ?? ""; }

export function useLearningState() {
  useSyncExternalStore(subscribe, snapshot, () => "");
  return read();
}
