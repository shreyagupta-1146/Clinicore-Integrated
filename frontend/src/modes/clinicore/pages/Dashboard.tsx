import { LayoutDashboard, Users, MessageSquare, AlertTriangle, Clock, TrendingUp, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { ClinHeader } from "../ClinHeader";
import { Pill } from "@/components/ui";

const KPIS = [
  { label: "Consults today", value: "14", icon: MessageSquare, delta: "+3" },
  { label: "Patients on panel", value: "312", icon: Users, delta: "+8" },
  { label: "Avg AI response", value: "1.9s", icon: Clock, delta: "-0.2s" },
  { label: "Open escalations", value: "2", icon: AlertTriangle, delta: "" },
];

const QUEUE = [
  { name: "Anita R.", abha: "12-3456-7890-1234", complaint: "Chest tightness on exertion", flag: "Cardiac red flag", tone: "bad" as const, id: "c1" },
  { name: "Suresh M.", abha: "45-6789-0123-4567", complaint: "Poorly controlled T2DM, HbA1c 9.1", flag: "Review meds", tone: "warn" as const, id: "c2" },
  { name: "Fatima K.", abha: "78-9012-3456-7890", complaint: "Follow-up: hypertension", flag: "Stable", tone: "good" as const, id: "c3" },
];

export function Dashboard() {
  return (
    <div>
      <ClinHeader icon={LayoutDashboard} title="Good morning, Dr. Sharma" subtitle="Apollo Hospitals, Bengaluru · Clinician" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {KPIS.map((k) => {
          const Icon = k.icon;
          return (
            <div key={k.label} className="soft-card p-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded-lg grid place-items-center" style={{ background: "color-mix(in oklab, var(--brand) 10%, white)", color: "var(--brand)" }}><Icon className="w-4 h-4" /></div>
                {k.delta && <span className="text-[11px] font-semibold flex items-center gap-0.5" style={{ color: "var(--success)" }}><TrendingUp className="w-3 h-3" /> {k.delta}</span>}
              </div>
              <div className="text-2xl font-semibold mt-3">{k.value}</div>
              <div className="text-[11px] text-muted-foreground">{k.label}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 soft-card p-5 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Today's consultation queue</h2>
            <Link to="/clinicore/roster" className="text-xs font-medium text-brand flex items-center gap-1">All patients <ArrowRight className="w-3.5 h-3.5" /></Link>
          </div>
          <div className="space-y-2.5">
            {QUEUE.map((q) => (
              <Link key={q.id} to={`/clinicore/consultation/${q.id}`} className="flex items-center gap-3 p-3 rounded-lg border hover:shadow-sm transition-shadow">
                <div className="w-9 h-9 rounded-full grid place-items-center text-white text-xs font-semibold" style={{ background: "var(--brand)" }}>{q.name.charAt(0)}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{q.name} <span className="text-[10px] text-muted-foreground font-mono ml-1">{q.abha}</span></div>
                  <div className="text-xs text-muted-foreground truncate">{q.complaint}</div>
                </div>
                <Pill tone={q.tone}>{q.flag}</Pill>
              </Link>
            ))}
          </div>
        </div>

        <div className="soft-card p-5 animate-fade-in">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4" style={{ color: "var(--destructive)" }} />
            <h2 className="text-base font-semibold">Red-flag alerts</h2>
          </div>
          <div className="space-y-3">
            <div className="rounded-lg p-3" style={{ background: "color-mix(in oklab, var(--destructive) 8%, white)", border: "1px solid color-mix(in oklab, var(--destructive) 25%, transparent)" }}>
              <div className="text-sm font-semibold" style={{ color: "var(--destructive)" }}>Possible ACS — Anita R.</div>
              <p className="text-xs text-muted-foreground mt-0.5">Chest pain radiating to jaw with diaphoresis flagged by input safety layer.</p>
            </div>
            <div className="rounded-lg p-3" style={{ background: "color-mix(in oklab, var(--warning) 12%, white)" }}>
              <div className="text-sm font-semibold" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }}>Unexplained weight loss — Ravi P.</div>
              <p className="text-xs text-muted-foreground mt-0.5">Malignancy / chronic disease workup suggested.</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t text-[11px] text-muted-foreground">Red flags are detected deterministically on input — never by the LLM alone.</div>
        </div>
      </div>
    </div>
  );
}
