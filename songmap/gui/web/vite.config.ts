import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built into ../static, which the Python server serves. `npm run dev` proxies the API to the server.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // the code editor and React change rarely: their own chunks keep the app chunk small and cacheable
        manualChunks: (id) =>
          id.includes("node_modules/@codemirror") || id.includes("node_modules/@lezer") || id.includes("node_modules/codemirror")
            ? "editor" : id.includes("node_modules/react") ? "react" : undefined,
      },
    },
  },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
});
