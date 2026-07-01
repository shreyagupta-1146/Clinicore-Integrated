import { HeartPulse } from "lucide-react";
import { ConsumerLogin } from "@/components/ConsumerLogin";

export function RelayLogin() {
  return (
    <ConsumerLogin
      mode="relaymed"
      brand="RelayMed"
      icon={HeartPulse}
      emoji="🌿"
      greeting="Your calm, intelligent health companion — vitals, medications, and the people who care for you, all in one place."
    />
  );
}
