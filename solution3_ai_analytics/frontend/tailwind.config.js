/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // App chrome — navy primary.
        navy: {
          DEFAULT: "#0F172A",
          900: "#0F172A",
          800: "#1E293B",
          700: "#334155",
        },
        // Interactive accent — teal family.
        teal: {
          DEFAULT: "#14B8A6",
          500: "#14B8A6",
          600: "#0D9488",
          400: "#2DD4BF",
        },
        // Status palette for ON TRACK / WATCH / AT RISK.
        status: {
          ontrack: "#22C55E",
          watch: "#F59E0B",
          atrisk: "#EF4444",
        },
      },
    },
  },
  plugins: [],
};
