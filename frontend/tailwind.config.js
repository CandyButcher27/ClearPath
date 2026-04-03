/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      "colors": {
        "on-secondary-container": "#ed0e0eff",
        "tertiary": "#000000",
        "on-secondary-fixed": "#310001",
        "secondary-fixed-dim": "#ffb4ab",
        "outline-variant": "#d8c2bf",
        "primary": "#000000",
        "secondary-fixed": "#ffdad6",
        "primary-container": "#1c1b1b",
        "surface-container-high": "#f5f5f5",
        "tertiary-fixed": "#d4e3ff",
        "tertiary-fixed-dim": "#a7c8fc",
        "primary-fixed": "#e5e2e1",
        "on-primary-fixed": "#1c1b1b",
        "surface-dim": "#e0e0e0",
        "surface-container-low": "#ffffff",
        "error-container": "#ffdad6",
        "surface-tint": "#000000",
        "on-primary": "#ffffff",
        "inverse-primary": "#c8c6c5",
        "on-secondary": "#ffffff",
        "surface-container-highest": "#f0f0f0",
        "on-tertiary-container": "#6485b6",
        "on-surface-variant": "#444444",
        "inverse-on-surface": "#f1f1f1",
        "surface-bright": "#ffffff",
        "secondary": "#e90716",
        "on-primary-container": "#858383",
        "error": "#ba1a1a",
        "surface-container-lowest": "#ffffff",
        "on-primary-fixed-variant": "#474646",
        "secondary-container": "#e30613",
        "on-tertiary-fixed-variant": "#244874",
        "surface-variant": "#f0f0f0",
        "on-surface": "#000000",
        "on-tertiary-fixed": "#001c3a",
        "on-tertiary": "#ffffff",
        "surface-container": "#f8f8f8",
        "background": "#ffffff",
        "on-secondary-fixed-variant": "#93000a",
        "primary-fixed-dim": "#c8c6c5",
        "outline": "#797474",
        "inverse-surface": "#2f3131",
        "on-error": "#ffffff",
        "on-error-container": "#93000a",
        "on-background": "#000000",
        "surface": "#ffffff",
        "tertiary-container": "#001c3a"
      },
      "borderRadius": {
        "DEFAULT": "0px",
        "lg": "0px",
        "xl": "0px",
        "full": "9999px"
      },
      "fontFamily": {
        "headline": ["Inter", "sans-serif"],
        "body": ["Inter", "sans-serif"],
        "label": ["Inter", "sans-serif"]
      },
      "animation": {
        "fade-up": "fadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "pulse-accent": "pulseAccent 2s infinite",
        "status-ping": "statusPing 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "grid-flow": "gridFlow 20s linear infinite",
        "float": "float 6s ease-in-out infinite"
      },
      "keyframes": {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        pulseAccent: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(227, 6, 19, 0.4)" },
          "50%": { boxShadow: "0 0 0 15px rgba(227, 6, 19, 0)" }
        },
        statusPing: {
          "75%, 100%": { transform: "scale(2.5)", opacity: "0" }
        },
        gridFlow: {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "100px 100px" }
        },
        float: {
          "0%, 100%": { transform: "translateY(0) rotate(0deg)" },
          "50%": { transform: "translateY(-20px) rotate(5deg)" }
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}
