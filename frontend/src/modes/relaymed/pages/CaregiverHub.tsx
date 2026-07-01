import { useState } from "react";
import { Users, Check, X, Shield, UserPlus, Heart, Pill, Activity } from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { Pill as Chip, Ring } from "@/components/ui";

type Tab = "patient" | "caregiver";

const APPROVED = [
  { name: "Priya (daughter)", cats: ["Vitals", "Medications"], color: "var(--ocean)" },
];
const PENDING = [
  { id: "req1", name: "Rahul (son)", cats: ["Vitals", "Medications", "Conditions"], msg: "Hi Dad, I'd like to keep an eye on your sugar levels." },
];
const CARING_FOR = [
  { name: "Mr. Sharma (father)", adherence: 86, lastVital: "BP 128/82 · 2h ago", flag: false },
  { name: "Mrs. Sharma (mother)", adherence: 54, lastVital: "Glucose 168 · 5h ago", flag: true },
];

export function CaregiverHub() {
  const [tab, setTab] = useState<Tab>("patient");
  const [pending, setPending] = useState(PENDING);

  return (
    <PageShell icon={Users} title="Caregiver Hub" subtitle="You decide who can see your health — and you can revoke it anytime." wide>
      <div className="flex gap-1 p-1 rounded-xl mb-5 w-fit" style={{ background: "var(--muted)" }}>
        {(["patient", "caregiver"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className="px-4 py-2 text-sm font-medium rounded-lg transition-all"
            style={tab === t ? { background: "white", color: "var(--brand)", boxShadow: "var(--shadow-soft)" } : { color: "var(--muted-foreground)" }}>
            {t === "patient" ? "People who help me" : "People I care for"}
          </button>
        ))}
      </div>

      {tab === "patient" ? (
        <div className="space-y-5">
          <div className="rounded-2xl p-4 flex items-start gap-3" style={{ background: "color-mix(in oklab, var(--brand) 8%, white)" }}>
            <Shield className="w-5 h-5 text-brand shrink-0" />
            <p className="text-sm text-muted-foreground"><span className="font-semibold text-foreground">You're in control.</span> Only you can approve a caregiver, and only the exact categories you choose are shared. Revoke access at any time.</p>
          </div>

          {pending.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Pending requests</h3>
              {pending.map((p) => (
                <div key={p.id} className="soft-card p-5 mb-3">
                  <div className="flex items-start gap-3">
                    <div className="w-11 h-11 rounded-full grid place-items-center text-white font-semibold" style={{ background: "var(--warning)" }}>{p.name.charAt(0)}</div>
                    <div className="flex-1">
                      <div className="font-medium">{p.name}</div>
                      <p className="text-xs text-muted-foreground italic mt-0.5">"{p.msg}"</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">{p.cats.map((c) => <Chip key={c} tone="brand">{c}</Chip>)}</div>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button onClick={() => setPending((x) => x.filter((y) => y.id !== p.id))} className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl gradient-brand text-white text-sm font-semibold"><Check className="w-4 h-4" /> Approve</button>
                    <button onClick={() => setPending((x) => x.filter((y) => y.id !== p.id))} className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border text-sm font-medium"><X className="w-4 h-4" /> Decline</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div>
            <h3 className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Approved caregivers</h3>
            {APPROVED.map((a) => (
              <div key={a.name} className="soft-card p-5 flex items-center gap-3">
                <div className="w-11 h-11 rounded-full grid place-items-center text-white font-semibold" style={{ background: a.color }}>{a.name.charAt(0)}</div>
                <div className="flex-1">
                  <div className="font-medium">{a.name}</div>
                  <div className="flex flex-wrap gap-1.5 mt-1">{a.cats.map((c) => <Chip key={c} tone="good">{c}</Chip>)}</div>
                </div>
                <button className="text-xs font-medium px-3 py-1.5 rounded-lg border" style={{ color: "var(--coral)", borderColor: "color-mix(in oklab, var(--coral) 30%, transparent)" }}>Revoke</button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <button className="w-full soft-card p-4 flex items-center justify-center gap-2 text-sm font-semibold text-brand border-dashed" style={{ borderStyle: "dashed" }}>
            <UserPlus className="w-4 h-4" /> Request to monitor someone
          </button>
          {CARING_FOR.map((c) => (
            <div key={c.name} className="soft-card p-5">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-full grid place-items-center text-white font-semibold" style={{ background: "var(--ocean)" }}>{c.name.charAt(0)}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium flex items-center gap-2">{c.name} {c.flag && <Chip tone="bad">Needs attention</Chip>}</div>
                  <div className="text-xs text-muted-foreground">{c.lastVital}</div>
                </div>
                <Ring value={c.adherence} label={`${c.adherence}%`} sub="adherence" />
              </div>
              <div className="grid grid-cols-3 gap-2 mt-4">
                {[{ i: Heart, l: "Vitals" }, { i: Pill, l: "Medications" }, { i: Activity, l: "Trends" }].map((x) => {
                  const Icon = x.i;
                  return <div key={x.l} className="rounded-xl border p-2.5 flex items-center gap-2 text-xs"><Icon className="w-3.5 h-3.5 text-brand" /> {x.l}</div>;
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  );
}
