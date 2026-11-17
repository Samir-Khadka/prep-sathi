import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Unit tests only (jsdom). The app itself builds with vite.config.ts.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
