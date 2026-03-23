/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sts: {
          bg: "#132130",
          surface: "#183749",
          card: "#1e4259",
          border: "#2a5a6b",
          // Primary palette
          gold: "#F2F0C4",
          "gold-light": "#F8F6DC",
          "gold-dim": "#776754",
          amber: "#F2F0C4",
          red: "#8B1913",
          green: "#5aba7c",
          blue: "#6aaacc",
          purple: "#b09ac0",
          // Text
          text: "#F2F0C4",
          "text-dim": "#b8a88a",
          "text-muted": "#8a9aa2",
          // Accents
          slate: "#54626B",
          metallic: "#6A4F4C",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
