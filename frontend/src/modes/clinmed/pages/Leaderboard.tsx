import { useState } from "react";
import { Trophy, Flame } from "lucide-react";

const BOARD = [
  { rank: 1, name: "Aarav K.", acc: 91, speed: "3m 40s", streak: 24, you: false },
  { rank: 2, name: "Diya R.", acc: 89, speed: "3m 55s", streak: 19, you: false },
  { rank: 3, name: "Kabir S.", acc: 87, speed: "4m 02s", streak: 15, you: false },
  { rank: 4, name: "You", acc: 84, speed: "4m 12s", streak: 8, you: true },
  { rank: 5, name: "Meera T.", acc: 82, speed: "4m 20s", streak: 11, you: false },
  { rank: 6, name: "Rohan V.", acc: 80, speed: "4m 33s", streak: 6, you: false },
];

export function Leaderboard() {
  const [scope, setScope] = useState("Cohort");
  return (
    <div className="soft-card p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5" style={{ color: "var(--ochre)" }} />
          <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Leaderboard</h2>
        </div>
        <div className="flex gap-1 p-1 rounded-xl" style={{ background: "var(--muted)" }}>
          {["Global", "Cohort", "Friends"].map((s) => (
            <button key={s} onClick={() => setScope(s)} className="px-3 py-1.5 text-xs font-medium rounded-lg transition-all"
              style={scope === s ? { background: "white", color: "var(--brand)", boxShadow: "var(--shadow-soft)" } : { color: "var(--muted-foreground)" }}>{s}</button>
          ))}
        </div>
      </div>
      <div className="space-y-2">
        {BOARD.map((r) => (
          <div key={r.rank} className="flex items-center gap-3 p-3 rounded-xl border"
            style={r.you ? { borderColor: "var(--brand)", background: "color-mix(in oklab, var(--brand) 6%, white)" } : { borderColor: "var(--border)" }}>
            <div className="w-8 h-8 rounded-lg grid place-items-center font-bold text-sm"
              style={r.rank <= 3 ? { background: "color-mix(in oklab, var(--ochre) 18%, white)", color: "var(--ochre)" } : { background: "var(--muted)", color: "var(--muted-foreground)" }}>
              {r.rank}
            </div>
            <div className="w-9 h-9 rounded-full grid place-items-center text-white text-xs font-semibold" style={{ background: r.you ? "var(--brand)" : "var(--ochre)" }}>{r.name.charAt(0)}</div>
            <div className="flex-1 font-medium text-sm">{r.name} {r.you && <span className="text-[10px] text-brand font-semibold">· you</span>}</div>
            <div className="hidden sm:block text-xs text-muted-foreground">{r.speed}</div>
            <div className="flex items-center gap-1 text-xs"><Flame className="w-3.5 h-3.5" style={{ color: "var(--ochre)" }} /> {r.streak}</div>
            <div className="text-sm font-bold w-12 text-right" style={{ color: "var(--brand)" }}>{r.acc}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}
