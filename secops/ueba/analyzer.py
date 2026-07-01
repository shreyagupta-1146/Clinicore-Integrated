"""
secops/ueba/analyzer.py

User and Entity Behaviour Analytics (UEBA) — real rule-based detection.

This replaces SentiHealth's fabricated ML metrics, random.uniform() tier-pushing,
and simulated block_ip/throttle_bandwidth with deterministic threshold rules
backed by actual event streams from OpenSearch.

What this is:
  Streaming rule engine that reads structured security events and evaluates
  stateful anomaly rules. Events come from Wazuh/Falco/Suricata/Zeek via
  OpenSearch Logstash pipeline.

What this is NOT:
  - Self-training ML (UEBA ML requires months of baselining; we don't fake it)
  - Fully automated enforcement (human-in-the-loop required per HITL design)
  - A replacement for a full SIEM (OpenSearch is the SIEM; this is an alerting layer)

Human-in-the-loop (HITL) escalation:
  CRITICAL findings are queued for analyst review with a 15-minute timeout.
  If unacknowledged, they auto-escalate to the on-call engineer via PagerDuty.
  No enforcement action fires automatically — analysts confirm before any action.
  This matches SentiHealth's one good pattern (tiered HITL) while removing
  the fake enforcement it claimed to run.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ThreatSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThreatFinding:
    rule_id: str
    severity: ThreatSeverity
    title: str
    description: str
    actor_id: Optional[str]
    source_ip: Optional[str]
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requires_human_review: bool = True
    auto_escalate_after_minutes: int = 15


class UEBAAnalyzer:
    """
    Stateful rule engine over a sliding-window event stream.
    All state is in-process; production would use Redis for HA failover.
    """

    _FAILED_LOGIN_THRESHOLD = 5     # within 5 minutes
    _MASS_RECORD_THRESHOLD = 100    # records accessed within 10 minutes
    _OFF_HOURS_PHI_THRESHOLD = 20   # PHI accesses between 23:00-05:00 IST

    def __init__(self):
        # actor_id -> deque of timestamps (sliding window)
        self._failed_logins: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self._phi_accesses: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self._off_hours_accesses: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

    async def process_event(self, event: Dict[str, Any]) -> Optional[ThreatFinding]:
        """
        Process one security event and return a ThreatFinding if a rule fires.
        Returns None if no anomaly detected.
        """
        event_type = event.get("event_type", "")
        actor_id = event.get("actor_id", "")
        now = datetime.now(timezone.utc)

        if event_type == "AUTH_FAILED":
            return self._check_brute_force(actor_id, event, now)

        elif event_type in ("PHI_ACCESSED", "CONSENT_CHECKED_PERMITTED"):
            return self._check_mass_record_access(actor_id, event, now)

        elif event_type == "PHI_ACCESSED":
            return self._check_off_hours_access(actor_id, event, now)

        elif event_type == "PRIVILEGE_ESCALATION_ATTEMPT":
            return ThreatFinding(
                rule_id="PRIV_ESC_001",
                severity=ThreatSeverity.HIGH,
                title="Privilege escalation attempt",
                description=f"Actor {actor_id} attempted to escalate privileges",
                actor_id=actor_id,
                source_ip=event.get("source_ip"),
                evidence=[event],
            )

        elif event_type == "IMPOSSIBLE_TRAVEL":
            return ThreatFinding(
                rule_id="GEO_001",
                severity=ThreatSeverity.HIGH,
                title="Impossible travel detected",
                description=(
                    f"Actor {actor_id} logged in from two geographically distant "
                    f"locations within a short time window"
                ),
                actor_id=actor_id,
                source_ip=event.get("source_ip"),
                evidence=[event],
            )

        elif event_type == "AUDIT_CHAIN_WRITE_FAILURE":
            # Critical: audit chain failure means we have a gap in the tamper-evident log
            return ThreatFinding(
                rule_id="AUDIT_001",
                severity=ThreatSeverity.CRITICAL,
                title="Audit chain write failure — compliance gap",
                description="One or more audit events failed to write to immudb. This is a DPDP compliance breach.",
                actor_id=None,
                source_ip=None,
                evidence=[event],
                auto_escalate_after_minutes=5,  # faster escalation for compliance breach
            )

        return None

    def _check_brute_force(
        self, actor_id: str, event: Dict, now: datetime
    ) -> Optional[ThreatFinding]:
        window_start = now - timedelta(minutes=5)
        q = self._failed_logins[actor_id]
        q.append(now)
        recent = [t for t in q if t >= window_start]
        if len(recent) >= self._FAILED_LOGIN_THRESHOLD:
            return ThreatFinding(
                rule_id="AUTH_001",
                severity=ThreatSeverity.HIGH,
                title=f"Brute-force login detected ({len(recent)} failures in 5 min)",
                description=f"Actor {actor_id or event.get('source_ip')} has failed authentication {len(recent)} times in 5 minutes.",
                actor_id=actor_id or None,
                source_ip=event.get("source_ip"),
                evidence=[event],
            )
        return None

    def _check_mass_record_access(
        self, actor_id: str, event: Dict, now: datetime
    ) -> Optional[ThreatFinding]:
        if not actor_id:
            return None
        window_start = now - timedelta(minutes=10)
        q = self._phi_accesses[actor_id]
        q.append(now)
        recent = [t for t in q if t >= window_start]
        if len(recent) >= self._MASS_RECORD_THRESHOLD:
            return ThreatFinding(
                rule_id="DLP_001",
                severity=ThreatSeverity.HIGH,
                title=f"Mass PHI record access ({len(recent)} records in 10 min)",
                description=(
                    f"Clinician {actor_id} accessed {len(recent)} patient records within 10 minutes. "
                    "Normal clinical workflow typically involves <20 records per session."
                ),
                actor_id=actor_id,
                source_ip=event.get("source_ip"),
                evidence=[event],
            )
        return None

    def _check_off_hours_access(
        self, actor_id: str, event: Dict, now: datetime
    ) -> Optional[ThreatFinding]:
        """Flag PHI access outside business hours (23:00-05:00 IST = 17:30-23:30 UTC)."""
        hour_utc = now.hour
        if not (17 <= hour_utc <= 23):  # approximate IST off-hours
            return None
        window_start = now - timedelta(hours=1)
        q = self._off_hours_accesses[actor_id]
        q.append(now)
        recent = [t for t in q if t >= window_start]
        if len(recent) >= self._OFF_HOURS_PHI_THRESHOLD:
            return ThreatFinding(
                rule_id="TEMPORAL_001",
                severity=ThreatSeverity.MEDIUM,
                title=f"Unusual off-hours PHI access ({len(recent)} in 1 hr)",
                description=(
                    f"Actor {actor_id} accessed {len(recent)} PHI records outside business hours. "
                    "This may be legitimate on-call activity — review required."
                ),
                actor_id=actor_id,
                source_ip=event.get("source_ip"),
                evidence=[event],
            )
        return None
