import { useState } from "react";
import { Link } from "react-router-dom";
import { Library, Play, Clock } from "lucide-react";
import { Pill } from "@/components/ui";

const SPECIALTIES = ["All", "Cardiology", "Respiratory", "Neurology", "Surgery", "Endocrine", "Paediatrics"];
const MODES = ["Practice", "Timed", "Exam"];

const CASES = [
  { id: "resp1", title: "Acute breathlessness in the ED", specialty: "Respiratory", diff: "Resident", mode: "Timed", acc: 61, min: 8, osce: false },
  { id: "neuro1", title: "Sudden severe headache", specialty: "Neurology", diff: "Attending", mode: "Exam", acc: 48, min: 10, osce: false },
  { id: "gastro1", title: "Right iliac fossa pain", specialty: "Surgery", diff: "Intern", mode: "Practice", acc: 72, min: 6, osce: true },
  { id: "card1", title: "Chest pain, 58M diabetic", specialty: "Cardiology", diff: "Resident", mode: "Timed", acc: 58, min: 8, osce: false },
  { id: "endo1", title: "Weight loss and palpitations", specialty: "Endocrine", diff: "Resident", mode: "Practice", acc: 66, min: 7, osce: false },
  { id: "paed1", title: "The febrile child", specialty: "Paediatrics", diff: "Intern", mode: "Timed", acc: 63, min: 6, osce: true },
];

const DIFF_TONE: Record<string, "good" | "warn" | "bad" | "brand"> = { Intern: "good", Resident: "warn", Attending: "bad" };

export function CaseLibrary() {
  const [spec, setSpec] = useState("All");
  const [mode, setMode] = useState("All modes");

  const filtered = CASES.filter((c) => (spec === "All" || c.specialty === spec) && (mode === "All modes" || c.mode === mode));

  return (
    <div className="soft-card p-6 animate-fade-in">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-11 h-11 rounded-2xl gradient-brand grid place-items-center text-white"><Library className="w-5 h-5" /></div>
        <div>
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Case Library</h2>
          <p className="text-xs text-muted-foreground">Vignettes & OSCE stations by specialty and difficulty</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {SPECIALTIES.map((s) => (
          <button key={s} onClick={() => setSpec(s)} className="text-xs px-3 py-1.5 rounded-full transition-all"
            style={spec === s ? { background: "var(--brand)", color: "white", fontWeight: 600 } : { background: "var(--muted)", color: "var(--muted-foreground)" }}>{s}</button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 mb-5">
        {["All modes", ...MODES].map((m) => (
          <button key={m} onClick={() => setMode(m)} className="text-xs px-3 py-1.5 rounded-full border transition-all"
            style={mode === m ? { borderColor: "var(--brand)", color: "var(--brand)", fontWeight: 600 } : { borderColor: "var(--border)", color: "var(--muted-foreground)" }}>{m}</button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((c) => (
          <div key={c.id} className="rounded-2xl border bg-card p-4 hover:shadow-md transition-shadow flex flex-col">
            <div className="flex items-center justify-between">
              <Pill tone={DIFF_TONE[c.diff]}>{c.diff}</Pill>
              {c.osce && <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "color-mix(in oklab, var(--ochre) 16%, white)", color: "var(--ochre)" }}>OSCE</span>}
            </div>
            <div className="text-base font-semibold mt-2" style={{ fontFamily: "var(--font-heading)" }}>{c.title}</div>
            <div className="text-xs text-muted-foreground mt-1">{c.specialty} · {c.mode}</div>
            <div className="flex items-center gap-3 mt-3 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {c.min} min</span>
              <span>Cohort acc. {c.acc}%</span>
            </div>
            <Link to={`/clinmed/simulator/${c.id}`} className="mt-4 flex items-center justify-center gap-1.5 py-2 rounded-xl gradient-brand text-white text-sm font-semibold">
              <Play className="w-4 h-4" /> Start
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
