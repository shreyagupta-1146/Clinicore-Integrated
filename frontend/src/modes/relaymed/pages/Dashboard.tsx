import { Heart, Activity, Droplet, Wind, Pill, Check, Clock, Users, ChevronRight, Shield, Target, TrendingUp, TrendingDown, FlaskConical, Stethoscope, Phone, FileText } from "lucide-react";
import { Sparkline } from "@/components/Sparkline";
import { ToneDot, Ring, Pill as Chip } from "@/components/ui";
import { SecurityFooter } from "@/components/PageShell";
import { HealthJourney } from "./CausalPathways";
import { useState } from "react";
import { Link } from "react-router-dom";

const QUICK = [
  { icon: FlaskConical, label: "What-If Simulator", to: "/relaymed/simulator", href: undefined },
  { icon: Stethoscope, label: "Doctors Near Me", to: undefined, href: "https://www.google.com/maps/search/doctors+hospitals+near+me" },
  { icon: FileText, label: "Wellness Reports", to: "/relaymed/reports", href: undefined },
  { icon: Phone, label: "Emergency 112", to: undefined, href: "tel:112", danger: true },
];

function WellnessMetrics() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="soft-card p-5">
        <div className="text-xs text-muted-foreground">Wellness Score</div>
        <div className="text-3xl font-semibold mt-1" style={{ fontFamily: "var(--font-heading)" }}>82<span className="text-sm text-muted-foreground">/100</span></div>
        <div className="flex items-center gap-1 text-xs mt-1.5 text-brand"><TrendingUp className="w-3 h-3" /> 6% this month</div>
      </div>
      <div className="soft-card p-5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Shield className="w-4 h-4" style={{ color: "var(--ocean)" }} /> Predicted Stability</div>
        <div className="text-2xl font-semibold mt-2" style={{ fontFamily: "var(--font-heading)" }}>Stable</div>
        <div className="text-[11px] text-muted-foreground">Next 6 months outlook</div>
      </div>
      <div className="soft-card p-5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Heart className="w-4 h-4" style={{ color: "var(--coral)" }} /> Risk Change</div>
        <div className="flex items-baseline gap-1 mt-2"><TrendingDown className="w-4 h-4" style={{ color: "var(--coral)" }} /><div className="text-2xl font-semibold" style={{ fontFamily: "var(--font-heading)", color: "var(--coral)" }}>12%</div></div>
        <div className="text-[11px] text-muted-foreground">Cardiovascular · improved</div>
      </div>
      <div className="soft-card p-5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Target className="w-4 h-4 text-brand" /> Active Goals</div>
        <div className="text-3xl font-semibold mt-2" style={{ fontFamily: "var(--font-heading)" }}>4</div>
        <div className="text-[11px] text-muted-foreground">in progress</div>
      </div>
    </div>
  );
}

function QuickActions() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {QUICK.map((q) => {
        const Icon = q.icon;
        const inner = (
          <div className="soft-card p-4 flex items-center gap-3 hover:-translate-y-0.5 transition-transform h-full" style={q.danger ? { background: "color-mix(in oklab, var(--coral) 8%, white)" } : undefined}>
            <div className="w-10 h-10 rounded-xl grid place-items-center shrink-0" style={q.danger ? { background: "color-mix(in oklab, var(--coral) 16%, white)", color: "var(--coral)" } : { background: "var(--chip-bg)", color: "var(--brand)" }}><Icon className="w-5 h-5" /></div>
            <div className="text-sm font-semibold" style={q.danger ? { color: "var(--coral)" } : undefined}>{q.label}</div>
          </div>
        );
        return q.to ? <Link key={q.label} to={q.to}>{inner}</Link>
          : <a key={q.label} href={q.href} target={q.href?.startsWith("http") ? "_blank" : undefined} rel="noreferrer">{inner}</a>;
      })}
    </div>
  );
}

const VITALS = [
  { label: "Heart Rate", value: "72", unit: "bpm", icon: Heart, tone: "good" as const, data: [70, 74, 71, 73, 72, 70, 72], color: "var(--coral)" },
  { label: "Blood Pressure", value: "122/80", unit: "mmHg", icon: Activity, tone: "good" as const, data: [118, 124, 120, 126, 122, 121, 122], color: "var(--ocean)" },
  { label: "SpO₂", value: "98", unit: "%", icon: Wind, tone: "good" as const, data: [97, 98, 98, 99, 98, 97, 98], color: "var(--sage)" },
  { label: "Blood Glucose", value: "142", unit: "mg/dL", icon: Droplet, tone: "warn" as const, data: [110, 128, 135, 150, 142, 138, 142], color: "var(--warning)" },
];

const DOSES = [
  { name: "Metformin", dose: "500 mg", time: "8:00 AM", taken: true },
  { name: "Amlodipine", dose: "5 mg", time: "8:00 AM", taken: true },
  { name: "Metformin", dose: "500 mg", time: "8:00 PM", taken: false },
  { name: "Atorvastatin", dose: "10 mg", time: "9:00 PM", taken: false },
];

export function Dashboard() {
  const [doses, setDoses] = useState(DOSES);
  const takenCount = doses.filter((d) => d.taken).length;

  return (
    <div className="space-y-5">
      {/* Quick actions — surface key features up top */}
      <QuickActions />

      {/* Wellness metrics */}
      <WellnessMetrics />

      {/* Vitals row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {VITALS.map((v) => {
          const Icon = v.icon;
          return (
            <div key={v.label} className="soft-card p-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="w-9 h-9 rounded-xl grid place-items-center bg-chip" style={{ color: "var(--brand)" }}>
                  <Icon className="w-4 h-4" />
                </div>
                <ToneDot tone={v.tone} />
              </div>
              <div className="mt-3 flex items-end justify-between">
                <div>
                  <div className="text-2xl font-semibold leading-none" style={{ fontFamily: "var(--font-heading)" }}>{v.value}</div>
                  <div className="text-[11px] text-muted-foreground mt-1">{v.label} · {v.unit}</div>
                </div>
                <Sparkline data={v.data} color={v.color} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Today's medications */}
        <div className="soft-card p-6 animate-fade-in lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl grid place-items-center gradient-brand text-white"><Pill className="w-5 h-5" /></div>
              <div>
                <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Today's Medications</h3>
                <p className="text-xs text-muted-foreground">{takenCount} of {doses.length} doses taken</p>
              </div>
            </div>
            <Ring value={(takenCount / doses.length) * 100} label={`${takenCount}/${doses.length}`} sub="today" />
          </div>
          <div className="space-y-2.5">
            {doses.map((d, i) => (
              <div key={i} className="flex items-center gap-3 rounded-xl border p-3" style={{ background: d.taken ? "color-mix(in oklab, var(--success) 6%, white)" : "white" }}>
                <div className="w-9 h-9 rounded-lg grid place-items-center bg-chip" style={{ color: "var(--brand)" }}><Pill className="w-4 h-4" /></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{d.name} <span className="text-muted-foreground font-normal">· {d.dose}</span></div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-1"><Clock className="w-3 h-3" /> {d.time}</div>
                </div>
                {d.taken ? (
                  <span className="flex items-center gap-1 text-xs font-medium" style={{ color: "var(--success)" }}><Check className="w-4 h-4" /> Taken</span>
                ) : (
                  <button
                    onClick={() => setDoses((p) => p.map((x, xi) => (xi === i ? { ...x, taken: true } : x)))}
                    className="text-xs font-semibold px-3 py-1.5 rounded-lg gradient-brand text-white hover:opacity-90"
                  >
                    Mark taken
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Caregiver + streak */}
        <div className="space-y-5">
          <div className="soft-card p-6 animate-fade-in">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl grid place-items-center gradient-brand text-white"><Users className="w-5 h-5" /></div>
              <h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Shared with</h3>
            </div>
            <div className="flex items-center gap-3 rounded-xl border p-3">
              <div className="w-9 h-9 rounded-full grid place-items-center text-white text-sm font-semibold" style={{ background: "var(--ocean)" }}>P</div>
              <div className="flex-1">
                <div className="text-sm font-medium">Priya (daughter)</div>
                <div className="text-[11px] text-muted-foreground">Vitals · Medications</div>
              </div>
              <Chip tone="good">Active</Chip>
            </div>
            <Link to="/relaymed/caregivers" className="mt-3 flex items-center justify-center gap-1 text-xs font-medium text-brand hover:underline">
              Manage caregivers <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="soft-card p-6 animate-fade-in text-center">
            <div className="text-4xl">🔥</div>
            <div className="text-2xl font-semibold mt-1" style={{ fontFamily: "var(--font-heading)" }}>12-day streak</div>
            <p className="text-xs text-muted-foreground mt-1">You've logged your vitals 12 days in a row. Keep it going!</p>
          </div>
        </div>
      </div>

      {/* Health journey hero */}
      <HealthJourney />

      <SecurityFooter />
    </div>
  );
}
