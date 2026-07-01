import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Stethoscope, ArrowLeft, Building2, Mail, Lock, Fingerprint, ShieldCheck, ArrowRight, Check } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const FACILITIES = ["Apollo Hospitals, Bengaluru", "Fortis Healthcare, Delhi", "Manipal Hospital, Bengaluru", "AIIMS, New Delhi"];
const ROLES = [
  { label: "Clinician", value: "clinician" },
  { label: "Facility Admin", value: "facility_admin" },
  { label: "Platform Admin", value: "platform_admin" },
];

export function AdminLogin() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [facility, setFacility] = useState(FACILITIES[0]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("clinician");

  const finish = () => {
    login({ name: email.split("@")[0] || "Dr. Sharma", email: email || "dr.sharma@apollo.in", mode: "clinicore", role, facility, provider: "sso" });
    navigate("/clinicore");
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left institutional panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 relative" style={{ background: "var(--gradient-brand)" }}>
        <button onClick={() => navigate("/")} className="flex items-center gap-2 text-sm text-white/80 hover:text-white w-fit"><ArrowLeft className="w-4 h-4" /> All modes</button>
        <div className="text-white">
          <div className="w-16 h-16 rounded-3xl grid place-items-center bg-white/15 backdrop-blur"><Stethoscope className="w-8 h-8" /></div>
          <h1 className="text-5xl font-semibold mt-6" style={{ fontFamily: "Inter, sans-serif" }}>Clinicore</h1>
          <p className="text-lg text-white/80 mt-3 max-w-md">Hybrid-sovereignty clinical decision support. Raw PHI stays on-prem; only de-identified text reaches the cloud model.</p>
          <div className="mt-8 space-y-2.5">
            {["Phishing-resistant sign-in (FIDO2)", "Every access audit-logged & hash-chained", "DPDP Act 2023 · ABDM HIE-CM ready"].map((t) => (
              <div key={t} className="flex items-center gap-2 text-sm text-white/85"><Check className="w-4 h-4" /> {t}</div>
            ))}
          </div>
        </div>
        <div className="text-xs text-white/60">For licensed clinicians & registered facilities only.</div>
      </div>

      {/* Right stepper */}
      <div className="flex items-center justify-center p-6">
        <div className="soft-card p-8 w-full max-w-md animate-fade-in">
          <button onClick={() => navigate("/")} className="lg:hidden flex items-center gap-2 text-sm text-muted-foreground mb-4"><ArrowLeft className="w-4 h-4" /> All modes</button>

          <div className="flex items-center gap-2 mb-6">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex-1 h-1.5 rounded-full" style={{ background: s <= step ? "var(--brand)" : "var(--muted)" }} />
            ))}
          </div>

          {step === 1 && (
            <>
              <h2 className="text-2xl font-semibold mb-1">Select your facility</h2>
              <p className="text-sm text-muted-foreground mb-5">Institutional access is scoped per facility.</p>
              <div className="space-y-2">
                {FACILITIES.map((f) => (
                  <button key={f} onClick={() => setFacility(f)} className="w-full flex items-center gap-3 p-3 rounded-xl border text-left text-sm transition-all"
                    style={facility === f ? { borderColor: "var(--brand)", background: "color-mix(in oklab, var(--brand) 6%, white)" } : { borderColor: "var(--border)" }}>
                    <Building2 className="w-4 h-4 text-brand" /> <span className="flex-1">{f}</span>
                    {facility === f && <Check className="w-4 h-4 text-brand" />}
                  </button>
                ))}
              </div>
              <button onClick={() => setStep(2)} className="w-full mt-5 flex items-center justify-center gap-2 py-3 rounded-xl gradient-brand text-white font-semibold">Continue <ArrowRight className="w-4 h-4" /></button>
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="text-2xl font-semibold mb-1">Clinician credentials</h2>
              <p className="text-sm text-muted-foreground mb-5">{facility}</p>
              <div className="space-y-3">
                <div className="flex items-center gap-2 px-3.5 py-3 rounded-xl border bg-white">
                  <Mail className="w-4 h-4 text-muted-foreground" />
                  <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Work email" className="flex-1 bg-transparent outline-none text-sm" />
                </div>
                <div className="flex items-center gap-2 px-3.5 py-3 rounded-xl border bg-white">
                  <Lock className="w-4 h-4 text-muted-foreground" />
                  <input type="password" placeholder="Password" className="flex-1 bg-transparent outline-none text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Role</label>
                  <div className="grid grid-cols-3 gap-2 mt-1.5">
                    {ROLES.map((r) => (
                      <button key={r.value} onClick={() => setRole(r.value)} className="text-[11px] py-2 px-2 rounded-lg border transition-all"
                        style={role === r.value ? { borderColor: "var(--brand)", background: "color-mix(in oklab, var(--brand) 8%, white)", color: "var(--brand)", fontWeight: 600 } : { borderColor: "var(--border)" }}>
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <button onClick={() => setStep(3)} className="w-full mt-5 flex items-center justify-center gap-2 py-3 rounded-xl gradient-brand text-white font-semibold">Continue <ArrowRight className="w-4 h-4" /></button>
            </>
          )}

          {step === 3 && (
            <>
              <h2 className="text-2xl font-semibold mb-1">Verify it's you</h2>
              <p className="text-sm text-muted-foreground mb-6">Phishing-resistant step-up authentication.</p>
              <button onClick={finish} className="w-full flex flex-col items-center gap-3 p-8 rounded-2xl border-2 border-dashed hover:bg-black/[0.02] transition-colors" style={{ borderColor: "color-mix(in oklab, var(--brand) 40%, transparent)" }}>
                <div className="w-16 h-16 rounded-full grid place-items-center gradient-brand text-white animate-pulse-ring"><Fingerprint className="w-8 h-8" /></div>
                <div className="text-sm font-semibold">Tap to authenticate with passkey</div>
                <div className="text-xs text-muted-foreground">FIDO2 / WebAuthn · Face, fingerprint or security key</div>
              </button>
              <button onClick={finish} className="w-full mt-4 text-xs text-muted-foreground hover:text-foreground">Use authenticator app instead</button>
              <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-5 justify-center">
                <ShieldCheck className="w-3.5 h-3.5 text-brand" /> This session will be audit-logged.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
