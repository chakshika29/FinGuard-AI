/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#f0f4fa",
          100: "#dce5f3",
          600: "#1e3a8a",
          700: "#172554",
          800: "#0f172a",
          900: "#0a1020",
        },
      },
    },
  },
  plugins: [],
};
