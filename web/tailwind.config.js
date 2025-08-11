/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html","./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0E0E12",
        bone: "#F5F5F0",
        ash: "#1A1A22",
        fog: "#B9B9B3",
        gild: "#C2A75E",         // subtle gold accent
        alert: "#FA5A5A",
        limewire: "#59D3A2",     // cold emerald accent
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "ui-serif", "Georgia", "serif"],
        sans: ['Inter', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 8px 30px rgba(0,0,0,0.25)",
        soft: "0 4px 14px rgba(0,0,0,0.18)",
      },
      transitionTimingFunction: {
        seep: "cubic-bezier(.19,1,.22,1)"
      },
      backgroundImage: {
        grain: "url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4gPGZpbHRlciBpZD0ibm9pc2UiPiA8ZmVUdXJidWxlbmNlIHR5cGU9ImZyYWN0YWxOb2lzZSIgYmFzZUZyZXF1ZW5jeT0iMC45IiBudW1PY3RhdmVzPSI0IiBzdGl0Y2hUaWxlcz0ic3RpdGNoIi8+IDwvZmlsdGVyPiA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWx0ZXI9InVybCgjbm9pc2UpIiBvcGFjaXR5PSIwLjQiLz4gPC9zdmc+')",     // tiny noise svg
        grid: "radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "18px 18px",
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
