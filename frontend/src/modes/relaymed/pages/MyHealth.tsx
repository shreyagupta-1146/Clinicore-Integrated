import { useState } from "react";
import {
  HeartPulse, Droplet, Activity, Thermometer, Watch, Stethoscope, Upload,
  Save, Check, AlertCircle, AlertTriangle, MapPin, Pill, Phone, Ban,
} from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { Pill as Chip } from "@/components/ui";
import { checkVital, hasImplausible } from "@/lib/vitals";
import { useSharingPrefs, canUse } from "@/lib/prefs";

interface HealthData { [k: string]: string | undefined }

function load(): HealthData { try { return JSON.parse(localStorage.getItem("relaymed.health") || "{}"); } catch { return {}; } }

const SNAPSHOT = [
  { label: "Resting HR", v: "62 bpm", trend: "Normal", tone: "good" as const },
  { label: "Sleep", v: "7h 24m", trend: "Good", tone: "good" as const },
  { label: "Steps Today", v: "8,420", trend: "On track", tone: "good" as const },
  { label: "Hydration", v: "1.6 L", trend: "Below target", tone: "warn" as const },
  { label: "Stress Score", v: "42", trend: "Elevated", tone: "warn" as const },
  { label: "SpO₂", v: "98%", trend: "Healthy", tone: "good" as const },
];

export function MyHealth() {
  const prefs = useSharingPrefs();
  const [data, setData] = useState<HealthData>(load);
  const [saved, setSaved] = useState(false);
  const [reports, setReports] = useState<string[]>([]);

  const set = (k: string, v: string) => setData((p) => ({ ...p, [k]: v }));
  const blocked = hasImplausible(data);

  const save = () => {
    if (!prefs.master) { alert("Data sharing is off in Settings. Turn it on to save."); return; }
    if (blocked) return;
    localStorage.setItem("relaymed.health", JSON.stringify(data));
    setSaved(true); setTimeout(() => setSaved(false), 2000);
  };

  const nearby = (q: string) => window.open(`https://www.google.com/maps/search/${encodeURIComponent(q + " near me")}`, "_blank");

  return (
    <PageShell icon={HeartPulse} title="My Health" subtitle="Your daily vitals, device readings, and nearby care — all in one place." wide>
      {/* Snapshot grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {SNAPSHOT.map((s) => (
          <div key={s.label} className="rounded-2xl border bg-card p-3">
            <div className="text-[11px] text-muted-foreground">{s.label}</div>
            <div className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{s.v}</div>
            <Chip tone={s.tone}>{s.trend}</Chip>
          </div>
        ))}
      </div>

      {/* Wearable sync sources */}
      <div className="rounded-2xl border bg-card p-4 mb-6 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="text-sm font-semibold flex items-center gap-2" style={{ fontFamily: "var(--font-heading)" }}>
          <Activity className="w-4 h-4 text-brand" /> Connected sources
        </div>
        {[
          { l: "Health Connect", s: "Android · on-device", on: true },
          { l: "Apple Health", s: "iOS · on-device", on: false },
          { l: "Fitbit", s: "cloud sync", on: true },
          { l: "Omron BP", s: "Bluetooth", on: false },
        ].map((src) => (
          <div key={src.l} className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full" style={{ background: src.on ? "var(--success)" : "var(--muted-foreground)" }} />
            <span className="font-medium">{src.l}</span>
            <span className="text-muted-foreground">· {src.s}</span>
          </div>
        ))}
        <button className="ml-auto text-xs font-semibold text-brand">Manage sources</button>
      </div>

      {/* Nearby services + emergency */}
      <div className="flex items-center gap-2 mb-3">
        <MapPin className="w-4 h-4 text-brand" />
        <h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>Nearby Care & Emergency</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <button onClick={() => nearby("doctors hospitals")} className="rounded-2xl border bg-card p-5 text-left hover:shadow-md transition-all group">
          <div className="w-12 h-12 rounded-xl grid place-items-center mb-3 bg-chip text-brand group-hover:scale-110 transition-transform"><Stethoscope className="w-6 h-6" /></div>
          <div className="font-semibold text-sm">Doctors & Hospitals Near Me</div>
          <div className="text-xs text-muted-foreground mt-1">Opens maps with nearby clinics & hospitals</div>
        </button>
        <button onClick={() => nearby("pharmacies")} className="rounded-2xl border bg-card p-5 text-left hover:shadow-md transition-all group">
          <div className="w-12 h-12 rounded-xl grid place-items-center mb-3 group-hover:scale-110 transition-transform" style={{ background: "color-mix(in oklab, var(--success) 12%, white)", color: "var(--success)" }}><Pill className="w-6 h-6" /></div>
          <div className="font-semibold text-sm">Pharmacies Near Me</div>
          <div className="text-xs text-muted-foreground mt-1">Find pharmacies for prescriptions & OTC</div>
        </button>
        <a href="tel:112" className="rounded-2xl border p-5 block text-left hover:shadow-md transition-all group" style={{ background: "color-mix(in oklab, var(--coral) 8%, white)", borderColor: "color-mix(in oklab, var(--coral) 30%, transparent)" }}>
          <div className="w-12 h-12 rounded-xl grid place-items-center mb-3 group-hover:scale-110 transition-transform" style={{ background: "color-mix(in oklab, var(--coral) 16%, white)", color: "var(--coral)" }}><Phone className="w-6 h-6" /></div>
          <div className="font-semibold text-sm" style={{ color: "var(--coral)" }}>Emergency Call (112)</div>
          <div className="text-xs mt-1" style={{ color: "var(--coral)" }}>Tap to call emergency services now</div>
        </a>
      </div>

      {/* Medical data input with threshold flagging */}
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-base font-semibold" style={{ fontFamily: "var(--font-heading)" }}>My Medical Data</h3>
        <button onClick={save} disabled={blocked}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all disabled:opacity-50"
          style={saved ? { background: "color-mix(in oklab, var(--success) 15%, white)", color: "var(--success)" } : { background: "var(--brand)", color: "white" }}>
          {saved ? <><Check className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Data</>}
        </button>
      </div>
      <p className="text-sm text-muted-foreground mb-3">Enter readings from your devices. Saved values personalise your AI health responses.</p>

      {blocked && (
        <div className="rounded-xl p-3 mb-4 flex items-start gap-2" style={{ background: "color-mix(in oklab, var(--coral) 10%, white)", border: "1px solid color-mix(in oklab, var(--coral) 35%, transparent)" }}>
          <Ban className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "var(--coral)" }} />
          <span className="text-xs" style={{ color: "var(--coral)" }}><strong>Implausible reading detected.</strong> One or more values are outside the physically possible range. Fix the flagged fields — they won't be saved or sent to the AI.</span>
        </div>
      )}
      {!prefs.master && (
        <div className="rounded-xl p-3 mb-4 flex items-start gap-2" style={{ background: "color-mix(in oklab, var(--warning) 14%, white)" }}>
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />
          <span className="text-xs">Data sharing is <strong>off</strong>. Inputs are disabled — enable it in Settings to save and personalise.</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <DeviceCard icon={Droplet} title="Glucometer" enabled={canUse("vitals") }>
          <Field k="blood_glucose" label="Blood Glucose (mg/dL)" ph="110" data={data} set={set} disabled={!canUse("vitals")} />
        </DeviceCard>
        <DeviceCard icon={HeartPulse} title="BP Machine" enabled={canUse("vitals")}>
          <div className="grid grid-cols-2 gap-2">
            <Field k="systolic" label="Systolic" ph="120" data={data} set={set} disabled={!canUse("vitals")} />
            <Field k="diastolic" label="Diastolic" ph="80" data={data} set={set} disabled={!canUse("vitals")} />
          </div>
        </DeviceCard>
        <DeviceCard icon={Activity} title="Pulse Oximeter" enabled={canUse("vitals")}>
          <Field k="spo2" label="SpO₂ (%)" ph="98" data={data} set={set} disabled={!canUse("vitals")} />
          <Field k="heart_rate" label="Heart Rate (bpm)" ph="72" data={data} set={set} disabled={!canUse("vitals")} />
        </DeviceCard>
        <DeviceCard icon={Thermometer} title="Thermometer" enabled={canUse("vitals")}>
          <Field k="temperature" label="Temperature (°F)" ph="98.6" data={data} set={set} disabled={!canUse("vitals")} />
          <Field k="weight" label="Weight (kg)" ph="65" data={data} set={set} disabled={!canUse("vitals")} />
        </DeviceCard>
        <DeviceCard icon={Watch} title="Fitbit / Wearable" enabled={canUse("activity")}>
          <Field k="fitbit_steps" label="Daily Steps" ph="8000" data={data} set={set} disabled={!canUse("activity")} />
          <Field k="fitbit_sleep" label="Sleep Hours" ph="7.5" data={data} set={set} disabled={!canUse("activity")} />
        </DeviceCard>
        <DeviceCard icon={Stethoscope} title="Medical History" enabled={canUse("history")}>
          <Field k="conditions" label="Known Conditions" ph="T2DM, Hypertension" data={data} set={set} disabled={!canUse("history")} text />
          <Field k="medications" label="Current Medications" ph="Metformin 500mg" data={data} set={set} disabled={!canUse("history")} text />
        </DeviceCard>
      </div>

      {/* Upload */}
      <div className="mt-4 rounded-2xl border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg grid place-items-center bg-chip text-brand"><Upload className="w-4 h-4" /></div>
          <div className="font-medium text-sm">Upload Medical Reports {!canUse("docs") && <span className="text-[10px] text-muted-foreground">(enable document sharing in Settings)</span>}</div>
        </div>
        <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-6 transition-colors ${canUse("docs") ? "cursor-pointer hover:bg-black/[0.02]" : "opacity-50 cursor-not-allowed"}`} style={{ borderColor: "var(--border)" }}>
          <Upload className="w-8 h-8 text-muted-foreground mb-2" />
          <span className="text-sm text-muted-foreground">Click to upload PDF, images, or documents</span>
          <input type="file" multiple disabled={!canUse("docs")} onChange={(e) => { const f = e.target.files; if (f) setReports((r) => [...r, ...[...f].map((x) => x.name)]); }} className="hidden" />
        </label>
        {reports.length > 0 && (
          <div className="mt-3 space-y-1">
            {reports.map((r, i) => <div key={i} className="text-xs flex items-center gap-2 rounded-lg px-3 py-1.5 bg-chip"><Check className="w-3 h-3 text-brand" /> {r}</div>)}
          </div>
        )}
      </div>
    </PageShell>
  );
}

function DeviceCard({ icon: Icon, title, enabled, children }: { icon: any; title: string; enabled: boolean; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border bg-card p-4" style={{ opacity: enabled ? 1 : 0.7 }}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg grid place-items-center bg-chip text-brand"><Icon className="w-4 h-4" /></div>
        <div className="font-medium text-sm">{title}</div>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Field({ k, label, ph, data, set, disabled, text }: { k: string; label: string; ph: string; data: any; set: (k: string, v: string) => void; disabled?: boolean; text?: boolean }) {
  const check = checkVital(k, data[k]);
  const borderColor = check.level === "implausible" ? "var(--coral)" : check.level === "abnormal" ? "var(--warning)" : "var(--border)";
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      <input
        type={text ? "text" : "number"}
        value={data[k] || ""}
        onChange={(e) => set(k, e.target.value)}
        disabled={disabled}
        placeholder={ph}
        className="w-full mt-1 px-3 py-2 rounded-lg border text-sm outline-none disabled:opacity-50 disabled:bg-black/[0.02]"
        style={{ borderColor }}
      />
      {check.message && (
        <div className="flex items-start gap-1 mt-1 text-[10px]" style={{ color: check.level === "implausible" ? "var(--coral)" : "color-mix(in oklab, var(--warning) 60%, black)" }}>
          <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" /> <span>{check.message}</span>
        </div>
      )}
    </div>
  );
}
