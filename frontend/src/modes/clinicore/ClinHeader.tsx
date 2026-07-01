import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

export function ClinHeader({ icon: Icon, title, subtitle, action }: { icon: LucideIcon; title: string; subtitle: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 mb-5 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg grid place-items-center text-white" style={{ background: "var(--brand)" }}><Icon className="w-5 h-5" /></div>
        <div>
          <h1 className="text-xl font-semibold" style={{ fontFamily: "Inter, sans-serif" }}>{title}</h1>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {action}
    </div>
  );
}
