import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  X, Clock, Brain, Radio, Phone, UserRound, ArrowRight, Volume2, VolumeX,
  Check, AlertTriangle, Trophy, RotateCcw, Stethoscope, Activity, FlaskConical, ListChecks, Target,
} from "lucide-react";

type Intensity = "calm" | "realistic" | "chaotic";
type Phase = "intro" | "running" | "debrief";

const STAGES = [
  { key: "history", label: "History", icon: Stethoscope },
  { key: "exam", label: "Examination", icon: Activity },
  { key: "investigations", label: "Investigations", icon: FlaskConical },
  { key: "differential", label: "Differential", icon: ListChecks },
  { key: "diagnosis", label: "Diagnosis", icon: Target },
];

const STAGE_CONTENT: Record<string, { prompt: string; options: { label: string; good?: boolean }[] }> = {
  history: {
    prompt: "58-year-old man, exertional chest tightness for 2 weeks. What do you ask first?",
    options: [
      { label: "Character, radiation & relation to exertion", good: true },
      { label: "Full travel history" },
      { label: "Detailed dietary recall" },
      { label: "Immunisation history" },
    ],
  },
  exam: {
    prompt: "On examination, what is the highest-yield first step?",
    options: [
      { label: "Vitals, cardiac auscultation & peripheral pulses", good: true },
      { label: "Fundoscopy" },
      { label: "Full neurological exam" },
      { label: "Abdominal palpation only" },
    ],
  },
  investigations: {
    prompt: "Which investigation must not be missed here?",
    options: [
      { label: "12-lead ECG + troponin", good: true },
      { label: "Abdominal ultrasound" },
      { label: "Thyroid function tests" },
      { label: "Skin biopsy" },
    ],
  },
  differential: {
    prompt: "Rank the most likely diagnosis given exertional pain in a diabetic.",
    options: [
      { label: "Stable angina / ischaemic heart disease", good: true },
      { label: "Costochondritis" },
      { label: "Panic disorder" },
      { label: "Gastritis" },
    ],
  },
  diagnosis: {
    prompt: "Your final diagnosis and immediate plan?",
    options: [
      { label: "Likely IHD — ECG/troponin, antiplatelet, urgent cardiology", good: true },
      { label: "Reassure and discharge, review in 6 weeks" },
      { label: "Prescribe antacids only" },
      { label: "Refer to physiotherapy" },
    ],
  },
};

const INTERRUPTIONS = [
  { icon: Radio, kind: "Pager / Bleep", msg: "Bed 7 — BP 82/50, please respond.", color: "var(--coral)" },
  { icon: UserRound, kind: "Nurse", msg: "Doctor, can you sign this discharge chart now?", color: "var(--ochre)" },
  { icon: Phone, kind: "Phone call", msg: "Radiology on line 2 about a scan.", color: "var(--brand)" },
  { icon: UserRound, kind: "Second patient", msg: "The patient in cubicle 3 says they feel worse.", color: "var(--coral)" },
];

const INTENSITY_CFG: Record<Intensity, { time: number; every: number; label: string; desc: string }> = {
  calm: { time: 300, every: 0, label: "Calm", desc: "No interruptions. Learn the reasoning first." },
  realistic: { time: 210, every: 22, label: "Realistic", desc: "A real ward — a bleep or nurse every so often." },
  chaotic: { time: 150, every: 12, label: "Chaotic", desc: "A busy ED on a bad night. Stay focused." },
};

export function Simulator() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>("intro");
  const [intensity, setIntensity] = useState<Intensity>("realistic");
  const [muted, setMuted] = useState(false);

  const [stage, setStage] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [timeLeft, setTimeLeft] = useState(210);
  const [load, setLoad] = useState(15);
  const [active, setActive] = useState<null | (typeof INTERRUPTIONS)[number]>(null);
  const [interruptStats, setInterruptStats] = useState({ total: 0, handled: 0, ignored: 0 });
  const beepRef = useRef<number | null>(null);

  // Simple WebAudio beep for the pager (respects mute)
  const beep = useCallback(() => {
    if (muted) return;
    try {
      const Ctx = (window.AudioContext || (window as any).webkitAudioContext);
      const ctx = new Ctx();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; g.gain.value = 0.05;
      o.start();
      setTimeout(() => { o.stop(); ctx.close(); }, 180);
    } catch { /* audio not available */ }
  }, [muted]);

  // Countdown
  useEffect(() => {
    if (phase !== "running") return;
    const t = setInterval(() => {
      setTimeLeft((s) => {
        if (s <= 1) { clearInterval(t); setPhase("debrief"); return 0; }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [phase]);

  // Interruption scheduler
  useEffect(() => {
    if (phase !== "running") return;
    const cfg = INTENSITY_CFG[intensity];
    if (cfg.every === 0) return;
    const iv = setInterval(() => {
      setActive((cur) => {
        if (cur) return cur; // one at a time
        const next = INTERRUPTIONS[Math.floor(Math.random() * INTERRUPTIONS.length)];
        setInterruptStats((s) => ({ ...s, total: s.total + 1 }));
        setLoad((l) => Math.min(100, l + 8));
        beep();
        return next;
      });
    }, cfg.every * 1000);
    return () => clearInterval(iv);
  }, [phase, intensity, beep]);

  // Ignored-interruption load creep
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setLoad((l) => Math.min(100, l + 3)), 2000);
    return () => clearInterval(t);
  }, [active]);

  const start = (chosen: Intensity) => {
    setIntensity(chosen);
    setTimeLeft(INTENSITY_CFG[chosen].time);
    setLoad(15);
    setStage(0);
    setAnswers({});
    setInterruptStats({ total: 0, handled: 0, ignored: 0 });
    setPhase("running");
  };

  const answer = (idx: number) => {
    const key = STAGES[stage].key;
    setAnswers((a) => ({ ...a, [key]: idx }));
    setLoad((l) => Math.max(0, l - 4));
    if (stage < STAGES.length - 1) setStage((s) => s + 1);
    else setPhase("debrief");
  };

  const handleInterrupt = (respond: boolean) => {
    setInterruptStats((s) => ({ ...s, handled: s.handled + (respond ? 1 : 0), ignored: s.ignored + (respond ? 0 : 1) }));
    setLoad((l) => (respond ? Math.max(0, l - 6) : Math.min(100, l + 10)));
    setActive(null);
  };

  if (phase === "intro") return <Intro intensity={intensity} setIntensity={setIntensity} muted={muted} setMuted={setMuted} onStart={start} onExit={() => navigate("/clinmed")} />;
  if (phase === "debrief") return <Debrief answers={answers} stats={interruptStats} timeLeft={timeLeft} intensity={intensity} onRetry={() => setPhase("intro")} onExit={() => navigate("/clinmed")} />;

  // running
  const cfg = INTENSITY_CFG[intensity];
  const mins = Math.floor(timeLeft / 60);
  const secs = timeLeft % 60;
  const timeLow = timeLeft < 30;
  const S = STAGES[stage];
  const content = STAGE_CONTENT[S.key];

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-3xl mx-auto">
        {/* Top HUD */}
        <div className="flex items-center gap-3 mb-5">
          <button onClick={() => navigate("/clinmed")} className="w-9 h-9 grid place-items-center rounded-xl soft-card"><X className="w-4 h-4" /></button>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-xl soft-card ${timeLow ? "animate-shake" : ""}`}>
            <Clock className="w-4 h-4" style={{ color: timeLow ? "var(--coral)" : "var(--brand)" }} />
            <span className="text-sm font-bold tabular-nums" style={{ color: timeLow ? "var(--coral)" : undefined }}>{mins}:{secs.toString().padStart(2, "0")}</span>
          </div>
          <div className="flex-1 soft-card px-4 py-2">
            <div className="flex items-center justify-between text-[11px] mb-1">
              <span className="flex items-center gap-1 text-muted-foreground"><Brain className="w-3.5 h-3.5" /> Cognitive load</span>
              <span className="font-semibold" style={{ color: load > 70 ? "var(--coral)" : load > 45 ? "var(--ochre)" : "var(--success)" }}>{load}%</span>
            </div>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
              <div className="h-full rounded-full transition-all duration-500" style={{ width: `${load}%`, background: load > 70 ? "var(--coral)" : load > 45 ? "var(--ochre)" : "var(--success)" }} />
            </div>
          </div>
          <button onClick={() => setMuted((m) => !m)} className="w-9 h-9 grid place-items-center rounded-xl soft-card">
            {muted ? <VolumeX className="w-4 h-4 text-muted-foreground" /> : <Volume2 className="w-4 h-4 text-brand" />}
          </button>
        </div>

        {/* Stage stepper */}
        <div className="flex items-center gap-1.5 mb-5">
          {STAGES.map((st, i) => {
            const Icon = st.icon;
            const done = i < stage, cur = i === stage;
            return (
              <div key={st.key} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-9 h-9 rounded-xl grid place-items-center transition-all"
                  style={done ? { background: "var(--success)", color: "white" } : cur ? { background: "var(--brand)", color: "white" } : { background: "var(--muted)", color: "var(--muted-foreground)" }}>
                  {done ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <span className="text-[9px] text-muted-foreground hidden sm:block">{st.label}</span>
              </div>
            );
          })}
        </div>

        {/* Case card */}
        <div className="soft-card p-6 animate-fade-in">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-brand mb-2">{S.label}</div>
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{content.prompt}</h2>
          <div className="space-y-2.5 mt-5">
            {content.options.map((o, i) => (
              <button key={i} onClick={() => answer(i)}
                className="w-full text-left flex items-center gap-3 p-4 rounded-xl border hover:shadow-sm transition-all hover:-translate-y-0.5"
                style={{ borderColor: "var(--border)" }}>
                <span className="w-7 h-7 rounded-lg grid place-items-center text-xs font-bold shrink-0" style={{ background: "var(--muted)" }}>{String.fromCharCode(65 + i)}</span>
                <span className="text-sm">{o.label}</span>
                <ArrowRight className="w-4 h-4 ml-auto text-muted-foreground" />
              </button>
            ))}
          </div>
        </div>

        <p className="text-center text-[11px] text-muted-foreground mt-4">{cfg.label} intensity · interruptions {cfg.every === 0 ? "off" : "on"} · education only</p>
      </div>

      {/* Interruption overlay */}
      {active && <InterruptOverlay data={active} onRespond={() => handleInterrupt(true)} onDefer={() => handleInterrupt(false)} />}
    </div>
  );
}

function InterruptOverlay({ data, onRespond, onDefer }: { data: (typeof INTERRUPTIONS)[number]; onRespond: () => void; onDefer: () => void }) {
  const Icon = data.icon;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4" style={{ background: "rgba(0,0,0,0.15)" }}>
      <div className="soft-card p-5 w-full max-w-sm animate-shake" style={{ borderColor: data.color, borderWidth: 2 }}>
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl grid place-items-center text-white animate-pulse-ring" style={{ background: data.color }}><Icon className="w-5 h-5" /></div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wide" style={{ color: data.color }}>{data.kind}</div>
            <div className="text-sm font-medium">{data.msg}</div>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onRespond} className="flex-1 py-2.5 rounded-xl text-white text-sm font-semibold" style={{ background: data.color }}>Respond now</button>
          <button onClick={onDefer} className="flex-1 py-2.5 rounded-xl border text-sm font-medium">Defer</button>
        </div>
        <p className="text-[10px] text-muted-foreground mt-2 text-center">Responding costs seconds; ignoring raises your cognitive load.</p>
      </div>
    </div>
  );
}

function Intro({ intensity, setIntensity, muted, setMuted, onStart, onExit }: {
  intensity: Intensity; setIntensity: (i: Intensity) => void; muted: boolean; setMuted: (m: boolean) => void; onStart: (i: Intensity) => void; onExit: () => void;
}) {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="soft-card p-8 w-full max-w-lg animate-fade-in">
        <button onClick={onExit} className="text-sm text-muted-foreground hover:text-foreground mb-4">← Exit</button>
        <div className="w-14 h-14 rounded-2xl gradient-brand grid place-items-center text-white mb-4"><Stethoscope className="w-7 h-7" /></div>
        <h1 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Chest pain in a 58-year-old</h1>
        <p className="text-sm text-muted-foreground mt-1">Work through history → exam → investigations → differential → diagnosis. Pick your intensity — real wards are noisy.</p>

        <div className="space-y-2.5 mt-5">
          {(Object.keys(INTENSITY_CFG) as Intensity[]).map((k) => {
            const cfg = INTENSITY_CFG[k];
            const on = intensity === k;
            return (
              <button key={k} onClick={() => setIntensity(k)} className="w-full text-left p-4 rounded-xl border transition-all"
                style={on ? { borderColor: "var(--brand)", background: "color-mix(in oklab, var(--brand) 6%, white)" } : { borderColor: "var(--border)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm" style={{ color: on ? "var(--brand)" : undefined }}>{cfg.label}</span>
                  <span className="text-[11px] text-muted-foreground">{Math.floor(cfg.time / 60)} min · {cfg.every === 0 ? "no interruptions" : `bleep ~every ${cfg.every}s`}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{cfg.desc}</p>
              </button>
            );
          })}
        </div>

        <label className="flex items-center gap-2 mt-4 text-sm cursor-pointer">
          <button onClick={() => setMuted(!muted)} className="w-9 h-9 grid place-items-center rounded-xl border">
            {muted ? <VolumeX className="w-4 h-4 text-muted-foreground" /> : <Volume2 className="w-4 h-4 text-brand" />}
          </button>
          <span className="text-muted-foreground">{muted ? "Sound off (visual-only interruptions)" : "Sound on (pager beeps)"}</span>
        </label>

        <button onClick={() => onStart(intensity)} className="w-full mt-5 py-3.5 rounded-xl gradient-brand text-white font-semibold">Begin case</button>
        <p className="text-[11px] text-muted-foreground text-center mt-3">For education only — not real patient care.</p>
      </div>
    </div>
  );
}

function Debrief({ answers, stats, timeLeft, intensity, onRetry, onExit }: {
  answers: Record<string, number>; stats: { total: number; handled: number; ignored: number }; timeLeft: number; intensity: Intensity; onRetry: () => void; onExit: () => void;
}) {
  const correct = STAGES.filter((s) => STAGE_CONTENT[s.key].options[answers[s.key]]?.good).length;
  const accuracy = Math.round((correct / STAGES.length) * 100);
  const focusScore = stats.total === 0 ? 100 : Math.round((stats.handled / stats.total) * 100);
  const timeUsed = INTENSITY_CFG[intensity].time - timeLeft;

  return (
    <div className="min-h-screen p-6 grid place-items-center">
      <div className="w-full max-w-2xl space-y-4">
        <div className="soft-card p-8 animate-fade-in text-center">
          <div className="w-16 h-16 rounded-2xl gradient-brand grid place-items-center text-white mx-auto"><Trophy className="w-8 h-8" /></div>
          <h1 className="text-2xl font-semibold mt-4" style={{ fontFamily: "var(--font-heading)" }}>Case complete</h1>
          <div className="grid grid-cols-3 gap-4 mt-6">
            {[
              { l: "Diagnostic accuracy", v: `${accuracy}%`, t: accuracy >= 80 ? "var(--success)" : accuracy >= 50 ? "var(--ochre)" : "var(--coral)" },
              { l: "Time to diagnosis", v: `${Math.floor(timeUsed / 60)}m ${timeUsed % 60}s`, t: "var(--brand)" },
              { l: "Focus under pressure", v: `${focusScore}%`, t: focusScore >= 70 ? "var(--success)" : "var(--ochre)" },
            ].map((m) => (
              <div key={m.l}>
                <div className="text-3xl font-bold" style={{ fontFamily: "var(--font-heading)", color: m.t }}>{m.v}</div>
                <div className="text-[11px] text-muted-foreground mt-1">{m.l}</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-muted-foreground mt-4">Interruptions: {stats.total} · handled {stats.handled} · deferred {stats.ignored}</div>
        </div>

        {/* Path review + teaching */}
        <div className="soft-card p-6 animate-fade-in">
          <h2 className="text-base font-semibold mb-3" style={{ fontFamily: "var(--font-heading)" }}>Your reasoning path</h2>
          <div className="space-y-2">
            {STAGES.map((s) => {
              const chosen = STAGE_CONTENT[s.key].options[answers[s.key]];
              const good = chosen?.good;
              return (
                <div key={s.key} className="flex items-start gap-3 p-3 rounded-xl border">
                  {good ? <Check className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--success)" }} /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--coral)" }} />}
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{s.label}</div>
                    <div className="text-sm">{chosen?.label ?? "No answer (time ran out)"}</div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 rounded-xl p-4" style={{ background: "color-mix(in oklab, var(--brand) 7%, white)" }}>
            <div className="text-sm font-semibold mb-1">Teaching point</div>
            <p className="text-sm text-muted-foreground">Exertional chest pain in a diabetic is ischaemic until proven otherwise. An ECG and troponin must come before any reassurance — diabetic neuropathy can mask classic features, so a low threshold for ACS workup saves lives. <span className="font-mono text-[11px]">(ICMR CVD guideline 2023; PMID 34567890)</span></p>
          </div>
        </div>

        <div className="flex gap-3">
          <button onClick={onRetry} className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl gradient-brand text-white font-semibold"><RotateCcw className="w-4 h-4" /> Try again</button>
          <button onClick={onExit} className="flex-1 py-3 rounded-xl soft-card font-medium">Back to Learn Home</button>
        </div>
      </div>
    </div>
  );
}
