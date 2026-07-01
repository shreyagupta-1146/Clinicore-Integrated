import { ReactNode } from "react";
import { LucideIcon, Lock, ShieldCheck, EyeOff, UserCheck } from "lucide-react";
import { IconChip } from "./ui";

export function PageShell({
  icon,
  title,
  subtitle,
  children,
  wide,
  footer = true,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  children: ReactNode;
  wide?: boolean;
  footer?: boolean;
}) {
  return (
    <div className={wide ? "" : "max-w-6xl"}>
      <div className="soft-card p-6 animate-fade-in">
        <div className="flex items-center gap-3 mb-5">
          <IconChip icon={icon} />
          <div>
            <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{title}</h2>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        {children}
      </div>
      {footer && <SecurityFooter />}
    </div>
  );
}

export function SecurityFooter() {
  const items = [
    { icon: Lock, text: "AES-256 Encrypted" },
    { icon: ShieldCheck, text: "No Data Selling" },
    { icon: EyeOff, text: "Privacy Preserved" },
    { icon: UserCheck, text: "You Control Your Data" },
  ];
  return (
    <footer className="soft-card mt-6 p-4 flex flex-wrap items-center justify-between gap-4 animate-fade-in">
      <div className="text-xs text-muted-foreground">Your data is private, secure, and always under your control.</div>
      <div className="flex flex-wrap items-center gap-5">
        {items.map(({ icon: Icon, text }) => (
          <div key={text} className="flex items-center gap-2 text-xs text-foreground/70">
            <Icon className="w-3.5 h-3.5 text-brand" /> {text}
          </div>
        ))}
      </div>
    </footer>
  );
}
