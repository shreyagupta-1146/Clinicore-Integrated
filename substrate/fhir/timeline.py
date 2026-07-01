"""
platform/fhir/timeline.py

Consented FHIR R4 patient timeline — the connective tissue between RelayMed and Clinicore.

RelayMed writes to this timeline (vitals, medications, conditions, lifestyle).
Clinicore reads from it (with consent) when a doctor opens a consultation.

This is the real moat: not just "B2B + B2C" but a shared, consented longitudinal
record that makes Clinicore's suggestions richer than a standalone chatbot.

FHIR resources used:
  Patient         — demographics + ABHA ID
  Observation     — vitals, lab results, lifestyle metrics
  MedicationStatement — current + past medications + adherence
  Condition       — problems list
  CarePlan        — personalised escalation / first-aid plans
  Consent         — mirrors the platform consent ledger (ABDM-compatible)

ABDM/ABHA integration:
  Patients are linked via their ABHA health ID (14-digit).
  Cross-facility queries use the ABDM HIE-CM federated consent model:
  QUERY, not COPY — we ask the other facility's FHIR server for the record
  rather than copying PHI to our server.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FHIRTimeline:
    """
    Client for the platform's FHIR R4 server (Medplum or HAPI FHIR).
    All reads require a verified ConsentVerificationResult (permitted=True).
    """

    def __init__(self, fhir_base_url: str, auth_token: str):
        self._base = fhir_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }
        self._timeout = httpx.Timeout(30.0)

    # ── Observations (vitals + labs + lifestyle) ──────────────────────────────

    async def add_observation(self, observation: Dict[str, Any]) -> str:
        """Write a FHIR Observation resource. Returns the server-assigned ID."""
        return await self._create("Observation", observation)

    async def get_observations(
        self,
        patient_id: str,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_count: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve observations for a patient.
        category: e.g., "vital-signs", "laboratory", "survey" (FHIR standard values)
        """
        params: Dict[str, str] = {
            "subject": f"Patient/{patient_id}",
            "_count": str(max_count),
            "_sort": "-date",
        }
        if category:
            params["category"] = category
        if date_from:
            params["date"] = f"ge{date_from.isoformat()}"
        if date_to:
            params["date"] = f"le{date_to.isoformat()}"

        return await self._search("Observation", params)

    # ── Medications ───────────────────────────────────────────────────────────

    async def add_medication_statement(self, med_statement: Dict[str, Any]) -> str:
        return await self._create("MedicationStatement", med_statement)

    async def get_medications(self, patient_id: str, status: str = "active") -> List[Dict[str, Any]]:
        return await self._search("MedicationStatement", {
            "subject": f"Patient/{patient_id}",
            "status": status,
        })

    # ── Care plans (personalised escalation + first-aid) ─────────────────────

    async def get_care_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        return await self._search("CarePlan", {
            "subject": f"Patient/{patient_id}",
            "status": "active",
        })

    async def upsert_care_plan(self, care_plan: Dict[str, Any]) -> str:
        fhir_id = care_plan.get("id")
        if fhir_id:
            return await self._update("CarePlan", fhir_id, care_plan)
        return await self._create("CarePlan", care_plan)

    # ── Conditions (problem list) ─────────────────────────────────────────────

    async def get_conditions(
        self, patient_id: str, clinical_status: str = "active"
    ) -> List[Dict[str, Any]]:
        return await self._search("Condition", {
            "subject": f"Patient/{patient_id}",
            "clinical-status": clinical_status,
        })

    # ── Patient ───────────────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return await self._read("Patient", patient_id)

    async def link_abha_id(self, patient_id: str, abha_id: str) -> None:
        """
        Add an ABHA identifier to the Patient resource.
        The ABHA system = "https://abha.abdm.gov.in"
        """
        patient = await self.get_patient(patient_id)
        if patient is None:
            raise FHIRResourceNotFound(f"Patient/{patient_id}")
        identifiers = patient.get("identifier", [])
        # Avoid duplicate ABHA linkage
        for ident in identifiers:
            if ident.get("system") == "https://abha.abdm.gov.in":
                return  # Already linked
        identifiers.append({
            "system": "https://abha.abdm.gov.in",
            "value": abha_id,
        })
        patient["identifier"] = identifiers
        await self._update("Patient", patient_id, patient)

    # ── Cross-facility federated query via ABDM HIE-CM ───────────────────────

    async def federated_query(
        self,
        abha_id: str,
        abdm_consent_artefact_id: str,
        resource_type: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query another facility's FHIR records via ABDM HIE-CM.

        Architecture: ABDM HIE-CM is callback-based, not request-response.
        This method initiates the request and returns a transaction_id.
        The actual FHIR bundles arrive asynchronously via POST to
        /api/v1/abdm/callback (see apps/clinicore/backend/api/v1/routes/).

        To use synchronously in tests: await the pending transaction via
        the ABDMCallbackStore (a small Redis queue keyed by transaction_id).

        Requires: ABDM_CLIENT_ID, ABDM_CLIENT_SECRET in environment.
        Register at: https://sandbox.abdm.gov.in/
        """
        from substrate.fhir.abdm_client import HealthInfoRequest, build_abdm_client_from_env
        from datetime import timezone

        abdm = build_abdm_client_from_env()

        request = HealthInfoRequest(
            consent_artefact_id=abdm_consent_artefact_id,
            date_from=date_from or (datetime.now(timezone.utc) - timedelta(days=365)),
            date_to=date_to or datetime.now(timezone.utc),
        )

        request_id = await abdm.request_health_info(request)
        logger.info(
            "abdm_federated_query_initiated abha_id=%s request_id=%s resource_type=%s",
            abha_id, request_id, resource_type,
        )

        # Return the request_id as a placeholder; caller must poll the callback store.
        # In the clinical UI, this drives a "Loading records from other facility..." indicator.
        return [{"status": "pending", "request_id": request_id, "resource_type": resource_type}]

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _create(self, resource_type: str, resource: Dict) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/{resource_type}",
                json=resource,
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def _read(self, resource_type: str, resource_id: str) -> Optional[Dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base}/{resource_type}/{resource_id}",
                headers=self._headers,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def _update(self, resource_type: str, resource_id: str, resource: Dict) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.put(
                f"{self._base}/{resource_type}/{resource_id}",
                json=resource,
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def _search(self, resource_type: str, params: Dict[str, str]) -> List[Dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base}/{resource_type}",
                params=params,
                headers=self._headers,
            )
            resp.raise_for_status()
            bundle = resp.json()
            return [e["resource"] for e in bundle.get("entry", [])]


class FHIRResourceNotFound(Exception):
    pass
