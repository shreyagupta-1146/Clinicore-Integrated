import { ReactNode, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, Stethoscope, FileCheck2, ScrollText, Network,
  ShieldAlert, Search, Server, Cloud, LogOut, Grid3x3, ChevronDown, Bell, FolderClosed, HeartPulse,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const NAV = [
  { to: "/clinicore", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/clinicore/roster", label: "Patient Roster", icon: Users },
  { to: "/clinicore/consultation", label: "Consultation", icon: Stethoscope },
  { to: "/clinicore/folders", label: "Folders & Sharing", icon: FolderClosed },
  { to: "/clinicore/consent", label: "Consent", icon: FileCheck2 },
  { to: "/clinicore/audit", label: "Audit Trail", icon: ScrollText },
  { to: "/clinicore/abdm", label: "ABDM Exchange", icon: Network },
  { to: "/clinicore/admin", label: "Admin & SecOps", icon: ShieldAlert, adminOnly: true },
  { to: "/clinicore/self-healing", label: "Self-Healing (SRE)", icon: HeartPulse, adminOnly: true },
];

export function ClinicoreLayout({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [route, setRoute] = useState<"onprem" | "cloud">("onprem");
  const isAdmin = user?.role === "facility_admin" || user?.role === "platform_admin";
  const name = user?.name || "Clinician";
  const initial = name.charAt(0).toUpperCase();

  return (
    <div className="flex min-h-screen">
      {/* Navy icon+label sidebar */}
      <aside className="w-[240px] shrink-0 h-screen sticky top-0 hidden lg:flex flex-col text-white" style={{ background: "var(--navy)" }}>
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="w-9 h-9 rounded-lg grid place-items-center" style={{ background: "var(--brand)" }}><Stethoscope className="w-5 h-5" /></div>
          <div>
            <div className="text-base font-semibold leading-tight">Clinicore</div>
            <div className="text-[10px] text-white/50">Clinical Decision Support</div>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-0.5 mt-2">
          {NAV.filter((n) => !n.adminOnly || isAdmin).map((item) => {
            const active = item.end ? loc.pathname === item.to : loc.pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link key={item.to} to={item.to} className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all"
                style={active ? { background: "rgba(255,255,255,0.12)", fontWeight: 600 } : { color: "rgba(255,255,255,0.65)" }}>
                <Icon className="w-[18px] h-[18px]" /> {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3">
          <div className="rounded-lg p-3" style={{ background: "rgba(255,255,255,0.08)" }}>
            <div className="text-[10px] text-white/50 uppercase tracking-wide">Signed in</div>
            <div className="text-sm font-medium mt-0.5 truncate">{name}</div>
            <div className="text-[10px] text-white/50 capitalize">{user?.role?.replace("_", " ")} · {user?.facility?.split(",")[0]}</div>
            <div className="flex gap-2 mt-2">
              <button onClick={() => navigate("/")} className="flex-1 flex items-center justify-center gap-1 text-[11px] py-1.5 rounded-md" style={{ background: "rgba(255,255,255,0.1)" }}><Grid3x3 className="w-3 h-3" /> Switch</button>
              <button onClick={logout} className="flex-1 flex items-center justify-center gap-1 text-[11px] py-1.5 rounded-md" style={{ background: "rgba(255,255,255,0.1)" }}><LogOut className="w-3 h-3" /> Out</button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Command bar */}
        <header className="sticky top-0 z-30 flex items-center gap-3 px-4 md:px-6 py-3 border-b bg-card/80 backdrop-blur">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-card flex-1 max-w-md">
            <Search className="w-4 h-4 text-muted-foreground" />
            <input placeholder="Search patients, ABHA ID…" className="flex-1 bg-transparent outline-none text-sm" />
          </div>
          {/* De-identification / routing indicator */}
          <button onClick={() => setRoute(route === "onprem" ? "cloud" : "onprem")}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-colors"
            style={route === "onprem"
              ? { background: "color-mix(in oklab, var(--brand) 12%, white)", color: "var(--brand)" }
              : { background: "color-mix(in oklab, var(--teal) 16%, white)", color: "color-mix(in oklab, var(--teal) 60%, black)" }}>
            {route === "onprem" ? <Server className="w-3.5 h-3.5" /> : <Cloud className="w-3.5 h-3.5" />}
            {route === "onprem" ? "On-Prem · Raw PHI" : "Cloud · De-identified"}
          </button>
          <button className="w-9 h-9 grid place-items-center rounded-lg border bg-card"><Bell className="w-4 h-4" /></button>
          <button className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg border bg-card">
            <div className="w-7 h-7 rounded-full grid place-items-center text-white text-xs font-semibold" style={{ background: "var(--brand)" }}>{initial}</div>
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          </button>
        </header>
        <main className="flex-1 px-4 md:px-6 py-6">{children}</main>
        <footer className="px-6 py-3 text-[11px] text-muted-foreground border-t flex items-center justify-between">
          <span>Decision support only — final judgment rests with the clinician.</span>
          <span>All access is audit-logged · DPDP Act 2023</span>
        </footer>
      </div>
    </div>
  );
}
