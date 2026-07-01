import { ShieldCheck, Lock, EyeOff, UserCheck, FileLock2 } from "lucide-react";
import { PageShell } from "@/components/PageShell";

const items = [
  { icon: Lock, t: "AES-256 Encryption", d: "All your data is encrypted at rest and in transit." },
  { icon: FileLock2, t: "Immutable Audit Trail", d: "Every access is logged and cryptographically signed." },
  { icon: EyeOff, t: "Zero Data Selling", d: "We never sell or share your data with third parties." },
  { icon: UserCheck, t: "Role-Based Access", d: "Only you and your authorized clinicians see your record." },
];

export function Trust() {
  return (
    <PageShell icon={ShieldCheck} title="Trust Center" subtitle="Transparency about how your data flows, who sees it, and why.">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map((i) => {
          const Icon = i.icon;
          return (
            <div key={i.t} className="rounded-2xl border bg-card p-5 flex items-start gap-4">
              <div className="w-11 h-11 rounded-xl bg-chip grid place-items-center text-brand"><Icon className="w-5 h-5" /></div>
              <div>
                <div className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{i.t}</div>
                <p className="text-sm text-muted-foreground mt-1">{i.d}</p>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 rounded-2xl p-4 text-sm text-muted-foreground" style={{ background: "color-mix(in oklab, var(--brand) 6%, white)" }}>
        Raw personal health information never leaves the secure on-prem boundary. Only de-identified text is ever routed to a cloud AI model, under a no-training / zero-data-retention contract. DPDP Act 2023 & ABDM aligned.
      </div>
    </PageShell>
  );
}
