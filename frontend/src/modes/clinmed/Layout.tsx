import { ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  GraduationCap, Home, Library, TrendingUp, Trophy, RotateCcw, PenSquare,
  Flame, Zap, Grid3x3, LogOut, PlayCircle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const NAV = [
  { to: "/clinmed", label: "Learn Home", icon: Home, end: true },
  { to: "/clinmed/modules", label: "Modules & Videos", icon: PlayCircle },
  { to: "/clinmed/cases", label: "Case Library", icon: Library },
  { to: "/clinmed/progress", label: "Progress", icon: TrendingUp },
  { to: "/clinmed/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/clinmed/review", label: "Review Deck", icon: RotateCcw },
  { to: "/clinmed/author", label: "Authoring", icon: PenSquare, educator: true },
];

export function ClinmedLayout({ children }: { children: ReactNode }) {
  const loc = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isEducator = user?.role === "educator";
  const name = user?.name || "Learner";
  const initial = name.charAt(0).toUpperCase();

  return (
    <div className="flex min-h-screen">
      <aside className="w-[240px] shrink-0 h-screen sticky top-0 p-4 hidden lg:block">
        <div className="soft-card h-full flex flex-col p-4">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-11 h-11 rounded-2xl gradient-brand grid place-items-center text-white shadow-md"><GraduationCap className="w-5 h-5" /></div>
            <div>
              <div className="text-lg font-semibold leading-tight" style={{ fontFamily: "var(--font-heading)" }}>Clinmed</div>
              <div className="text-[11px] text-muted-foreground">Diagnostic Training</div>
            </div>
          </div>

          <nav className="mt-5 flex-1 space-y-1">
            {NAV.filter((n) => !n.educator || isEducator).map((item) => {
              const active = item.end ? loc.pathname === item.to : loc.pathname.startsWith(item.to);
              const Icon = item.icon;
              return (
                <Link key={item.to} to={item.to} className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all"
                  style={active ? { background: "color-mix(in oklab, var(--brand) 12%, white)", color: "var(--brand)", fontWeight: 600 } : { color: "var(--muted-foreground)" }}>
                  <Icon className="w-[18px] h-[18px]" /> {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-3 flex items-center gap-3 p-2 rounded-2xl">
            <div className="w-10 h-10 rounded-full gradient-brand grid place-items-center text-white font-semibold">{initial}</div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{name}</div>
              <div className="text-[11px] text-muted-foreground capitalize">{user?.role} · Level 7</div>
            </div>
            <button onClick={() => navigate("/")} title="Switch mode" className="text-muted-foreground hover:text-foreground"><Grid3x3 className="w-4 h-4" /></button>
            <button onClick={logout} title="Sign out" className="text-muted-foreground hover:text-foreground"><LogOut className="w-4 h-4" /></button>
          </div>
        </div>
      </aside>

      <main className="flex-1 min-w-0 px-4 md:px-6 pb-10">
        <header className="flex items-center justify-between pt-6 pb-6 animate-fade-in gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl md:text-3xl font-semibold tracking-tight truncate" style={{ fontFamily: "var(--font-heading)" }}>Hi {name} 📚</h1>
            <p className="text-sm text-muted-foreground mt-1 hidden sm:block">Ready to sharpen your diagnostic edge?</p>
          </div>
          <div className="flex items-center gap-2 md:gap-3 shrink-0">
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-2xl soft-card">
              <Flame className="w-4 h-4" style={{ color: "var(--ochre)" }} /> <span className="text-sm font-semibold">8</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-2xl soft-card">
              <Zap className="w-4 h-4" style={{ color: "var(--brand)" }} /> <span className="text-sm font-semibold">2,340 XP</span>
            </div>
            <Link to="/clinmed/simulator" className="px-4 py-2.5 rounded-2xl gradient-brand text-white text-sm font-semibold">Daily Case</Link>
          </div>
        </header>
        {children}
        <footer className="soft-card mt-6 p-3 text-center text-[11px] text-muted-foreground">
          For education only — not for real patient care. Cases are illustrative.
        </footer>
      </main>
    </div>
  );
}
