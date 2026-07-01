/**
 * lib/vitals.ts
 *
 * Deterministic threshold checks for entered vital data.
 * Two jobs:
 *   1. Flag physiologically IMPLAUSIBLE / exaggerated values (obviously fake input,
 *      data-entry errors, or someone gaming the AI) — these are hard-rejected.
 *   2. Flag ABNORMAL-but-possible values that warrant attention (soft warning).
 *
 * This mirrors the backend safety layer: the frontend should never feed
 * garbage vitals to the AI, and should never let an obviously impossible
 * reading silently personalise advice.
 */

export type VitalLevel = "ok" | "abnormal" | "implausible";

export interface VitalCheck {
  level: VitalLevel;
  message?: string;
}

interface Range {
  // possible-but-abnormal band
  normalLo: number;
  normalHi: number;
  // outside this band = physically implausible / exaggerated → reject
  hardLo: number;
  hardHi: number;
  unit: string;
  label: string;
}

export const VITAL_RANGES: Record<string, Range> = {
  blood_glucose: { normalLo: 70, normalHi: 180, hardLo: 10, hardHi: 1000, unit: "mg/dL", label: "Blood glucose" },
  systolic: { normalLo: 90, normalHi: 140, hardLo: 40, hardHi: 300, unit: "mmHg", label: "Systolic BP" },
  diastolic: { normalLo: 60, normalHi: 90, hardLo: 20, hardHi: 200, unit: "mmHg", label: "Diastolic BP" },
  spo2: { normalLo: 94, normalHi: 100, hardLo: 50, hardHi: 100, unit: "%", label: "SpO₂" },
  heart_rate: { normalLo: 50, normalHi: 110, hardLo: 20, hardHi: 250, unit: "bpm", label: "Heart rate" },
  temperature: { normalLo: 97, normalHi: 99.5, hardLo: 80, hardHi: 115, unit: "°F", label: "Temperature" },
  weight: { normalLo: 3, normalHi: 300, hardLo: 1, hardHi: 500, unit: "kg", label: "Weight" },
  fitbit_steps: { normalLo: 0, normalHi: 40000, hardLo: 0, hardHi: 100000, unit: "steps", label: "Daily steps" },
  fitbit_sleep: { normalLo: 3, normalHi: 12, hardLo: 0, hardHi: 24, unit: "hrs", label: "Sleep" },
};

export function checkVital(key: string, raw: string | number | undefined): VitalCheck {
  if (raw === undefined || raw === "" || raw === null) return { level: "ok" };
  const v = typeof raw === "number" ? raw : parseFloat(raw);
  const r = VITAL_RANGES[key];
  if (!r || Number.isNaN(v)) return { level: "ok" };

  if (v < r.hardLo || v > r.hardHi) {
    return {
      level: "implausible",
      message: `${r.label} of ${v} ${r.unit} is outside the physically possible range (${r.hardLo}–${r.hardHi}). Please re-check — this value won't be sent to the AI.`,
    };
  }
  if (v < r.normalLo || v > r.normalHi) {
    return {
      level: "abnormal",
      message: `${r.label} of ${v} ${r.unit} is outside the typical range (${r.normalLo}–${r.normalHi}). Consider discussing with your doctor.`,
    };
  }
  return { level: "ok" };
}

/** True if any provided value is implausible (used to block save / AI use). */
export function hasImplausible(data: Record<string, string | undefined>): boolean {
  return Object.entries(data).some(([k, v]) => checkVital(k, v).level === "implausible");
}
