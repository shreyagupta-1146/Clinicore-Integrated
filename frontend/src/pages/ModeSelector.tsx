import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Stethoscope, HeartPulse, GraduationCap, ArrowRight, ShieldCheck, Lock } from "lucide-react";

type ModeKey = "clinicore" | "relaymed" | "clinmed";

const MODES: {
  key: ModeKey;
  name: string;
  tag: string;
  desc: string;
  icon: typeof Stethoscope;
  accent: string;
  accent2: string;
  auth: string;
  preview: string[];
}[] = [
  {
    key: "clinicore",
    name: "Clinicore",
    tag: "Professional",
    desc: "Clinical decision support for licensed clinicians & facilities.",
    icon: Stethoscope,
    accent: "oklch(0.55 0.14 245)",
    accent2: "oklch(0.4 0.12 250)",
    auth: "Institutional / admin sign-in · MFA",
    preview: ["Patient roster", "AI consult workspace", "Audit & consent"],
  },
  {
    key: "relaymed",
    name: "RelayMed",
    tag: "Personal",
    desc: "Track your health, medications & share with the people who care for you.",
    icon: HeartPulse,
    accent: "oklch(0.62 0.12 160)",
    accent2: "oklch(0.55 0.12 170)",
    auth: "Personal account · Google / OTP",
    preview: ["Vitals & trends", "Medication adherence", "Caregiver hub"],
  },
  {
    key: "clinmed",
    name: "Clinmed",
    tag: "Learn",
    desc: "Sharpen diagnostic skill with realistic case simulations under pressure.",
    icon: GraduationCap,
    accent: "oklch(0.68 0.12 65)",
    accent2: "oklch(0.5 0.09 200)",
    auth: "Student / educator account",
    preview: ["Case library", "Diagnosis simulator", "Progress & leaderboard"],
  },
];

export function ModeSelector() {
  const navigate = useNavigate();
  const [hover, setHover] = useState<ModeKey | null>(null);

  const ambient =
    hover === "clinicore"
      ? "radial-gradient(1200px 800px at 50% -10%, oklch(0.93 0.06 245 / 0.55), transparent 60%)"
      : hover === "relaymed"
        ? "radial-gradient(1200px 800px at 50% -10%, oklch(0.93 0.06 160 / 0.55), transparent 60%)"
        : hover === "clinmed"
          ? "radial-gradient(1200px 800px at 50% -10%, oklch(0.93 0.06 80 / 0.6), transparent 60%)"
          : "transparent";

  return (
    <div className="min-h-screen relative">
      <div className="pointer-events-none fixed inset-0 transition-all duration-500" style={{ background: ambient }} />
      <div className="relative max-w-6xl mx-auto px-6 py-12 md:py-20">
        {/* Wordmark */}
        <div className="text-center animate-fade-in">
          <div className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-6"
            style={{ background: "white", boxShadow: "var(--shadow-soft)" }}>
            <ShieldCheck className="w-3.5 h-3.5" style={{ color: "var(--brand)" }} /> DPDP Act 2023 · ABDM-ready · India-first
          </div>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight" style={{ fontFamily: "Fraunces, serif" }}>
            Clinicore
          </h1>
          <p className="text-base md:text-lg text-muted-foreground mt-3">One platform. Three ways to care.</p>
        </div>

        {/* Mode cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-12">
          {MODES.map((m, i) => {
            const Icon = m.icon;
            return (
              <button
                key={m.key}
                onMouseEnter={() => setHover(m.key)}
                onMouseLeave={() => setHover(null)}
                onClick={() => navigate(`/${m.key}`)}
                className="text-left soft-card p-6 transition-all duration-300 hover:-translate-y-1.5 animate-fade-in group"
                style={{
                  animationDelay: `${i * 90}ms`,
                  borderColor: hover === m.key ? m.accent : undefined,
                  boxShadow: hover === m.key ? `0 24px 60px -24px ${m.accent}` : undefined,
                }}
              >
                <div
                  className="w-14 h-14 rounded-2xl grid place-items-center text-white shadow-md"
                  style={{ background: `linear-gradient(135deg, ${m.accent}, ${m.accent2})` }}
                >
                  <Icon className="w-7 h-7" />
                </div>

                <div className="mt-5 flex items-center gap-2">
                  <h2 className="text-2xl font-semibold" style={{ fontFamily: "Fraunces, serif" }}>{m.name}</h2>
                  <span
                    className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                    style={{ background: `color-mix(in oklab, ${m.accent} 14%, white)`, color: m.accent }}
                  >
                    {m.tag}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed min-h-[60px]">{m.desc}</p>

                <ul className="mt-3 space-y-1.5">
                  {m.preview.map((p) => (
                    <li key={p} className="flex items-center gap-2 text-xs text-foreground/70">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: m.accent }} /> {p}
                    </li>
                  ))}
                </ul>

                <div className="mt-5 pt-4 flex items-center justify-between" style={{ borderTop: "1px solid var(--border)" }}>
                  <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <Lock className="w-3 h-3" /> {m.auth}
                  </span>
                  <span
                    className="flex items-center gap-1 text-sm font-semibold transition-transform group-hover:translate-x-1"
                    style={{ color: m.accent }}
                  >
                    Continue <ArrowRight className="w-4 h-4" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <p className="text-center text-xs text-muted-foreground mt-12">
          Hybrid-sovereignty AI · Raw PHI never leaves the on-prem boundary · You control your data.
        </p>
      </div>
    </div>
  );
}
