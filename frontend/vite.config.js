import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served from https://ray98872.github.io/swarm/ so the base must be /swarm/.
export default defineConfig({
  plugins: [react()],
  base: "/swarm/",
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
