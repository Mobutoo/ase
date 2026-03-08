/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Afrofuturist theme palette
        ase: {
          bg: "#0a0a14",
          surface: "#14142a",
          border: "#1e1e3f",
          gold: "#f59e0b",
          amber: "#d97706",
          accent: "#fbbf24",
          text: "#e2e8f0",
          muted: "#94a3b8",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
