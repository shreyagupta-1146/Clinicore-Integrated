/**
 * sre/console/src/App.tsx
 *
 * SOC/SRE Operations Console — built on weave-heal-main's React/TanStack UI
 * skeleton, but wired to REAL data instead of mock-mesh.ts hardcoded incidents.
 *
 * This component is intentionally read-only for display. Analyst actions
 * (acknowledge incident, approve containment) call the backend REST API
 * and require a second confirmation step. There are no "click to auto-block"
 * buttons — the HITL design is enforced in the UI, not just the backend.
 */

import React, { useEffect, useState } from "react";

interface Incident {
  incident_id: string;
  rule_id: string;
  severity: "info" | "low" | "medium" | "high" | "critical";
  title: string;
  description: string;
  actor_id?: string;
  source_ip?: string;
  detected_at: string;
  status: "pending_review" | "acknowledged" | "escalated_unacknowledged";
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#2563eb",
  info: "#6b7280",
};

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      style={{
        background: SEVERITY_COLORS[severity] || "#6b7280",
        color: "#fff",
        padding: "2px 8px",
        borderRadius: 4,
        fontWeight: 700,
        fontSize: 12,
        textTransform: "uppercase",
      }}
    >
      {severity}
    </span>
  );
}

function IncidentRow({
  incident,
  onAcknowledge,
}: {
  incident: Incident;
  onAcknowledge: (id: string) => void;
}) {
  const isPending = incident.status === "pending_review";
  const isEscalated = incident.status === "escalated_unacknowledged";

  return (
    <tr
      style={{
        borderBottom: "1px solid #e5e7eb",
        background: isEscalated ? "#fff1f2" : isPending ? "#fffbeb" : "white",
      }}
    >
      <td style={{ padding: "10px 12px" }}>
        <SeverityBadge severity={incident.severity} />
      </td>
      <td style={{ padding: "10px 12px", fontWeight: 600 }}>{incident.title}</td>
      <td style={{ padding: "10px 12px", color: "#6b7280", fontSize: 13 }}>
        {incident.rule_id}
      </td>
      <td style={{ padding: "10px 12px", fontSize: 13 }}>
        {incident.actor_id || incident.source_ip || "—"}
      </td>
      <td style={{ padding: "10px 12px", fontSize: 12, color: "#6b7280" }}>
        {new Date(incident.detected_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
      </td>
      <td style={{ padding: "10px 12px" }}>
        <span
          style={{
            fontSize: 12,
            color: isEscalated ? "#dc2626" : isPending ? "#d97706" : "#16a34a",
          }}
        >
          {isEscalated ? "Escalated" : isPending ? "Pending Review" : "Acknowledged"}
        </span>
      </td>
      <td style={{ padding: "10px 12px" }}>
        {isPending && (
          <button
            onClick={() => onAcknowledge(incident.incident_id)}
            style={{
              background: "#2563eb",
              color: "white",
              border: "none",
              padding: "4px 12px",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Acknowledge
          </button>
        )}
      </td>
    </tr>
  );
}

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");

  async function fetchIncidents() {
    try {
      // In production: GET /api/secops/incidents from the SecOps REST API
      // For now the endpoint reads from Redis incident queue
      const resp = await fetch("/api/secops/incidents");
      if (resp.ok) {
        setIncidents(await resp.json());
      }
    } catch (_) {
      // Backend not running in dev; show empty state
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 15_000);
    return () => clearInterval(interval);
  }, []);

  async function handleAcknowledge(incidentId: string) {
    const confirmed = window.confirm(
      `Mark incident ${incidentId} as reviewed?\n\n` +
        "This confirms you have investigated this finding. " +
        "To take a containment action, use the Containment panel."
    );
    if (!confirmed) return;
    await fetch(`/api/secops/incidents/${incidentId}/acknowledge`, { method: "POST" });
    fetchIncidents();
  }

  const filtered =
    filter === "all" ? incidents : incidents.filter((i) => i.severity === filter);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>
          Clinicore SecOps Console
        </h1>
        <span style={{ fontSize: 13, color: "#6b7280" }}>
          Auto-refreshes every 15 s · All times in IST
        </span>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {["all", "critical", "high", "medium", "low"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            style={{
              padding: "4px 14px",
              borderRadius: 4,
              border: "1px solid #d1d5db",
              background: filter === s ? "#1e40af" : "white",
              color: filter === s ? "white" : "#374151",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: filter === s ? 700 : 400,
            }}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <p>Loading incidents...</p>
      ) : filtered.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No incidents to display.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "#f9fafb", textAlign: "left" }}>
              <th style={{ padding: "8px 12px" }}>Severity</th>
              <th style={{ padding: "8px 12px" }}>Title</th>
              <th style={{ padding: "8px 12px" }}>Rule</th>
              <th style={{ padding: "8px 12px" }}>Actor / IP</th>
              <th style={{ padding: "8px 12px" }}>Detected (IST)</th>
              <th style={{ padding: "8px 12px" }}>Status</th>
              <th style={{ padding: "8px 12px" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((inc) => (
              <IncidentRow
                key={inc.incident_id}
                incident={inc}
                onAcknowledge={handleAcknowledge}
              />
            ))}
          </tbody>
        </table>
      )}

      <div
        style={{
          marginTop: 32,
          padding: 12,
          background: "#f0fdf4",
          borderLeft: "4px solid #16a34a",
          borderRadius: 4,
          fontSize: 13,
        }}
      >
        <strong>HITL Policy:</strong> Containment actions (session termination, account
        disable) require analyst confirmation and are logged to the immutable audit chain.
        No enforcement fires automatically.
      </div>
    </div>
  );
}
