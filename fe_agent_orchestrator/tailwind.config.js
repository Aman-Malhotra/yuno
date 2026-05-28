/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Aeonik Fono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        mono: ['"Aeonik Fono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        display: ['"Aeonik Fono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        // Paper-warm light palette. Hierarchy is weight + color, not typeface.
        canvas: {
          DEFAULT: "#fafaf7", // page bg — warm off-white
          panel: "#ffffff", // primary card surface
          inset: "#f3f2ec", // sunken panel / terminal well
          rule: "#e5e4df", // hairline borders
          ruleStrong: "#cfcec7",
        },
        ink: {
          DEFAULT: "#14161d", // body text — near-black, slight blue
          dim: "#5b6072",
          mute: "#8a8e99",
          faint: "#b6b8c1",
        },
        sodium: {
          DEFAULT: "#c68922", // amber, deepened for light-bg contrast
          bright: "#f5b948",
          glow: "rgba(198, 137, 34, 0.18)",
          tint: "#fbf2dd",
        },
        signal: {
          ok: "#2f8a4e",
          warn: "#c68922",
          err: "#c44a36",
          idle: "#9aa0ad",
        },
      },
      letterSpacing: {
        eyebrow: "0.18em",
      },
      boxShadow: {
        panel: "0 1px 2px rgba(20,22,29,0.04), 0 0 0 1px #e5e4df",
        elev: "0 8px 24px -8px rgba(20,22,29,0.12), 0 0 0 1px #e5e4df",
      },
      animation: {
        "caret-blink": "caret-blink 1.1s steps(2, end) infinite",
        "fade-up": "fade-up 220ms ease-out both",
      },
      keyframes: {
        "caret-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
