import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { AdminLogin } from "./Login";
import { ClinicoreLayout } from "./Layout";
import { Dashboard } from "./pages/Dashboard";
import { Roster } from "./pages/Roster";
import { Consultation } from "./pages/Consultation";
import { Folders } from "./pages/Folders";
import { Consent } from "./pages/Consent";
import { Audit } from "./pages/Audit";
import { ABDM } from "./pages/ABDM";
import { Admin } from "./pages/Admin";
import { SelfHealing } from "./pages/SelfHealing";

export function ClinicoreApp() {
  const { user } = useAuth();
  if (!user || user.mode !== "clinicore") return <AdminLogin />;

  return (
    <ClinicoreLayout>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="roster" element={<Roster />} />
        <Route path="consultation/:id" element={<Consultation />} />
        <Route path="consultation" element={<Consultation />} />
        <Route path="folders" element={<Folders />} />
        <Route path="consent" element={<Consent />} />
        <Route path="audit" element={<Audit />} />
        <Route path="abdm" element={<ABDM />} />
        <Route path="admin" element={<Admin />} />
        <Route path="self-healing" element={<SelfHealing />} />
        <Route path="*" element={<Navigate to="/clinicore" replace />} />
      </Routes>
    </ClinicoreLayout>
  );
}
