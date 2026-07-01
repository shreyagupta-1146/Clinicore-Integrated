/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
        serif: ["Lora", "ui-serif", "Georgia", "serif"],
        sans: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        clinical: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        // All colors resolve to CSS vars set per-theme (see index.css)
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: "var(--card)",
        primary: "var(--primary)",
        "primary-foreground": "var(--primary-foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        border: "var(--border)",
        success: "var(--success)",
        warning: "var(--warning)",
        destructive: "var(--destructive)",
        brand: "var(--brand)",
        "brand-2": "var(--brand-2)",
      },
      borderRadius: {
        xl: "var(--radius)",
        "2xl": "calc(var(--radius) + 4px)",
        "3xl": "calc(var(--radius) + 8px)",
      },
      keyframes: {
        floatY: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-6px)" } },
        fadeUp: { from: { opacity: "0", transform: "translateY(10px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        dashFlow: { to: { "stroke-dashoffset": "-120" } },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 var(--pulse-color)" },
          "70%": { boxShadow: "0 0 0 14px transparent" },
          "100%": { boxShadow: "0 0 0 0 transparent" },
        },
        shake: {
          "0%,100%": { transform: "translateX(0)" },
          "20%,60%": { transform: "translateX(-4px)" },
          "40%,80%": { transform: "translateX(4px)" },
        },
      },
      animation: {
        float: "floatY 6s ease-in-out infinite",
        "fade-in": "fadeUp 0.6s ease-out both",
        "pulse-ring": "pulseRing 2.4s ease-out infinite",
        shake: "shake 0.4s ease-in-out",
      },
    },
  },
  plugins: [],
};
