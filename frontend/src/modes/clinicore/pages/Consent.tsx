import { FileCheck2, Check, Clock, X, ShieldAlert } from "lucide-react";
import { ClinHeader } from "../ClinHeader";
import { Pill } from "@/components/ui";

const CONSENTS = [
  { patient: "Anita R.", purpose: "Clinical decision support", cats: ["Vitals", "Conditions", "Medications"], status: "Active", expires: "in 340 days", sensitive: false, tone: "good" as const },
  { patient: "Suresh M.", purpose: "Clinical decision support", cats: ["Vitals", "Medications", "Labs"], status: "Active", expires: "in 88 days", sensitive: false, tone: "good" as const },
  { patient: "Priya S.", purpose: "Mental health assessment", cats: ["Mental health"], status: "Active", expires: "in 30 days", sensitive: true, tone: "good" as const },
  { patient: "Ravi P.", purpose: "Clinical decision support", cats: ["Vitals", "Conditions"], status: "Expiring", expires: "in 3 days", sensitive: false, tone: "warn" as const },
];

export function Consent() {
  return (
    <div>
      <ClinHeader icon={FileCheck2} title="Consent Management" subtitle="Purpose-bound, category-bound, time-boxed — DPDP Act 2023" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {CONSENTS.map((c, i) => (
          <div key={i} className="soft-card p-5 animate-fade-in">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold">{c.patient}</div>
                <div className="text-xs text-muted-foreground">{c.purpose}</div>
              </div>
              <Pill tone={c.tone}>{c.status}</Pill>
            </div>
            {c.sensitive && (
              <div className="flex items-center gap-1.5 text-[11px] mt-2 px-2 py-1 rounded-md w-fit" style={{ background: "color-mix(in oklab, var(--destructive) 8%, white)", color: "var(--destructive)" }}>
                <ShieldAlert className="w-3 h-3" /> Sensitive category · explicit consent on file
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 mt-3">
              {c.cats.map((cat) => <Pill key={cat} tone="brand">{cat}</Pill>)}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-3"><Clock className="w-3.5 h-3.5" /> Expires {c.expires}</div>
            <div className="flex gap-2 mt-4">
              <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold text-white" style={{ background: "var(--brand)" }}><Check className="w-3.5 h-3.5" /> Verify</button>
              <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border text-xs font-medium" style={{ color: "var(--destructive)" }}><X className="w-3.5 h-3.5" /> Revoke</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
