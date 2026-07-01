import { useState } from "react";
import {
  HeartPulse, Bot, Zap, AlertTriangle, CheckCircle2, XCircle, Terminal,
  ShieldCheck, GitBranch, Clock, Cpu, Activity, Lock,
} from "lucide-react";
import { ClinHeader } from "../ClinHeader";
import { DiffViewer } from "@/components/DiffViewer";

/**
 * Self-Healing SRE console — ported from weave-heal / PRISM.
 *
 * AI agents diagnose the platform's OWN infra incidents and propose a config
 * fix (shown as a diff). A human approves the deploy. The PRISM policy engine
 * is preserved: production namespace OR critical severity => mandatory human
 * sign-off (no autonomous apply). This is the SRE twin of the SecOps HITL rule.
 */

type Sev = "critical" | "warning" | "info";
type Status = "pending" | "deploying" | "resolved" | "rejected";

interface Incident {
  id: string; service: string; namespace: string; env: string; severity: Sev; status: Status;
  agent: string; diagnosis: string; rootCause: string; confidence: number; oldYaml: string; newYaml: string;
}

// Policy engine (from PRISM middleware app.py): prod OR critical => human sign-off.
function requiresApproval(inc: Incident): { required: boolean; reason: string } {
  if (inc.env === "production" || inc.namespace === "clinicore")
    return { required: true, reason: "Manual approval required for the production namespace." };
  if (inc.severity === "critical")
    return { required: true, reason: "Critical incidents require human sign-off." };
  return { required: false, reason: "" };
}

const INITIAL: Incident[] = [
  {
    id: "ERR-2041", service: "clinicore-backend", namespace: "clinicore", env: "production", severity: "critical", status: "pending",
    agent: "k8s-healer-v3", confidence: 0.94,
    rootCause: "Quota exceeded · ResourceQuota/compute-prod",
    diagnosis: "Deployment 'replicas: 6' exceeds prod node quota after a scale-up. Proposing 6→3 replicas and right-sizing CPU/memory requests to fit current capacity while keeping 2× redundancy.",
    oldYaml: "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: clinicore-backend\nspec:\n  replicas: 6\n  template:\n    spec:\n      containers:\n        - resources:\n            requests:\n              cpu: \"2\"\n              memory: 4Gi",
    newYaml: "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: clinicore-backend\nspec:\n  replicas: 3\n  template:\n    spec:\n      containers:\n        - resources:\n            requests:\n              cpu: \"1\"\n              memory: 2Gi",
  },
  {
    id: "ERR-2040", service: "relaymed-backend", namespace: "staging", env: "staging", severity: "warning", status: "pending",
    agent: "cicd-doctor-v2", confidence: 0.88,
    rootCause: "Dependency conflict · presidio-analyzer vs spacy 3.8",
    diagnosis: "Build #5521 fails: presidio-analyzer 2.2.354 pins spacy<3.8. Proposing spacy downgrade to 3.7.6 to restore the PII de-identification pipeline.",
    oldYaml: "# requirements.txt\npresidio-analyzer==2.2.354\nspacy==3.8.2\nfastapi==0.115.0",
    newYaml: "# requirements.txt\npresidio-analyzer==2.2.354\nspacy==3.7.6\nfastapi==0.115.0",
  },
  {
    id: "ERR-2039", service: "celery-worker", namespace: "staging", env: "staging", severity: "info", status: "pending",
    agent: "rollback-agent", confidence: 0.79,
    rootCause: "OOMKilled · memory limit too low",
    diagnosis: "Worker OOMKilled processing a large FHIR bundle. Proposing memory limit 512Mi→1Gi and concurrency 4→2 to reduce peak footprint.",
    oldYaml: "resources:\n  limits:\n    memory: 512Mi\nargs:\n  - --concurrency=4",
    newYaml: "resources:\n  limits:\n    memory: 1Gi\nargs:\n  - --concurrency=2",
  },
];

const HEALINGS = [
  { id: "ERR-2037", service: "vault", action: "Restarted sealed pod, re-unsealed via KMS", agent: "k8s-healer-v3", duration: "14s", status: "resolved" as const },
  { id: "ERR-2036", service: "postgres", action: "Raised connection pool max_connections", agent: "data-steward", duration: "8s", status: "resolved" as const },
  { id: "ERR-2035", service: "keycloak", action: "Rotated expiring TLS cert", agent: "cicd-doctor-v2", duration: "11s", status: "resolved" as const },
  { id: "ERR-2034", service: "qdrant", action: "Reverted faulty index migration", agent: "rollback-agent", duration: "19s", status: "resolved" as const },
  { id: "ERR-2033", service: "immudb", action: "Attempted compaction (needs review)", agent: "data-steward", duration: "31s", status: "rejected" as const },
];

const CHATTER = [
  { agent: "openclaw-router", msg: "Routed ERR-2041 → k8s-healer-v3 (conf 0.94).", time: "09:21:04" },
  { agent: "k8s-healer-v3", msg: "Drift detected in clinicore ns. Diagnosis ready — awaiting sign-off (prod gate).", time: "09:20:51" },
  { agent: "policy-guard", msg: "Blocked autonomous apply on ERR-2041 — production namespace.", time: "09:20:50" },
  { agent: "cicd-doctor-v2", msg: "Resolved dependency conflict in relaymed build #5521.", time: "09:18:42" },
  { agent: "rollback-agent", msg: "Stable revision restored on qdrant.", time: "09:14:11" },
];

const SEV_COLOR: Record<Sev, string> = { critical: "var(--destructive)", warning: "var(--warning)", info: "var(--teal)" };

export function SelfHealing() {
  const [incidents, setIncidents] = useState(INITIAL);
  const [selId, setSelId] = useState(INITIAL[0].id);
  const sel = incidents.find((i) => i.id === selId)!;
  const gate = requiresApproval(sel);

  const act = (decision: "approve" | "reject") =>
    setIncidents((prev) => prev.map((i) => (i.id === selId ? { ...i, status: decision === "approve" ? "deploying" : "rejected" } : i)));

  const pending = incidents.filter((i) => i.status === "pending").length;

  return (
    <div>
      <ClinHeader icon={HeartPulse} title="Self-Healing (SRE)" subtitle="AI-diagnosed infra incidents · policy-gated, human-approved remediation" />

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {[
          { l: "Mesh health", v: "98.4%", icon: ShieldCheck, tone: "var(--success)" },
          { l: "Auto-heal rate", v: "91.7%", icon: Zap, tone: "var(--brand)" },
          { l: "Awaiting approval", v: String(pending), icon: AlertTriangle, tone: "var(--warning)" },
          { l: "Agents online", v: "14", icon: Bot, tone: "var(--teal)" },
        ].map((k) => {
          const Icon = k.icon;
          return (
            <div key={k.l} className="soft-card p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground"><Icon className="w-4 h-4" style={{ color: k.tone }} /> {k.l}</div>
              <div className="text-2xl font-semibold mt-1" style={{ fontFamily: "var(--font-heading)" }}>{k.v}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-5">
        {/* Triage queue */}
        <aside className="space-y-2.5">
          <div className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Queue · {incidents.length}</div>
          {incidents.map((i) => {
            const active = i.id === selId;
            return (
              <button key={i.id} onClick={() => setSelId(i.id)} className="w-full soft-card p-3 text-left transition-all" style={active ? { borderColor: "var(--brand)" } : {}}>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] text-muted-foreground">{i.id}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: SEV_COLOR[i.severity] }}>{i.severity}</span>
                </div>
                <div className="mt-1.5 text-sm font-medium">{i.service}</div>
                <div className="text-[11px] text-muted-foreground">{i.namespace} · {i.env}</div>
                <div className="mt-2 flex items-center justify-between text-[11px]">
                  <span className="inline-flex items-center gap-1 text-muted-foreground"><Bot className="w-3 h-3" /> {i.agent}</span>
                  <span className="font-mono text-brand">{Math.round(i.confidence * 100)}%</span>
                </div>
                {i.status !== "pending" && (
                  <span className="mt-2 inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded"
                    style={i.status === "deploying" ? { background: "color-mix(in oklab, var(--teal) 16%, white)", color: "color-mix(in oklab, var(--teal) 60%, black)" }
                      : i.status === "rejected" ? { background: "color-mix(in oklab, var(--destructive) 12%, white)", color: "var(--destructive)" }
                        : { background: "color-mix(in oklab, var(--success) 14%, white)", color: "var(--success)" }}>
                    {i.status}
                  </span>
                )}
              </button>
            );
          })}
        </aside>

        {/* Theater */}
        <section className="space-y-4">
          <div className="soft-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" style={{ color: SEV_COLOR[sel.severity] }} />
                  <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-heading)" }}>{sel.service}</h2>
                  <span className="rounded-md px-2 py-0.5 font-mono text-xs" style={{ background: "var(--muted)" }}>{sel.namespace}</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">Root cause: <span className="text-foreground">{sel.rootCause}</span></p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => act("reject")} disabled={sel.status !== "pending"} className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition disabled:opacity-40" style={{ color: "var(--destructive)" }}>
                  <XCircle className="w-4 h-4" /> Reject & reroute
                </button>
                <button onClick={() => act("approve")} disabled={sel.status !== "pending"} className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-40" style={{ background: "var(--brand)" }}>
                  <CheckCircle2 className="w-4 h-4" /> Approve & kubectl apply
                </button>
              </div>
            </div>

            {/* Policy gate banner */}
            {gate.required && (
              <div className="mt-3 rounded-lg p-2.5 flex items-center gap-2 text-[12px]" style={{ background: "color-mix(in oklab, var(--warning) 12%, white)" }}>
                <Lock className="w-4 h-4 shrink-0" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />
                <span><strong>Policy gate:</strong> {gate.reason} Autonomous apply is blocked — this fix needs an engineer's sign-off.</span>
              </div>
            )}
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            {/* Agentic diagnosis */}
            <div className="soft-card p-5 lg:col-span-1">
              <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground"><Terminal className="w-4 h-4 text-brand" /> Agentic diagnosis</h3>
              <div className="rounded-lg border p-3 font-mono text-[11px] leading-relaxed" style={{ background: "color-mix(in oklab, var(--navy) 4%, white)" }}>
                <div className="text-muted-foreground">&gt; analyzing logs…</div>
                <div className="text-muted-foreground">&gt; building dependency graph…</div>
                <div className="text-muted-foreground">&gt; root cause identified.</div>
                <div className="mt-2 text-brand">&gt; {sel.diagnosis}</div>
                <div className="mt-3 flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                  <ShieldCheck className="w-3 h-3" style={{ color: "var(--success)" }} /> policy check ran
                  <GitBranch className="ml-2 w-3 h-3" /> {sel.agent}
                </div>
              </div>
              <div className="mt-3">
                <div className="mb-1 flex items-center justify-between text-[11px] uppercase tracking-wider text-muted-foreground"><span>Confidence</span><span>{Math.round(sel.confidence * 100)}%</span></div>
                <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "var(--muted)" }}>
                  <div className="h-full rounded-full" style={{ width: `${sel.confidence * 100}%`, background: "var(--brand)" }} />
                </div>
              </div>
            </div>

            {/* Config diff */}
            <div className="soft-card p-5 lg:col-span-2">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Proposed configuration change</h3>
              <DiffViewer oldText={sel.oldYaml} newText={sel.newYaml} />
            </div>
          </div>

          {/* Recent healings + agent feed */}
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="soft-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><ShieldCheck className="w-4 h-4" style={{ color: "var(--success)" }} /> Recent healings</h3>
              <div className="space-y-2">
                {HEALINGS.map((a) => (
                  <div key={a.id} className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm">
                    <div className="flex items-center gap-3">
                      <span className="w-7 h-7 grid place-items-center rounded-lg border" style={a.status === "resolved" ? { borderColor: "color-mix(in oklab, var(--success) 30%, transparent)", color: "var(--success)" } : { borderColor: "color-mix(in oklab, var(--destructive) 30%, transparent)", color: "var(--destructive)" }}>
                        {a.status === "resolved" ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                      </span>
                      <div><div className="font-medium">{a.service}</div><div className="text-xs text-muted-foreground">{a.action}</div></div>
                    </div>
                    <span className="flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[11px] text-muted-foreground"><Clock className="w-3 h-3" /> {a.duration}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="soft-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Activity className="w-4 h-4 text-brand" /> Agent activity</h3>
              <div className="space-y-2">
                {CHATTER.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 text-[12px] rounded-lg border px-3 py-2">
                    <Cpu className="w-3.5 h-3.5 mt-0.5 shrink-0 text-brand" />
                    <div className="flex-1 min-w-0">
                      <span className="font-mono text-brand">{c.agent}</span> <span className="text-muted-foreground">{c.msg}</span>
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground shrink-0">{c.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
