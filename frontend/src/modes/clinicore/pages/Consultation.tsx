import { useState, useEffect } from "react";
import {
  Stethoscope, Activity, Pill, FileText, Send, Server, Cloud, AlertTriangle,
  BookOpen, ChevronDown, ChevronRight, Network, Sparkles, ExternalLink, Loader2, Search,
  Brain, GitCompare, HelpCircle, ListChecks, ShieldQuestion, EyeOff,
} from "lucide-react";
import { ClinHeader } from "../ClinHeader";
import { Pill as Chip } from "@/components/ui";
import { ChatFeedback } from "@/components/ChatFeedback";
import { searchPubMed, generateTldr, PubMedRef } from "@/lib/pubmed";
import { scanPii } from "@/lib/pii";

const EVIDENCE_LABEL: Record<string, string> = {
  meta_analysis: "meta-analysis", rct: "RCT", clinical_trial: "clinical trial",
  guideline: "guideline", cohort: "cohort", case_report: "case report",
};

const TIMELINE = [
  { icon: Activity, cat: "Vitals", items: ["BP 148/94 mmHg (today)", "HR 92 bpm", "SpO₂ 97%", "BMI 29.4"] },
  { icon: Pill, cat: "Medications", items: ["Metformin 1g BD", "Amlodipine 5mg OD", "Atorvastatin 10mg OD"] },
  { icon: FileText, cat: "Conditions", items: ["Type 2 diabetes (2019)", "Essential hypertension (2021)"] },
  { icon: Network, cat: "ABDM records", items: ["Lipid panel — Fortis, 3mo ago (query, not copy)", "ECG — Manipal, 6mo ago"] },
];

const DIFFERENTIALS = [
  { dx: "Stable angina pectoris", likelihood: 62, evidence: "meta-analysis", query: "stable angina pectoris diagnosis exertional chest pain", link: "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001038" },
  { dx: "Acute coronary syndrome", likelihood: 18, evidence: "guideline", query: "acute coronary syndrome diabetes chest pain diagnosis", link: "https://www.escardio.org/Guidelines" },
  { dx: "Gastro-oesophageal reflux", likelihood: 11, evidence: "cohort", query: "GERD versus cardiac chest pain differentiation", link: "https://pubmed.ncbi.nlm.nih.gov/?term=GERD+cardiac+chest+pain" },
  { dx: "Musculoskeletal chest pain", likelihood: 6, evidence: "guideline", query: "costochondritis musculoskeletal chest pain evaluation", link: "https://pubmed.ncbi.nlm.nih.gov/?term=costochondritis+chest+pain" },
  { dx: "Anxiety / panic disorder", likelihood: 3, evidence: "cohort", query: "panic disorder chest pain non-cardiac", link: "https://pubmed.ncbi.nlm.nih.gov/?term=panic+disorder+chest+pain" },
];
// Agentic query the AI runs against PubMed for the leading working diagnosis.
const REFERENCE_QUERY = "exertional chest pain diabetes hypertension stable angina diagnosis";
const GAPS = [
  { gap: "No troponin / cardiac enzymes on file", impact: "Cannot exclude acute coronary syndrome" },
  { gap: "Exercise tolerance not documented", impact: "Limits angina risk stratification" },
];

// ── Rich explainability output (from clinicore-backend AIResponse schema) ─────
const CONFIDENCE: string = "moderate"; // low | moderate | high
const REASONING_STEPS = [
  "Exertional chest tightness that radiates to the left arm is a classic anginal pattern.",
  "Diabetes + hypertension are major cardiovascular risk factors, raising pre-test probability of ischaemia.",
  "2-week duration with an exertional trigger points to stable angina rather than an acute event — but ACS must be excluded first.",
  "Absence of troponin/ECG on file is the key gap preventing exclusion of ACS.",
];
const MISSING_INFO = [
  "12-lead ECG (resting + with symptoms)",
  "Serial troponin",
  "HbA1c and current lipid panel",
];
const BIAS_ALERTS = [
  { type: "Anchoring", desc: "Risk of anchoring on 'angina' and under-working-up ACS.", alt: "Actively exclude acute coronary syndrome before out-patient angina management." },
  { type: "Demographic", desc: "Women more often present with atypical ischaemic symptoms; classic criteria can under-detect.", alt: "Do not down-rank ischaemia due to an 'atypical' presentation in a 58-year-old woman." },
];
const COUNTERFACTUALS = [
  { variable: "Troponin", current: "Not measured", alternative: "If elevated", impact: "Would reclassify toward NSTEMI → emergency pathway, not out-patient." },
  { variable: "Pain character", current: "Exertional", alternative: "If at rest / crescendo", impact: "Would raise unstable angina probability significantly." },
];
const UNCERTAINTY = [
  { factor: "No cardiac biomarkers", impact: "high", rec: "Order ECG + serial troponin before disposition." },
  { factor: "Symptom-onset timing vague", impact: "medium", rec: "Clarify exact onset and progression pattern." },
];

const EVIDENCE_COLOR: Record<string, string> = {
  "meta-analysis": "var(--success)", cohort: "var(--teal)", guideline: "var(--brand)", "case-report": "var(--warning)",
};

export function Consultation() {
  const [msgs, setMsgs] = useState([
    { role: "clinician", text: "58F, exertional chest tightness 2 weeks, radiates to left arm. T2DM + HTN. Differential and next steps?" },
    { role: "ai", text: "structured" },
  ]);
  const [text, setText] = useState("");
  const [route] = useState<"onprem" | "cloud">("cloud");
  const piiHits = scanPii(text);

  const send = () => {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "clinician", text }, { role: "ai", text: "structured" }]);
    setText("");
  };

  return (
    <div>
      <ClinHeader
        icon={Stethoscope}
        title="Consultation — Anita R., 58F"
        subtitle="ABHA 12-3456-7890-1234 · Consent: active (clinical decision support)"
        action={<Chip tone="good">Consent verified</Chip>}
      />

      {/* Red-flag banner */}
      <div className="rounded-lg p-3 mb-4 flex items-start gap-3 animate-fade-in" style={{ background: "color-mix(in oklab, var(--destructive) 8%, white)", border: "1px solid color-mix(in oklab, var(--destructive) 30%, transparent)" }}>
        <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: "var(--destructive)" }} />
        <div className="text-sm">
          <span className="font-semibold" style={{ color: "var(--destructive)" }}>Cardiac red flag detected.</span>
          <span className="text-muted-foreground"> Chest pain with radiation in a diabetic patient — consider urgent ACS workup (ECG, troponin) before out-patient management.</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        {/* Left: FHIR timeline */}
        <div className="lg:col-span-2 space-y-4">
          <div className="soft-card p-5 animate-fade-in">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><FileText className="w-4 h-4 text-brand" /> Patient FHIR Timeline</h3>
            <div className="space-y-4">
              {TIMELINE.map((t) => {
                const Icon = t.icon;
                return (
                  <div key={t.cat}>
                    <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5"><Icon className="w-3.5 h-3.5" /> {t.cat}</div>
                    <ul className="space-y-1 pl-5">
                      {t.items.map((it) => (
                        <li key={it} className="text-sm relative before:content-[''] before:absolute before:-left-3 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full" style={{}}>
                          <span className="absolute -left-3 top-2 w-1.5 h-1.5 rounded-full" style={{ background: "var(--brand)" }} />
                          {it}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: AI CDS */}
        <div className="lg:col-span-3 space-y-4">
          <div className="soft-card p-5 animate-fade-in flex flex-col" style={{ minHeight: "60vh" }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-2"><Sparkles className="w-4 h-4 text-brand" /> AI Clinical Decision Support</h3>
              <span className="flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full"
                style={route === "onprem" ? { background: "color-mix(in oklab, var(--brand) 12%, white)", color: "var(--brand)" } : { background: "color-mix(in oklab, var(--teal) 16%, white)", color: "color-mix(in oklab, var(--teal) 60%, black)" }}>
                {route === "onprem" ? <Server className="w-3 h-3" /> : <Cloud className="w-3 h-3" />}
                {route === "onprem" ? "On-Prem · Raw PHI" : "Cloud · De-identified"}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {msgs.map((m, i) =>
                m.role === "clinician" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[85%] rounded-xl px-4 py-2.5 text-sm text-white" style={{ background: "var(--brand)" }}>{m.text}</div>
                  </div>
                ) : (
                  <StructuredAnswer key={i} />
                )
              )}
            </div>

            {/* PII pre-scan — shows what will be redacted before cloud send */}
            {route === "cloud" && piiHits.length > 0 && (
              <div className="mt-3 rounded-lg p-2.5 flex items-start gap-2" style={{ background: "color-mix(in oklab, var(--warning) 12%, white)" }}>
                <EyeOff className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />
                <div className="text-[11px]">
                  <span className="font-medium">{piiHits.length} PII item{piiHits.length > 1 ? "s" : ""} will be redacted before this leaves for the cloud model:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {piiHits.map((h, i) => (
                      <span key={i} className="font-mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: "white", color: "color-mix(in oklab, var(--warning) 60%, black)" }}>[{h.type}]</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div className="mt-3 flex items-center gap-2">
              <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Ask about differentials, workup, dosing…" className="flex-1 px-4 py-2.5 rounded-lg border bg-white outline-none text-sm" />
              <button onClick={send} className="w-10 h-10 grid place-items-center rounded-lg text-white" style={{ background: "var(--brand)" }}><Send className="w-4 h-4" /></button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-2">Decision support only — final diagnostic and treatment decisions rest with the clinician.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function StructuredAnswer() {
  const [expanded, setExpanded] = useState(false);
  const [refs, setRefs] = useState<PubMedRef[] | null>(null);
  const [loadingRefs, setLoadingRefs] = useState(true);

  // Agentic step: on mount, the AI queries PubMed for the precedent cases
  // behind the leading working diagnosis, then generates a TL;DR for each.
  useEffect(() => {
    let alive = true;
    (async () => {
      const found = await searchPubMed(REFERENCE_QUERY, 6);
      if (!alive) return;
      setRefs(found);
      setLoadingRefs(false);
      // enrich with AI TL;DRs (Grok proxy if configured, else heuristic)
      const withTldr = await Promise.all(
        found.map(async (r) => ({ ...r, tldr: r.tldr || (await generateTldr(r.title, REFERENCE_QUERY)) }))
      );
      if (alive) setRefs(withTldr);
    })();
    return () => { alive = false; };
  }, []);

  const shown = expanded ? DIFFERENTIALS : DIFFERENTIALS.slice(0, 3);

  const confTone = CONFIDENCE === "high" ? "var(--success)" : CONFIDENCE === "moderate" ? "var(--teal)" : "var(--warning)";

  return (
    <div className="rounded-xl p-4 text-sm" style={{ background: "var(--muted)" }}>
      <div className="flex items-start justify-between gap-3">
        <p className="leading-relaxed flex-1">Given exertional chest pain radiating to the left arm in a 58-year-old with diabetes and hypertension, this presentation is concerning for an ischaemic cause and warrants exclusion of ACS first.</p>
        <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full shrink-0 text-white" style={{ background: confTone }}>
          {CONFIDENCE} confidence
        </span>
      </div>

      {/* Chain-of-thought reasoning */}
      <div className="mt-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5"><Brain className="w-3.5 h-3.5 text-brand" /> Reasoning steps</div>
        <ol className="space-y-1.5">
          {REASONING_STEPS.map((s, i) => (
            <li key={i} className="flex gap-2 text-[13px] leading-snug">
              <span className="w-5 h-5 grid place-items-center rounded-md text-[10px] font-bold shrink-0" style={{ background: "color-mix(in oklab, var(--brand) 12%, white)", color: "var(--brand)" }}>{i + 1}</span>
              <span>{s}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Differentials — top 3, expand to 5 */}
      <div className="mt-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Possible diagnoses (ranked)</div>
          <span className="text-[10px] text-muted-foreground">Top {shown.length} of {DIFFERENTIALS.length}</span>
        </div>
        <div className="space-y-2">
          {shown.map((d, i) => (
            <a key={d.dx} href={d.link} target="_blank" rel="noreferrer" className="block bg-card rounded-lg p-3 border hover:shadow-md transition-shadow group">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium flex items-center gap-1.5">
                  <span className="w-5 h-5 grid place-items-center rounded-md text-[10px] font-bold" style={{ background: "color-mix(in oklab, var(--brand) 12%, white)", color: "var(--brand)" }}>{i + 1}</span>
                  {d.dx}
                  <ExternalLink className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </span>
                <span className="text-xs font-semibold">{d.likelihood}%</span>
              </div>
              <div className="h-1.5 rounded-full mt-2 overflow-hidden" style={{ background: "var(--muted)" }}>
                <div className="h-full rounded-full" style={{ width: `${d.likelihood}%`, background: "var(--brand)" }} />
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full text-white" style={{ background: EVIDENCE_COLOR[d.evidence] || "var(--brand)" }}>{d.evidence}</span>
                <span className="text-[10px] text-brand">View guideline / evidence →</span>
              </div>
            </a>
          ))}
        </div>
        {!expanded && (
          <button onClick={() => setExpanded(true)} className="mt-2 w-full flex items-center justify-center gap-1 text-xs font-medium text-brand py-2 rounded-lg border border-dashed hover:bg-black/[0.02]">
            <ChevronDown className="w-3.5 h-3.5" /> Show {DIFFERENTIALS.length - 3} more diagnoses
          </button>
        )}
      </div>

      {/* Diagnostic gaps */}
      <div className="mt-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Diagnostic gaps</div>
        <div className="space-y-2">
          {GAPS.map((g) => (
            <div key={g.gap} className="flex items-start gap-2 rounded-lg p-2.5" style={{ background: "color-mix(in oklab, var(--warning) 10%, white)" }}>
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: "color-mix(in oklab, var(--warning) 60%, black)" }} />
              <div>
                <div className="text-xs font-medium">{g.gap}</div>
                <div className="text-[11px] text-muted-foreground">{g.impact}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cognitive bias alerts */}
      <div className="mt-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5"><ShieldQuestion className="w-3.5 h-3.5" style={{ color: "var(--coral)" }} /> Cognitive bias alerts</div>
        <div className="space-y-2">
          {BIAS_ALERTS.map((b) => (
            <div key={b.type} className="rounded-lg p-2.5 border" style={{ background: "color-mix(in oklab, var(--coral) 6%, white)", borderColor: "color-mix(in oklab, var(--coral) 25%, transparent)" }}>
              <div className="text-xs font-semibold" style={{ color: "var(--coral)" }}>{b.type} bias</div>
              <div className="text-[11px] mt-0.5">{b.desc}</div>
              <div className="text-[11px] text-muted-foreground mt-1"><span className="font-medium">Consider:</span> {b.alt}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Counterfactual insights */}
      <div className="mt-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5"><GitCompare className="w-3.5 h-3.5 text-brand" /> Counterfactual insights</div>
        <div className="space-y-2">
          {COUNTERFACTUALS.map((c) => (
            <div key={c.variable} className="rounded-lg p-2.5 bg-card border text-[11px]">
              <span className="font-semibold">{c.variable}:</span> <span className="text-muted-foreground">{c.current}</span> → <span className="font-medium">{c.alternative}</span>
              <div className="text-muted-foreground mt-0.5">{c.impact}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Uncertainty + missing info — two columns */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5"><HelpCircle className="w-3.5 h-3.5 text-brand" /> Uncertainty</div>
          <div className="space-y-1.5">
            {UNCERTAINTY.map((u) => (
              <div key={u.factor} className="rounded-lg p-2 bg-card border text-[11px]">
                <div className="flex items-center gap-1.5"><Chip tone={u.impact === "high" ? "bad" : u.impact === "medium" ? "warn" : "neutral"}>{u.impact}</Chip> <span className="font-medium">{u.factor}</span></div>
                <div className="text-muted-foreground mt-0.5">{u.rec}</div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5"><ListChecks className="w-3.5 h-3.5 text-brand" /> Missing information</div>
          <ul className="space-y-1">
            {MISSING_INFO.map((m) => (
              <li key={m} className="flex items-center gap-2 text-[11px] rounded-lg p-2 bg-card border"><EyeOff className="w-3 h-3 text-muted-foreground shrink-0" /> {m}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Agentic PubMed references — the cases the AI referred to, with links */}
      <div className="mt-4">
        <div className="flex items-center gap-2 mb-2">
          <Search className="w-3.5 h-3.5 text-brand" />
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Referenced cases & precedents</div>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: "color-mix(in oklab, var(--teal) 16%, white)", color: "color-mix(in oklab, var(--teal) 60%, black)" }}>via PubMed agent</span>
        </div>
        {loadingRefs ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground py-2"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Searching PubMed for supporting cases…</div>
        ) : (
          <div className="space-y-1.5">
            {refs?.map((r) => (
              <a key={r.pmid} href={r.url} target="_blank" rel="noreferrer" className="block text-[11px] rounded-lg p-2.5 bg-card border hover:shadow-md transition-shadow group">
                <div className="flex items-start gap-2">
                  <BookOpen className="w-3.5 h-3.5 mt-0.5 shrink-0 text-brand" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium leading-snug">{r.title}</div>
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      {r.pmid !== "search" && <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full text-white" style={{ background: EVIDENCE_COLOR[EVIDENCE_LABEL[r.evidenceLevel]] || "var(--brand)" }}>{EVIDENCE_LABEL[r.evidenceLevel] || r.evidenceLevel}</span>}
                      <span className="text-muted-foreground">{r.source} {r.pmid !== "search" && <span className="font-mono">· PMID {r.pmid}</span>}</span>
                      {r.pmid !== "search" && <span className="text-[9px] text-muted-foreground">· relevance {(r.relevance * 100).toFixed(0)}%</span>}
                    </div>
                    {r.tldr && <div className="mt-1 text-muted-foreground italic flex items-start gap-1"><Sparkles className="w-2.5 h-2.5 mt-0.5 shrink-0 text-brand" /> {r.tldr}</div>}
                  </div>
                  <ExternalLink className="w-3 h-3 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </a>
            ))}
            <a href={`https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(REFERENCE_QUERY)}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[11px] font-medium text-brand mt-1">
              See all results on PubMed <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </div>

      {/* Clinician feedback — feeds the model adaptation loop */}
      <ChatFeedback mode="clinicore" question="differential + next steps" answer="structured CDS answer" />
    </div>
  );
}
