import { useState } from "react";
import { FlaskConical } from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { LineChart, Line, ResponsiveContainer } from "recharts";

export function Simulator() {
  const [walk, setWalk] = useState(30);
  const [sleep, setSleep] = useState(1);
  const [stress, setStress] = useState(20);
  const [weight, setWeight] = useState(2);
  const improvement = Math.round(walk * 0.35 + sleep * 6 + stress * 0.3 + weight * 4);
  const data = Array.from({ length: 18 }, (_, i) => ({ v: 50 + i * (improvement / 22) + Math.sin(i / 1.6) * 3 }));

  return (
    <PageShell icon={FlaskConical} title="What-If Simulator" subtitle="Test interventions and see the causal impact on your future risk.">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="space-y-4">
          <Slider label="Walk minutes/day" value={walk} setValue={setWalk} max={120} unit="min" />
          <Slider label="Sleep extra hours" value={sleep} setValue={setSleep} max={3} unit="h" />
          <Slider label="Reduce stress %" value={stress} setValue={setStress} max={50} unit="%" />
          <Slider label="Weight loss" value={weight} setValue={setWeight} max={10} unit="kg" />
        </div>
        <div className="rounded-2xl border bg-card p-5">
          <div className="text-xs text-muted-foreground">Predicted cardiovascular improvement (6 months)</div>
          <div className="text-4xl font-semibold text-brand mt-1" style={{ fontFamily: "var(--font-heading)" }}>+{improvement}%</div>
          <div className="mt-3">
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={data}><Line dataKey="v" stroke="var(--brand)" strokeWidth={2.5} dot={false} type="monotone" /></LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Based on a causal counterfactual model over your trust-filtered data graph.</p>
        </div>
      </div>
    </PageShell>
  );
}

function Slider({ label, value, setValue, max, unit }: { label: string; value: number; setValue: (n: number) => void; max: number; unit: string }) {
  return (
    <div className="rounded-2xl border bg-card p-4">
      <div className="flex items-center justify-between text-sm">
        <span>{label}</span><span className="text-brand font-semibold">{value} {unit}</span>
      </div>
      <input type="range" min={0} max={max} value={value} onChange={(e) => setValue(Number(e.target.value))} className="w-full mt-2" />
    </div>
  );
}
