import { useState } from "react";
import { MessageCircle, Sparkles, Send, ShieldAlert, UserCheck, UserX, MapPin } from "lucide-react";
import { SecurityFooter } from "@/components/PageShell";
import { ChatFeedback } from "@/components/ChatFeedback";
import { useSharingPrefs } from "@/lib/prefs";

interface Msg { role: "user" | "ai"; text: string; q?: string }

const SUGGESTIONS = [
  "What factors are increasing my cardiovascular risk?",
  "How do I treat a burn at home?",
  "Find doctors and pharmacies near me",
  "What medicine can help with headaches?",
];

const SEED: Msg[] = [
  { role: "ai", text: "Hello! I'm Relay Guide, your AI health companion. I can explain your health data, suggest lifestyle changes, discuss medicines (always with a check-with-your-doctor reminder), and help you find care nearby. How can I support your health today?" },
];

export function RelayGuide() {
  const prefs = useSharingPrefs();
  const [msgs, setMsgs] = useState<Msg[]>(SEED);
  const [text, setText] = useState("");

  const send = (t: string) => {
    if (!t.trim()) return;
    const q = t.trim();
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setText("");

    if (/near me|nearby|doctor|pharmac|hospital/i.test(q)) {
      window.open("https://www.google.com/maps/search/doctors+and+pharmacies+near+me", "_blank");
    }
    setTimeout(() => {
      const personalized = prefs.master;
      const prefix = personalized ? "*(Personalised from your health data)* " : "";
      setMsgs((m) => [...m, {
        role: "ai",
        q,
        text: prefix + "Here's a calm, general suggestion based on what you asked. Remember, I'm a companion — not a replacement for your doctor. For anything urgent (chest pain, breathing trouble, fainting), contact your clinician or call 112.",
      }]);
    }, 500);
  };

  return (
    <div className="max-w-4xl mx-auto w-full space-y-4">
      <div className="soft-card px-4 py-3 animate-fade-in flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl grid place-items-center bg-chip text-brand shrink-0 animate-pulse-ring"><MessageCircle className="w-4 h-4" /></div>
        <div className="flex-1 min-w-0">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Relay Guide</div>
          <div className="text-sm font-medium truncate">AI Health Companion · {msgs.length} messages</div>
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-brand px-2.5 py-1 rounded-full bg-chip"><Sparkles className="w-3 h-3" /> Online</div>
      </div>

      {/* disclaimers + personalization indicator */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex-1 flex items-center gap-2 rounded-xl px-3 py-2 text-[11px]" style={{ background: "color-mix(in oklab, var(--warning) 12%, white)" }}>
          <ShieldAlert className="w-4 h-4 shrink-0" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />
          AI can suggest medicines but may make mistakes. Always consult your doctor before taking any medication.
        </div>
        <div className="flex items-center gap-2 rounded-xl px-3 py-2 text-[11px]"
          style={prefs.master ? { background: "color-mix(in oklab, var(--success) 12%, white)", color: "var(--success)" } : { background: "color-mix(in oklab, var(--coral) 10%, white)", color: "var(--coral)" }}>
          {prefs.master ? <><UserCheck className="w-3.5 h-3.5" /> Personalised</> : <><UserX className="w-3.5 h-3.5" /> Generic — enable sharing in Settings</>}
        </div>
      </div>

      <div className="soft-card p-5 animate-fade-in flex flex-col" style={{ height: "56vh" }}>
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={m.role === "user" ? "max-w-[85%]" : "max-w-[85%] w-full"}>
                <div className="rounded-2xl px-4 py-2.5 text-sm leading-relaxed" style={m.role === "user" ? { background: "var(--brand)", color: "white" } : { background: "var(--muted)" }}>
                  {m.text}
                </div>
                {m.role === "ai" && i > 0 && <ChatFeedback mode="relaymed" question={m.q} answer={m.text} />}
              </div>
            </div>
          ))}
        </div>

        <div className="pt-3 border-t mt-2">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">Suggested</div>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} className="text-[11px] px-2.5 py-1.5 rounded-full border hover:bg-black/[0.03] transition-colors flex items-center gap-1">
                {/near me/i.test(s) && <MapPin className="w-3 h-3 text-brand" />} {s}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send(text)}
              placeholder="Ask me anything…" className="flex-1 px-4 py-3 rounded-xl border bg-card outline-none text-sm" />
            <button onClick={() => send(text)} className="w-11 h-11 grid place-items-center rounded-xl gradient-brand text-white"><Send className="w-4 h-4" /></button>
          </div>
        </div>
      </div>
      <SecurityFooter />
    </div>
  );
}
