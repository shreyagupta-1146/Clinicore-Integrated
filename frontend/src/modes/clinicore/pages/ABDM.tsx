import { useState } from "react";
import { Network, Search, Download, Server } from "lucide-react";
import { ClinHeader } from "../ClinHeader";
import { Pill } from "@/components/ui";

const RECORDS = [
  { facility: "Fortis Healthcare, Delhi", type: "Lipid panel", date: "3 months ago", status: "received" as const },
  { facility: "Manipal Hospital", type: "ECG report", date: "6 months ago", status: "received" as const },
  { facility: "Apollo Diagnostics", type: "HbA1c trend", date: "pending", status: "pending" as const },
];

export function ABDM() {
  const [requested, setRequested] = useState(false);
  return (
    <div>
      <ClinHeader icon={Network} title="ABDM Health Records Exchange" subtitle="Federated query via HIE-CM — PHI stays at the source facility" />

      <div className="soft-card p-5 mb-5 animate-fade-in">
        <h3 className="text-sm font-semibold mb-3">Request records from another facility</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border flex-1">
            <Search className="w-4 h-4 text-muted-foreground" />
            <input placeholder="Patient ABHA ID (14-digit)" defaultValue="12-3456-7890-1234" className="flex-1 bg-transparent outline-none text-sm font-mono" />
          </div>
          <button onClick={() => setRequested(true)} className="px-4 py-2.5 rounded-lg text-sm font-semibold text-white" style={{ background: "var(--brand)" }}>Request via ABDM</button>
        </div>
        {requested && (
          <div className="mt-3 flex items-center gap-2 text-xs rounded-lg p-2.5" style={{ background: "color-mix(in oklab, var(--brand) 8%, white)", color: "var(--brand)" }}>
            <Server className="w-3.5 h-3.5" /> Request sent. The holding facility will push encrypted records to the callback (ECDH + AES-256-GCM). Query, not copy.
          </div>
        )}
      </div>

      <div className="soft-card p-5 animate-fade-in">
        <h3 className="text-sm font-semibold mb-3">Records available for this patient</h3>
        <div className="space-y-2.5">
          {RECORDS.map((r, i) => (
            <div key={i} className="flex items-center gap-3 p-3 rounded-lg border">
              <div className="w-9 h-9 rounded-lg grid place-items-center" style={{ background: "color-mix(in oklab, var(--brand) 10%, white)", color: "var(--brand)" }}><Network className="w-4 h-4" /></div>
              <div className="flex-1">
                <div className="text-sm font-medium">{r.type}</div>
                <div className="text-xs text-muted-foreground">{r.facility} · {r.date}</div>
              </div>
              {r.status === "received" ? (
                <button className="flex items-center gap-1.5 text-xs font-medium text-brand"><Download className="w-3.5 h-3.5" /> View</button>
              ) : (
                <Pill tone="warn">Pending</Pill>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
