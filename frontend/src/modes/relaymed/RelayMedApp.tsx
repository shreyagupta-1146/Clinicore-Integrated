import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { RelayLogin } from "./Login";
import { RelayLayout } from "./Layout";
import { Dashboard } from "./pages/Dashboard";
import { MyHealth } from "./pages/MyHealth";
import { Insights } from "./pages/Insights";
import { CausalPathways } from "./pages/CausalPathways";
import { Simulator } from "./pages/Simulator";
import { Alerts } from "./pages/Alerts";
import { RelayGuide } from "./pages/RelayGuide";
import { CaregiverHub } from "./pages/CaregiverHub";
import { Trust } from "./pages/Trust";
import { Settings } from "./pages/Settings";
import { Library } from "./pages/Library";
import { Reports } from "./pages/Reports";

export function RelayMedApp() {
  const { user } = useAuth();
  if (!user || user.mode !== "relaymed") return <RelayLogin />;

  return (
    <RelayLayout>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="my-health" element={<MyHealth />} />
        <Route path="insights" element={<Insights />} />
        <Route path="causal-pathways" element={<CausalPathways />} />
        <Route path="simulator" element={<Simulator />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="relay-guide" element={<RelayGuide />} />
        <Route path="caregivers" element={<CaregiverHub />} />
        <Route path="reports" element={<Reports />} />
        <Route path="library" element={<Library />} />
        <Route path="trust" element={<Trust />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/relaymed" replace />} />
      </Routes>
    </RelayLayout>
  );
}
