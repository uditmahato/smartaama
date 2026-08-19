// frontend/playwright.config.ts
//
// Browser end-to-end tests (Chromium only). `npx playwright test` starts BOTH
// servers itself (see `webServer` below), seeds the first admin in
// e2e/global-setup.ts and then runs e2e/*.spec.ts against the real stack:
//
//   backend  : FastAPI + SQLite file  -> http://127.0.0.1:8000
//   frontend : Vite dev server        -> http://localhost:5173
//
// See e2e/README.md for prerequisites and environment variables.
import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  API_BASE,
  BACKEND_ENV,
  BACKEND_ORIGIN,
  FRONTEND_ORIGIN,
  FRONTEND_PORT,
} from "./e2e/env";

const frontendDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts$/,
  globalSetup: "./e2e/global-setup.ts",
  outputDir: "./test-results",

  timeout: 90_000,
  expect: { timeout: 15_000 },

  // Files run in parallel across workers; tests inside a file run in order.
  fullyParallel: false,
  workers: process.env.CI ? 1 : 2,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: Boolean(process.env.CI),

  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: FRONTEND_ORIGIN,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Wide enough that the admin DataGrid renders every column (incl. Actions).
        viewport: { width: 1400, height: 900 },
      },
    },
  ],

  webServer: [
    {
      // Deletes the previous e2e SQLite DB / uploads, then runs
      //   <E2E_PYTHON or python> -m uvicorn app.main:app --host 127.0.0.1 --port 8000
      // from ../backend with BACKEND_ENV (see e2e/env.ts).
      command: "node e2e/start-backend.mjs",
      cwd: frontendDir,
      url: `${BACKEND_ORIGIN}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      stdout: "ignore",
      stderr: "pipe",
      env: BACKEND_ENV,
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: frontendDir,
      url: `${FRONTEND_ORIGIN}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "ignore",
      stderr: "pipe",
      env: {
        VITE_API_BASE_URL: API_BASE,
      },
    },
  ],
});
