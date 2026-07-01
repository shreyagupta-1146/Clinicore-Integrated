import { useState } from "react";
import { ShieldAlert, Server, Cloud, Activity, Check, Cpu, Lock, RefreshCw, Beaker, Ban } from "lucide-react";
import { ClinHeader } from "../ClinHeader";
import { Pill, Bar } from "@/components/ui";

const INCIDENTS = [
  { id: "i1", title: "Mass PHI record access (112 in 10 min)", rule: "DLP_001", sev: "High", actor: "dr.verma@apollo.in", tone: "bad" as const, features: ["records_per_min", "off_baseline_ratio", "bulk_export_flag"] },
  { id: "i2", title: "Off-hours PHI access spike", rule: "TEMPORAL_001", sev: "Medium", actor: "nurse.rao@apollo.in", tone: "warn" as const, features: ["hour_of_day", "access_count_1h", "role_expected_hours"] },
  { id: "i3", title: "Audit chain write latency elevated", rule: "AUDIT_002", sev: "Low", actor: "system", tone: "neutral" as const, features: ["immudb_write_ms", "queue_depth", "cpu_load"] },
];

// Retraining feedback queue — deception-oracle labels + poisoning quarantine
const RETRAIN = [
  { id: "sess_9f2a1c", tier: "High", source: "mirage_oracle", why: "Decoy-confirmed attack (canary DB-7731). Ground truth.", confirmed: true, quarantined: false },
  { id: "sess_44b0e2", tier: "Medium", source: "analyst", why: "Analyst-labelled brute-force attempt.", confirmed: false, quarantined: false },
  { id: "sess_71cc03", tier: "Low", source: "analyst", why: "Batch would drop High-tier fraction 41%→9% — possible label poisoning.", confirmed: false, quarantined: true },
];

export function Admin() {
  const [acked, setAcked] = useState<string[]>([]);
  const [mode, setMode] = useState<"hybrid" | "cloud" | "onprem">("hybrid");
  const [approved, setApproved] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div>
      <ClinHeader icon={ShieldAlert} title="Admin & SecOps" subtitle="Security incidents, model gateway & system health" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* SecOps incidents */}
        <div className="lg:col-span-2 soft-card p-5 animate-fade-in">
          <h3 className="text-sm font-semibold mb-3">Security incidents — human-in-the-loop queue</h3>
          <div className="space-y-2.5">
            {INCIDENTS.map((inc) => {
              const done = acked.includes(inc.id);
              return (
                <div key={inc.id} className="p-3 rounded-lg border" style={{ opacity: done ? 0.55 : 1 }}>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg grid place-items-center shrink-0" style={{ background: "color-mix(in oklab, var(--destructive) 8%, white)", color: "var(--destructive)" }}><ShieldAlert className="w-4 h-4" /></div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{inc.title}</div>
                      <div className="text-[11px] text-muted-foreground font-mono">{inc.rule} · {inc.actor}</div>
                    </div>
                    <Pill tone={inc.tone}>{inc.sev}</Pill>
                    {done ? (
                      <span className="text-xs font-medium flex items-center gap-1" style={{ color: "var(--success)" }}><Check className="w-4 h-4" /> Ack'd</span>
                    ) : (
                      <button onClick={() => setAcked((a) => [...a, inc.id])} className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white" style={{ background: "var(--brand)" }}>Acknowledge</button>
                    )}
                  </div>
                  {/* SHAP-style explainability: why the model flagged this */}
                  <div className="flex items-center gap-1.5 mt-2 pl-12 flex-wrap">
                    <span className="text-[10px] text-muted-foreground">Top factors:</span>
                    {inc.features.map((f) => (
                      <span key={f} className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ background: "color-mix(in oklab, var(--brand) 8%, white)", color: "var(--brand)" }}>{f}</span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-muted-foreground mt-3">No enforcement fires automatically. Analysts confirm every containment action, which is itself audit-logged.</p>
        </div>

        {/* Model gateway + health */}
        <div className="space-y-5">
          <div className="soft-card p-5 animate-fade-in">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Cpu className="w-4 h-4 text-brand" /> Model Gateway</h3>
            <div className="space-y-2">
              {([
                { k: "hybrid", label: "Hybrid", icon: Activity, desc: "Route by PHI risk" },
                { k: "cloud", label: "Cloud only", icon: Cloud, desc: "De-identified only" },
                { k: "onprem", label: "On-prem only", icon: Server, desc: "Never leaves boundary" },
              ] as const).map((m) => {
                const Icon = m.icon;
                const on = mode === m.k;
                return (
                  <button key={m.k} onClick={() => setMode(m.k)} className="w-full flex items-center gap-3 p-2.5 rounded-lg border text-left transition-all"
                    style={on ? { borderColor: "var(--brand)", background: "color-mix(in oklab, var(--brand) 6%, white)" } : { borderColor: "var(--border)" }}>
                    <Icon className="w-4 h-4" style={{ color: on ? "var(--brand)" : "var(--muted-foreground)" }} />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{m.label}</div>
                      <div className="text-[10px] text-muted-foreground">{m.desc}</div>
                    </div>
                    {on && <Check className="w-4 h-4 text-brand" />}
                  </button>
                );
              })}
            </div>
            <div className="mt-3 text-[11px] text-muted-foreground">PHI risk threshold: <span className="font-mono">0.70</span></div>
          </div>

          <div className="soft-card p-5 animate-fade-in">
            <h3 className="text-sm font-semibold mb-3">System health</h3>
            {[
              { l: "API latency (p99)", v: 88, t: "good" as const, s: "180ms" },
              { l: "On-prem vLLM load", v: 62, t: "warn" as const, s: "62%" },
              { l: "Audit chain writes", v: 99, t: "good" as const, s: "healthy" },
            ].map((h) => (
              <div key={h.l} className="mb-3">
                <div className="flex items-center justify-between text-xs mb-1"><span className="text-muted-foreground">{h.l}</span><span className="font-medium">{h.s}</span></div>
                <Bar value={h.v} tone={h.t} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Model adaptation + privacy */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-5">
        {/* Retraining feedback loop with poisoning quarantine */}
        <div className="lg:col-span-2 soft-card p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold flex items-center gap-2"><RefreshCw className="w-4 h-4 text-brand" /> Detection retraining queue</h3>
            <span className="text-[11px] text-muted-foreground">Self-improving · human-in-the-loop</span>
          </div>
          <p className="text-[11px] text-muted-foreground mb-3">Confirmed labels feed model retraining. Decoy-oracle labels are ground truth; suspicious batches are quarantined as possible poisoning.</p>
          <div className="space-y-2">
            {RETRAIN.map((r) => {
              const ok = r.confirmed || approved.includes(r.id);
              return (
                <div key={r.id} className="p-3 rounded-lg border" style={r.quarantined ? { background: "color-mix(in oklab, var(--destructive) 6%, white)", borderColor: "color-mix(in oklab, var(--destructive) 30%, transparent)" } : {}}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono">{r.id}</span>
                    <Pill tone={r.tier === "High" ? "bad" : r.tier === "Medium" ? "warn" : "neutral"}>{r.tier}</Pill>
                    {r.source === "mirage_oracle" && <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "color-mix(in oklab, var(--teal) 16%, white)", color: "color-mix(in oklab, var(--teal) 60%, black)" }}>decoy-oracle · ground truth</span>}
                    {r.quarantined && <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1" style={{ background: "color-mix(in oklab, var(--destructive) 12%, white)", color: "var(--destructive)" }}><Ban className="w-3 h-3" /> poison quarantine</span>}
                    <div className="ml-auto">
                      {ok ? <span className="text-[11px] font-medium flex items-center gap-1" style={{ color: "var(--success)" }}><Check className="w-3.5 h-3.5" /> {r.confirmed && r.source === "mirage_oracle" ? "Auto-confirmed" : "Approved"}</span>
                        : <button onClick={() => setApproved((a) => [...a, r.id])} className="text-[11px] font-semibold px-2.5 py-1 rounded-lg text-white" style={{ background: r.quarantined ? "var(--destructive)" : "var(--brand)" }}>{r.quarantined ? "Override & approve" : "Approve"}</button>}
                    </div>
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-1">{r.why}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Differential privacy on analytics */}
        <div className="soft-card p-5 animate-fade-in">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2"><Lock className="w-4 h-4 text-brand" /> Differential Privacy</h3>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "color-mix(in oklab, var(--success) 14%, white)", color: "var(--success)" }}>Active</span>
            <span className="text-[11px] text-muted-foreground">Laplace · ε = 2.0</span>
          </div>
          <p className="text-[11px] text-muted-foreground mb-3">Released aggregate analytics carry calibrated noise so an attacker cannot reconstruct individual records. Individual authorized lookups are never noised.</p>
          <div className="space-y-2">
            {[
              { l: "Patients accessed (today)", raw: 312, noised: 314 },
              { l: "PHI reads (this facility)", raw: 1840, noised: 1836 },
              { l: "Avg records/session", raw: 7, noised: 8 },
            ].map((m) => (
              <div key={m.l} className="flex items-center justify-between text-[11px] rounded-lg p-2 bg-card border">
                <span className="text-muted-foreground">{m.l}</span>
                <span className="flex items-center gap-1.5">
                  <span className="line-through text-muted-foreground/50">{m.raw}</span>
                  <span className="font-semibold flex items-center gap-1"><Beaker className="w-3 h-3 text-brand" /> {m.noised}</span>
                </span>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">Moving-target timing jitter also applied to prevent latency fingerprinting.</p>
        </div>
      </div>
    </div>
  );
}
