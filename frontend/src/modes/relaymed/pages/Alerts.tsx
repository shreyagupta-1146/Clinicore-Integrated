import { Bell } from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { Pill } from "@/components/ui";

const ALERTS = [
  { title: "Glucose above target range", body: "Your reading of 168 mg/dL is above your target. Consider a short walk and hydration.", time: "2h ago", sev: "warn" as const },
  { title: "Evening dose reminder", body: "Metformin 500 mg is due at 8:00 PM.", time: "4h ago", sev: "neutral" as const },
  { title: "Caregiver request", body: "Rahul (son) requested to monitor your vitals & medications.", time: "1d ago", sev: "brand" as const },
  { title: "Great streak!", body: "12 days of consistent vital logging. Keep it up 🌿", time: "1d ago", sev: "good" as const },
];

export function Alerts() {
  return (
    <PageShell icon={Bell} title="Health Alerts" subtitle="Timely, gentle nudges — never noise.">
      <div className="space-y-3">
        {ALERTS.map((a, i) => (
          <div key={i} className="rounded-2xl border bg-card p-4 flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg grid place-items-center bg-chip text-brand shrink-0"><Bell className="w-4 h-4" /></div>
            <div className="flex-1">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold">{a.title}</div>
                <span className="text-[10px] text-muted-foreground shrink-0">{a.time}</span>
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">{a.body}</p>
            </div>
            <Pill tone={a.sev}>{a.sev === "warn" ? "Watch" : a.sev === "good" ? "Good" : a.sev === "brand" ? "Action" : "Info"}</Pill>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
