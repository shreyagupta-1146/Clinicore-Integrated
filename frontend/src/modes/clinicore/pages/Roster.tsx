import { Users, Search, Eye } from "lucide-react";
import { Link } from "react-router-dom";
import { ClinHeader } from "../ClinHeader";
import { Pill } from "@/components/ui";

const PATIENTS = [
  { id: "c1", name: "Anita R.", abha: "12-3456-7890-1234", age: "58F", problems: "T2DM, HTN", seen: "Today", consent: "Active", tone: "good" as const },
  { id: "c2", name: "Suresh M.", abha: "45-6789-0123-4567", age: "64M", problems: "T2DM (uncontrolled)", seen: "Today", consent: "Active", tone: "good" as const },
  { id: "c3", name: "Fatima K.", abha: "78-9012-3456-7890", age: "51F", problems: "Hypertension", seen: "2d ago", consent: "Active", tone: "good" as const },
  { id: "c4", name: "Ravi P.", abha: "23-4567-8901-2345", age: "47M", problems: "Wt loss workup", seen: "3d ago", consent: "Expiring", tone: "warn" as const },
  { id: "c5", name: "Meena T.", abha: "56-7890-1234-5678", age: "39F", problems: "Asthma", seen: "1w ago", consent: "Revoked", tone: "bad" as const },
];

export function Roster() {
  return (
    <div>
      <ClinHeader icon={Users} title="Patient Roster" subtitle="312 patients on your panel" />
      <div className="soft-card p-2 animate-fade-in">
        <div className="flex items-center gap-2 px-3 py-2 m-2 rounded-lg border">
          <Search className="w-4 h-4 text-muted-foreground" />
          <input placeholder="Filter by name, ABHA ID, or condition…" className="flex-1 bg-transparent outline-none text-sm" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2 font-medium">Patient</th>
                <th className="px-4 py-2 font-medium">ABHA ID</th>
                <th className="px-4 py-2 font-medium">Age/Sex</th>
                <th className="px-4 py-2 font-medium">Problems</th>
                <th className="px-4 py-2 font-medium">Last seen</th>
                <th className="px-4 py-2 font-medium">Consent</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {PATIENTS.map((p) => (
                <tr key={p.id} className="border-t hover:bg-black/[0.015]">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full grid place-items-center text-white text-xs font-semibold" style={{ background: "var(--brand)" }}>{p.name.charAt(0)}</div>
                      <span className="font-medium">{p.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{p.abha}</td>
                  <td className="px-4 py-3">{p.age}</td>
                  <td className="px-4 py-3 text-muted-foreground">{p.problems}</td>
                  <td className="px-4 py-3 text-muted-foreground">{p.seen}</td>
                  <td className="px-4 py-3"><Pill tone={p.tone}>{p.consent}</Pill></td>
                  <td className="px-4 py-3">
                    <Link to={`/clinicore/consultation/${p.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-brand"><Eye className="w-3.5 h-3.5" /> Open</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
