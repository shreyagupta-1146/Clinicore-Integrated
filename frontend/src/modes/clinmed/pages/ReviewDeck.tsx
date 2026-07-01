import { RotateCcw, Clock, Play } from "lucide-react";
import { Link } from "react-router-dom";
import { Pill } from "@/components/ui";

const DUE = [
  { id: "neuro1", title: "Sudden severe headache", why: "Missed: subarachnoid haemorrhage", due: "Due today", specialty: "Neurology" },
  { id: "resp1", title: "Acute breathlessness", why: "Ordered wrong first investigation", due: "Due today", specialty: "Respiratory" },
  { id: "endo1", title: "Weight loss & palpitations", why: "Missed: thyrotoxicosis", due: "In 2 days", specialty: "Endocrine" },
];

export function ReviewDeck() {
  return (
    <div className="soft-card p-6 animate-fade-in">
      <div className="flex items-center gap-2 mb-2">
        <RotateCcw className="w-5 h-5 text-brand" />
        <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Review Deck</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-5">Spaced repetition of cases you missed. Master them before they fade.</p>

      <div className="rounded-2xl p-4 mb-5 flex items-center justify-between" style={{ background: "color-mix(in oklab, var(--brand) 7%, white)" }}>
        <div>
          <div className="text-sm font-semibold">2 cases due today</div>
          <div className="text-xs text-muted-foreground">Reviewing now boosts retention by ~40%.</div>
        </div>
        <Link to="/clinmed/simulator/neuro1" className="px-4 py-2.5 rounded-xl gradient-brand text-white text-sm font-semibold flex items-center gap-1.5"><Play className="w-4 h-4" /> Review now</Link>
      </div>

      <div className="space-y-2.5">
        {DUE.map((c) => (
          <div key={c.id} className="flex items-center gap-3 p-3 rounded-xl border">
            <div className="w-10 h-10 rounded-xl grid place-items-center bg-chip" style={{ color: "var(--brand)" }}><RotateCcw className="w-5 h-5" /></div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">{c.title}</div>
              <div className="text-xs text-muted-foreground">{c.why}</div>
            </div>
            <Pill tone={c.due === "Due today" ? "warn" : "neutral"}>{c.due}</Pill>
            <Link to={`/clinmed/simulator/${c.id}`} className="text-xs font-semibold text-brand flex items-center gap-1"><Play className="w-3.5 h-3.5" /> Redo</Link>
          </div>
        ))}
      </div>
    </div>
  );
}
