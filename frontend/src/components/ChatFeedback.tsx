import { useState } from "react";
import { ThumbsUp, ThumbsDown, Check } from "lucide-react";
import { submitFeedback, Rating } from "@/lib/feedback";
import { Mode } from "@/context/AuthContext";

const DOWN_REASONS = ["Inaccurate", "Not helpful", "Unsafe advice", "Too generic", "Missed my data"];

/**
 * Thumbs up/down feedback control shown under every AI answer.
 * A down-vote asks for a quick reason. Feedback is queued for model adaptation.
 */
export function ChatFeedback({ mode, question, answer }: { mode: Mode; question?: string; answer?: string }) {
  const [rated, setRated] = useState<Rating | null>(null);
  const [askReason, setAskReason] = useState(false);
  const [done, setDone] = useState(false);

  const rate = (r: Rating) => {
    setRated(r);
    if (r === "up") {
      submitFeedback({ mode, rating: "up", question, answerSnippet: answer?.slice(0, 200) });
      setDone(true);
    } else {
      setAskReason(true);
    }
  };

  const sendReason = (reason: string) => {
    submitFeedback({ mode, rating: "down", reason, question, answerSnippet: answer?.slice(0, 200) });
    setAskReason(false);
    setDone(true);
  };

  if (done) {
    return (
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-1.5">
        <Check className="w-3 h-3" style={{ color: "var(--success)" }} /> Thanks — this helps the AI improve.
      </div>
    );
  }

  return (
    <div className="mt-1.5">
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-muted-foreground">Was this helpful?</span>
        <button onClick={() => rate("up")} aria-label="Helpful"
          className="w-6 h-6 grid place-items-center rounded-md hover:bg-black/5 transition-colors"
          style={{ color: rated === "up" ? "var(--success)" : "var(--muted-foreground)" }}>
          <ThumbsUp className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => rate("down")} aria-label="Not helpful"
          className="w-6 h-6 grid place-items-center rounded-md hover:bg-black/5 transition-colors"
          style={{ color: rated === "down" ? "var(--coral)" : "var(--muted-foreground)" }}>
          <ThumbsDown className="w-3.5 h-3.5" />
        </button>
      </div>
      {askReason && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {DOWN_REASONS.map((r) => (
            <button key={r} onClick={() => sendReason(r)}
              className="text-[11px] px-2.5 py-1 rounded-full border hover:bg-black/[0.03] transition-colors">
              {r}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
