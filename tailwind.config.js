/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        panel: "#101a2c",
        panelAlt: "#152238",
        border: "#223252",
        accent: "#3fd0c9",
        warn: "#f5b942",
        critical: "#ef5959",
        good: "#5fd68e",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
