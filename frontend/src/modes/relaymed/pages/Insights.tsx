import { Sparkles, TrendingUp, AlertTriangle, Lightbulb } from "lucide-react";
import { PageShell } from "@/components/PageShell";

const insights = [
  { icon: TrendingUp, title: "Cardiovascular load improving", body: "Your HRV has improved 9% over the last 14 days, suggesting better autonomic recovery.", tone: "good" },
  { icon: AlertTriangle, title: "Recurring evening stress spikes", body: "Stress consistently rises between 8–10pm. Consider a wind-down routine.", tone: "warn" },
  { icon: Lightbulb, title: "Sleep window optimization", body: "Falling asleep before 11:15pm correlates with +18% next-day recovery.", tone: "good" },
  { icon: TrendingUp, title: "Activity consistency streak", body: "5 days in a row above your daily activity goal. Keep it going!", tone: "good" },
];

export function Insights() {
  return (
    <PageShell icon={Sparkles} title="Health Insights" subtitle="AI-derived patterns from your trusted health signals.">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {insights.map((it) => {
          const Icon = it.icon;
          const warn = it.tone === "warn";
          return (
            <div key={it.title} className="rounded-2xl border bg-card p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl grid place-items-center" style={warn ? { background: "color-mix(in oklab, var(--coral) 15%, white)", color: "var(--coral)" } : { background: "var(--chip-bg)", color: "var(--brand)" }}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{it.title}</div>
                  <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{it.body}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </PageShell>
  );
}
