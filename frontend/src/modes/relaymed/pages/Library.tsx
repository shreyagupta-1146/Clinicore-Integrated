import { BookOpen, Heart, Droplet, Moon, Apple, Activity, Brain } from "lucide-react";
import { PageShell } from "@/components/PageShell";

const ARTICLES = [
  { icon: Droplet, t: "Understanding your blood sugar", d: "What the numbers mean and simple ways to keep them steady.", tag: "Diabetes" },
  { icon: Heart, t: "Blood pressure, explained simply", d: "Systolic vs diastolic and why both matter.", tag: "Heart" },
  { icon: Moon, t: "Sleep and recovery", d: "How rest shapes your next-day energy and mood.", tag: "Wellness" },
  { icon: Apple, t: "Eating well with diabetes", d: "Balanced plates without giving up the foods you love.", tag: "Nutrition" },
  { icon: Activity, t: "Movement that fits your day", d: "Small, sustainable activity ideas for every ability.", tag: "Activity" },
  { icon: Brain, t: "Managing everyday stress", d: "Gentle techniques to calm the evening spikes.", tag: "Mind" },
];

export function Library() {
  return (
    <PageShell icon={BookOpen} title="Health Library" subtitle="Friendly, trustworthy reading — written for you, not textbooks.">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {ARTICLES.map((a) => {
          const Icon = a.icon;
          return (
            <div key={a.t} className="rounded-2xl border bg-card p-5 hover:shadow-md transition-shadow cursor-pointer">
              <div className="w-11 h-11 rounded-xl grid place-items-center bg-chip text-brand"><Icon className="w-5 h-5" /></div>
              <div className="text-base font-semibold mt-3" style={{ fontFamily: "var(--font-heading)" }}>{a.t}</div>
              <p className="text-sm text-muted-foreground mt-1">{a.d}</p>
              <span className="inline-block mt-3 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-chip text-brand">{a.tag}</span>
            </div>
          );
        })}
      </div>
    </PageShell>
  );
}
