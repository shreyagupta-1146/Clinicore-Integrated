import { useState, useEffect } from "react";
import {
  PlayCircle, BookOpen, MonitorPlay, ExternalLink, ShieldCheck, ShieldOff,
  Check, X, GraduationCap, Clock,
} from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { Pill, Ring } from "@/components/ui";
import { useLearningState, setTrackingEnabled, setProgress, getProgress, hydrateLearning } from "@/lib/learning";

/**
 * Learning modules are OUTSOURCED from established platforms (YouTube medical
 * educators, Osmosis, Radiopaedia, PubMed, NEJM) rather than reproduced. We
 * link out, embed where allowed, and (with permission) track progress in
 * Supabase.
 */
type Kind = "Video" | "Course" | "Article" | "Interactive";

interface Module {
  id: string;
  title: string;
  provider: string;
  kind: Kind;
  topic: string;
  duration: string;
  url: string;
  youtubeId?: string; // if embeddable
}

const MODULES: Module[] = [
  { id: "ecg-basics", title: "ECG Interpretation — The Basics", provider: "Ninja Nerd", kind: "Video", topic: "Cardiology", duration: "48 min", url: "https://www.youtube.com/watch?v=OI4YHNc9wxc", youtubeId: "OI4YHNc9wxc" },
  { id: "acs-approach", title: "Acute Coronary Syndrome — Approach", provider: "Armando Hasudungan", kind: "Video", topic: "Cardiology", duration: "22 min", url: "https://www.youtube.com/watch?v=jDLmzPa2c9Q", youtubeId: "jDLmzPa2c9Q" },
  { id: "dka-osmosis", title: "Diabetic Ketoacidosis", provider: "Osmosis", kind: "Video", topic: "Endocrinology", duration: "12 min", url: "https://www.youtube.com/watch?v=uNsGDN9F5CQ", youtubeId: "uNsGDN9F5CQ" },
  { id: "sepsis-3", title: "Sepsis-3 Definitions & Early Management", provider: "PubMed / JAMA", kind: "Article", topic: "Critical Care", duration: "20 min read", url: "https://pubmed.ncbi.nlm.nih.gov/26903338/" },
  { id: "cxr-radiopaedia", title: "Chest X-ray Interpretation Course", provider: "Radiopaedia", kind: "Interactive", topic: "Radiology", duration: "Self-paced", url: "https://radiopaedia.org/articles/chest-radiograph" },
  { id: "stroke-nejm", title: "Acute Ischaemic Stroke — Review", provider: "NEJM", kind: "Article", topic: "Neurology", duration: "25 min read", url: "https://www.nejm.org/doi/full/10.1056/NEJMra1917544" },
];

const KIND_ICON: Record<Kind, typeof PlayCircle> = { Video: PlayCircle, Course: MonitorPlay, Article: BookOpen, Interactive: MonitorPlay };
const TOPICS = ["All", "Cardiology", "Endocrinology", "Critical Care", "Radiology", "Neurology"];

export function Modules() {
  const { tracking, progress } = useLearningState();
  const [topic, setTopic] = useState("All");
  const [player, setPlayer] = useState<Module | null>(null);

  // Pull the learner's saved progress from Supabase into the local mirror.
  useEffect(() => { hydrateLearning(); }, []);

  const list = topic === "All" ? MODULES : MODULES.filter((m) => m.topic === topic);
  const overall = MODULES.length ? Math.round(MODULES.reduce((s, m) => s + (progress[m.id] ?? 0), 0) / MODULES.length) : 0;
  const completed = MODULES.filter((m) => (progress[m.id] ?? 0) >= 100).length;

  const open = (m: Module) => {
    if (m.youtubeId) setPlayer(m);
    else {
      window.open(m.url, "_blank");
      if (tracking) setProgress(m.id, Math.min(100, getProgress(m.id) + 34)); // count a visit
    }
  };

  return (
    <PageShell icon={GraduationCap} title="Learning Modules & Videos" subtitle="Curated from the best medical-education platforms — watch, read, and track your progress." wide>
      {/* Permission banner */}
      <div className="rounded-2xl p-4 mb-5 flex items-start gap-3" style={{ background: tracking ? "color-mix(in oklab, var(--success) 8%, white)" : "color-mix(in oklab, var(--warning) 12%, white)" }}>
        {tracking ? <ShieldCheck className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "var(--success)" }} /> : <ShieldOff className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />}
        <div className="flex-1">
          <div className="text-sm font-semibold">Progress tracking is {tracking ? "on" : "off"}</div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {tracking
              ? "We save how far you get through each module in your account, so you can resume and see your growth. You can turn this off anytime."
              : "Nothing is saved. You can still open every module, but the platform keeps no record of your progress."}
          </p>
        </div>
        <button onClick={() => setTrackingEnabled(!tracking)} className="w-11 h-6 rounded-full p-0.5 transition-colors shrink-0 mt-0.5"
          style={{ background: tracking ? "var(--brand)" : "var(--muted)" }}>
          <span className="block w-5 h-5 rounded-full bg-white shadow-sm transition-transform" style={{ transform: tracking ? "translateX(20px)" : "none" }} />
        </button>
      </div>

      {/* Overall progress (only when tracking) */}
      {tracking && (
        <div className="soft-card p-5 mb-5 flex items-center gap-5">
          <Ring value={overall} label={`${overall}%`} sub="overall" />
          <div>
            <div className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Your learning progress</div>
            <p className="text-sm text-muted-foreground mt-0.5">{completed} of {MODULES.length} modules completed · {MODULES.length - completed} in progress or not started</p>
          </div>
        </div>
      )}

      {/* Topic filter */}
      <div className="flex flex-wrap gap-2 mb-5">
        {TOPICS.map((t) => (
          <button key={t} onClick={() => setTopic(t)} className="text-sm px-3.5 py-1.5 rounded-full transition-all"
            style={topic === t ? { background: "var(--brand)", color: "white", fontWeight: 600 } : { background: "var(--muted)", color: "var(--muted-foreground)" }}>
            {t}
          </button>
        ))}
      </div>

      {/* Module grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list.map((m) => {
          const Icon = KIND_ICON[m.kind];
          const pct = tracking ? (progress[m.id] ?? 0) : 0;
          const done = pct >= 100;
          return (
            <div key={m.id} className="soft-card p-4 flex flex-col">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded-xl grid place-items-center bg-chip text-brand"><Icon className="w-5 h-5" /></div>
                <Pill tone="neutral">{m.kind}</Pill>
              </div>
              <div className="mt-3 flex-1">
                <div className="text-sm font-semibold leading-snug" style={{ fontFamily: "var(--font-heading)" }}>{m.title}</div>
                <div className="text-[11px] text-muted-foreground mt-1">{m.provider} · {m.topic}</div>
                <div className="flex items-center gap-1 text-[11px] text-muted-foreground mt-1"><Clock className="w-3 h-3" /> {m.duration}</div>
              </div>

              {tracking && (
                <div className="mt-3">
                  <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: done ? "var(--success)" : "var(--brand)" }} />
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-1">{done ? "Completed" : pct > 0 ? `${pct}% watched` : "Not started"}</div>
                </div>
              )}

              <div className="mt-3 flex gap-2">
                <button onClick={() => open(m)} className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg gradient-brand text-white text-xs font-semibold">
                  {done ? <>Rewatch</> : pct > 0 ? <>Resume</> : <><PlayCircle className="w-3.5 h-3.5" /> {m.kind === "Article" ? "Read" : "Start"}</>}
                </button>
                <a href={m.url} target="_blank" rel="noreferrer" className="w-9 grid place-items-center rounded-lg border" title="Open source"><ExternalLink className="w-3.5 h-3.5" /></a>
              </div>
            </div>
          );
        })}
      </div>

      {player && <PlayerModal module={player} tracking={tracking} onClose={() => setPlayer(null)} />}
    </PageShell>
  );
}

function PlayerModal({ module, tracking, onClose }: { module: Module; tracking: boolean; onClose: () => void }) {
  const [watched, setWatched] = useState(getProgress(module.id));
  const markComplete = () => { if (tracking) setProgress(module.id, 100); setWatched(100); };
  const markQuarter = () => { if (tracking) { const n = Math.min(100, getProgress(module.id) + 25); setProgress(module.id, n); setWatched(n); } };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="soft-card p-4 w-full max-w-2xl animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{module.title}</div>
          <button onClick={onClose} className="w-8 h-8 grid place-items-center rounded-lg hover:bg-black/5"><X className="w-4 h-4" /></button>
        </div>
        <div className="rounded-xl overflow-hidden bg-black" style={{ aspectRatio: "16/9" }}>
          <iframe
            title={module.title}
            src={`https://www.youtube.com/embed/${module.youtubeId}`}
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
        {tracking ? (
          <div className="mt-3 flex items-center gap-3">
            <div className="flex-1">
              <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
                <div className="h-full rounded-full" style={{ width: `${watched}%`, background: watched >= 100 ? "var(--success)" : "var(--brand)" }} />
              </div>
              <div className="text-[11px] text-muted-foreground mt-1">{watched >= 100 ? "Completed ✓" : `${watched}% watched`}</div>
            </div>
            <button onClick={markQuarter} className="text-xs px-3 py-1.5 rounded-lg border">+25%</button>
            <button onClick={markComplete} className="text-xs px-3 py-1.5 rounded-lg gradient-brand text-white font-semibold flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Mark complete</button>
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground mt-3">Progress tracking is off — turn it on to save how far you watch.</p>
        )}
      </div>
    </div>
  );
}
