"""
secops/detection/rules.py

Deterministic Sigma-style detection rules that complement the UEBA analyzer.

These rules operate on parsed log events forwarded from:
  Wazuh     → host IDS / FIM / rootkit detection
  Falco     → Kubernetes container runtime anomalies
  Suricata  → network IDS (signature-based)
  Zeek      → network protocol analysis

Rules are expressed as Python dataclasses (not YAML) for testability.
A real production deployment would also export these as Sigma YAML for
compatibility with OpenSearch SIEM dashboards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from secops.ueba.analyzer import ThreatFinding, ThreatSeverity


@dataclass
class DetectionRule:
    rule_id: str
    title: str
    severity: ThreatSeverity
    description: str
    match_fn: Callable[[Dict[str, Any]], bool]
    build_finding_fn: Callable[[Dict[str, Any]], ThreatFinding]


def _make_finding(
    event: Dict[str, Any],
    rule_id: str,
    severity: ThreatSeverity,
    title: str,
    description: str,
    auto_escalate_after_minutes: int = 15,
) -> ThreatFinding:
    return ThreatFinding(
        rule_id=rule_id,
        severity=severity,
        title=title,
        description=description,
        actor_id=event.get("actor_id") or event.get("user"),
        source_ip=event.get("source_ip") or event.get("src_ip"),
        evidence=[event],
        auto_escalate_after_minutes=auto_escalate_after_minutes,
    )


DETECTION_RULES: List[DetectionRule] = [

    # ── Falco: sensitive file access inside container ──────────────────────
    DetectionRule(
        rule_id="FALCO_001",
        title="Sensitive file read inside clinical container",
        severity=ThreatSeverity.HIGH,
        description="A process inside a container read a sensitive file (e.g. /etc/passwd, /etc/shadow, private keys).",
        match_fn=lambda e: (
            e.get("source") == "falco"
            and re.search(r"(/etc/shadow|/etc/passwd|\.pem|\.key|/proc/1/)", e.get("file", ""))
        ),
        build_finding_fn=lambda e: _make_finding(e, "FALCO_001", ThreatSeverity.HIGH, "Sensitive file read inside container", f"File: {e.get('file')}"),
    ),

    # ── Falco: unexpected outbound connection from backend ─────────────────
    DetectionRule(
        rule_id="FALCO_002",
        title="Unexpected outbound connection from backend pod",
        severity=ThreatSeverity.MEDIUM,
        description="Backend container opened an outbound TCP connection to an unexpected destination. Possible data exfiltration or C2.",
        match_fn=lambda e: (
            e.get("source") == "falco"
            and e.get("rule") == "Unexpected outbound connection destination"
        ),
        build_finding_fn=lambda e: _make_finding(e, "FALCO_002", ThreatSeverity.MEDIUM, "Unexpected outbound connection", f"Dest: {e.get('fd_name')}"),
    ),

    # ── Wazuh: FIM — unexpected binary modification ────────────────────────
    DetectionRule(
        rule_id="WAZUH_FIM_001",
        title="Unexpected binary modification (FIM alert)",
        severity=ThreatSeverity.HIGH,
        description="Wazuh FIM detected modification of a monitored binary or config. Possible supply-chain or persistence attack.",
        match_fn=lambda e: (
            e.get("source") == "wazuh"
            and e.get("rule_group") == "syscheck"
            and e.get("syscheck.changed_attributes") is not None
        ),
        build_finding_fn=lambda e: _make_finding(e, "WAZUH_FIM_001", ThreatSeverity.HIGH, "FIM: unexpected file modification", f"File: {e.get('syscheck.path')}"),
    ),

    # ── Suricata: known malware signature ─────────────────────────────────
    DetectionRule(
        rule_id="SURICATA_001",
        title="Suricata IDS: known malware signature matched",
        severity=ThreatSeverity.CRITICAL,
        description="Suricata matched an ET MALWARE or ET TROJAN signature in network traffic.",
        match_fn=lambda e: (
            e.get("source") == "suricata"
            and re.search(r"ET MALWARE|ET TROJAN|ET CURRENT_EVENTS", e.get("alert_signature", ""))
        ),
        build_finding_fn=lambda e: _make_finding(
            e, "SURICATA_001", ThreatSeverity.CRITICAL,
            "Malware signature in network traffic",
            f"Sig: {e.get('alert_signature')} — SrcIP: {e.get('src_ip')} DstIP: {e.get('dest_ip')}",
            auto_escalate_after_minutes=5,
        ),
    ),

    # ── Zeek: DNS tunneling heuristic ─────────────────────────────────────
    DetectionRule(
        rule_id="ZEEK_DNS_001",
        title="DNS tunneling heuristic (long DNS query)",
        severity=ThreatSeverity.MEDIUM,
        description="Zeek logged a DNS query with an unusually long hostname — possible DNS tunneling for data exfiltration.",
        match_fn=lambda e: (
            e.get("source") == "zeek"
            and e.get("proto") == "dns"
            and len(e.get("query", "")) > 100
        ),
        build_finding_fn=lambda e: _make_finding(e, "ZEEK_DNS_001", ThreatSeverity.MEDIUM, "Possible DNS tunneling", f"Query len: {len(e.get('query',''))} — {e.get('query','')[:80]}..."),
    ),
]


def evaluate_all_rules(event: Dict[str, Any]) -> Optional[ThreatFinding]:
    """
    Evaluate every detection rule against the event.
    Returns the first matching finding (highest severity rules should be listed first).
    """
    for rule in DETECTION_RULES:
        try:
            if rule.match_fn(event):
                return rule.build_finding_fn(event)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("rule_eval_error rule_id=%s error=%s", rule.rule_id, exc)
    return None
