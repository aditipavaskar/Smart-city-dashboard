import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Relative base path: works whether this is served from a domain root
  // (npm run dev, a custom domain) or a GitHub Pages project subpath like
  // https://<user>.github.io/<repo>/. Avoids hard-coding the repo name.
  base: "./",
  server: {
    port: 5173,
  },
});
