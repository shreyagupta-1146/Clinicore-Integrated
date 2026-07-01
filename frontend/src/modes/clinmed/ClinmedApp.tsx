import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ClinmedLogin } from "./Login";
import { ClinmedLayout } from "./Layout";
import { LearnHome } from "./pages/LearnHome";
import { CaseLibrary } from "./pages/CaseLibrary";
import { Simulator } from "./pages/Simulator";
import { Progress } from "./pages/Progress";
import { Leaderboard } from "./pages/Leaderboard";
import { ReviewDeck } from "./pages/ReviewDeck";
import { Authoring } from "./pages/Authoring";
import { Modules } from "./pages/Modules";

export function ClinmedApp() {
  const { user } = useAuth();
  if (!user || user.mode !== "clinmed") return <ClinmedLogin />;

  return (
    <Routes>
      {/* Simulator runs full-screen (no chrome) for immersion */}
      <Route path="simulator/:id" element={<Simulator />} />
      <Route path="simulator" element={<Simulator />} />
      <Route
        path="*"
        element={
          <ClinmedLayout>
            <Routes>
              <Route index element={<LearnHome />} />
              <Route path="modules" element={<Modules />} />
              <Route path="cases" element={<CaseLibrary />} />
              <Route path="progress" element={<Progress />} />
              <Route path="leaderboard" element={<Leaderboard />} />
              <Route path="review" element={<ReviewDeck />} />
              <Route path="author" element={<Authoring />} />
              <Route path="*" element={<Navigate to="/clinmed" replace />} />
            </Routes>
          </ClinmedLayout>
        }
      />
    </Routes>
  );
}
