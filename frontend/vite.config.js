import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = "http://127.0.0.1:8000";

function proxyApi() {
  return {
    target: apiTarget,
    bypass(req) {
      if (req.headers.accept?.includes("text/html")) return "/index.html";
    },
  };
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": proxyApi(),
      "/health": proxyApi(),
      "/media": proxyApi(),
    },
  },
});
