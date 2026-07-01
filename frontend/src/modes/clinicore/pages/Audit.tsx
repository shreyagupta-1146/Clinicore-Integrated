import { ScrollText, ShieldCheck, Search } from "lucide-react";
import { ClinHeader } from "../ClinHeader";

const ENTRIES = [
  { ts: "14:32:07", type: "PHI_ACCESSED", actor: "dr.sharma@apollo.in", resource: "Patient/Anita R.", hash: "9f3a…c21e" },
  { ts: "14:31:55", type: "CONSENT_CHECKED_PERMITTED", actor: "clinicore-backend", resource: "Consent/anita-cds", hash: "1b78…44af" },
  { ts: "14:30:12", type: "AI_CONSULT_ROUTED_CLOUD", actor: "model-gateway", resource: "De-identified/req-8812", hash: "c40d…9e02" },
  { ts: "14:28:40", type: "PHI_ACCESSED", actor: "dr.sharma@apollo.in", resource: "Patient/Suresh M.", hash: "77aa…10bd" },
  { ts: "14:26:03", type: "CONSENT_GRANTED", actor: "patient:priya-s", resource: "Consent/priya-mh", hash: "e5c1…3f7a" },
  { ts: "14:20:19", type: "AUTH_STEP_UP_MFA", actor: "dr.sharma@apollo.in", resource: "Session/9921", hash: "2d90…88c4" },
];

export function Audit() {
  return (
    <div>
      <ClinHeader
        icon={ScrollText}
        title="Audit Trail"
        subtitle="Immutable, hash-chained access log (immudb WORM)"
        action={<span className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full" style={{ background: "color-mix(in oklab, var(--success) 12%, white)", color: "var(--success)" }}><ShieldCheck className="w-3.5 h-3.5" /> Chain verified ✓</span>}
      />
      <div className="soft-card p-2 animate-fade-in">
        <div className="flex items-center gap-2 px-3 py-2 m-2 rounded-lg border">
          <Search className="w-4 h-4 text-muted-foreground" />
          <input placeholder="Filter by actor, patient, or event type…" className="flex-1 bg-transparent outline-none text-sm" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2 font-medium">Time</th>
                <th className="px-4 py-2 font-medium">Event</th>
                <th className="px-4 py-2 font-medium">Actor</th>
                <th className="px-4 py-2 font-medium">Resource</th>
                <th className="px-4 py-2 font-medium">Entry hash</th>
                <th className="px-4 py-2 font-medium">Proof</th>
              </tr>
            </thead>
            <tbody>
              {ENTRIES.map((e, i) => (
                <tr key={i} className="border-t">
                  <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">{e.ts}</td>
                  <td className="px-4 py-2.5"><span className="font-mono text-[11px] px-2 py-0.5 rounded" style={{ background: "color-mix(in oklab, var(--brand) 8%, white)", color: "var(--brand)" }}>{e.type}</span></td>
                  <td className="px-4 py-2.5 text-xs">{e.actor}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{e.resource}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">{e.hash}</td>
                  <td className="px-4 py-2.5"><ShieldCheck className="w-4 h-4" style={{ color: "var(--success)" }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground mt-3">Each entry's hash chains to the previous one and is verified against immudb's Merkle proof. Tampering is cryptographically detectable.</p>
    </div>
  );
}
