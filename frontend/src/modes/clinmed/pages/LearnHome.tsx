import { Link } from "react-router-dom";
import { Play, Target, Clock, TrendingUp, Brain, ArrowRight, Stethoscope } from "lucide-react";
import { Bar, Pill } from "@/components/ui";

const RECOMMENDED = [
  { id: "resp1", title: "Acute breathlessness in the ED", specialty: "Respiratory", diff: "Resident", acc: 61 },
  { id: "neuro1", title: "Sudden severe headache", specialty: "Neurology", diff: "Attending", acc: 48 },
  { id: "gastro1", title: "Right iliac fossa pain", specialty: "Surgery", diff: "Intern", acc: 72 },
];

export function LearnHome() {
  return (
    <div className="space-y-5">
      {/* Daily case hero */}
      <div className="soft-card p-6 animate-fade-in relative overflow-hidden">
        <div className="absolute -right-8 -top-8 w-40 h-40 rounded-full opacity-10" style={{ background: "var(--brand)" }} />
        <div className="flex flex-col md:flex-row md:items-center gap-5 relative">
          <div className="flex-1">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: "color-mix(in oklab, var(--ochre) 18%, white)", color: "var(--ochre)" }}>Daily Case · +150 XP</span>
            <h2 className="text-2xl font-semibold mt-2" style={{ fontFamily: "var(--font-heading)" }}>Chest pain in a 58-year-old</h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-lg">A timed case in a busy ED. Expect interruptions — a bleep, a nurse, a phone call. Diagnose accurately without losing your train of thought.</p>
            <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> ~8 min</span>
              <span className="flex items-center gap-1"><Target className="w-3.5 h-3.5" /> Cardiology</span>
              <Pill tone="warn">Realistic intensity</Pill>
            </div>
          </div>
          <Link to="/clinmed/simulator/daily" className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl gradient-brand text-white font-semibold shrink-0">
            <Play className="w-5 h-5" /> Start case
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Progress snapshot */}
        <div className="soft-card p-6 animate-fade-in">
          <h3 className="text-base font-semibold mb-4" style={{ fontFamily: "var(--font-heading)" }}>Your edge this week</h3>
          {[
            { l: "Diagnostic accuracy", v: 68, s: "68%", t: "warn" as const },
            { l: "Time-to-diagnosis", v: 74, s: "4m 12s avg", t: "good" as const },
            { l: "Focus under pressure", v: 55, s: "moderate", t: "warn" as const },
          ].map((m) => (
            <div key={m.l} className="mb-3">
              <div className="flex items-center justify-between text-xs mb-1"><span className="text-muted-foreground">{m.l}</span><span className="font-medium">{m.s}</span></div>
              <Bar value={m.v} tone={m.t} />
            </div>
          ))}
          <Link to="/clinmed/progress" className="text-xs font-medium text-brand flex items-center gap-1 mt-2">Full progress <ArrowRight className="w-3.5 h-3.5" /></Link>
        </div>

        {/* Recommended */}
        <div className="lg:col-span-2 soft-card p-6 animate-fade-in">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-4 h-4 text-brand" />
            <h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Recommended for your weak spots</h3>
          </div>
          <div className="space-y-2.5">
            {RECOMMENDED.map((c) => (
              <Link key={c.id} to={`/clinmed/simulator/${c.id}`} className="flex items-center gap-3 p-3 rounded-xl border hover:shadow-sm transition-shadow">
                <div className="w-10 h-10 rounded-xl grid place-items-center bg-chip" style={{ color: "var(--brand)" }}><Stethoscope className="w-5 h-5" /></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{c.title}</div>
                  <div className="text-xs text-muted-foreground">{c.specialty} · {c.diff}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-semibold" style={{ color: c.acc < 60 ? "var(--coral)" : "var(--success)" }}>{c.acc}%</div>
                  <div className="text-[10px] text-muted-foreground">cohort acc.</div>
                </div>
                <TrendingUp className="w-4 h-4 text-muted-foreground" />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
