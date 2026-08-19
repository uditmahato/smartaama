import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        // Long-lived vendor chunks (cached across deploys) separate from the
        // per-route page chunks created by React.lazy in App.tsx.
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-mui": ["@mui/material", "@emotion/react", "@emotion/styled"],
          "vendor-datagrid": ["@mui/x-data-grid"],
        },
      },
    },
  },
});
