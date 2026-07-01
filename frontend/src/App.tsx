import { Routes, Route, Navigate } from "react-router-dom";
import { ThemeScope } from "./components/ThemeScope";
import { ModeSelector } from "./pages/ModeSelector";
import { RelayMedApp } from "./modes/relaymed/RelayMedApp";
import { ClinicoreApp } from "./modes/clinicore/ClinicoreApp";
import { ClinmedApp } from "./modes/clinmed/ClinmedApp";

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ThemeScope theme="landing">
            <ModeSelector />
          </ThemeScope>
        }
      />
      <Route
        path="/relaymed/*"
        element={
          <ThemeScope theme="relaymed">
            <RelayMedApp />
          </ThemeScope>
        }
      />
      <Route
        path="/clinicore/*"
        element={
          <ThemeScope theme="clinicore">
            <ClinicoreApp />
          </ThemeScope>
        }
      />
      <Route
        path="/clinmed/*"
        element={
          <ThemeScope theme="clinmed">
            <ClinmedApp />
          </ThemeScope>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
