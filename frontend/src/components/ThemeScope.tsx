import { ReactNode, useEffect } from "react";

type Theme = "relaymed" | "clinicore" | "clinmed" | "landing";

/**
 * Applies a mode's design-token scope to <html> so the fixed-attachment
 * gradient background (set on body) also switches with the mode.
 */
export function ThemeScope({ theme, children }: { theme: Theme; children: ReactNode }) {
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    return () => {
      // leave last theme in place on unmount; next scope overwrites
    };
  }, [theme]);

  return <div data-theme={theme}>{children}</div>;
}
