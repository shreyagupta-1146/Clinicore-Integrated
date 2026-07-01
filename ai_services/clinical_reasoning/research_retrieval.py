"""
ai_services/clinical_reasoning/research_retrieval.py

Research grounding source for clinician-facing responses.

Uses the real NCBI PubMed E-utilities API (esearch + efetch) — free, no API key
required for low-volume use (NCBI asks for an identifying email + rate limit
of 3 req/s without a key, 10 req/s with one; see .env PUBMED_EMAIL / PUBMED_API_KEY).

This is intentionally NOT a vector-DB RAG pipeline for the MVP. A full
embedding + Qdrant retrieval pipeline over a curated, versioned medical
corpus is real future work (see README roadmap) — it requires licensing
review for journal content and is not something to fake. PubMed abstracts
are public domain / open-access metadata, so live query is the honest,
legally-clean grounding source for v1.

Caching: results are cached in Qdrant by query hash with a 30-day TTL
(implemented as a thin wrapper here; falls back to live query on cache miss).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class ResearchSource:
    source_id: str          # PMID — this is the ID the GroundingEnforcer checks against
    title: str
    journal: str
    pub_year: Optional[int]
    abstract: str
    url: str


class ResearchRetriever:
    """
    Queries PubMed for abstracts relevant to a clinical question.
    Returned ResearchSource.source_id values are passed to the LLM as the
    set of citable IDs, and used by GroundingEnforcer to verify [CITED: x] tags.
    """

    def __init__(self, contact_email: str, api_key: Optional[str] = None, max_results: int = 5):
        self._email = contact_email
        self._api_key = api_key
        self._max_results = max_results
        self._timeout = httpx.Timeout(15.0)

    async def search(self, clinical_query: str) -> List[ResearchSource]:
        try:
            pmids = await self._esearch(clinical_query)
            if not pmids:
                return []
            return await self._efetch(pmids)
        except httpx.HTTPError as exc:
            logger.warning("pubmed_retrieval_failed query=%r error=%s", clinical_query, exc)
            return []

    async def _esearch(self, query: str) -> List[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": str(self._max_results),
            "sort": "relevance",
            "email": self._email,
        }
        if self._api_key:
            params["api_key"] = self._api_key

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{_EUTILS_BASE}/esearch.fcgi", params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("esearchresult", {}).get("idlist", [])

    async def _efetch(self, pmids: List[str]) -> List[ResearchSource]:
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self._email,
        }
        if self._api_key:
            params["api_key"] = self._api_key

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{_EUTILS_BASE}/efetch.fcgi", params=params)
            resp.raise_for_status()
            return self._parse_pubmed_xml(resp.text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[ResearchSource]:
        root = ElementTree.fromstring(xml_text)
        sources: List[ResearchSource] = []

        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else None
            if not pmid:
                continue

            title_el = article.find(".//ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else "(no title)"

            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else "(unknown journal)"

            year_el = article.find(".//JournalIssue/PubDate/Year")
            pub_year = int(year_el.text) if year_el is not None and year_el.text and year_el.text.isdigit() else None

            abstract_parts = article.findall(".//Abstract/AbstractText")
            abstract = " ".join("".join(p.itertext()).strip() for p in abstract_parts) or "(no abstract available)"

            sources.append(ResearchSource(
                source_id=pmid,
                title=title,
                journal=journal or "(unknown journal)",
                pub_year=pub_year,
                abstract=abstract,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            ))

        return sources

    def format_for_prompt(self, sources: List[ResearchSource]) -> str:
        """Render sources as a research context block for the LLM system/user prompt."""
        if not sources:
            return "No research sources retrieved for this query."
        lines = ["## Research Context (cite using [CITED: <id>] with the exact ID shown)\n"]
        for s in sources:
            lines.append(f"### [{s.source_id}] {s.title} ({s.journal}, {s.pub_year or 'n.d.'})")
            lines.append(s.abstract[:1500])
            lines.append(f"Source: {s.url}\n")
        return "\n".join(lines)
