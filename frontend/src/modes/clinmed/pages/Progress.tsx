import { TrendingUp, Award } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, XAxis, Tooltip } from "recharts";
import { Bar } from "@/components/ui";

const ACCURACY = Array.from({ length: 12 }, (_, i) => ({ w: `W${i + 1}`, v: 45 + i * 2 + Math.round(Math.sin(i) * 5) }));
const RADAR = [
  { s: "Cardio", v: 78 }, { s: "Resp", v: 61 }, { s: "Neuro", v: 48 },
  { s: "GI", v: 70 }, { s: "Endo", v: 66 }, { s: "Paeds", v: 63 },
];
const BADGES = ["🩺 First 10 cases", "🔥 7-day streak", "⚡ Speed diagnostician", "🧠 Focus master", "🎯 90% in Cardio"];

export function Progress() {
  return (
    <div className="space-y-5">
      <div className="soft-card p-6 animate-fade-in">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-brand" />
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Your Progress</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="text-xs text-muted-foreground mb-2">Diagnostic accuracy over time</div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={ACCURACY}>
                <defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--brand)" stopOpacity={0.35} /><stop offset="100%" stopColor="var(--brand)" stopOpacity={0} /></linearGradient></defs>
                <XAxis dataKey="w" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", fontSize: 12 }} />
                <Area dataKey="v" stroke="var(--brand)" strokeWidth={2.5} fill="url(#pg)" type="monotone" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-2">Accuracy by specialty</div>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={RADAR}>
                <PolarGrid stroke="var(--border)" />
                <PolarAngleAxis dataKey="s" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
                <Radar dataKey="v" stroke="var(--brand)" fill="var(--brand)" fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 soft-card p-6 animate-fade-in">
          <h3 className="text-base font-semibold mb-4" style={{ fontFamily: "var(--font-heading)" }}>Resilience metrics</h3>
          {[
            { l: "Focus under pressure", v: 55, s: "moderate", t: "warn" as const },
            { l: "Time-to-diagnosis trend", v: 74, s: "improving", t: "good" as const },
            { l: "Cognitive-load recovery", v: 68, s: "good", t: "good" as const },
            { l: "Interruption handling", v: 62, s: "62% handled", t: "warn" as const },
          ].map((m) => (
            <div key={m.l} className="mb-3">
              <div className="flex items-center justify-between text-xs mb-1"><span className="text-muted-foreground">{m.l}</span><span className="font-medium">{m.s}</span></div>
              <Bar value={m.v} tone={m.t} />
            </div>
          ))}
        </div>
        <div className="soft-card p-6 animate-fade-in">
          <div className="flex items-center gap-2 mb-4"><Award className="w-5 h-5" style={{ color: "var(--ochre)" }} /><h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Badges</h3></div>
          <div className="flex flex-wrap gap-2">
            {BADGES.map((b) => (
              <span key={b} className="text-xs px-3 py-1.5 rounded-full" style={{ background: "color-mix(in oklab, var(--ochre) 12%, white)" }}>{b}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
