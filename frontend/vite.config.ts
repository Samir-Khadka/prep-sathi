import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// PrepSathi PWA — HashRouter on the client, so the static build works on
// any free static host (GitHub Pages, Vercel, Netlify) with no rewrites.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
