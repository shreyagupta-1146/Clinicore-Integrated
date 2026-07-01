/**
 * lib/prefs.ts
 *
 * Transparent, per-category data-sharing preferences + a permissions log.
 * The AI layer reads these before using any personal data — when a category
 * is off, the AI must not use it (generic guidance instead of personalised).
 */

import { useSyncExternalStore } from "react";

export interface SharingPrefs {
  master: boolean;
  vitals: boolean;
  activity: boolean;
  history: boolean;
  docs: boolean;
  clinician: boolean;
}

const DEFAULTS: SharingPrefs = {
  master: true,
  vitals: true,
  activity: true,
  history: false,
  docs: false,
  clinician: false,
};

const KEY = "relaymed.sharing";
const listeners = new Set<() => void>();

export function getPrefs(): SharingPrefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULTS;
}

export function setPref(key: keyof SharingPrefs, value: boolean) {
  const next = { ...getPrefs(), [key]: value };
  localStorage.setItem(KEY, JSON.stringify(next));
  listeners.forEach((l) => l());
}

/** AI may use category X only if the master switch AND that category are on. */
export function canUse(category: keyof Omit<SharingPrefs, "master">): boolean {
  const p = getPrefs();
  return p.master && p[category];
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

// snapshot = the raw JSON string, so React knows when it changed
function getSnapshot(): string {
  return localStorage.getItem(KEY) ?? "";
}

/** React hook — re-renders when any sharing pref changes. */
export function useSharingPrefs(): SharingPrefs {
  useSyncExternalStore(subscribe, getSnapshot, () => "");
  return getPrefs();
}
