/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ase: {
          bg: "#0a0a14",
          surface: "#14142a",
          "surface-2": "#1a1a36",
          border: "#1e1e3f",
          "border-2": "#2a2a4f",
          gold: "#f59e0b",
          amber: "#d97706",
          accent: "#fbbf24",
          text: "#e2e8f0",
          muted: "#94a3b8",
          subtle: "#64748b",
        },
        mode: {
          deep: "#8b5cf6",
          pomo: "#ef4444",
          kids: "#22c55e",
          sprint: "#eab308",
          flow: "#3b82f6",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 15px rgba(245, 158, 11, 0.1), 0 0 45px rgba(245, 158, 11, 0.05)",
        "glow-lg": "0 0 20px rgba(245, 158, 11, 0.2), 0 0 60px rgba(245, 158, 11, 0.1)",
        card: "0 4px 24px rgba(0, 0, 0, 0.2)",
        "card-hover": "0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(245, 158, 11, 0.08)",
      },
    },
  },
  plugins: [],
};
