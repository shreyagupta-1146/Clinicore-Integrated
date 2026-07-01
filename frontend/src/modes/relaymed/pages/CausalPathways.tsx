import { Moon, Footprints, Activity, Apple, Heart, RotateCw, Scale, HeartPulse, Waves, Flame, Battery, Zap, ShieldCheck, Bed, Smile, Info, GitBranch } from "lucide-react";
import { PageShell } from "@/components/PageShell";

type Node = { id: string; label: string; sub: string; icon: any; trust?: number; tone?: "good" | "warn" | "bad" };

const inputs: Node[] = [
  { id: "sleep", label: "Sleep Quality", sub: "Good", icon: Moon, trust: 95, tone: "good" },
  { id: "activity", label: "Daily Activity", sub: "Moderate", icon: Footprints, trust: 92, tone: "good" },
  { id: "stress", label: "Stress Levels", sub: "Elevated", icon: Activity, trust: 78, tone: "bad" },
  { id: "nutrition", label: "Nutrition", sub: "Balanced", icon: Apple, trust: 88, tone: "good" },
  { id: "hr", label: "Heart Rate Trends", sub: "Normal", icon: Heart, trust: 94, tone: "good" },
  { id: "rec", label: "Recovery Consistency", sub: "Good", icon: RotateCw, trust: 91, tone: "good" },
];
const middle: Node[] = [
  { id: "weight", label: "Weight Stability", sub: "Improving", icon: Scale },
  { id: "bp", label: "Blood Pressure Balance", sub: "Balanced", icon: HeartPulse },
  { id: "cv", label: "Cardiovascular Load", sub: "Moderate", icon: Waves },
  { id: "meta", label: "Metabolic Stress", sub: "Normal", icon: Flame },
  { id: "cap", label: "Recovery Capacity", sub: "Good", icon: Battery },
];
const outputs: Node[] = [
  { id: "energy", label: "Improved Energy", sub: "High", icon: Zap },
  { id: "risk", label: "Lower Long-Term Risk", sub: "Improving", icon: ShieldCheck },
  { id: "heart", label: "Better Heart Health", sub: "On Track", icon: Heart },
  { id: "sleeprec", label: "Better Sleep Recovery", sub: "Improving", icon: Bed },
  { id: "stressred", label: "Reduced Stress Burden", sub: "Improving", icon: Smile },
];

const edges: { from: [number, number]; to: [number, number]; tone: "pos" | "neg" | "neu" }[] = [
  { from: [0, 0], to: [1, 0], tone: "pos" }, { from: [0, 1], to: [1, 1], tone: "pos" },
  { from: [0, 2], to: [1, 2], tone: "neg" }, { from: [0, 2], to: [1, 3], tone: "neg" },
  { from: [0, 3], to: [1, 0], tone: "pos" }, { from: [0, 4], to: [1, 1], tone: "pos" },
  { from: [0, 4], to: [1, 2], tone: "pos" }, { from: [0, 5], to: [1, 4], tone: "pos" },
  { from: [0, 1], to: [1, 3], tone: "pos" },
  { from: [1, 0], to: [2, 0], tone: "pos" }, { from: [1, 1], to: [2, 1], tone: "pos" },
  { from: [1, 2], to: [2, 2], tone: "pos" }, { from: [1, 2], to: [2, 1], tone: "pos" },
  { from: [1, 3], to: [2, 2], tone: "neg" }, { from: [1, 4], to: [2, 3], tone: "pos" },
  { from: [1, 4], to: [2, 4], tone: "pos" }, { from: [1, 1], to: [2, 2], tone: "pos" },
];

const colX = [16, 50, 84];
const rowsY = (count: number) => Array.from({ length: count }, (_, i) => 10 + (i * 80) / (count - 1));

function NodeChip({ n }: { n: Node }) {
  const Icon = n.icon;
  const border =
    n.tone === "bad" ? "color-mix(in oklab, var(--coral) 40%, transparent)"
      : n.tone === "warn" ? "color-mix(in oklab, var(--warning) 40%, transparent)"
        : "color-mix(in oklab, var(--brand) 25%, transparent)";
  return (
    <div className="rounded-2xl border px-3.5 py-2.5 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5" style={{ borderColor: border, background: "white" }}>
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl grid place-items-center shrink-0 bg-chip" style={{ color: "var(--brand)" }}><Icon className="w-4 h-4" /></div>
        <div className="min-w-0">
          <div className="text-[12px] font-medium leading-tight truncate">{n.label}</div>
          <div className="text-[10px] leading-tight" style={{ color: n.tone === "bad" ? "var(--coral)" : "var(--muted-foreground)" }}>{n.sub}</div>
        </div>
        {n.trust != null && <div className="ml-auto text-[10px] font-semibold text-brand">{n.trust}%</div>}
      </div>
    </div>
  );
}

export function HealthJourney() {
  const ys = [rowsY(inputs.length), rowsY(middle.length), rowsY(outputs.length)];
  const cols = [inputs, middle, outputs];
  return (
    <section className="soft-card p-6 animate-fade-in">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2" style={{ fontFamily: "var(--font-heading)" }}>
            Your Health Journey <Info className="w-4 h-4 text-muted-foreground" />
          </h2>
          <p className="text-sm text-muted-foreground mt-1">AI-powered prediction of how daily habits shape future health.</p>
        </div>
        <button className="text-xs font-medium text-brand neu-btn px-3.5 py-2 rounded-xl">View Full Pathway</button>
      </div>

      <div className="grid grid-cols-3 text-[11px] font-medium text-muted-foreground mt-6 mb-2 px-2">
        <div>Your Habits & Inputs <span className="ml-2 text-brand">Trust Score</span></div>
        <div className="text-center">Key Health Factors</div>
        <div className="text-right">Future Outcomes</div>
      </div>

      <div className="relative w-full" style={{ height: 420 }}>
        <svg className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 100 100">
          {edges.map((e, i) => {
            const [c1, r1] = e.from; const [c2, r2] = e.to;
            const x1 = colX[c1] + 6, y1 = ys[c1][r1], x2 = colX[c2] - 6, y2 = ys[c2][r2];
            const cx = (x1 + x2) / 2;
            const stroke = e.tone === "pos" ? "var(--sage)" : e.tone === "neg" ? "var(--coral)" : "var(--ocean)";
            return <path key={i} d={`M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`} fill="none" stroke={stroke} strokeOpacity={0.5} strokeWidth={0.4} className="pathway-line" vectorEffect="non-scaling-stroke" />;
          })}
        </svg>
        {cols.map((col, ci) => (
          <div key={ci} className="absolute" style={{ left: `${colX[ci]}%`, transform: "translateX(-50%)", top: 0, bottom: 0, width: "28%" }}>
            {col.map((n, ri) => (
              <div key={n.id} className="absolute left-0 right-0" style={{ top: `${ys[ci][ri]}%`, transform: "translateY(-50%)" }}><NodeChip n={n} /></div>
            ))}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-5 text-[11px] text-muted-foreground mt-4 pt-4 border-t">
        <span className="flex items-center gap-2"><span className="inline-block w-6 h-[2px] rounded" style={{ background: "var(--sage)" }} /> Positive Influence</span>
        <span className="flex items-center gap-2"><span className="inline-block w-6 h-[2px] rounded border-t border-dashed" style={{ borderColor: "var(--coral)" }} /> Negative Influence</span>
        <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "color-mix(in oklab, var(--sage) 40%, white)" }} /> Input</span>
        <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "color-mix(in oklab, var(--ocean) 40%, white)" }} /> Factor</span>
        <span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ background: "color-mix(in oklab, var(--warning) 60%, white)" }} /> Outcome</span>
      </div>
    </section>
  );
}

export function CausalPathways() {
  return (
    <PageShell icon={GitBranch} title="Causal Pathways" subtitle="See how lifestyle factors causally shape your future outcomes.">
      <HealthJourney />
      <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { t: "Root Cause", d: "Sedentary lifestyle → ↑ BMI → ↑ Hypertension" },
          { t: "Counterfactual", d: "If activity ↑ 20% → cardio risk ↓ 14%" },
          { t: "Filter", d: "Spurious correlation removed: caffeine ↔ stress" },
        ].map((c) => (
          <div key={c.t} className="rounded-2xl border bg-card p-4">
            <div className="text-xs text-muted-foreground">{c.t}</div>
            <div className="text-base font-semibold mt-1" style={{ fontFamily: "var(--font-heading)" }}>{c.d}</div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
