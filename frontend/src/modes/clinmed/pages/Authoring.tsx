import { PenSquare, Plus, Users, BarChart3, Radio } from "lucide-react";
import { Pill } from "@/components/ui";

export function Authoring() {
  return (
    <div className="space-y-5">
      <div className="soft-card p-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PenSquare className="w-5 h-5 text-brand" />
            <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Case Authoring</h2>
          </div>
          <button className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl gradient-brand text-white text-sm font-semibold"><Plus className="w-4 h-4" /> New case</button>
        </div>
        <p className="text-sm text-muted-foreground mt-1">Build vignettes, set the correct reasoning path, add teaching points, and configure the interruption script.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="soft-card p-6 animate-fade-in">
          <h3 className="text-base font-semibold mb-3" style={{ fontFamily: "var(--font-heading)" }}>Your cases</h3>
          <div className="space-y-2.5">
            {[
              { t: "Chest pain, 58M diabetic", status: "Published", tone: "good" as const, attempts: 214 },
              { t: "Paediatric fever pathway", status: "Draft", tone: "warn" as const, attempts: 0 },
              { t: "Acute abdomen triage", status: "Published", tone: "good" as const, attempts: 98 },
            ].map((c) => (
              <div key={c.t} className="flex items-center gap-3 p-3 rounded-xl border">
                <div className="flex-1">
                  <div className="text-sm font-medium">{c.t}</div>
                  <div className="text-xs text-muted-foreground">{c.attempts} attempts</div>
                </div>
                <Pill tone={c.tone}>{c.status}</Pill>
              </div>
            ))}
          </div>
        </div>

        <div className="soft-card p-6 animate-fade-in">
          <h3 className="text-base font-semibold mb-3" style={{ fontFamily: "var(--font-heading)" }}>Interruption script builder</h3>
          <p className="text-xs text-muted-foreground mb-3">Configure what interrupts learners and when — this is what makes Clinmed realistic.</p>
          <div className="space-y-2.5">
            {[
              { i: Radio, l: "Pager: hypotensive patient", at: "at 0:45" },
              { i: Users, l: "Nurse: sign discharge chart", at: "at 1:30" },
              { i: Radio, l: "Second patient deteriorating", at: "at 2:10" },
            ].map((s) => {
              const Icon = s.i;
              return (
                <div key={s.l} className="flex items-center gap-3 p-3 rounded-xl border">
                  <div className="w-9 h-9 rounded-lg grid place-items-center bg-chip" style={{ color: "var(--brand)" }}><Icon className="w-4 h-4" /></div>
                  <div className="flex-1 text-sm">{s.l}</div>
                  <span className="text-xs text-muted-foreground font-mono">{s.at}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="soft-card p-6 animate-fade-in">
        <div className="flex items-center gap-2 mb-4"><BarChart3 className="w-5 h-5 text-brand" /><h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Cohort analytics</h3></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { l: "Active learners", v: "48" },
            { l: "Avg accuracy", v: "67%" },
            { l: "Weakest topic", v: "Neuro" },
            { l: "Cases assigned", v: "12" },
          ].map((m) => (
            <div key={m.l} className="rounded-xl border p-4 text-center">
              <div className="text-2xl font-bold" style={{ fontFamily: "var(--font-heading)", color: "var(--brand)" }}>{m.v}</div>
              <div className="text-[11px] text-muted-foreground mt-1">{m.l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
