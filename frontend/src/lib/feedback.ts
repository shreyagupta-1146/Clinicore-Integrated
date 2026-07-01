/**
 * lib/feedback.ts
 *
 * AI feedback queue. Every AI response can be rated 👍/👎 with an optional
 * reason. Feedback is queued (here: localStorage; in production: POSTed to the
 * model-ops service) and used to:
 *   - flag low-quality / unsafe answers for human review
 *   - build a preference dataset for fine-tuning / RLHF
 *   - measure per-topic accuracy over time
 *
 * This is the adaptation loop the platform needs to actually get more accurate.
 */

import { insertRow } from "./db";

export type Rating = "up" | "down";

export interface FeedbackItem {
  id: string;
  mode: "relaymed" | "clinicore" | "clinmed";
  rating: Rating;
  reason?: string;
  question?: string;
  answerSnippet?: string;
  ts: number;
}

const KEY = "clinicore.feedbackQueue";

export function getQueue(): FeedbackItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function submitFeedback(item: Omit<FeedbackItem, "id" | "ts">): FeedbackItem {
  const full: FeedbackItem = { ...item, id: crypto.randomUUID(), ts: Date.now() };
  // local mirror (instant, offline-safe)
  const q = getQueue();
  q.push(full);
  localStorage.setItem(KEY, JSON.stringify(q));
  // durable: append to Supabase ai_feedback (system of record for adaptation)
  insertRow("ai_feedback", {
    mode: full.mode,
    rating: full.rating,
    reason: full.reason ?? null,
    question: full.question ?? null,
    answer_snippet: full.answerSnippet ?? null,
  });
  return full;
}

export function queueStats(): { total: number; up: number; down: number } {
  const q = getQueue();
  return { total: q.length, up: q.filter((f) => f.rating === "up").length, down: q.filter((f) => f.rating === "down").length };
}
