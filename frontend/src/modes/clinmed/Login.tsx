import { GraduationCap } from "lucide-react";
import { ConsumerLogin } from "@/components/ConsumerLogin";

export function ClinmedLogin() {
  return (
    <ConsumerLogin
      mode="clinmed"
      brand="Clinmed"
      icon={GraduationCap}
      emoji="📚"
      greeting="Train diagnostic reasoning the way real medicine feels — under time pressure, with noise and interruptions. Learn to think clearly anyway."
      roleOptions={[
        { label: "Medical student", value: "student" },
        { label: "Resident", value: "resident" },
        { label: "Practicing doctor", value: "doctor" },
        { label: "Educator", value: "educator" },
      ]}
    />
  );
}
