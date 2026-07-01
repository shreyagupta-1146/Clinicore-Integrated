import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LucideIcon, ArrowLeft, Mail, Lock, ArrowRight, ShieldCheck } from "lucide-react";
import { useAuth, Mode } from "@/context/AuthContext";

/**
 * Shared consumer auth used by RelayMed and Clinmed (themed by the active scope).
 * Extra fields (for Clinmed role selection) are passed via `extraStep`.
 */
export function ConsumerLogin({
  mode,
  brand,
  icon: Icon,
  greeting,
  emoji,
  roleOptions,
}: {
  mode: Mode;
  brand: string;
  icon: LucideIcon;
  greeting: string;
  emoji: string;
  roleOptions?: { label: string; value: string }[];
}) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState(roleOptions?.[0]?.value ?? "");

  const submit = () => {
    login({
      name: name || email.split("@")[0] || "Guest",
      email: email || "guest@example.com",
      mode,
      role: roleOptions ? role : "patient",
      provider: "email",
    });
    navigate(`/${mode}`);
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left hero */}
      <div className="hidden lg:flex flex-col justify-between p-12 relative overflow-hidden">
        <button onClick={() => navigate("/")} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground w-fit">
          <ArrowLeft className="w-4 h-4" /> All modes
        </button>
        <div>
          <div className="w-16 h-16 rounded-3xl grid place-items-center text-white gradient-brand shadow-lg animate-float">
            <Icon className="w-8 h-8" />
          </div>
          <h1 className="text-5xl font-semibold mt-6 leading-tight" style={{ fontFamily: "var(--font-heading)" }}>
            {brand}
          </h1>
          <p className="text-lg text-muted-foreground mt-3 max-w-md">{greeting}</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="w-4 h-4 text-brand" /> Encrypted · DPDP Act 2023 compliant · You control your data
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6">
        <div className="soft-card p-8 w-full max-w-md animate-fade-in">
          <button onClick={() => navigate("/")} className="lg:hidden flex items-center gap-2 text-sm text-muted-foreground mb-4">
            <ArrowLeft className="w-4 h-4" /> All modes
          </button>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-2xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
              {tab === "signin" ? "Welcome back" : "Create your account"} <span className="inline-block animate-float">{emoji}</span>
            </h2>
          </div>
          <p className="text-sm text-muted-foreground mb-6">{brand} · {mode === "relaymed" ? "Personal health" : "Learning"}</p>

          <div className="flex gap-1 p-1 rounded-xl mb-5" style={{ background: "var(--muted)" }}>
            {(["signin", "signup"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="flex-1 py-2 text-sm font-medium rounded-lg transition-all"
                style={tab === t ? { background: "white", color: "var(--brand)", boxShadow: "var(--shadow-soft)" } : { color: "var(--muted-foreground)" }}
              >
                {t === "signin" ? "Sign in" : "Sign up"}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {tab === "signup" && (
              <Field icon={Mail} placeholder="Full name" value={name} onChange={setName} />
            )}
            <Field icon={Mail} placeholder="Email address" value={email} onChange={setEmail} />
            <Field icon={Lock} placeholder="Password" type="password" value="" onChange={() => {}} />

            {tab === "signup" && roleOptions && (
              <div>
                <label className="text-xs text-muted-foreground">I am a…</label>
                <div className="grid grid-cols-2 gap-2 mt-1.5">
                  {roleOptions.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setRole(r.value)}
                      className="text-xs py-2 px-3 rounded-lg border text-left transition-all"
                      style={
                        role === r.value
                          ? { borderColor: "var(--brand)", background: "color-mix(in oklab, var(--brand) 8%, white)", color: "var(--brand)", fontWeight: 600 }
                          : { borderColor: "var(--border)" }
                      }
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <button
            onClick={submit}
            className="w-full mt-5 flex items-center justify-center gap-2 py-3 rounded-xl gradient-brand text-white font-semibold hover:opacity-90 transition-opacity"
          >
            {tab === "signin" ? "Sign in" : "Create account"} <ArrowRight className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            <span className="text-xs text-muted-foreground">or continue with</span>
            <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button onClick={submit} className="neu-btn py-2.5 rounded-xl text-sm font-medium">Google</button>
            <button onClick={submit} className="neu-btn py-2.5 rounded-xl text-sm font-medium">Phone OTP</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({
  icon: Icon,
  placeholder,
  value,
  onChange,
  type = "text",
}: {
  icon: LucideIcon;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div className="flex items-center gap-2 px-3.5 py-3 rounded-xl border" style={{ borderColor: "var(--border)", background: "white" }}>
      <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 bg-transparent outline-none text-sm"
      />
    </div>
  );
}
