import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

/* ---- Icon chip (rounded gradient tile holding an icon) ---- */
export function IconChip({
  icon: Icon,
  className,
  size = "md",
}: {
  icon: LucideIcon;
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const dims = size === "sm" ? "w-8 h-8" : size === "lg" ? "w-12 h-12" : "w-11 h-11";
  const isz = size === "sm" ? "w-4 h-4" : size === "lg" ? "w-6 h-6" : "w-5 h-5";
  return (
    <div className={cn(dims, "rounded-2xl grid place-items-center text-white gradient-brand shrink-0", className)}>
      <Icon className={isz} />
    </div>
  );
}

/* ---- Tone dot (status indicator) ---- */
export function ToneDot({ tone }: { tone: "good" | "warn" | "bad" | "neutral" }) {
  const color =
    tone === "good"
      ? "var(--success)"
      : tone === "warn"
        ? "var(--warning)"
        : tone === "bad"
          ? "var(--coral)"
          : "var(--muted-foreground)";
  return <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: color }} />;
}

/* ---- Status pill ---- */
export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "good" | "warn" | "bad" | "neutral" | "brand";
}) {
  const map: Record<string, string> = {
    good: "color-mix(in oklab, var(--success) 16%, white)",
    warn: "color-mix(in oklab, var(--warning) 22%, white)",
    bad: "color-mix(in oklab, var(--coral) 15%, white)",
    brand: "color-mix(in oklab, var(--brand) 14%, white)",
    neutral: "var(--muted)",
  };
  const text: Record<string, string> = {
    good: "var(--success)",
    warn: "color-mix(in oklab, var(--warning) 60%, black)",
    bad: "var(--coral)",
    brand: "var(--brand)",
    neutral: "var(--muted-foreground)",
  };
  return (
    <span
      className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full whitespace-nowrap"
      style={{ background: map[tone], color: text[tone] }}
    >
      {children}
    </span>
  );
}

/* ---- Section card ---- */
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("soft-card p-6 animate-fade-in", className)}>{children}</div>;
}

/* ---- Card header with icon ---- */
export function CardHead({
  icon: Icon,
  title,
  subtitle,
  action,
}: {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <IconChip icon={Icon} />
      <div className="min-w-0">
        <h2 className="font-[var(--font-heading)] text-xl font-semibold leading-tight" style={{ fontFamily: "var(--font-heading)" }}>
          {title}
        </h2>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      {action && <div className="ml-auto">{action}</div>}
    </div>
  );
}

/* ---- Simple progress bar ---- */
export function Bar({ value, tone = "brand" }: { value: number; tone?: "brand" | "good" | "warn" | "bad" }) {
  const color =
    tone === "good" ? "var(--success)" : tone === "warn" ? "var(--warning)" : tone === "bad" ? "var(--coral)" : "var(--brand)";
  return (
    <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, value)}%`, background: color }} />
    </div>
  );
}

/* ---- Circular progress ring ---- */
export function Ring({ value, label, sub }: { value: number; label: string; sub?: string }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const off = c - (value / 100) * c;
  return (
    <div className="relative w-24 h-24 grid place-items-center">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="var(--muted)" strokeWidth="7" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="var(--brand)"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-lg font-bold" style={{ fontFamily: "var(--font-heading)" }}>{label}</div>
        {sub && <div className="text-[9px] text-muted-foreground">{sub}</div>}
      </div>
    </div>
  );
}
