/**
 * lib/pii.ts
 *
 * Lightweight client-side PII pre-scan — mirrors the entity types the backend
 * Presidio service redacts (presidio_service.ENTITIES_TO_DETECT). This is a
 * PREVIEW only: it shows the clinician what will be stripped before any text
 * leaves for a cloud model, so there are no surprises. The authoritative
 * redaction still happens server-side with Presidio + spaCy NER.
 */

export interface PiiHit {
  type: string; // PERSON | DATE_TIME | PHONE_NUMBER | EMAIL | ID | MRN | LOCATION
  text: string;
}

const PATTERNS: { type: string; re: RegExp }[] = [
  { type: "EMAIL", re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g },
  { type: "PHONE_NUMBER", re: /\b(?:\+?91[-\s]?)?[6-9]\d{9}\b|\b\d{3}[-\s]\d{3}[-\s]\d{4}\b/g },
  { type: "AADHAAR", re: /\b\d{4}\s?\d{4}\s?\d{4}\b/g },
  { type: "MRN", re: /\b(?:MRN|mrn)[:\s#]*[A-Za-z0-9-]{4,}\b/g },
  { type: "DATE_TIME", re: /\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/g },
  { type: "IP_ADDRESS", re: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g },
  // Person names: "Mr./Mrs./Dr. Xxx" or two consecutive capitalised words
  { type: "PERSON", re: /\b(?:Mr|Mrs|Ms|Dr|Miss)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b/g },
];

export function scanPii(text: string): PiiHit[] {
  if (!text) return [];
  const hits: PiiHit[] = [];
  const seen = new Set<string>();
  for (const { type, re } of PATTERNS) {
    for (const m of text.matchAll(re)) {
      const key = `${type}:${m[0]}`;
      if (!seen.has(key)) {
        seen.add(key);
        hits.push({ type, text: m[0] });
      }
    }
  }
  return hits;
}

/** Replace detected PII with [TYPE] placeholders — same shape as the backend. */
export function redactPreview(text: string): string {
  let out = text;
  for (const { type, re } of PATTERNS) {
    out = out.replace(re, `[${type}]`);
  }
  return out;
}
