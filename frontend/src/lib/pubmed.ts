/**
 * lib/pubmed.ts
 *
 * Agentic evidence retrieval. Rather than building our own literature index,
 * we outsource to PubMed's public E-utilities API (NCBI) — a fully-built,
 * authoritative platform. The Clinicore differential engine calls this to
 * fetch the actual cases/precedents behind each suggested diagnosis and links
 * straight to the source articles.
 *
 * esearch -> PMIDs, esummary -> titles/journals. Public API (an API key only
 * raises rate limits; set VITE_PUBMED_API_KEY to use one). Falls back to a
 * curated set if the network call fails (offline preview).
 */

export interface PubMedRef {
  pmid: string;
  title: string;
  source: string; // journal · year
  url: string;
  evidenceLevel: string; // meta_analysis | rct | clinical_trial | guideline | cohort | case_report
  tldr: string;          // AI 1-line "why this is relevant"
  relevance: number;     // 0..1
}

// Mirrors rag_service._classify_evidence_level
function classifyEvidence(pubtypes: string[]): string {
  const t = pubtypes.map((p) => p.toLowerCase());
  if (t.some((x) => x.includes("meta-analysis") || x.includes("systematic review"))) return "meta_analysis";
  if (t.some((x) => x.includes("randomized controlled trial"))) return "rct";
  if (t.some((x) => x.includes("clinical trial"))) return "clinical_trial";
  if (t.some((x) => x.includes("guideline"))) return "guideline";
  if (t.some((x) => x.includes("cohort"))) return "cohort";
  return "case_report";
}

/**
 * Generate a 1-line TL;DR for an article. Uses the Grok proxy when configured
 * (VITE_AI_PROXY_URL), else falls back to a concise heuristic from the title.
 * Mirrors llm_service.generate_research_tldr on the backend.
 */
export async function generateTldr(title: string, context: string): Promise<string> {
  const proxy = import.meta.env.VITE_AI_PROXY_URL;
  if (proxy) {
    try {
      const r = await fetch(proxy, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: "research_tldr", title, context }),
      });
      if (r.ok) {
        const d = await r.json();
        if (d.tldr) return d.tldr as string;
      }
    } catch { /* fall through */ }
  }
  // Heuristic fallback — honest, no fabricated findings
  return `Relevant to "${context.slice(0, 48)}…" — open to review the trial design and outcomes.`;
}

const EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils";
const KEY = import.meta.env.VITE_PUBMED_API_KEY as string | undefined;

export async function searchPubMed(query: string, retmax = 6): Promise<PubMedRef[]> {
  try {
    const keyParam = KEY ? `&api_key=${KEY}` : "";
    const esearch = await fetch(
      `${EUTILS}/esearch.fcgi?db=pubmed&retmode=json&sort=relevance&retmax=${retmax}&term=${encodeURIComponent(query)}${keyParam}`
    );
    const sj = await esearch.json();
    const ids: string[] = sj?.esearchresult?.idlist ?? [];
    if (!ids.length) return fallback(query);

    const esum = await fetch(`${EUTILS}/esummary.fcgi?db=pubmed&retmode=json&id=${ids.join(",")}${keyParam}`);
    const uj = await esum.json();
    const result = uj?.result ?? {};
    return ids.map((id, i) => {
      const r = result[id] ?? {};
      const year = (r.pubdate || "").split(" ")[0] || "";
      const evidenceLevel = classifyEvidence(r.pubtype ?? []);
      return {
        pmid: id,
        title: r.title || "Untitled article",
        source: [r.fulljournalname || r.source, year].filter(Boolean).join(" · "),
        url: `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
        evidenceLevel,
        tldr: "", // filled in by the caller via generateTldr (async)
        relevance: Math.max(0.4, 1 - i * 0.09), // relevance-ranked order from esearch
      };
    });
  } catch {
    return fallback(query);
  }
}

function fallback(query: string): PubMedRef[] {
  return [
    {
      pmid: "search",
      title: `Search PubMed for "${query}"`,
      source: "PubMed · live search",
      url: `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(query)}`,
      evidenceLevel: "guideline",
      tldr: "Live PubMed search for this clinical query.",
      relevance: 0.5,
    },
  ];
}
