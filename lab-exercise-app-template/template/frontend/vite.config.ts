import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base (Addendum A §A1) so asset references are relative and resolve correctly
// under any mount prefix (e.g. /apps/<slug>/) without a rebuild. The frontend discovers its
// base path at runtime from the URL (see src/lib/basepath.ts). Dev serves from "/" and
// proxies the API to the local backend on port 8000.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "./" : "/",
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
}));
