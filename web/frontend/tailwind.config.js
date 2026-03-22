/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sts: {
          bg: "#1a1a2e",
          surface: "#16213e",
          card: "#1e2d4a",
          border: "#2a3a5c",
          gold: "#d4a843",
          "gold-light": "#f0d68a",
          "gold-dim": "#8a6d2b",
          amber: "#f59e0b",
          red: "#ef4444",
          green: "#22c55e",
          blue: "#3b82f6",
          purple: "#a855f7",
          text: "#e2e8f0",
          "text-dim": "#94a3b8",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
