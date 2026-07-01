import { useState } from "react";
import {
  Settings as SettingsIcon, User, Bell, ShieldCheck, Database, Brain, Lock,
  Eye, EyeOff, Info, LogOut, Grid3x3, Download, Trash2,
} from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { useSharingPrefs, setPref, SharingPrefs } from "@/lib/prefs";

function Toggle({ label, desc, on, onChange }: { label: string; desc: string; on: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border bg-card p-4">
      <div className="flex-1 mr-4">
        <div className="font-medium text-sm">{label}</div>
        <div className="text-xs text-muted-foreground leading-relaxed">{desc}</div>
      </div>
      <button onClick={() => onChange(!on)} className="w-11 h-6 rounded-full p-0.5 transition-colors shrink-0"
        style={{ background: on ? "var(--brand)" : "var(--muted)" }}>
        <span className="block w-5 h-5 rounded-full bg-white shadow-sm transition-transform" style={{ transform: on ? "translateX(20px)" : "none" }} />
      </button>
    </div>
  );
}

function Section({ icon: Icon, title, sub, children }: { icon: any; title: string; sub: string; children: React.ReactNode }) {
  return (
    <>
      <div className="flex items-center gap-3 mb-3 mt-6 first:mt-0">
        <div className="w-9 h-9 rounded-xl bg-chip grid place-items-center text-brand shrink-0"><Icon className="w-4 h-4" /></div>
        <div>
          <div className="font-semibold text-sm" style={{ fontFamily: "var(--font-heading)" }}>{title}</div>
          <div className="text-[11px] text-muted-foreground">{sub}</div>
        </div>
      </div>
      {children}
    </>
  );
}

export function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const prefs = useSharingPrefs();
  const [ai, setAi] = useState({ meds: true, proactive: true, interactions: true, federated: false });
  const [notif, setNotif] = useState({ daily: true, anomaly: true, weekly: true, interactions: true });

  const S = (k: keyof SharingPrefs) => (v: boolean) => setPref(k, v);
  const initial = (user?.name || "U").charAt(0).toUpperCase();

  const permRows = [
    { type: "Vital Signs", on: prefs.vitals, since: "Jan 2026" },
    { type: "Activity Data", on: prefs.activity, since: "Feb 2026" },
    { type: "Medical History", on: prefs.history, since: "Today" },
    { type: "Medical Certificates", on: prefs.docs, since: "Today" },
    { type: "Clinician Access", on: prefs.clinician, since: "Today" },
  ];

  return (
    <PageShell icon={SettingsIcon} title="Settings" subtitle="Your profile, privacy, and exactly what the AI is allowed to use." wide>
      <div className="max-w-3xl space-y-2">
        <Section icon={User} title="Account" sub="Profile and login">
          <div className="rounded-2xl border bg-card p-4 flex items-center gap-4">
            <div className="w-14 h-14 rounded-full gradient-brand grid place-items-center text-white font-bold text-lg">{initial}</div>
            <div className="flex-1">
              <div className="font-semibold">{user?.name}</div>
              <div className="text-xs text-muted-foreground">{user?.email}</div>
            </div>
            <button onClick={() => navigate("/")} className="text-xs flex items-center gap-1 border rounded-lg px-3 py-1.5"><Grid3x3 className="w-3 h-3" /> Switch mode</button>
            <button onClick={logout} className="text-xs flex items-center gap-1 border rounded-lg px-3 py-1.5" style={{ color: "var(--coral)" }}><LogOut className="w-3 h-3" /> Sign out</button>
          </div>
        </Section>

        <Section icon={Bell} title="Notifications" sub="Control how you receive updates">
          <div className="space-y-2">
            <Toggle label="Daily wellness summaries" desc="A calm morning briefing with your health overview." on={notif.daily} onChange={(v) => setNotif({ ...notif, daily: v })} />
            <Toggle label="Anomaly alerts" desc="Only meaningful or concerning changes in your vitals." on={notif.anomaly} onChange={(v) => setNotif({ ...notif, anomaly: v })} />
            <Toggle label="Weekly progress reports" desc="Trends and improvements every Sunday." on={notif.weekly} onChange={(v) => setNotif({ ...notif, weekly: v })} />
            <Toggle label="Medicine interaction warnings" desc="Alert when potential drug interactions are detected." on={notif.interactions} onChange={(v) => setNotif({ ...notif, interactions: v })} />
          </div>
        </Section>

        <Section icon={ShieldCheck} title="Privacy & Data Sharing" sub="Custom, transparent — decide exactly what the AI can use">
          <div className="rounded-2xl border p-4 mb-2 flex items-start gap-2" style={{ background: "color-mix(in oklab, var(--warning) 12%, white)", borderColor: "color-mix(in oklab, var(--warning) 30%, transparent)" }}>
            <Info className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />
            <div className="text-xs leading-relaxed">
              <strong>How sharing affects your experience:</strong> more data → more accurate, personalised insights. Turn anything off and the AI simply won't use it — your data is still stored safely and nothing is ever sold. Change these any time.
            </div>
          </div>
          <div className="space-y-2">
            <Toggle label="Allow AI to use my health data" desc="Master switch. When off, the AI gives generic guidance and uses none of your data." on={prefs.master} onChange={S("master")} />
            {!prefs.master && (
              <div className="rounded-xl p-3 text-xs ml-4" style={{ background: "color-mix(in oklab, var(--coral) 8%, white)", color: "var(--coral)" }}>
                AI personalisation is <strong>disabled</strong>. You'll get generic guidance. Existing data is stored safely and can be re-enabled anytime.
              </div>
            )}
            <Toggle label="Share vital signs (HR, BP, SpO₂, glucose)" desc="Let the AI analyse your device readings." on={prefs.vitals} onChange={S("vitals")} />
            <Toggle label="Share activity data (steps, sleep)" desc="Factor in physical activity and sleep patterns." on={prefs.activity} onChange={S("activity")} />
            <Toggle label="Share medical history" desc="Include conditions, allergies, and past diagnoses." on={prefs.history} onChange={S("history")} />
            <Toggle label="Share medical certificates & documents" desc="Let uploaded documents be referenced by the AI." on={prefs.docs} onChange={S("docs")} />
            <Toggle label="Share with clinician" desc="Allow your verified clinician to view reports & AI insights." on={prefs.clinician} onChange={S("clinician")} />
          </div>
        </Section>

        <Section icon={Database} title="Data Permissions Log" sub="Exactly what you've shared, and since when">
          <div className="rounded-2xl border bg-card p-4 space-y-3">
            {permRows.map((r) => (
              <div key={r.type} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {r.on ? <Eye className="w-4 h-4 text-brand" /> : <EyeOff className="w-4 h-4 text-muted-foreground" />}
                  <div>
                    <div className="text-sm font-medium">{r.type}</div>
                    <div className="text-[10px] text-muted-foreground">{r.on ? `Active since ${r.since}` : "Never shared"}</div>
                  </div>
                </div>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full" style={r.on ? { background: "var(--chip-bg)", color: "var(--brand)" } : { background: "var(--muted)", color: "var(--muted-foreground)" }}>
                  {r.on ? "Shared" : "Not shared"}
                </span>
              </div>
            ))}
          </div>
        </Section>

        <Section icon={Brain} title="AI Preferences" sub="Customise how the AI behaves">
          <div className="space-y-2">
            <Toggle label="Personalised medicine suggestions" desc="Suggest specific medicines (always with a consult-a-doctor warning)." on={ai.meds} onChange={(v) => setAi({ ...ai, meds: v })} />
            <Toggle label="Proactive health alerts" desc="Flag concerning trends without you asking." on={ai.proactive} onChange={(v) => setAi({ ...ai, proactive: v })} />
            <Toggle label="Drug interaction checks" desc="Cross-reference suggestions with your medications." on={ai.interactions} onChange={(v) => setAi({ ...ai, interactions: v })} />
            <Toggle label="Federated learning opt-in" desc="Help improve the model — your raw data never leaves your device." on={ai.federated} onChange={(v) => setAi({ ...ai, federated: v })} />
          </div>
        </Section>

        <Section icon={Lock} title="Security" sub="Protect your account">
          <div className="rounded-2xl border bg-card p-4 space-y-3">
            {[
              { t: "Encryption", d: "All data encrypted with AES-256", tag: "Active" },
              { t: "Two-Factor Authentication", d: "Add extra security to your account", action: "Enable" },
              { t: "Login Sessions", d: `Signed in — ${new Date().toLocaleDateString()}`, tag: "Active" },
            ].map((row) => (
              <div key={row.t} className="flex items-center justify-between">
                <div><div className="text-sm font-medium">{row.t}</div><div className="text-[10px] text-muted-foreground">{row.d}</div></div>
                {row.tag ? <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-chip text-brand">{row.tag}</span> : <button className="text-xs text-brand hover:underline">{row.action}</button>}
              </div>
            ))}
            <div className="flex items-center justify-between pt-2 border-t">
              <div><div className="text-sm font-medium flex items-center gap-1.5"><Download className="w-3.5 h-3.5" /> Data Export</div><div className="text-[10px] text-muted-foreground">Download all your health data</div></div>
              <button className="text-xs text-brand hover:underline">Export</button>
            </div>
            <div className="flex items-center justify-between">
              <div><div className="text-sm font-medium flex items-center gap-1.5" style={{ color: "var(--coral)" }}><Trash2 className="w-3.5 h-3.5" /> Delete Account</div><div className="text-[10px] text-muted-foreground">Permanently remove all data</div></div>
              <button className="text-xs hover:underline" style={{ color: "var(--coral)" }}>Delete</button>
            </div>
          </div>
        </Section>
      </div>
    </PageShell>
  );
}
