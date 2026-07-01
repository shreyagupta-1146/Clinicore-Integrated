import { ReactNode, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, HeartPulse, Sparkles, GitBranch, FlaskConical, Bell,
  MessageCircle, Users, BookOpen, ShieldCheck, Settings as SettingsIcon,
  Gem, LogOut, Monitor, ChevronDown, X, RefreshCw, Grid3x3, FileText,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const NAV = [
  { to: "/relaymed", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/relaymed/my-health", label: "My Health", icon: HeartPulse },
  { to: "/relaymed/insights", label: "Health Insights", icon: Sparkles },
  { to: "/relaymed/causal-pathways", label: "Causal Pathways", icon: GitBranch },
  { to: "/relaymed/simulator", label: "What-If Simulator", icon: FlaskConical },
  { to: "/relaymed/alerts", label: "Health Alerts", icon: Bell, badge: 2 },
  { to: "/relaymed/relay-guide", label: "Relay Guide", icon: MessageCircle },
  { to: "/relaymed/caregivers", label: "Caregiver Hub", icon: Users },
  { to: "/relaymed/reports", label: "Wellness Reports", icon: FileText },
  { to: "/relaymed/library", label: "Health Library", icon: BookOpen },
  { to: "/relaymed/trust", label: "Trust Center", icon: ShieldCheck },
  { to: "/relaymed/settings", label: "Settings", icon: SettingsIcon },
];

export function RelayLayout({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showSync, setShowSync] = useState(false);
  const name = user?.name || "there";
  const initial = name.charAt(0).toUpperCase();
  const hour = new Date().getHours();
  const timeGreeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-[260px] shrink-0 h-screen sticky top-0 p-4 hidden lg:block">
        <div className="soft-card h-full flex flex-col p-4">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-11 h-11 rounded-2xl gradient-brand grid place-items-center text-white shadow-md">
              <HeartPulse className="w-5 h-5" />
            </div>
            <div>
              <div className="text-lg font-semibold leading-tight" style={{ fontFamily: "var(--font-heading)" }}>RelayMed</div>
              <div className="text-[11px] text-muted-foreground">Your AI Health Companion</div>
            </div>
          </div>

          <nav className="mt-5 flex-1 space-y-1 overflow-y-auto">
            {NAV.map((item) => {
              const active = item.end ? loc.pathname === item.to : loc.pathname.startsWith(item.to);
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className="group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all"
                  style={
                    active
                      ? { background: "color-mix(in oklab, var(--brand) 12%, white)", color: "var(--brand)", fontWeight: 600 }
                      : { color: "var(--muted-foreground)" }
                  }
                >
                  <Icon className="w-[18px] h-[18px]" />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ color: "var(--coral)", background: "color-mix(in oklab, var(--coral) 18%, transparent)" }}>
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="mt-4 rounded-2xl p-4" style={{ background: "color-mix(in oklab, var(--brand) 10%, white)" }}>
            <div className="flex items-center gap-2 text-brand font-medium text-sm">
              <Gem className="w-4 h-4" /> Upgrade to Pro
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 leading-snug">Longer forecasts & personalized recommendations.</p>
            <button className="mt-3 w-full neu-btn rounded-xl py-2 text-xs font-semibold text-brand">Upgrade Now</button>
          </div>

          <div className="mt-3 flex items-center gap-3 p-2 rounded-2xl group">
            <div className="relative">
              <div className="w-10 h-10 rounded-full gradient-brand grid place-items-center text-white font-semibold">{initial}</div>
              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full ring-2 ring-white" style={{ background: "var(--success)" }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{name}</div>
              <div className="text-[11px] text-muted-foreground">Personal account</div>
            </div>
            <button onClick={() => navigate("/")} title="Switch mode" className="text-muted-foreground hover:text-foreground">
              <Grid3x3 className="w-4 h-4" />
            </button>
            <button onClick={logout} title="Sign out" className="text-muted-foreground hover:text-foreground">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 px-4 md:px-6 pb-10">
        <header className="flex items-center justify-between pt-6 pb-6 animate-fade-in gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl md:text-4xl font-semibold tracking-tight truncate">
              {timeGreeting}, {name} <span className="inline-block animate-float">🌿</span>
            </h1>
            <p className="text-sm text-muted-foreground mt-1 hidden sm:block">Here's your health at a glance today.</p>
          </div>
          <div className="flex items-center gap-2 md:gap-3 shrink-0">
            <button onClick={() => setShowSync(true)} className="neu-btn flex items-center gap-2 text-sm px-3 md:px-4 py-2.5 rounded-2xl">
              <Monitor className="w-4 h-4" /> <span className="hidden md:inline">Sync</span>
            </button>
            <Link to="/relaymed/alerts" className="relative neu-btn w-11 h-11 grid place-items-center rounded-2xl">
              <Bell className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 w-5 h-5 text-[10px] font-bold rounded-full grid place-items-center text-white" style={{ background: "var(--coral)" }}>2</span>
            </Link>
            <Link to="/relaymed/settings" className="neu-btn flex items-center gap-2 pl-1 pr-2 py-1 rounded-2xl">
              <div className="w-8 h-8 rounded-full gradient-brand grid place-items-center text-white text-xs font-semibold">{initial}</div>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </Link>
          </div>
        </header>
        {children}
      </main>

      {showSync && <SyncModal onClose={() => setShowSync(false)} />}
    </div>
  );
}

function SyncModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="soft-card p-6 w-full max-w-md animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Sync Devices</h3>
          <button onClick={onClose} className="w-8 h-8 grid place-items-center rounded-lg hover:bg-black/5"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-muted-foreground mb-4">Your data syncs automatically across all devices signed into the same account.</p>
        <div className="space-y-3">
          {[
            { name: "This Device", type: "Desktop — Chrome", synced: true },
            { name: "My Phone", type: "Mobile — RelayMed App", synced: true },
            { name: "Tablet", type: "iPad — Safari", synced: false },
          ].map((d) => (
            <div key={d.name} className="flex items-center justify-between rounded-xl border p-3">
              <div>
                <div className="text-sm font-medium">{d.name}</div>
                <div className="text-[10px] text-muted-foreground">{d.type}</div>
              </div>
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full"
                style={d.synced ? { background: "var(--mint)", color: "var(--sage)" } : { background: "var(--muted)", color: "var(--muted-foreground)" }}>
                {d.synced ? "Synced" : "Not synced"}
              </span>
            </div>
          ))}
        </div>
        <button onClick={onClose} className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl gradient-brand text-white text-sm font-medium">
          <RefreshCw className="w-4 h-4" /> Sync All Now
        </button>
      </div>
    </div>
  );
}
