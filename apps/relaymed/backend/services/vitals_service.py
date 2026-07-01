"""
apps/relaymed/backend/services/vitals_service.py

Wearable/vital ingestion pipeline:
  1. Consent check (WELLNESS_TRACKING purpose)
  2. Write Observation to the shared FHIR timeline (the durable record —
     this is what Clinicore reads from, NOT a RelayMed-local table)
  3. Pull recent baseline observations for the same metric
  4. Run the deterministic anomaly check (rules/vitals_anomaly.py)
  5. If anomalous AND the patient has consented caregivers for this category,
     dispatch an alert
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from apps.relaymed.backend.modules.caregiver.service import CaregiverService
from apps.relaymed.backend.rules.vitals_anomaly import AnomalySeverity, VitalMetric, evaluate_vital
from apps.relaymed.backend.services.notification_service import AlertPayload, NotificationService
from substrate.audit.models import AuditEvent, AuditEventType
from substrate.audit.service import AuditLogger
from substrate.consent.models import ConsentPurpose, DataCategory
from substrate.consent.service import ConsentManager
from substrate.fhir.timeline import FHIRTimeline

logger = logging.getLogger(__name__)

_FHIR_LOINC_CODE = {
    VitalMetric.HEART_RATE: ("8867-4", "Heart rate"),
    VitalMetric.SPO2: ("59408-5", "Oxygen saturation"),
    VitalMetric.SYSTOLIC_BP: ("8480-6", "Systolic blood pressure"),
    VitalMetric.DIASTOLIC_BP: ("8462-4", "Diastolic blood pressure"),
    VitalMetric.BLOOD_GLUCOSE: ("2339-0", "Blood glucose"),
    VitalMetric.TEMPERATURE: ("8310-5", "Body temperature"),
}


class VitalsIngestionDeniedError(Exception):
    pass


class VitalsService:
    def __init__(
        self,
        fhir: FHIRTimeline,
        consent_manager: ConsentManager,
        caregiver_service: CaregiverService,
        notification_service: NotificationService,
        audit_logger: AuditLogger,
    ):
        self._fhir = fhir
        self._consent = consent_manager
        self._caregivers = caregiver_service
        self._notify = notification_service
        self._audit = audit_logger

    async def ingest(
        self,
        *,
        patient_id: str,
        patient_display_name: str,
        metric: VitalMetric,
        value: float,
        device_source: str,
        ip_address: str,
    ) -> dict:
        consent_result = await self._consent.check_consent(
            data_principal_id=patient_id,
            requesting_entity_id="relaymed",
            purpose=ConsentPurpose.WELLNESS_TRACKING,
            data_categories=[DataCategory.WEARABLE_STREAM, DataCategory.VITALS],
        )
        if not consent_result.permitted:
            raise VitalsIngestionDeniedError(consent_result.denial_reason or "Consent not granted")

        code, display = _FHIR_LOINC_CODE[metric]
        observed_at = datetime.now(timezone.utc)

        observation_id = await self._fhir.add_observation({
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": observed_at.isoformat(),
            "valueQuantity": {"value": value},
            "device": {"display": device_source},
        })

        await self._audit.log(AuditEvent(
            event_type=AuditEventType.WELLNESS_VITAL_INGESTED,
            actor_id=patient_id,
            resource_type="observation",
            resource_id=observation_id,
            details={"metric": metric.value, "value": value, "device_source": device_source},
            ip_address=ip_address,
            authorising_consent_id=consent_result.consent_id,
        ))

        baseline = await self._fetch_baseline_values(patient_id, metric, exclude_observation_id=observation_id)
        anomaly = evaluate_vital(metric, value, baseline)

        if anomaly.severity != AnomalySeverity.NORMAL:
            await self._handle_anomaly(patient_id, patient_display_name, anomaly, ip_address)

        return {
            "observation_id": observation_id,
            "anomaly_severity": anomaly.severity.value,
            "anomaly_reasoning": anomaly.reasoning,
        }

    async def ingest_batch(
        self,
        *,
        patient_id: str,
        patient_display_name: str,
        readings,  # list[wearables.normalizer.NormalizedReading]
        ip_address: str,
    ) -> dict:
        """
        Ingest a batch of already-normalized wearable readings (from the mobile
        app's Health Connect / HealthKit read, a Fitbit pull, or an aggregator
        webhook). Each reading goes through the SAME single-reading pipeline —
        consent check, FHIR write, anomaly z-score, caregiver alert — so there is
        one code path and one audit trail regardless of source.
        """
        results = []
        for r in readings:
            try:
                res = await self.ingest(
                    patient_id=patient_id,
                    patient_display_name=patient_display_name,
                    metric=r.metric,
                    value=r.value,
                    device_source=f"{r.source.value}:{r.device_display}".rstrip(":"),
                    ip_address=ip_address,
                )
                results.append(res)
            except VitalsIngestionDeniedError:
                raise  # consent failure applies to the whole batch — surface it
            except Exception as exc:  # a single bad reading must not drop the batch
                logger.warning("wearable_batch_reading_failed metric=%s error=%s", r.metric, exc)
        return {"ingested": len(results), "readings": results}

    async def _fetch_baseline_values(
        self, patient_id: str, metric: VitalMetric, exclude_observation_id: str, max_count: int = 30
    ) -> List[float]:
        observations = await self._fhir.get_observations(
            patient_id=patient_id, category="vital-signs", max_count=max_count
        )
        code, _ = _FHIR_LOINC_CODE[metric]
        values: List[float] = []
        for obs in observations:
            if obs.get("id") == exclude_observation_id:
                continue
            codings = obs.get("code", {}).get("coding", [])
            if any(c.get("code") == code for c in codings):
                value = obs.get("valueQuantity", {}).get("value")
                if value is not None:
                    values.append(float(value))
        return values

    async def _handle_anomaly(self, patient_id, patient_display_name, anomaly, ip_address) -> None:
        await self._audit.log(AuditEvent(
            event_type=AuditEventType.WELLNESS_ANOMALY_DETECTED,
            actor_id="system",
            resource_type="patient",
            resource_id=patient_id,
            details={
                "metric": anomaly.metric.value,
                "value": anomaly.value,
                "severity": anomaly.severity.value,
                "z_score": anomaly.z_score,
                "reasoning": anomaly.reasoning,
            },
            ip_address=ip_address,
        ))

        links = await self._caregivers.list_active_links_for_caregiver.__self__.list_links_for_patient(patient_id)
        active_links = [
            l for l in links
            if l.status == "active" and l.alert_on_vital_anomaly and "vitals" in l.visible_categories
        ]

        severity = "critical" if anomaly.severity.value == "absolute_threshold" else "warning"
        for link in active_links:
            delivered = await self._notify.send_caregiver_alert(AlertPayload(
                caregiver_id=link.caregiver_id,
                patient_display_name=patient_display_name,
                title=f"Unusual {anomaly.metric.value.replace('_', ' ')} reading",
                body=anomaly.reasoning,
                severity=severity,
            ))
            await self._audit.log(AuditEvent(
                event_type=AuditEventType.WELLNESS_ALERT_SENT,
                actor_id="system",
                resource_type="caregiver_link",
                resource_id=link.link_id,
                details={"delivered": delivered, "severity": severity},
                ip_address=ip_address,
            ))
