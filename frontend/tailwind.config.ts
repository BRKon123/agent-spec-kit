import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        border: "hsl(220 13% 91%)",
        ring: "hsl(220 13% 80%)",
        background: "hsl(0 0% 100%)",
        foreground: "hsl(220 13% 16%)",
        muted: "hsl(220 14% 96%)",
        "muted-foreground": "hsl(220 9% 46%)",
      },
    },
  },
  plugins: [],
} satisfies Config;
